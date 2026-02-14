"""Tests for Monte Carlo simulation module and controller integration."""

from unittest.mock import MagicMock

import numpy as np
import pytest
from controllers.simulation_controller import (SimulationController,
                                               SimulationResult)
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from simulation.monte_carlo import (DEFAULT_TOLERANCES, MC_ELIGIBLE_TYPES,
                                    apply_tolerance, compute_mc_statistics,
                                    format_spice_value, parse_spice_value)


class TestParseSpiceValue:
    def test_plain_number(self):
        assert parse_spice_value("100") == 100.0

    def test_kilo(self):
        assert parse_spice_value("1k") == 1000.0

    def test_mega(self):
        assert parse_spice_value("4.7MEG") == pytest.approx(4.7e6)

    def test_nano(self):
        assert parse_spice_value("100n") == pytest.approx(100e-9)

    def test_micro(self):
        assert parse_spice_value("10u") == pytest.approx(10e-6)

    def test_pico(self):
        assert parse_spice_value("22p") == pytest.approx(22e-12)

    def test_with_unit_suffix(self):
        assert parse_spice_value("5V") == 5.0

    def test_empty_string(self):
        assert parse_spice_value("") is None

    def test_unparseable(self):
        assert parse_spice_value("SIN(0 5 1k)") is None


class TestFormatSpiceValue:
    def test_zero(self):
        assert format_spice_value(0) == "0"

    def test_kilo(self):
        assert format_spice_value(1000) == "1k"

    def test_mega(self):
        assert format_spice_value(1e6) == "1MEG"

    def test_fractional_kilo(self):
        assert format_spice_value(4700) == "4.7k"

    def test_micro(self):
        assert format_spice_value(1e-6) == "1u"


class TestApplyTolerance:
    def test_gaussian_varies_value(self):
        rng = np.random.default_rng(42)
        results = [apply_tolerance("1k", 5.0, "gaussian", rng) for _ in range(100)]
        # All should produce different strings (highly likely with 100 runs)
        unique = set(results)
        assert len(unique) > 1

    def test_uniform_varies_value(self):
        rng = np.random.default_rng(42)
        results = [apply_tolerance("1k", 10.0, "uniform", rng) for _ in range(100)]
        unique = set(results)
        assert len(unique) > 1

    def test_zero_tolerance_returns_same(self):
        rng = np.random.default_rng(42)
        result = apply_tolerance("1k", 0.0, "gaussian", rng)
        # 0% tolerance → 0 sigma → no variation
        assert parse_spice_value(result) == pytest.approx(1000.0)

    def test_unparseable_returns_original(self):
        rng = np.random.default_rng(42)
        result = apply_tolerance("SIN(0 5 1k)", 5.0, "gaussian", rng)
        assert result == "SIN(0 5 1k)"

    def test_values_within_expected_range(self):
        """Gaussian with 5% tolerance: 99.7% within ±5%."""
        rng = np.random.default_rng(42)
        base = 1000.0
        results = []
        for _ in range(1000):
            val_str = apply_tolerance("1k", 5.0, "gaussian", rng)
            val = parse_spice_value(val_str)
            results.append(val)
        arr = np.array(results)
        # Mean should be close to 1000
        assert np.mean(arr) == pytest.approx(base, rel=0.02)
        # Std should be roughly 5%/3 ≈ 1.67% of base
        assert np.std(arr) < base * 0.05


