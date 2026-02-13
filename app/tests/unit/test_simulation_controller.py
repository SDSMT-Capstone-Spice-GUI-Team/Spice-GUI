"""Tests for SimulationController."""

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


class TestSetAnalysis:
    def test_set_analysis_updates_model(self):
        ctrl = SimulationController()
        ctrl.set_analysis("DC Sweep", {"min": "0", "max": "10", "step": "1"})
        assert ctrl.model.analysis_type == "DC Sweep"
        assert ctrl.model.analysis_params["max"] == "10"

    def test_set_analysis_copies_params(self):
        ctrl = SimulationController()
        params = {"min": "0"}
        ctrl.set_analysis("DC Sweep", params)
        params["min"] = "999"
        assert ctrl.model.analysis_params["min"] == "0"


class TestValidation:
    def test_valid_circuit_passes(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        result = ctrl.validate_circuit()
        assert result.success

    def test_empty_circuit_fails(self):
        ctrl = SimulationController()
        ctrl.set_analysis("DC Operating Point")
        result = ctrl.validate_circuit()
        assert not result.success
        assert len(result.errors) > 0

    def test_no_ground_fails(self):
        model = CircuitModel()
        model.components["R1"] = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0.0, 0.0),
        )
        model.components["V1"] = ComponentData(
            component_id="V1",
            component_type="Voltage Source",
            value="5V",
            position=(100.0, 0.0),
        )
        model.wires = [
            WireData(
                start_component_id="R1",
                start_terminal=1,
                end_component_id="V1",
                end_terminal=0,
            ),
        ]
        model.analysis_type = "DC Operating Point"
        model.rebuild_nodes()
        ctrl = SimulationController(model)
        result = ctrl.validate_circuit()
        assert not result.success


