"""Tests targeting uncovered lines in controllers/simulation_controller.py.

Covers: 152-160, 172, 191-192, 207, 218, 348-349, 386-389, 416,
        483-484, 510, 527-530, 534-542, 553, 823-826, 837-839, 849-851.

All tests use mocked NgspiceRunner — no Qt imports.
"""

from unittest.mock import MagicMock, patch

from controllers.simulation_controller import SimulationController, SimulationResult
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from tests.conftest import make_simulation_controller


def _build_circuit(ctrl):
    """Add a V1-R1-GND circuit to the controller's model."""
    m = ctrl.model
    m.add_component(
        ComponentData(
            component_id="V1",
            component_type="Voltage Source",
            value="5V",
            position=(0, 0),
        )
    )
    m.add_component(ComponentData(component_id="R1", component_type="Resistor", value="1k", position=(100, 0)))
    m.add_component(
        ComponentData(
            component_id="GND1",
            component_type="Ground",
            value="0V",
            position=(100, 100),
        )
    )
    m.add_wire(
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="R1",
            end_terminal=0,
        )
    )
    m.add_wire(
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        )
    )
    m.add_wire(
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        )
    )


# ---- Lines 152-160: netlist generation error in run_simulation ----


class TestRunSimulationNetlistError:
    def test_netlist_generation_value_error(self):
        """Lines 152-160: ValueError during netlist generation returns failure."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = ValueError("bad param")
                result = ctrl.run_simulation()

        assert result.success is False
        assert "Netlist generation failed" in result.error
        assert "bad param" in result.error

    def test_netlist_generation_key_error(self):
        """Lines 152-160: KeyError during netlist generation returns failure."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = KeyError("missing_key")
                result = ctrl.run_simulation()

        assert result.success is False
        assert "Netlist generation failed" in result.error

    def test_netlist_generation_type_error(self):
        """Lines 152-160: TypeError during netlist generation returns failure."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = TypeError("wrong type")
                result = ctrl.run_simulation()

        assert result.success is False
        assert "Netlist generation failed" in result.error

    def test_netlist_error_notifies_circuit_ctrl(self):
        """Lines 158-159: circuit_ctrl notified on netlist failure."""
        cc = MagicMock()
        ctrl, runner = make_simulation_controller(circuit_ctrl=cc)
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = ValueError("fail")
                ctrl.run_simulation()

        cc._notify.assert_any_call("simulation_started", None)
        # Verify simulation_completed was also called
        calls = [c for c in cc._notify.call_args_list if c[0][0] == "simulation_completed"]
        assert len(calls) >= 1
        assert calls[-1][0][1].success is False


# ---- Line 172: notify when ngspice not found with circuit_ctrl ----


class TestNgspiceNotFoundNotify:
    def test_ngspice_not_found_notifies_circuit_ctrl(self):
        """Line 172: circuit_ctrl notified when ngspice not found."""
        cc = MagicMock()
        ctrl, runner = make_simulation_controller(circuit_ctrl=cc)
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")
        runner.find_ngspice.return_value = None

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                result = ctrl.run_simulation()

        assert result.success is False
        assert "ngspice" in result.error.lower()
        calls = [c for c in cc._notify.call_args_list if c[0][0] == "simulation_completed"]
        assert len(calls) >= 1


# ---- Lines 191-192: retry netlist generation fails ----


class TestRetryNetlistFails:
    def test_retry_netlist_generation_fails(self):
        """Lines 191-192: retry netlist generation raises exception, falls through."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        runner.run_simulation.return_value = (
            False,
            None,
            "",
            "Error: no convergence in DC operating point",
        )

        call_count = 0

        def netlist_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "* first netlist"
            raise ValueError("retry netlist failed")

        mock_diagnosis = MagicMock()
        mock_diagnosis.category = "dc_convergence"

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = netlist_side_effect
                with patch("simulation.convergence.diagnose_error", return_value=mock_diagnosis):
                    with patch(
                        "simulation.convergence.format_user_message",
                        return_value="Convergence error",
                    ):
                        with patch("simulation.convergence.is_retriable", return_value=True):
                            with patch(
                                "simulation.convergence.RELAXED_OPTIONS",
                                {"reltol": "0.01"},
                            ):
                                result = ctrl.run_simulation()

        assert result.success is False
        # Should show the friendly message, not the netlist error
        assert "Convergence error" in result.error


