"""Tests for parameter sweep functionality."""

from unittest.mock import MagicMock, patch

import pytest
from controllers.simulation_controller import SimulationController, SimulationResult
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData


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
        WireData(start_component_id="V1", start_terminal=1, end_component_id="R1", end_terminal=0),
        WireData(start_component_id="R1", start_terminal=1, end_component_id="GND1", end_terminal=0),
        WireData(start_component_id="V1", start_terminal=0, end_component_id="GND1", end_terminal=0),
    ]
    model.analysis_type = "DC Operating Point"
    model.rebuild_nodes()
    return model


class TestFormatSweepValue:
    """Test the _format_sweep_value static method."""

    def test_zero(self):
        assert SimulationController._format_sweep_value(0) == "0"

    def test_integer_kilo(self):
        assert SimulationController._format_sweep_value(1000) == "1k"

    def test_fractional_kilo(self):
        assert SimulationController._format_sweep_value(1500) == "1.5k"

    def test_mega(self):
        assert SimulationController._format_sweep_value(1e6) == "1MEG"

    def test_milli(self):
        assert SimulationController._format_sweep_value(0.001) == "1m"

    def test_micro(self):
        assert SimulationController._format_sweep_value(1e-6) == "1u"

    def test_nano(self):
        assert SimulationController._format_sweep_value(1e-9) == "1n"

    def test_pico(self):
        assert SimulationController._format_sweep_value(1e-12) == "1p"

    def test_plain_number(self):
        assert SimulationController._format_sweep_value(100) == "100"

    def test_giga(self):
        assert SimulationController._format_sweep_value(1e9) == "1G"

    def test_negative_value(self):
        result = SimulationController._format_sweep_value(-5)
        assert result == "-5"

    def test_small_fractional(self):
        result = SimulationController._format_sweep_value(4.7e3)
        assert result == "4.7k"


class TestParameterSweepMissingComponent:
    """Test sweep when component doesn't exist."""

    def test_missing_component_returns_error(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)

        config = {
            "component_id": "R99",
            "start": 1000,
            "stop": 10000,
            "num_steps": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        assert not result.success
        assert "R99" in result.error


class TestParameterSweepValidation:
    """Test that sweep validates the circuit first."""

    def test_sweep_fails_on_invalid_circuit(self):
        ctrl = SimulationController()  # empty model
        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 10000,
            "num_steps": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        assert not result.success


class TestParameterSweepNgspiceNotFound:
    """Test sweep when ngspice is not available."""

    def test_sweep_fails_without_ngspice(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = None
        mock_runner.output_dir = "simulation_output"
        ctrl._runner = mock_runner

        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 10000,
            "num_steps": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        assert not result.success
        assert "ngspice" in result.error.lower()


class TestParameterSweepExecution:
    """Test the parameter sweep execution flow with mocked ngspice."""

    def _make_ctrl_with_mock_runner(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "/tmp/sim_output"
        mock_runner.run_simulation.return_value = (True, "/tmp/output.txt", "stdout", "")
        mock_runner.read_output.return_value = (
            "Node                      Voltage\n"
            "----                      -------\n"
            "nodea                     5.000000e+00\n"
        )
        ctrl._runner = mock_runner
        return ctrl, mock_runner

    def test_sweep_runs_correct_number_of_steps(self):
        ctrl, mock_runner = self._make_ctrl_with_mock_runner()
        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 10000,
            "num_steps": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        assert result.success
        assert result.analysis_type == "Parameter Sweep"
        assert mock_runner.run_simulation.call_count == 5

    def test_sweep_restores_original_value(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        original_value = ctrl.model.components["R1"].value
        config = {
            "component_id": "R1",
            "start": 500,
            "stop": 5000,
            "num_steps": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        ctrl.run_parameter_sweep(config)
        assert ctrl.model.components["R1"].value == original_value

    def test_sweep_restores_original_analysis(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        ctrl.set_analysis("Transient", {"duration": 0.01, "step": 0.001})
        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 5000,
            "num_steps": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        ctrl.run_parameter_sweep(config)
        assert ctrl.model.analysis_type == "Transient"

    def test_sweep_data_structure(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 5000,
            "num_steps": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        data = result.data
        assert data["component_id"] == "R1"
        assert data["component_type"] == "Resistor"
        assert data["base_analysis_type"] == "DC Operating Point"
        assert len(data["sweep_values"]) == 3
        assert len(data["results"]) == 3
        assert data["sweep_values"][0] == 1000
        assert data["sweep_values"][-1] == 5000

    def test_sweep_with_cancellation(self):
        ctrl, mock_runner = self._make_ctrl_with_mock_runner()
        cancel_after = 2
        call_count = [0]

        def progress_cb(step, total):
            call_count[0] += 1
            return call_count[0] <= cancel_after

        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 10000,
            "num_steps": 10,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config, progress_callback=progress_cb)
        # Should have run fewer steps than total
        assert result.data["cancelled"] is True
        assert len(result.data["results"]) < 10

    def test_sweep_handles_step_failure(self):
        ctrl, mock_runner = self._make_ctrl_with_mock_runner()
        # Fail on second call
        mock_runner.run_simulation.side_effect = [
            (True, "/tmp/output.txt", "stdout", ""),
            (False, None, "", "ngspice error"),
            (True, "/tmp/output.txt", "stdout", ""),
        ]
        config = {
            "component_id": "R1",
            "start": 1000,
            "stop": 3000,
            "num_steps": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        # Should still succeed (at least one step succeeded)
        assert result.success
        assert len(result.errors) == 1
        assert len(result.data["results"]) == 3

    def test_sweep_values_are_linearly_spaced(self):
        ctrl, _ = self._make_ctrl_with_mock_runner()
        config = {
            "component_id": "R1",
            "start": 100,
            "stop": 500,
            "num_steps": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {"analysis_type": "DC Operating Point"},
        }
        result = ctrl.run_parameter_sweep(config)
        values = result.data["sweep_values"]
        assert values == [100, 200, 300, 400, 500]


class TestSweepableComponentTypes:
    """Test that the dialog correctly identifies sweepable components."""

    def test_sweepable_types_list(self):
        from GUI.parameter_sweep_dialog import SWEEPABLE_TYPES

        assert "Resistor" in SWEEPABLE_TYPES
        assert "Capacitor" in SWEEPABLE_TYPES
        assert "Inductor" in SWEEPABLE_TYPES
        assert "Voltage Source" in SWEEPABLE_TYPES
        assert "Current Source" in SWEEPABLE_TYPES
        assert "Ground" not in SWEEPABLE_TYPES
        assert "Op-Amp" not in SWEEPABLE_TYPES
        assert "Waveform Source" not in SWEEPABLE_TYPES

    def test_base_analysis_types(self):
        from GUI.parameter_sweep_dialog import BASE_ANALYSIS_TYPES

        assert "DC Operating Point" in BASE_ANALYSIS_TYPES
        assert "Transient" in BASE_ANALYSIS_TYPES
        assert "AC Sweep" in BASE_ANALYSIS_TYPES
        assert "DC Sweep" in BASE_ANALYSIS_TYPES


class TestNoQtDependenciesInController:
    """Verify the controller still has no Qt imports after adding parameter sweep."""

    def test_no_pyqt_imports(self):
        import controllers.simulation_controller as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
