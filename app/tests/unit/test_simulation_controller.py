"""Tests for SimulationController."""

import pytest
from unittest.mock import patch, MagicMock
from controllers.simulation_controller import SimulationController, SimulationResult
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

def _build_simple_circuit():
    """Build a simple V1-R1-GND circuit model."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1", component_type="Voltage Source",
        value="5V", position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1", component_type="Resistor",
        value="1k", position=(100.0, 0.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1", component_type="Ground",
        value="0V", position=(0.0, 100.0),
    )
    model.wires = [
        WireData(start_component_id="V1", start_terminal=1,
                 end_component_id="R1", end_terminal=0),
        WireData(start_component_id="R1", start_terminal=1,
                 end_component_id="GND1", end_terminal=0),
        WireData(start_component_id="V1", start_terminal=0,
                 end_component_id="GND1", end_terminal=0),
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
            component_id="R1", component_type="Resistor",
            value="1k", position=(0.0, 0.0),
        )
        model.components["V1"] = ComponentData(
            component_id="V1", component_type="Voltage Source",
            value="5V", position=(100.0, 0.0),
        )
        model.wires = [
            WireData(start_component_id="R1", start_terminal=1,
                     end_component_id="V1", end_terminal=0),
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
        r = SimulationResult(success=True, analysis_type="DC Operating Point",
                             data={"nodeA": 5.0})
        assert r.success
        assert r.data["nodeA"] == 5.0

    def test_failure_result(self):
        r = SimulationResult(success=False, error="ngspice not found")
        assert not r.success
        assert "ngspice" in r.error


class TestRunSimulation:
    @patch('controllers.simulation_controller.SimulationController.runner',
           new_callable=lambda: property(lambda self: MagicMock()))
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
        assert "Simulation error" in result.error


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import controllers.simulation_controller as mod
        source = open(mod.__file__).read()
        assert 'PyQt' not in source
        assert 'QtCore' not in source
        assert 'QtWidgets' not in source
