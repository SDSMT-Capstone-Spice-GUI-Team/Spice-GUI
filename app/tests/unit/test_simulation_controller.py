"""Tests for SimulationController."""

from pathlib import Path
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


class TestExportNetlist:
    def test_export_netlist_writes_file(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        filepath = tmp_path / "test.cir"
        ctrl.export_netlist(str(filepath))
        assert filepath.exists()
        content = filepath.read_text()
        assert ".op" in content.lower() or ".end" in content.lower()

    def test_export_netlist_raises_on_bad_path(self):
        model = _build_simple_circuit()
        ctrl = SimulationController(model)
        with pytest.raises(OSError):
            ctrl.export_netlist("/nonexistent/dir/test.cir")


class TestExportResultsCSV:
    def test_generate_results_csv_returns_content_for_op(self):
        ctrl = SimulationController()
        op_results = {"v(1)": 5.0, "v(2)": 3.3}
        content = ctrl.generate_results_csv(op_results, "DC Operating Point", "test")
        assert content is not None
        assert "v(1)" in content or "5.0" in content

    def test_generate_results_csv_returns_none_for_unsupported(self):
        ctrl = SimulationController()
        content = ctrl.generate_results_csv({}, "Pole-Zero", "test")
        assert content is None

    def test_export_results_csv_writes_file(self, tmp_path):
        ctrl = SimulationController()
        op_results = {"v(1)": 5.0, "v(2)": 3.3}
        filepath = tmp_path / "results.csv"
        ctrl.export_results_csv(op_results, "DC Operating Point", str(filepath), "test")
        assert filepath.exists()

    def test_export_results_csv_skips_unsupported_type(self, tmp_path):
        ctrl = SimulationController()
        filepath = tmp_path / "results.csv"
        ctrl.export_results_csv({}, "Pole-Zero", str(filepath), "test")
        assert not filepath.exists()


class TestExportResultsExcel:
    def test_export_results_excel_writes_file(self, tmp_path):
        ctrl = SimulationController()
        op_results = {"v(1)": 5.0}
        filepath = tmp_path / "results.xlsx"
        ctrl.export_results_excel(op_results, "DC Operating Point", str(filepath), "test")
        assert filepath.exists()


class TestExportResultsMarkdown:
    def test_generate_results_markdown_returns_content(self):
        ctrl = SimulationController()
        op_results = {"v(1)": 5.0}
        content = ctrl.generate_results_markdown(op_results, "DC Operating Point", "test")
        assert content is not None
        assert "v(1)" in content or "5.0" in content

    def test_generate_results_markdown_returns_none_for_unsupported(self):
        ctrl = SimulationController()
        content = ctrl.generate_results_markdown({}, "Sensitivity", "test")
        assert content is None

    def test_export_results_markdown_writes_file(self, tmp_path):
        ctrl = SimulationController()
        op_results = {"v(1)": 5.0}
        filepath = tmp_path / "results.md"
        ctrl.export_results_markdown(op_results, "DC Operating Point", str(filepath), "test")
        assert filepath.exists()


class TestOperationalPointAlias:
    """'Operational Point' analysis type must parse results like 'DC Operating Point' (#540)."""

    def test_operational_point_routes_to_op_parser(self):
        model = _build_simple_circuit()
        model.analysis_type = "Operational Point"
        ctrl = SimulationController(model)
        mock_runner = MagicMock()
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.output_dir = "simulation_output"
        mock_runner.run_simulation.return_value = (True, "/tmp/out.txt", "", "")
        mock_runner.read_output.return_value = "v(nodeA) = 5.00000\n"
        ctrl._runner = mock_runner
        result = ctrl.run_simulation()
        assert result.success
        assert result.data["node_voltages"]["nodeA"] == pytest.approx(5.0)


class TestWrdataCleanup:
    """Verify wrdata files are registered for cleanup (#542)."""

    def test_run_simulation_registers_wrdata(self):
        """run_simulation registers the wrdata file for cleanup."""
        model = _build_simple_circuit()
        model.analysis_type = "DC Operating Point"
        ctrl = SimulationController(model=model)

        mock_runner = MagicMock()
        mock_runner.output_dir = "/tmp/sim"
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.run_simulation.return_value = (
            True,
            "/tmp/sim/output.txt",
            "v(1) = 5.0",
            "",
        )
        mock_runner.read_output.return_value = "v(nodeA) = 5.00000\n"
        ctrl._runner = mock_runner

        ctrl.run_simulation()

        mock_runner.register_extra_files.assert_called_once()
        registered = mock_runner.register_extra_files.call_args[0][0]
        assert len(registered) == 1
        assert "wrdata_" in registered[0]

    def test_parameter_sweep_registers_wrdata(self):
        """run_parameter_sweep registers all wrdata files for cleanup."""
        model = _build_simple_circuit()
        model.analysis_type = "DC Operating Point"
        ctrl = SimulationController(model=model)

        mock_runner = MagicMock()
        mock_runner.output_dir = "/tmp/sim"
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.run_simulation.return_value = (
            True,
            "/tmp/sim/output.txt",
            "v(1) = 5.0",
            "",
        )
        mock_runner.read_output.return_value = "v(nodeA) = 5.00000\n"
        ctrl._runner = mock_runner

        sweep_config = {
            "component_id": "R1",
            "start": 100,
            "stop": 1000,
            "num_steps": 3,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
        }
        ctrl.run_parameter_sweep(sweep_config)

        mock_runner.register_extra_files.assert_called_once()
        registered = mock_runner.register_extra_files.call_args[0][0]
        assert len(registered) == 3
        assert all("wrdata_sweep_" in f for f in registered)

    def test_monte_carlo_registers_wrdata(self):
        """run_monte_carlo registers all wrdata files for cleanup."""
        model = _build_simple_circuit()
        model.analysis_type = "DC Operating Point"
        ctrl = SimulationController(model=model)

        mock_runner = MagicMock()
        mock_runner.output_dir = "/tmp/sim"
        mock_runner.find_ngspice.return_value = "/usr/bin/ngspice"
        mock_runner.run_simulation.return_value = (
            True,
            "/tmp/sim/output.txt",
            "v(1) = 5.0",
            "",
        )
        mock_runner.read_output.return_value = "v(nodeA) = 5.00000\n"
        ctrl._runner = mock_runner

        mc_config = {
            "num_runs": 2,
            "base_analysis_type": "DC Operating Point",
            "base_params": {},
            "tolerances": {
                "R1": {"tolerance_pct": 10, "distribution": "gaussian"},
            },
        }
        ctrl.run_monte_carlo(mc_config)

        mock_runner.register_extra_files.assert_called_once()
        registered = mock_runner.register_extra_files.call_args[0][0]
        assert len(registered) == 2
        assert all("wrdata_mc_" in f for f in registered)


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import controllers.simulation_controller as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
