"""Integration tests for MVC observer pattern and controller interactions.

Covers:
- Observer propagation (events fired for each mutation)
- Cross-controller coordination (shared model reference)
- Undo/redo across mixed operations
- File round-trip with full controller state
"""

import tempfile
from pathlib import Path

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import (
    AddComponentCommand,
    AddWireCommand,
    ChangeValueCommand,
    CompoundCommand,
    DeleteComponentCommand,
    MoveComponentCommand,
)
from controllers.file_controller import FileController
from controllers.simulation_controller import SimulationController
from models.annotation import AnnotationData
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class EventLog:
    """Simple observer that records (event, data) tuples."""

    def __init__(self):
        self.events = []

    def __call__(self, event, data):
        self.events.append((event, data))

    def count(self, event_name):
        return sum(1 for e, _ in self.events if e == event_name)

    def last(self):
        return self.events[-1] if self.events else None

    def clear(self):
        self.events.clear()


# ---------------------------------------------------------------------------
# Observer propagation
# ---------------------------------------------------------------------------


class TestObserverPropagation:
    def test_add_component_fires_event(self):
        ctrl = CircuitController()
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.add_component("Resistor", (0, 0))
        assert log.count("component_added") == 1

    def test_remove_component_fires_event(self):
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.remove_component(comp.component_id)
        assert log.count("component_removed") == 1

    def test_remove_component_fires_wire_removed_for_connected_wires(self):
        ctrl = CircuitController()
        c1 = ctrl.add_component("Resistor", (0, 0))
        c2 = ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire(c1.component_id, 0, c2.component_id, 0)

        log = EventLog()
        ctrl.add_observer(log)
        ctrl.remove_component(c1.component_id)
        assert log.count("wire_removed") == 1
        assert log.count("component_removed") == 1

    def test_move_component_fires_event(self):
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.move_component(comp.component_id, (50, 50))
        assert log.count("component_moved") == 1

    def test_rotate_component_fires_event(self):
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.rotate_component(comp.component_id)
        assert log.count("component_rotated") == 1

    def test_flip_component_fires_event(self):
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.flip_component(comp.component_id, horizontal=True)
        assert log.count("component_flipped") == 1

    def test_value_change_fires_event(self):
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.update_component_value(comp.component_id, "2k")
        assert log.count("component_value_changed") == 1

    def test_add_wire_fires_event(self):
        ctrl = CircuitController()
        c1 = ctrl.add_component("Resistor", (0, 0))
        c2 = ctrl.add_component("Resistor", (100, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.add_wire(c1.component_id, 0, c2.component_id, 0)
        assert log.count("wire_added") == 1

    def test_clear_circuit_fires_event(self):
        ctrl = CircuitController()
        ctrl.add_component("Resistor", (0, 0))
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.clear_circuit()
        assert log.count("circuit_cleared") == 1

    def test_multiple_observers_all_receive_events(self):
        ctrl = CircuitController()
        log1 = EventLog()
        log2 = EventLog()
        ctrl.add_observer(log1)
        ctrl.add_observer(log2)
        ctrl.add_component("Resistor", (0, 0))
        assert log1.count("component_added") == 1
        assert log2.count("component_added") == 1

    def test_remove_observer_stops_notifications(self):
        ctrl = CircuitController()
        log = EventLog()
        ctrl.add_observer(log)
        ctrl.add_component("Resistor", (0, 0))
        assert log.count("component_added") == 1

        ctrl.remove_observer(log)
        ctrl.add_component("Resistor", (100, 0))
        assert log.count("component_added") == 1  # still 1, not 2


# ---------------------------------------------------------------------------
# Cross-controller coordination
# ---------------------------------------------------------------------------


class TestCrossControllerCoordination:
    def test_all_controllers_share_model(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sc = SimulationController(model)
        fc = FileController(model)
        assert cc.model is model
        assert sc.model is model
        assert fc.model is model

    def test_circuit_changes_visible_to_simulation(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sc = SimulationController(model)
        comp = cc.add_component("Resistor", (0, 0))
        assert comp.component_id in sc.model.components

    def test_file_load_updates_model_for_circuit_controller(self, tmp_path):
        model = CircuitModel()
        cc = CircuitController(model)
        fc = FileController(model, circuit_ctrl=cc)

        # Build and save a circuit
        cc.add_component("Resistor", (0, 0))
        filepath = tmp_path / "test.json"
        fc.save_circuit(filepath)

        # Create fresh controllers sharing a new model
        model2 = CircuitModel()
        cc2 = CircuitController(model2)
        fc2 = FileController(model2, circuit_ctrl=cc2)

        log = EventLog()
        cc2.add_observer(log)

        fc2.load_circuit(filepath)
        assert len(model2.components) == 1
        assert log.count("model_loaded") == 1

    def test_clear_circuit_resets_for_all(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sc = SimulationController(model)
        fc = FileController(model)

        cc.add_component("Resistor", (0, 0))
        assert len(model.components) == 1

        cc.clear_circuit()
        assert len(model.components) == 0
        assert len(sc.model.components) == 0
        assert len(fc.model.components) == 0


# ---------------------------------------------------------------------------
# Undo/redo across operations
# ---------------------------------------------------------------------------


class TestUndoRedoIntegration:
    def test_mixed_operations_undo_in_correct_order(self):
        ctrl = CircuitController()

        # Add component via command
        add_cmd = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(add_cmd)
        comp_id = add_cmd.component_id
        assert comp_id in ctrl.model.components

        # Move via command
        move_cmd = MoveComponentCommand(ctrl, comp_id, (100, 100))
        ctrl.execute_command(move_cmd)
        assert ctrl.model.components[comp_id].position == (100, 100)

        # Change value via command
        val_cmd = ChangeValueCommand(ctrl, comp_id, "2k")
        ctrl.execute_command(val_cmd)
        assert ctrl.model.components[comp_id].value == "2k"

        # Undo value change
        ctrl.undo()
        assert ctrl.model.components[comp_id].value == "1k"

        # Undo move
        ctrl.undo()
        assert ctrl.model.components[comp_id].position == (0, 0)

        # Undo add
        ctrl.undo()
        assert comp_id not in ctrl.model.components

    def test_redo_stack_cleared_on_new_command(self):
        ctrl = CircuitController()
        add_cmd = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(add_cmd)
        ctrl.undo()
        assert ctrl.can_redo()

        # New command clears redo
        add_cmd2 = AddComponentCommand(ctrl, "Capacitor", (100, 0))
        ctrl.execute_command(add_cmd2)
        assert not ctrl.can_redo()

    def test_undo_depth_limit(self):
        ctrl = CircuitController(max_undo_depth=5)
        for i in range(10):
            cmd = AddComponentCommand(ctrl, "Resistor", (i * 10, 0))
            ctrl.execute_command(cmd)

        assert ctrl.undo_manager.get_undo_count() == 5

    def test_compound_command_undoes_atomically(self):
        ctrl = CircuitController()

        # Create compound: add two components
        cmd1 = AddComponentCommand(ctrl, "Resistor", (0, 0))
        cmd2 = AddComponentCommand(ctrl, "Capacitor", (100, 0))
        compound = CompoundCommand([cmd1, cmd2], "Add pair")
        ctrl.execute_command(compound)

        assert len(ctrl.model.components) == 2

        # Single undo removes both
        ctrl.undo()
        assert len(ctrl.model.components) == 0

    def test_add_wire_undo(self):
        ctrl = CircuitController()
        c1 = ctrl.add_component("Resistor", (0, 0))
        c2 = ctrl.add_component("Resistor", (100, 0))

        wire_cmd = AddWireCommand(ctrl, c1.component_id, 0, c2.component_id, 0)
        ctrl.execute_command(wire_cmd)
        assert len(ctrl.model.wires) == 1

        ctrl.undo()
        assert len(ctrl.model.wires) == 0

    def test_delete_component_undo_restores_wires(self):
        ctrl = CircuitController()
        c1 = ctrl.add_component("Resistor", (0, 0))
        c2 = ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire(c1.component_id, 0, c2.component_id, 0)

        del_cmd = DeleteComponentCommand(ctrl, c1.component_id)
        ctrl.execute_command(del_cmd)
        assert c1.component_id not in ctrl.model.components
        assert len(ctrl.model.wires) == 0

        ctrl.undo()
        assert c1.component_id in ctrl.model.components
        assert len(ctrl.model.wires) == 1


# ---------------------------------------------------------------------------
# File round-trip with controller state
# ---------------------------------------------------------------------------


class TestFileRoundTrip:
    def test_save_load_preserves_components_and_wires(self, tmp_path):
        model = CircuitModel()
        cc = CircuitController(model)
        fc = FileController(model)

        c1 = cc.add_component("Voltage Source", (0, 0))
        c2 = cc.add_component("Resistor", (100, 0))
        gnd = cc.add_component("Ground", (100, 100))
        cc.add_wire(c1.component_id, 0, c2.component_id, 0)
        cc.add_wire(c2.component_id, 1, gnd.component_id, 0)
        cc.add_wire(c1.component_id, 1, gnd.component_id, 0)

        filepath = tmp_path / "circuit.json"
        fc.save_circuit(filepath)

        model2 = CircuitModel()
        fc2 = FileController(model2)
        fc2.load_circuit(filepath)

        assert len(model2.components) == 3
        assert len(model2.wires) == 3
        assert c1.component_id in model2.components
        assert c2.component_id in model2.components
        assert gnd.component_id in model2.components

    def test_analysis_settings_survive_save_load(self, tmp_path):
        model = CircuitModel()
        sc = SimulationController(model)
        fc = FileController(model)

        sc.set_analysis("Transient", {"duration": "1ms", "step": "1us"})
        filepath = tmp_path / "circuit.json"
        fc.save_circuit(filepath)

        model2 = CircuitModel()
        fc2 = FileController(model2)
        fc2.load_circuit(filepath)

        assert model2.analysis_type == "Transient"
        assert model2.analysis_params["duration"] == "1ms"
        assert model2.analysis_params["step"] == "1us"

    def test_annotation_state_persists(self, tmp_path):
        model = CircuitModel()
        cc = CircuitController(model)
        fc = FileController(model)

        cc.add_annotation(AnnotationData(text="Test Note", x=50.0, y=75.0, font_size=14, bold=True, color="#FF0000"))
        filepath = tmp_path / "circuit.json"
        fc.save_circuit(filepath)

        model2 = CircuitModel()
        fc2 = FileController(model2)
        fc2.load_circuit(filepath)

        assert len(model2.annotations) == 1
        ann = model2.annotations[0]
        assert ann.text == "Test Note"
        assert ann.x == pytest.approx(50.0)
        assert ann.y == pytest.approx(75.0)
        assert ann.font_size == 14
        assert ann.bold is True
        assert ann.color == "#FF0000"

    def test_new_circuit_resets_all_state(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sc = SimulationController(model)
        fc = FileController(model)

        cc.add_component("Resistor", (0, 0))
        cc.add_annotation(AnnotationData(text="Note"))
        sc.set_analysis("Transient", {"duration": "1ms"})

        fc.new_circuit()

        assert len(model.components) == 0
        assert len(model.wires) == 0
        assert len(model.annotations) == 0
        assert fc.current_file is None

    def test_component_values_preserved(self, tmp_path):
        model = CircuitModel()
        cc = CircuitController(model)
        fc = FileController(model)

        comp = cc.add_component("Resistor", (0, 0))
        cc.update_component_value(comp.component_id, "4.7k")
        cc.rotate_component(comp.component_id, clockwise=True)

        filepath = tmp_path / "circuit.json"
        fc.save_circuit(filepath)

        model2 = CircuitModel()
        fc2 = FileController(model2)
        fc2.load_circuit(filepath)

        restored = model2.components[comp.component_id]
        assert restored.value == "4.7k"
        assert restored.rotation == 90
