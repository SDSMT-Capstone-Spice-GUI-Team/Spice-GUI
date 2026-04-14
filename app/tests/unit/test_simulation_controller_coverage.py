"""Tests for controllers.simulation_controller — additional coverage.

Mocks NgspiceRunner and simulation modules to avoid actual subprocess calls.
The static methods in SimulationController use lazy imports inside the method
body, so we mock at the source module level (e.g. simulation.power_calculator).
"""

from unittest.mock import MagicMock, patch

from controllers.simulation_controller import SimulationController, SimulationResult
from models.circuit import CircuitModel
from tests.conftest import make_simulation_controller


def _build_simple_circuit(ctrl):
    """Add a V1-R1-GND circuit to the controller's model."""
    from models.component import ComponentData
    from models.wire import WireData

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


class TestSimulationResult:
    def test_default_fields(self):
        r = SimulationResult(success=True)
        assert r.success is True
        assert r.errors == []
        assert r.warnings == []
        assert r.error == ""
        assert r.data is None

    def test_fields_populated(self):
        r = SimulationResult(
            success=False,
            analysis_type="Transient",
            error="boom",
            errors=["e1"],
            warnings=["w1"],
            netlist="* netlist",
        )
        assert r.analysis_type == "Transient"
        assert r.error == "boom"


class TestAnalysisConfig:
    def test_set_and_get_analysis(self):
        ctrl, _ = make_simulation_controller()
        ctrl.set_analysis("Transient", {"tstep": "1u", "tstop": "1m"})
        assert ctrl.get_analysis_type() == "Transient"
        params = ctrl.get_analysis_params()
        assert params["tstep"] == "1u"

    def test_set_analysis_none_params(self):
        ctrl, _ = make_simulation_controller()
        ctrl.set_analysis("DC Operating Point", None)
        assert ctrl.get_analysis_params() == {}

    def test_get_params_returns_copy(self):
        ctrl, _ = make_simulation_controller()
        ctrl.set_analysis("AC Sweep", {"fstart": "1", "fstop": "1Meg"})
        p1 = ctrl.get_analysis_params()
        p1["extra"] = "X"
        assert "extra" not in ctrl.get_analysis_params()


class TestRunSimulationNgspiceNotFound:
    def test_ngspice_not_found(self):
        ctrl, runner = make_simulation_controller()
        _build_simple_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")
        runner.find_ngspice.return_value = None

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            result = ctrl.run_simulation()
        assert result.success is False
        assert "ngspice" in result.error.lower()


class TestRunSimulationValidationFailure:
    def test_validation_failure_returns_errors(self):
        ctrl, runner = make_simulation_controller()
        ctrl.set_analysis("DC Operating Point")

        with patch("simulation.validate_circuit", return_value=(False, ["No ground"], ["warn"])):
            result = ctrl.run_simulation()
        assert result.success is False
        assert "No ground" in result.error


class TestRunSimulationNotify:
    def test_notifies_on_start_and_complete(self):
        ctrl, runner = make_simulation_controller()
        _build_simple_circuit(ctrl)
        ctrl.set_analysis("DC Operating Point")
        cc = MagicMock()
        ctrl.circuit_ctrl = cc
        runner.run_simulation.return_value = (True, "/tmp/out", "stdout", "")
        runner.read_output.return_value = "v(1) = 5.0"

        with patch("simulation.validate_circuit", return_value=(True, [], [])):
            with patch("simulation.NetlistGenerator") as mock_gen:
                mock_gen.return_value.generate.return_value = "* netlist"
                with patch("simulation.ResultParser") as mock_rp:
                    mock_rp.parse_op_results.return_value = {"V(1)": 5.0}
                    mock_rp.parse_measurement_results.return_value = {}
                    with patch("simulation.result_parser.ResultParseError", Exception):
                        ctrl.run_simulation()

        cc._notify.assert_any_call("simulation_started", None)

    def test_notifies_on_validation_failure(self):
        ctrl, _ = make_simulation_controller()
        ctrl.set_analysis("DC Operating Point")
        cc = MagicMock()
        ctrl.circuit_ctrl = cc

        with patch("simulation.validate_circuit", return_value=(False, ["No ground"], [])):
            ctrl.run_simulation()
        assert cc._notify.call_count >= 2


