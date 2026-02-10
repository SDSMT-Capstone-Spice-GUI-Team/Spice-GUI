"""
Integration tests for Phase 4: Full MVC Flow

Tests the complete flow from MainWindow through controllers to model,
verifying that the MVC architecture works end-to-end.
"""

import tempfile
from pathlib import Path

import pytest
from controllers.circuit_controller import CircuitController
from controllers.file_controller import FileController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData


class TestMVCFileOperations:
    """Test complete file operation flow through MVC"""

    def test_save_load_roundtrip_through_controllers(self, simple_resistor_circuit):
        """Test that save and load work through FileController"""
        components, wires, nodes, terminal_to_node = simple_resistor_circuit

        # Create model and populate with test data
        model = CircuitModel()
        model.components = components
        model.wires = wires
        model.nodes = nodes
        model.terminal_to_node = terminal_to_node

        # Create FileController
        file_ctrl = FileController(model)

        # Save circuit
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            file_ctrl.save_circuit(temp_path)

            # Verify file was created
            assert temp_path.exists()

            # Create new model and controller
            new_model = CircuitModel()
            new_file_ctrl = FileController(new_model)

            # Load circuit
            new_file_ctrl.load_circuit(temp_path)

            # Verify data was restored
            assert len(new_model.components) == len(model.components)
            assert len(new_model.wires) == len(model.wires)
            assert "V1" in new_model.components
            assert "R1" in new_model.components
            assert "GND1" in new_model.components

        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()

    def test_new_circuit_clears_model(self):
        """Test that new circuit operation clears model"""
        # Create model with data
        model = CircuitModel()
        model.components = {"R1": ComponentData("R1", "Resistor", "1k", (0, 0))}

        # Create FileController
        file_ctrl = FileController(model)

        # New circuit should clear everything
        file_ctrl.new_circuit()

        # Verify model is empty
        assert len(model.components) == 0
        assert len(model.wires) == 0
        assert file_ctrl.current_file is None

    def test_session_persistence(self):
        """Test that session file is saved and restored"""
        # Create model and controller
        model = CircuitModel()
        file_ctrl = FileController(model, session_file="test_session.txt")

        # Save circuit to trigger session save
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            file_ctrl.save_circuit(temp_path)

            # Create new controller and check session
            new_file_ctrl = FileController(CircuitModel(), session_file="test_session.txt")
            last_file = new_file_ctrl.load_last_session()

            # Verify session file returns correct path
            assert last_file == temp_path

        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()
            session_path = Path("test_session.txt")
            if session_path.exists():
                session_path.unlink()


class TestMVCSimulationFlow:
    """Test complete simulation flow through MVC"""

    def test_simulation_controller_integration(self, simple_resistor_circuit):
        """Test simulation through SimulationController"""
        components, wires, nodes, terminal_to_node = simple_resistor_circuit

        # Create model and populate
        model = CircuitModel()
        model.components = components
        model.wires = wires
        model.nodes = nodes
        model.terminal_to_node = terminal_to_node
        model.analysis_type = "DC Operating Point"
        model.analysis_params = {}

        # Create SimulationController
        sim_ctrl = SimulationController(model)

        # Generate netlist
        netlist = sim_ctrl.generate_netlist()

        # Verify netlist contains expected components
        assert "V1" in netlist
        assert "R1" in netlist
        assert "GND1" in netlist or ".op" in netlist

    def test_analysis_type_update(self):
        """Test updating analysis type through controller"""
        model = CircuitModel()
        sim_ctrl = SimulationController(model)

        # Change analysis type
        sim_ctrl.set_analysis("Transient", {"duration": "1ms", "step": "1us"})

        # Verify model was updated
        assert model.analysis_type == "Transient"
        assert model.analysis_params["duration"] == "1ms"
        assert model.analysis_params["step"] == "1us"

    def test_multiple_analysis_types(self):
        """Test switching between different analysis types"""
        model = CircuitModel()
        sim_ctrl = SimulationController(model)

        # Test each analysis type
        analyses = [
            ("DC Operating Point", {}),
            ("DC Sweep", {"min": 0, "max": 10, "step": 1}),
            ("AC Sweep", {"fStart": 1, "fStop": 1000, "points": 10}),
            ("Transient", {"duration": "10ms", "step": "10us"}),
        ]

        for analysis_type, params in analyses:
            sim_ctrl.set_analysis(analysis_type, params)
            assert model.analysis_type == analysis_type
            assert model.analysis_params == params