# ---- Line 207: notify circuit_ctrl after successful convergence retry ----


class TestRetrySuccessNotify:
    def test_convergence_retry_success_notifies_circuit_ctrl(self):
        """Line 207: circuit_ctrl notified after successful convergence retry."""
        cc = MagicMock()
        ctrl, runner = make_simulation_controller(circuit_ctrl=cc)
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        runner.run_simulation.side_effect = [
            (False, None, "", "Error: no convergence in DC operating point"),
            (True, "/tmp/out", "v(1) = 5.0", ""),
        ]
        runner.read_output.return_value = "v(1) = 5.000000e+00\n"

        mock_diagnosis = MagicMock()
        mock_diagnosis.category = "dc_convergence"

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.convergence.diagnose_error", return_value=mock_diagnosis):
                    with patch(
                        "simulation.convergence.format_user_message",
                        return_value="Convergence error",
                    ):
                        with patch("simulation.convergence.is_retriable", return_value=True):
                            with patch(
                                "simulation.convergence.RELAXED_OPTIONS",
                                {"reltol": "0.01"},
                            ):
                                with patch("simulation.ResultParser") as mock_rp:
                                    mock_rp.parse_op_results.return_value = {"V(1)": 5.0}
                                    mock_rp.parse_measurement_results.return_value = {}
                                    with patch(
                                        "simulation.result_parser.ResultParseError",
                                        Exception,
                                    ):
                                        result = ctrl.run_simulation()

        assert result.success is True
        calls = [c for c in cc._notify.call_args_list if c[0][0] == "simulation_completed"]
        assert len(calls) >= 1
        assert calls[-1][0][1].success is True


# ---- Line 218: notify circuit_ctrl on simulation failure ----


class TestSimFailureNotify:
    def test_simulation_failure_notifies_circuit_ctrl(self):
        """Line 218: circuit_ctrl notified on simulation failure (non-retriable)."""
        cc = MagicMock()
        ctrl, runner = make_simulation_controller(circuit_ctrl=cc)
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        runner.run_simulation.return_value = (False, None, "", "Error: singular matrix")

        mock_diagnosis = MagicMock()
        mock_diagnosis.category = "singular_matrix"

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.convergence.diagnose_error", return_value=mock_diagnosis):
                    with patch(
                        "simulation.convergence.format_user_message",
                        return_value="Singular matrix",
                    ):
                        with patch("simulation.convergence.is_retriable", return_value=False):
                            result = ctrl.run_simulation()

        assert result.success is False
        calls = [c for c in cc._notify.call_args_list if c[0][0] == "simulation_completed"]
        assert len(calls) >= 1


# ---- Line 332: parameter sweep component not found ----