class TestRunSimulationConvergenceRetry:
    def test_retry_with_relaxed_tolerances(self):
        ctrl, runner = make_simulation_controller()
        _build_simple_circuit(ctrl)
        ctrl.set_analysis("Transient", {"tstep": "1u", "tstop": "1m"})

        runner.run_simulation.side_effect = [
            (False, "", "stdout", "timestep too small"),
            (True, "/tmp/retry_out", "retry_stdout", ""),
        ]

        mock_diagnosis = MagicMock()
        mock_diagnosis.category = "timestep"

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
                                    mock_rp.parse_transient_results.return_value = {"time": [0]}
                                    mock_rp.parse_measurement_results.return_value = {}
                                    with patch(
                                        "simulation.result_parser.ResultParseError",
                                        Exception,
                                    ):
                                        runner.read_output.return_value = ""
                                        result = ctrl.run_simulation()

        assert result.success is True
        assert any("relaxed" in w.lower() for w in result.warnings)


class TestParseResultsBranches:
    def _run_parse(self, ctrl, runner, analysis_type):
        ctrl.model.analysis_type = analysis_type
        runner.read_output.return_value = "output data"

        with patch("simulation.ResultParser") as mock_rp:
            mock_rp.parse_op_results.return_value = {"v(1)": 5.0}
            mock_rp.parse_dc_results.return_value = {"sweep": [1, 2]}
            mock_rp.parse_ac_results.return_value = {"freq": [1, 10]}
            mock_rp.parse_transient_results.return_value = {"time": [0, 1]}
            mock_rp.parse_noise_results.return_value = {"noise": [0.1]}
            mock_rp.parse_sensitivity_results.return_value = {"sens": [1]}
            mock_rp.parse_tf_results.return_value = {"tf": 10}
            mock_rp.parse_pz_results.return_value = {"poles": []}
            mock_rp.parse_measurement_results.return_value = {}

            with patch("simulation.result_parser.ResultParseError", Exception):
                return ctrl._parse_results(
                    output_file="/tmp/out",
                    wrdata_filepath="/tmp/wrdata",
                    netlist="* netlist",
                    raw_output="stdout",
                    warnings=[],
                )

    def test_dc_op(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "DC Operating Point")
        assert result.success is True

    def test_dc_sweep(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "DC Sweep")
        assert result.success is True

    def test_ac_sweep(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "AC Sweep")
        assert result.success is True

    def test_transient(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "Transient")
        assert result.success is True

    def test_temperature_sweep(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "Temperature Sweep")
        assert result.success is True

    def test_noise(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "Noise")
        assert result.success is True

    def test_sensitivity(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "Sensitivity")
        assert result.success is True

    def test_transfer_function(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "Transfer Function")
        assert result.success is True

    def test_pole_zero(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "Pole-Zero")
        assert result.success is True

    def test_unknown_type(self):
        ctrl, runner = make_simulation_controller()
        result = self._run_parse(ctrl, runner, "UnknownAnalysis")
        assert result.success is False
        assert "Unknown" in result.error

    def test_parse_error_handled(self):
        ctrl, runner = make_simulation_controller()
        ctrl.model.analysis_type = "DC Operating Point"
        runner.read_output.return_value = "output"

        with patch("simulation.ResultParser") as mock_rp:
            mock_rp.parse_op_results.side_effect = ValueError("bad data")
            with patch("simulation.result_parser.ResultParseError", ValueError):
                result = ctrl._parse_results(
                    output_file="/tmp/out",
                    wrdata_filepath="/tmp/wr",
                    netlist="* net",
                    raw_output="stdout",
                    warnings=[],
                )
        assert result.success is False
        assert "parsing failed" in result.error.lower()