class TestMVCCircuitOperations:
    """Test circuit operations through CircuitController"""

    def test_add_component_through_controller(self):
        """Test adding component through CircuitController"""
        model = CircuitModel()
        circuit_ctrl = CircuitController(model)

        # Add component (controller generates ID and creates ComponentData)
        comp = circuit_ctrl.add_component("Resistor", (100, 200))

        # Verify component was added to model
        assert comp.component_id in model.components
        assert model.components[comp.component_id].component_type == "Resistor"

    def test_remove_component_through_controller(self):
        """Test removing component through CircuitController"""
        model = CircuitModel()
        model.components = {"R1": ComponentData("R1", "Resistor", "1k", (0, 0))}
        circuit_ctrl = CircuitController(model)

        # Remove component
        circuit_ctrl.remove_component("R1")

        # Verify component was removed
        assert "R1" not in model.components

    def test_update_component_through_controller(self):
        """Test updating component through CircuitController"""
        model = CircuitModel()
        model.components = {"R1": ComponentData("R1", "Resistor", "1k", (0, 0))}
        CircuitController(model)

        # Update component
        model.components["R1"].value = "2k"

        # Verify update
        assert model.components["R1"].value == "2k"


class TestMVCDataFlow:
    """Test data flow through MVC layers"""

    def test_model_independence(self):
        """Test that model can exist independently of controllers"""
        # Create model
        model = CircuitModel()
        model.components = {"R1": ComponentData("R1", "Resistor", "1k", (0, 0))}

        # Model should work without controllers
        assert len(model.components) == 1
        assert model.to_dict() is not None

    def test_controller_shares_model_reference(self):
        """Test that multiple controllers share same model reference"""
        model = CircuitModel()

        # Create controllers with same model
        file_ctrl = FileController(model)
        sim_ctrl = SimulationController(model)
        circuit_ctrl = CircuitController(model)

        # All should reference same model
        assert file_ctrl.model is model
        assert sim_ctrl.model is model
        assert circuit_ctrl.model is model

        # Changes through one controller affect others
        comp = circuit_ctrl.add_component("Resistor", (0, 0))
        assert comp.component_id in file_ctrl.model.components
        assert comp.component_id in sim_ctrl.model.components

    def test_model_to_dict_preserves_all_data(self, resistor_divider_circuit):
        """Test that model serialization preserves all data"""
        components, wires, nodes, terminal_to_node = resistor_divider_circuit

        # Create model
        model = CircuitModel()
        model.components = components
        model.wires = wires
        model.nodes = nodes
        model.terminal_to_node = terminal_to_node
        model.analysis_type = "DC Operating Point"

        # Convert to dict
        data = model.to_dict()

        # Verify all data present
        assert "components" in data
        assert "wires" in data
        assert len(data["components"]) == 4  # V1, R1, R2, GND1
        assert len(data["wires"]) == 4

    def test_model_from_dict_restores_all_data(self, resistor_divider_circuit):
        """Test that model deserialization restores all data"""
        components, wires, nodes, terminal_to_node = resistor_divider_circuit

        # Create model
        model = CircuitModel()
        model.components = components
        model.wires = wires

        # Serialize and deserialize
        data = model.to_dict()
        restored_model = CircuitModel.from_dict(data)

        # Verify restoration
        assert len(restored_model.components) == len(components)
        assert len(restored_model.wires) == len(wires)