class TestParameterSweepComponentNotFound:
    def test_sweep_component_not_found(self):
        """Line 332: component_id not in circuit returns failure."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        sweep_config = {
            "component_id": "MISSING",
            "start": 100.0,
            "stop": 1000.0,
            "num_steps": 2,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        result = ctrl.run_parameter_sweep(sweep_config)
        assert result.success is False
        assert "MISSING" in result.error
        assert "not found" in result.error


# ---- Lines 354-355: parameter sweep ngspice not found ----


class TestParameterSweepNgspiceNotFound:
    def test_sweep_ngspice_not_found(self):
        """Lines 354-355: ngspice not found restores analysis and returns failure."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("AC Sweep", {"fstart": "1", "fstop": "1Meg"})
        runner.find_ngspice.return_value = None

        sweep_config = {
            "component_id": "R1",
            "start": 100.0,
            "stop": 1000.0,
            "num_steps": 2,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            result = ctrl.run_parameter_sweep(sweep_config)

        assert result.success is False
        assert "ngspice" in result.error.lower()
        # Original analysis restored
        assert ctrl.model.analysis_type == "AC Sweep"


# ---- Lines 375-376: parameter sweep cancellation ----


class TestParameterSweepCancellation:
    def test_sweep_cancelled_by_callback(self):
        """Lines 375-376: progress_callback returning False cancels sweep."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        sweep_config = {
            "component_id": "R1",
            "start": 100.0,
            "stop": 1000.0,
            "num_steps": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            result = ctrl.run_parameter_sweep(sweep_config, progress_callback=lambda i, t: False)

        assert result.data["cancelled"] is True
        assert result.data["num_steps"] == 0


# ---- Lines 394-403: parameter sweep sim failure at step ----


class TestParameterSweepSimFailure:
    def test_sweep_step_sim_failure(self):
        """Lines 394-403: simulation failure at a sweep step records error."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        sweep_config = {
            "component_id": "R1",
            "start": 100.0,
            "stop": 1000.0,
            "num_steps": 1,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        runner.run_simulation.return_value = (False, None, "stdout", "sim failed")

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                result = ctrl.run_parameter_sweep(sweep_config)

        assert result.success is False
        assert any("sim failed" in e for e in result.errors)


# ---- Lines 348-349: parameter sweep validation failure restores analysis ----


class TestParameterSweepValidationFailure:
    def test_sweep_validation_failure_restores_analysis(self):
        """Lines 348-349: validation failure restores original analysis type."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("AC Sweep", {"fstart": "1", "fstop": "1Meg"})

        sweep_config = {
            "component_id": "R1",
            "start": 100.0,
            "stop": 10000.0,
            "num_steps": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        with patch("simulation.validate_circuit", return_value=(False, ["No ground"], [])):
            result = ctrl.run_parameter_sweep(sweep_config)

        assert result.success is False
        # Original analysis should be restored
        assert ctrl.model.analysis_type == "AC Sweep"
        assert ctrl.model.analysis_params["fstart"] == "1"


# ---- Lines 386-389: parameter sweep netlist generation failure at step ----


class TestParameterSweepNetlistFailure:
    def test_sweep_step_netlist_failure(self):
        """Lines 386-389: netlist generation failure at a sweep step."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        sweep_config = {
            "component_id": "R1",
            "start": 100.0,
            "stop": 1000.0,
            "num_steps": 2,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = ValueError("bad netlist")
                result = ctrl.run_parameter_sweep(sweep_config)

        assert result.success is False
        assert any("netlist failed" in e for e in result.errors)


# ---- Line 416: parameter sweep parse result failure error recording ----


class TestParameterSweepParseFailure:
    def test_sweep_step_parse_failure_records_error(self):
        """Line 416: parse result failure at a sweep step records error."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        sweep_config = {
            "component_id": "R1",
            "start": 100.0,
            "stop": 1000.0,
            "num_steps": 1,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }

        runner.run_simulation.return_value = (True, "/tmp/out", "stdout", "")
        runner.read_output.return_value = "output data"

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.ResultParser") as mock_rp:
                    mock_rp.parse_op_results.side_effect = ValueError("bad parse")
                    with patch("simulation.result_parser.ResultParseError", ValueError):
                        result = ctrl.run_parameter_sweep(sweep_config)

        assert any("Step 1" in e for e in result.errors)


# ---- Lines 483-484: Monte Carlo validation failure restores analysis ----


class TestMonteCarloValidationFailure:
    def test_mc_validation_failure_restores_analysis(self):
        """Lines 483-484: validation failure restores original analysis type."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("AC Sweep", {"fstart": "1", "fstop": "1Meg"})

        mc_config = {
            "num_runs": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        with patch("simulation.validate_circuit", return_value=(False, ["No ground"], [])):
            result = ctrl.run_monte_carlo(mc_config)

        assert result.success is False
        assert ctrl.model.analysis_type == "AC Sweep"
        assert ctrl.model.analysis_params["fstart"] == "1"


# ---- Lines 488-489: Monte Carlo ngspice not found ----


class TestMonteCarloNgspiceNotFound:
    def test_mc_ngspice_not_found(self):
        """Lines 488-489: ngspice not found restores analysis and returns failure."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("AC Sweep", {"fstart": "1", "fstop": "1Meg"})
        runner.find_ngspice.return_value = None

        mc_config = {
            "num_runs": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            result = ctrl.run_monte_carlo(mc_config)

        assert result.success is False
        assert "ngspice" in result.error.lower()
        assert ctrl.model.analysis_type == "AC Sweep"


# ---- Lines 503-504: Monte Carlo cancellation ----


class TestMonteCarloCancellation:
    def test_mc_cancelled_by_callback(self):
        """Lines 503-504: progress_callback returning False cancels MC."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        mc_config = {
            "num_runs": 5,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            result = ctrl.run_monte_carlo(mc_config, progress_callback=lambda i, t: False)

        assert result.data["cancelled"] is True
        assert result.data["num_runs"] == 0


# ---- Line 510: Monte Carlo component None guard ----


class TestMonteCarloComponentNone:
    def test_mc_component_removed_during_run(self):
        """Line 510: component removed between validation and inner loop.

        R1 passes the invalid_ids filter (line 467) and original_values (line 473),
        then the progress_callback removes it so components.get returns None at line 508.
        """
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        mc_config = {
            "num_runs": 1,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        runner.run_simulation.return_value = (True, "/tmp/out", "stdout", "")
        runner.read_output.return_value = "v(1) = 5.0"

        def remove_r1_callback(i, total):
            """Remove R1 before the inner tolerance loop runs."""
            ctrl.model.components.pop("R1", None)
            return True

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.ResultParser") as mock_rp:
                    mock_rp.parse_op_results.return_value = {"V(1)": 5.0}
                    mock_rp.parse_measurement_results.return_value = {}
                    with patch("simulation.result_parser.ResultParseError", Exception):
                        result = ctrl.run_monte_carlo(mc_config, progress_callback=remove_r1_callback)

        assert result.success is True


# ---- Lines 527-530: Monte Carlo netlist generation failure ----


class TestMonteCarloNetlistFailure:
    def test_mc_step_netlist_failure(self):
        """Lines 527-530: netlist generation failure at a Monte Carlo step."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        mc_config = {
            "num_runs": 2,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.side_effect = ValueError("bad mc netlist")
                with patch("simulation.monte_carlo.apply_tolerance", return_value="1.1k"):
                    result = ctrl.run_monte_carlo(mc_config)

        assert result.success is False
        assert any("netlist failed" in e for e in result.errors)


# ---- Lines 534-542: Monte Carlo simulation failure at step ----


class TestMonteCarloSimFailure:
    def test_mc_step_simulation_failure(self):
        """Lines 534-542: simulation fails at a Monte Carlo step."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        mc_config = {
            "num_runs": 1,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        runner.run_simulation.return_value = (False, None, "stdout", "sim error")

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.monte_carlo.apply_tolerance", return_value="1.1k"):
                    result = ctrl.run_monte_carlo(mc_config)

        assert result.success is False
        assert any("sim error" in e for e in result.errors)


# ---- Line 553: Monte Carlo parse result failure error recording ----


class TestMonteCarloParseFailure:
    def test_mc_step_parse_failure_records_error(self):
        """Line 553: parse result failure in MC step records error."""
        ctrl, runner = make_simulation_controller()
        _build_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")

        mc_config = {
            "num_runs": 1,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {"R1": {"tolerance_pct": 10, "distribution": "gaussian"}},
        }

        runner.run_simulation.return_value = (True, "/tmp/out", "stdout", "")
        runner.read_output.return_value = "bad data"

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.monte_carlo.apply_tolerance", return_value="1.1k"):
                    with patch("simulation.ResultParser") as mock_rp:
                        mock_rp.parse_op_results.side_effect = ValueError("parse fail")
                        with patch("simulation.result_parser.ResultParseError", ValueError):
                            result = ctrl.run_monte_carlo(mc_config)

        assert any("Run 1" in e for e in result.errors)


# ---- Lines 823-826: generate_circuitikz ----


class TestGenerateCircuitikz:
    def test_generate_circuitikz(self):
        """Lines 823-826: generate_circuitikz delegates to exporter."""
        ctrl, _ = make_simulation_controller()
        _build_circuit(ctrl)

        with patch(
            "simulation.circuitikz_exporter.generate",
            return_value="\\begin{circuitikz}...",
        ):
            result = ctrl.generate_circuitikz()

        assert result == "\\begin{circuitikz}..."


# ---- Lines 837-839: suggest_bundle_name ----


class TestSuggestBundleName:
    def test_suggest_bundle_name(self):
        """Lines 837-839: suggest_bundle_name delegates to bundle_exporter."""
        with patch(
            "simulation.bundle_exporter.suggest_bundle_name",
            return_value="my_circuit_bundle.zip",
        ):
            result = SimulationController.suggest_bundle_name("my_circuit")

        assert result == "my_circuit_bundle.zip"


# ---- Lines 849-851: create_bundle ----


class TestCreateBundle:
    def test_create_bundle(self):
        """Lines 849-851: create_bundle delegates to bundle_exporter."""
        with patch("simulation.bundle_exporter.create_bundle", return_value="/tmp/bundle.zip") as mock_cb:
            result = SimulationController.create_bundle("/tmp/bundle.zip", circuit_json="{}", netlist="* net")

        assert result == "/tmp/bundle.zip"
        mock_cb.assert_called_once_with("/tmp/bundle.zip", circuit_json="{}", netlist="* net")


# ---- Lines 657-659: lazy preset_manager initialization ----


class TestPresetManagerLazyInit:
    def test_preset_manager_creates_instance(self):
        """Lines 657-659: preset_manager lazy-creates PresetManager."""
        ctrl, _ = make_simulation_controller()
        assert ctrl._preset_manager is None
        with patch("simulation.preset_manager.PresetManager") as mock_pm_cls:
            mock_pm_cls.return_value = MagicMock()
            pm = ctrl.preset_manager
            assert pm is mock_pm_cls.return_value


# ---- Lines 690-722: static metadata methods ----


class TestMetadataStaticMethods:
    def test_get_analysis_domain_map(self):
        """Lines 690-692: get_analysis_domain_map returns mapping."""
        with patch(
            "simulation.measurement_builder.ANALYSIS_DOMAIN_MAP",
            {"DC Operating Point": "dc"},
        ):
            result = SimulationController.get_analysis_domain_map()
            assert "DC Operating Point" in result

    def test_get_meas_types(self):
        """Lines 697-699: get_meas_types returns type definitions."""
        with patch("simulation.measurement_builder.MEAS_TYPES", {"max": "MAX"}):
            result = SimulationController.get_meas_types()
            assert "max" in result

    def test_build_meas_directive(self):
        """Lines 704-706: build_meas_directive delegates correctly."""
        with patch(
            "simulation.measurement_builder.build_directive",
            return_value=".meas tran v_max MAX v(1)",
        ):
            result = SimulationController.build_meas_directive("tran", "v_max", "MAX", {"signal": "v(1)"})
            assert ".meas" in result

    def test_get_mc_eligible_types(self):
        """Lines 713-715: get_mc_eligible_types returns set."""
        with patch(
            "simulation.monte_carlo.MC_ELIGIBLE_TYPES",
            {"Resistor", "Capacitor"},
        ):
            result = SimulationController.get_mc_eligible_types()
            assert "Resistor" in result

    def test_get_mc_default_tolerance(self):
        """Lines 720-722: get_mc_default_tolerance returns default."""
        with patch(
            "simulation.monte_carlo.DEFAULT_TOLERANCES",
            {"Resistor": 5.0, "Capacitor": 20.0},
        ):
            assert SimulationController.get_mc_default_tolerance("Resistor") == 5.0
            assert SimulationController.get_mc_default_tolerance("Inductor") == 5.0