class TestGenerateNetlist:
    def test_generates_netlist_string(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        netlist = ctrl.generate_netlist()
        assert isinstance(netlist, str)
        assert "R1" in netlist or "r1" in netlist.lower()
        assert ".op" in netlist.lower() or ".end" in netlist.lower()


class TestSimulationResult:
    def test_success_result(self):
        r = SimulationResult(success=True, analysis_type="DC Operating Point", data={"nodeA": 5.0})
        assert r.success
        assert r.data["nodeA"] == 5.0

    def test_failure_result(self):
        r = SimulationResult(success=False, error="ngspice not found")
        assert not r.success
        assert "ngspice" in r.error


class TestRunSimulation:
    @patch(
        "controllers.simulation_controller.SimulationController.runner",
        new_callable=lambda: property(lambda self: MagicMock()),
    )
    def test_run_fails_on_invalid_circuit(self, mock_runner):
        ctrl = SimulationController()
        ctrl.set_analysis("DC Operating Point")
        result = ctrl.run_simulation()
        assert not result.success

    def test_run_fails_when_ngspice_not_found(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = None
        mock_runner.output_dir = "simulation_output"
        ctrl._runner = mock_runner
        result = ctrl.run_simulation()
        assert not result.success
        assert "ngspice" in result.error.lower()

    def test_run_returns_error_on_sim_failure(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "simulation_output"
        mock_runner.run_simulation.return_value = (False, None, "", "Simulation error")
        ctrl._runner = mock_runner
        result = ctrl.run_simulation()
        assert not result.success
        # Error is now a student-friendly message (classified as UNKNOWN)
        assert "failed" in result.error.lower()

    def test_convergence_error_shows_friendly_message(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "simulation_output"
        # First call fails with convergence error, retry also fails
        mock_runner.run_simulation.return_value = (
            False,
            None,
            "",
            "Error: no convergence in DC operating point",
        )
        ctrl._runner = mock_runner
        result = ctrl.run_simulation()
        assert not result.success
        assert "stable DC operating point" in result.error

    def test_singular_matrix_shows_friendly_message(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "simulation_output"
        mock_runner.run_simulation.return_value = (
            False,
            None,
            "",
            "Error: singular matrix",
        )
        ctrl._runner = mock_runner
        result = ctrl.run_simulation()
        assert not result.success
        assert "singular" in result.error.lower()
        # Singular matrix is not retriable, so only one call
        assert mock_runner.run_simulation.call_count == 1

    def test_convergence_retry_succeeds(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "simulation_output"
        # First call fails, retry succeeds
        mock_runner.run_simulation.side_effect = [
            (False, None, "", "Error: no convergence in DC operating point"),
            (True, "/tmp/output.txt", "v(1) = 5.0", ""),
        ]
        mock_runner.read_output.return_value = "v(1) = 5.000000e+00\n"
        ctrl._runner = mock_runner
        result = ctrl.run_simulation()
        assert result.success
        assert any("relaxed tolerances" in w for w in result.warnings)
        assert mock_runner.run_simulation.call_count == 2


class TestSetAnalysisVariants:
    def test_set_ac_sweep(self):
        ctrl = SimulationController()
        ctrl.set_analysis(
            "AC Sweep",
            {"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        assert ctrl.model.analysis_type == "AC Sweep"
        assert ctrl.model.analysis_params["fStop"] == "1MEG"

    def test_set_transient(self):
        ctrl = SimulationController()
        ctrl.set_analysis("Transient", {"step": "1u", "duration": "10m"})
        assert ctrl.model.analysis_type == "Transient"
        assert ctrl.model.analysis_params["step"] == "1u"

    def test_set_noise(self):
        ctrl = SimulationController()
        ctrl.set_analysis(
            "Noise",
            {"output_node": "out", "source": "V1", "fStart": 1, "fStop": 1e6},
        )
        assert ctrl.model.analysis_type == "Noise"

    def test_set_sensitivity(self):
        ctrl = SimulationController()
        ctrl.set_analysis("Sensitivity", {"output_node": "out"})
        assert ctrl.model.analysis_type == "Sensitivity"

    def test_set_transfer_function(self):
        ctrl = SimulationController()
        ctrl.set_analysis(
            "Transfer Function",
            {"output_var": "v(out)", "input_source": "V1"},
        )
        assert ctrl.model.analysis_type == "Transfer Function"

    def test_set_pole_zero(self):
        ctrl = SimulationController()
        ctrl.set_analysis(
            "Pole-Zero",
            {
                "input_pos": "1",
                "input_neg": "0",
                "output_pos": "2",
                "output_neg": "0",
            },
        )
        assert ctrl.model.analysis_type == "Pole-Zero"

    def test_set_analysis_none_params(self):
        ctrl = SimulationController()
        ctrl.set_analysis("DC Operating Point", None)
        assert ctrl.model.analysis_params == {}

    def test_set_temperature_sweep(self):
        ctrl = SimulationController()
        ctrl.set_analysis(
            "Temperature Sweep",
            {"tempStart": -40, "tempStop": 85, "tempStep": 25},
        )
        assert ctrl.model.analysis_type == "Temperature Sweep"
        assert ctrl.model.analysis_params["tempStart"] == -40


class TestParseResultsDispatch:
    """Test that _parse_results dispatches to the correct parser."""

    def test_dc_op_dispatch(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "v(nodeA) = 5.0\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "DC Operating Point"

    def test_dc_sweep_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "DC Sweep"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "Index   v-sweep   v(nodeA)\n0   0.0   0.0\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "DC Sweep"

    def test_ac_sweep_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "AC Sweep"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = (
            "Index   frequency   v(out)   vp(out)\n0       100.0       1.0      -45.0\n"
        )
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "AC Sweep"

    def test_noise_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "Noise"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = (
            "Index   frequency   onoise_spectrum   inoise_spectrum\n0       100.0       1.5e-8            2.3e-7\n"
        )
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "Noise"

    def test_sensitivity_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "Sensitivity"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "DC Sensitivities of output v(out)\n\nR1   1e3   5e-4   0.5\n\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "Sensitivity"

    def test_transfer_function_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "Transfer Function"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "Transfer function, output/input = 5.000000e-01\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "Transfer Function"

    def test_pole_zero_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "Pole-Zero"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "pole(1) = -1.00000e+03, 0.00000e+00\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "Pole-Zero"

    def test_temperature_sweep_dispatch(self):
        model = _build_simple_circuit()
        model.analysis_type = "Temperature Sweep"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "v(nodeA) = 5.0\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert result.success
        assert result.analysis_type == "Temperature Sweep"

    def test_unknown_analysis_type(self):
        model = _build_simple_circuit()
        model.analysis_type = "Nonexistent Analysis"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="",
            warnings=[],
        )
        assert not result.success
        assert "Unknown analysis type" in result.error

    def test_measurement_results_parsed(self):
        """Measurement results from stdout should be captured."""
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.read_output.return_value = "v(nodeA) = 5.0\n"
        ctrl._runner = mock_runner
        result = ctrl._parse_results(
            output_file="/tmp/out.txt",
            wrdata_filepath="/tmp/wr.txt",
            netlist="* test",
            raw_output="  rise_time  =  1.23456e-06\n",
            warnings=[],
        )
        assert result.success
        assert result.measurements is not None
        assert "rise_time" in result.measurements


class TestGenerateNetlistOptions:
    def test_generate_with_spice_options(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        netlist = ctrl.generate_netlist(spice_options={"RELTOL": "0.01"})
        assert ".options RELTOL=0.01" in netlist

    def test_generate_with_measurements(self):
        model = _build_simple_circuit()
        model.analysis_type = "Transient"
        model.analysis_params = {"step": "1u", "duration": "10m", "start": "0"}
        ctrl = SimulationController(model)
        netlist = ctrl.generate_netlist(measurements=[".meas TRAN delay TRIG v(1) VAL=2.5 RISE=1"])
        assert ".meas TRAN delay" in netlist


class TestParameterSweepEdgeCases:
    def test_sweep_missing_component(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "simulation_output"
        ctrl._runner = mock_runner
        result = ctrl.run_parameter_sweep(
            {
                "component_id": "NONEXISTENT",
                "start": 100,
                "stop": 10000,
                "num_steps": 5,
                "base_analysis_type": "DC Operating Point",
                "base_params": {},
            }
        )
        assert not result.success
        assert "NONEXISTENT" in result.error

    def test_sweep_restores_original_values(self):
        model = _build_simple_circuit()
        original_value = model.components["R1"].value
        original_analysis = model.analysis_type

        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "/tmp"
        mock_runner.run_simulation.return_value = (
            True,
            "/tmp/out.txt",
            "v(1) = 5.0",
            "",
        )
        mock_runner.read_output.return_value = "v(nodeA) = 5.0\n"
        ctrl._runner = mock_runner

        ctrl.run_parameter_sweep(
            {
                "component_id": "R1",
                "start": 100,
                "stop": 10000,
                "num_steps": 3,
                "base_analysis_type": "DC Operating Point",
                "base_params": {},
            }
        )
        assert model.components["R1"].value == original_value
        assert model.analysis_type == original_analysis

    def test_sweep_cancellation(self):
        """Sweep should stop when progress_callback returns False."""
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "/tmp"
        mock_runner.run_simulation.return_value = (
            True,
            "/tmp/out.txt",
            "v(1) = 5.0",
            "",
        )
        mock_runner.read_output.return_value = "v(nodeA) = 5.0\n"
        ctrl._runner = mock_runner

        call_count = 0

        def cancel_after_one(step, total):
            nonlocal call_count
            call_count += 1
            return call_count <= 1

        result = ctrl.run_parameter_sweep(
            {
                "component_id": "R1",
                "start": 100,
                "stop": 10000,
                "num_steps": 5,
                "base_analysis_type": "DC Operating Point",
                "base_params": {},
            },
            progress_callback=cancel_after_one,
        )
        assert result.data["cancelled"] is True
        assert result.data["num_steps"] < 5


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import controllers.simulation_controller as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