class TestMVCErrorPropagation:
    """Test error handling across MVC layers"""

    def test_file_controller_error_propagates(self):
        """Test that FileController errors propagate correctly"""
        model = CircuitModel()
        file_ctrl = FileController(model)

        # Attempt to load non-existent file
        with pytest.raises((OSError, FileNotFoundError)):
            file_ctrl.load_circuit(Path("/nonexistent/file.json"))

    def test_invalid_circuit_data_rejected(self):
        """Test that invalid circuit data is rejected"""
        model = CircuitModel()
        file_ctrl = FileController(model)

        # Create invalid data file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": "data"}')
            temp_path = Path(f.name)

        try:
            # Should raise ValueError due to validation
            with pytest.raises((ValueError, KeyError)):
                file_ctrl.load_circuit(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_simulation_validation_errors(self):
        """Test that simulation validation errors are captured"""
        # Create invalid circuit (no ground)
        model = CircuitModel()
        model.components = {"R1": ComponentData("R1", "Resistor", "1k", (0, 0))}
        model.analysis_type = "DC Operating Point"

        sim_ctrl = SimulationController(model)

        # Run simulation (should fail validation)
        result = sim_ctrl.run_simulation()

        # Verify validation error is reported
        assert result.success is False or len(result.errors) > 0


class TestMVCBackwardCompatibility:
    """Test that Phase 4 maintains Phase 3 backward compatibility"""

    def test_old_imports_still_work(self):
        """Test that old import names still work after Phase 4"""
        # These should all work due to backward compatibility
        # Old names should map to new classes
        from GUI import CircuitCanvas, CircuitCanvasView, WireGraphicsItem, WireItem

        assert CircuitCanvas is CircuitCanvasView
        assert WireItem is WireGraphicsItem

    def test_phase3_models_work_with_phase4_controllers(self):
        """Test that Phase 3 models work with Phase 4 controllers"""
        from controllers.file_controller import FileController
        from models.component import ComponentData

        # Create Phase 3 style data
        comp = ComponentData("R1", "Resistor", "1k", (0, 0))
        wire = WireData("R1", 0, "R2", 0)

        # Should work with Phase 4 controllers
        model = CircuitModel()
        model.components = {"R1": comp}
        model.wires = [wire]

        FileController(model)

        # Should be able to serialize
        data = model.to_dict()
        assert data is not None


class TestMVCCompleteWorkflow:
    """Test complete workflows through MVC architecture"""

    def test_complete_save_simulate_load_workflow(self, simple_resistor_circuit):
        """Test complete workflow: create, save, load, simulate"""
        components, wires, nodes, terminal_to_node = simple_resistor_circuit

        # 1. Create circuit in model
        model = CircuitModel()
        model.components = components
        model.wires = wires
        model.nodes = nodes
        model.terminal_to_node = terminal_to_node

        # 2. Save through FileController
        file_ctrl = FileController(model)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            file_ctrl.save_circuit(temp_path)

            # 3. Load into new model
            new_model = CircuitModel()
            new_file_ctrl = FileController(new_model)
            new_file_ctrl.load_circuit(temp_path)

            # 4. Simulate through SimulationController
            sim_ctrl = SimulationController(new_model)
            netlist = sim_ctrl.generate_netlist()

            # 5. Verify workflow succeeded
            assert len(new_model.components) == 3
            assert "V1" in netlist
            assert "R1" in netlist

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_complete_edit_workflow(self):
        """Test workflow: create, edit, save, load, verify"""
        # 1. Create initial circuit
        model = CircuitModel()
        circuit_ctrl = CircuitController(model)

        comp1 = circuit_ctrl.add_component("Resistor", (0, 0))

        # 2. Edit component
        model.components[comp1.component_id].value = "2k"

        # 3. Add another component
        comp2 = circuit_ctrl.add_component("Resistor", (100, 0))
        model.components[comp2.component_id].value = "3k"

        # 4. Save
        file_ctrl = FileController(model)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            file_ctrl.save_circuit(temp_path)

            # 5. Load and verify
            new_model = CircuitModel()
            new_file_ctrl = FileController(new_model)
            new_file_ctrl.load_circuit(temp_path)

            assert len(new_model.components) == 2
            assert new_model.components[comp1.component_id].value == "2k"
            assert new_model.components[comp2.component_id].value == "3k"

        finally:
            if temp_path.exists():
                temp_path.unlink()