class TestComputeMcStatistics:
    def test_basic_statistics(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = compute_mc_statistics(values)
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["min"] == pytest.approx(1.0)
        assert stats["max"] == pytest.approx(5.0)
        assert stats["median"] == pytest.approx(3.0)
        assert stats["count"] == 5
        assert stats["std"] > 0

    def test_single_value(self):
        stats = compute_mc_statistics([42.0])
        assert stats["mean"] == pytest.approx(42.0)
        assert stats["std"] == pytest.approx(0.0)
        assert stats["count"] == 1


class TestEligibleTypes:
    def test_resistor_eligible(self):
        assert "Resistor" in MC_ELIGIBLE_TYPES

    def test_capacitor_eligible(self):
        assert "Capacitor" in MC_ELIGIBLE_TYPES

    def test_ground_not_eligible(self):
        assert "Ground" not in MC_ELIGIBLE_TYPES

    def test_default_tolerances(self):
        assert DEFAULT_TOLERANCES["Resistor"] == 5.0
        assert DEFAULT_TOLERANCES["Capacitor"] == 10.0


def _build_simple_circuit():
    """Build a simple V1-R1-GND circuit model."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5V",
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 0.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
    )
    model.wires = [
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="R1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="GND1",
            end_terminal=0,
        ),
    ]
    model.analysis_type = "DC Operating Point"
    model.rebuild_nodes()
    return model


class TestMonteCarloController:
    def _make_ctrl_with_mock_runner(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "/tmp/sim_output"
        mock_runner.run_simulation.return_value = (
            True,
            "/tmp/output.txt",
            "stdout",
            "",
        )
        mock_runner.read_output.return_value = (
            "Node                      Voltage\n"
            "----                      -------\n"
            "nodea                     5.000000e+00\n"
        )
        ctrl._runner = mock_runner
        return ctrl, mock_runner

    def test_monte_carlo_runs_correct_number(self):
        ctrl, mock_runner = self._make_ctrl_with_mock_runner()
        config = {
            "num_runs": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 5.0, "distribution": "gaussian"}},
        }
        result = ctrl.run_monte_carlo(config)
        assert result.success
        assert result.analysis_type == "Monte Carlo"
        assert mock_runner.run_simulation.call_count == 5

    def test_monte_carlo_restores_original_values(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        original_value = ctrl.model.components["R1"].value
        config = {
            "num_runs": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 10.0, "distribution": "uniform"}},
        }
        ctrl.run_monte_carlo(config)
        assert ctrl.model.components["R1"].value == original_value

    def test_monte_carlo_restores_analysis_type(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        ctrl.set_analysis("Transient", {"duration": 0.01, "step": 0.001})
        config = {
            "num_runs": 2,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 5.0, "distribution": "gaussian"}},
        }
        ctrl.run_monte_carlo(config)
        assert ctrl.model.analysis_type == "Transient"

    def test_monte_carlo_data_structure(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        config = {
            "num_runs": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 5.0, "distribution": "gaussian"}},
        }
        result = ctrl.run_monte_carlo(config)
        data = result.data
        assert data["num_runs"] == 3
        assert data["base_analysis_type"] == "DC Operating Point"
        assert len(data["results"]) == 3
        assert len(data["run_values"]) == 3
        assert data["cancelled"] is False

    def test_monte_carlo_with_cancellation(self):
        ctrl, mock_runner = self._make_ctrl_with_mock_runner()
        call_count = [0]

        def progress_cb(step, total):
            call_count[0] += 1
            return call_count[0] <= 2

        config = {
            "num_runs": 10,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 5.0, "distribution": "gaussian"}},
        }
        result = ctrl.run_monte_carlo(config, progress_callback=progress_cb)
        assert result.data["cancelled"] is True
        assert len(result.data["results"]) < 10

    def test_monte_carlo_no_ngspice(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = None
        mock_runner.output_dir = "/tmp/sim_output"
        ctrl._runner = mock_runner

        config = {
            "num_runs": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 5.0, "distribution": "gaussian"}},
        }
        result = ctrl.run_monte_carlo(config)
        assert not result.success
        assert "ngspice" in result.error.lower()

    def test_monte_carlo_run_values_varied(self):
        """Verify that component values are actually varied between runs."""
        ctrl, _ = self._make_ctrl_with_mock_runner()
        config = {
            "num_runs": 10,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
            "tolerances": {"R1": {"tolerance_pct": 10.0, "distribution": "uniform"}},
        }
        result = ctrl.run_monte_carlo(config)
        r1_values = [rv.get("R1", "") for rv in result.data["run_values"]]
        # With 10% tolerance and 10 runs, we should get variety
        assert len(set(r1_values)) > 1


class TestNoQtInMonteCarloModule:
    """Verify that the monte_carlo module has no Qt dependencies."""

    def test_no_pyqt_imports(self):
        import simulation.monte_carlo as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source


class TestSpiceValueConsolidation:
    """Verify _format_sweep_value delegates to format_spice_value."""

    def test_sweep_value_matches_spice_format(self):
        """_format_sweep_value must produce identical output to format_spice_value."""
        test_values = [0, 1, 1000, 4700, 1e6, 1e-3, 1e-6, 1e-9, 1e-12, 47e3, -5.0]
        for val in test_values:
            sweep = SimulationController._format_sweep_value(val)
            spice = format_spice_value(val)
            assert sweep == spice, f"Mismatch for {val}: {sweep!r} != {spice!r}"

    def test_parse_format_roundtrip(self):
        """parse_spice_value(format_spice_value(x)) ≈ x for common values."""
        test_values = [100, 1e3, 4.7e3, 1e6, 1e-3, 1e-6, 100e-9, 22e-12]
        for val in test_values:
            formatted = format_spice_value(val)
            parsed = parse_spice_value(formatted)
            assert parsed == pytest.approx(
                val
            ), f"Round-trip failed: {val} -> {formatted!r} -> {parsed}"

    def test_negative_values(self):
        """Negative values should format with a minus sign."""
        assert format_spice_value(-1000) == "-1k"
        assert parse_spice_value("-1k") == -1000.0

    def test_very_small_values(self):
        """Values smaller than femto should use scientific notation."""
        result = format_spice_value(1e-18)
        assert "e" in result.lower() or result == "0.001f"

    def test_very_large_values(self):
        """Tera prefix for large values."""
        assert format_spice_value(1e12) == "1T"
        assert parse_spice_value("1T") == 1e12

    def test_parse_case_insensitive_k(self):
        """Both k and K should be recognized as kilo."""
        assert parse_spice_value("1K") == 1000.0
        assert parse_spice_value("1k") == 1000.0

    def test_parse_meg_case_insensitive(self):
        """Both MEG and meg should be recognized."""
        assert parse_spice_value("4.7MEG") == pytest.approx(4.7e6)
        assert parse_spice_value("4.7meg") == pytest.approx(4.7e6)