class TestStaticHelpers:
    def test_format_sweep_value(self):
        val = SimulationController._format_sweep_value(1000.0)
        assert isinstance(val, str)
        assert val

    def test_compute_mc_statistics(self):
        with patch("simulation.monte_carlo.compute_mc_statistics", return_value={"mean": 5}):
            result = SimulationController.compute_mc_statistics([1, 2, 3])
            assert result == {"mean": 5}

    def test_format_results_table(self):
        with patch("simulation.ResultParser") as mock_rp:
            mock_rp.format_results_as_table.return_value = "table"
            result = SimulationController.format_results_table({"data": 1})
            assert result == "table"

    def test_compute_frequency_markers(self):
        with patch("simulation.freq_markers.compute_markers", return_value={"bw": 1000}):
            result = SimulationController.compute_frequency_markers([1, 10], [0, -3])
            assert result == {"bw": 1000}

    def test_compute_signal_fft(self):
        with patch(
            "simulation.fft_analysis.analyze_signal_spectrum",
            return_value={"freqs": [1]},
        ):
            result = SimulationController.compute_signal_fft([0, 1], [0, 1], "v1")
            assert result == {"freqs": [1]}


class TestPresetManagement:
    def test_preset_manager_lazy(self):
        ctrl, _ = make_simulation_controller()
        mock_pm = MagicMock()
        ctrl._preset_manager = mock_pm
        assert ctrl.preset_manager is mock_pm

    def test_get_presets(self):
        ctrl, _ = make_simulation_controller()
        mock_pm = MagicMock()
        mock_pm.get_presets.return_value = [{"name": "default"}]
        ctrl._preset_manager = mock_pm
        ctrl.get_presets("Transient")
        mock_pm.get_presets.assert_called_once_with("Transient")

    def test_get_preset_by_name(self):
        ctrl, _ = make_simulation_controller()
        mock_pm = MagicMock()
        ctrl._preset_manager = mock_pm
        ctrl.get_preset_by_name("fast", "Transient")
        mock_pm.get_preset_by_name.assert_called_once_with("fast", "Transient")

    def test_save_preset(self):
        ctrl, _ = make_simulation_controller()
        mock_pm = MagicMock()
        ctrl._preset_manager = mock_pm
        ctrl.save_preset("my_preset", "AC Sweep", {"fstart": "1"})
        mock_pm.save_preset.assert_called_once()

    def test_delete_preset(self):
        ctrl, _ = make_simulation_controller()
        mock_pm = MagicMock()
        ctrl._preset_manager = mock_pm
        ctrl.delete_preset("old_preset")
        mock_pm.delete_preset.assert_called_once()

    def test_generate_analysis_command(self):
        with patch(
            "simulation.netlist_generator.generate_analysis_command",
            return_value=".tran 1u 1m",
        ):
            result = SimulationController.generate_analysis_command("Transient", {"tstep": "1u", "tstop": "1m"})
            assert result == ".tran 1u 1m"


class TestExportHelpers:
    def test_compute_power(self):
        with patch("simulation.power_calculator.calculate_power", return_value={"R1": 0.005}):
            with patch("simulation.power_calculator.total_power", return_value=0.005):
                data, total = SimulationController.compute_power({}, [], {})
                assert total == 0.005

    def test_compute_power_empty(self):
        with patch("simulation.power_calculator.calculate_power", return_value={}):
            with patch("simulation.power_calculator.total_power", return_value=0.0):
                data, total = SimulationController.compute_power({}, [], {})
                assert data == {}
                assert total == 0.0

    def test_compute_power_metrics(self):
        mock_metrics = [{"component": "R1", "avg_power": 0.005}]
        with patch(
            "simulation.power_metrics.compute_transient_power_metrics",
            return_value=mock_metrics,
        ):
            with patch("simulation.power_metrics.format_power_summary", return_value="R1: 5mW"):
                metrics, summary = SimulationController.compute_power_metrics({"data": 1}, {})
                assert len(metrics) == 1
                assert "R1" in summary

    def test_compute_power_metrics_empty(self):
        with patch("simulation.power_metrics.compute_transient_power_metrics", return_value=[]):
            with patch("simulation.power_metrics.format_power_summary", return_value=""):
                metrics, summary = SimulationController.compute_power_metrics({}, {})
                assert metrics == []
                assert summary == ""

    def test_generate_results_csv_unknown_type(self):
        ctrl, _ = make_simulation_controller()
        result = ctrl.generate_results_csv({"data": 1}, "Unknown Type", "test")
        assert result is None
