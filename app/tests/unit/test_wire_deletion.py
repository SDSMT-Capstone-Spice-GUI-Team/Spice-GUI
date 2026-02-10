"""Tests for wire deletion model sync and undo/redo integration.

Covers issue #154: wire deletion should update the model, support undo/redo,
and survive a save/load round-trip.
"""

import json

from controllers.circuit_controller import CircuitController
from controllers.commands import DeleteWireCommand
from models.circuit import CircuitModel


def _make_circuit_with_wire():
    """Helper: create a model with two resistors connected by a wire."""
    model = CircuitModel()
    ctrl = CircuitController(model)
    r1 = ctrl.add_component("Resistor", (0, 0))
    r2 = ctrl.add_component("Resistor", (200, 0))
    ctrl.add_wire(r1.component_id, 1, r2.component_id, 0)
    return model, ctrl, r1, r2


class TestWireDeletionModelSync:
    """Wire deletion must update CircuitModel.wires."""

    def test_remove_wire_updates_model(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        assert len(model.wires) == 1

        ctrl.remove_wire(0)

        assert len(model.wires) == 0

    def test_remove_wire_via_command_updates_model(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        assert len(model.wires) == 1

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)

        assert len(model.wires) == 0

    def test_remove_wire_rebuilds_nodes(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        # Before deletion, nodes should exist
        assert len(model.nodes) > 0

        ctrl.remove_wire(0)

        # After deletion with no wires, nodes should be rebuilt (possibly empty or ground-only)
        # The key assertion: no stale nodes referencing deleted wire
        for node in model.nodes:
            assert len(node.wires) == 0 or all(w in model.wires for w in node.wires)


class TestWireDeletionUndoRedo:
    """Wire deletion via command must support Ctrl+Z / Ctrl+Y."""

    def test_undo_restores_wire(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        original_wire = model.wires[0]
        original_start = original_wire.start_component_id
        original_end = original_wire.end_component_id

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)
        assert len(model.wires) == 0

        ctrl.undo()
        assert len(model.wires) == 1
        restored = model.wires[0]
        assert restored.start_component_id == original_start
        assert restored.end_component_id == original_end

    def test_redo_re_deletes_wire(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)
        assert len(model.wires) == 0

        ctrl.undo()
        assert len(model.wires) == 1

        ctrl.redo()
        assert len(model.wires) == 0

    def test_undo_description(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)

        assert ctrl.get_undo_description() == "Delete wire"


class TestWireDeletionSaveLoadRoundTrip:
    """Deleted wires must NOT reappear after save/load."""

    def test_deleted_wire_not_in_saved_data(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        assert len(model.wires) == 1

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)
        assert len(model.wires) == 0

        data = model.to_dict()
        assert len(data["wires"]) == 0

    def test_save_load_roundtrip(self, tmp_path):
        model, ctrl, r1, r2 = _make_circuit_with_wire()

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)

        # Save to file
        filepath = tmp_path / "test_circuit.json"
        data = model.to_dict()
        with open(filepath, "w") as f:
            json.dump(data, f)

        # Load into a fresh model
        with open(filepath, "r") as f:
            loaded_data = json.load(f)
        loaded_model = CircuitModel.from_dict(loaded_data)

        assert len(loaded_model.wires) == 0
        assert len(loaded_model.components) == 2

    def test_undone_wire_survives_roundtrip(self, tmp_path):
        """Wire restored by undo should persist through save/load."""
        model, ctrl, r1, r2 = _make_circuit_with_wire()

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)
        ctrl.undo()  # restore the wire

        filepath = tmp_path / "test_circuit.json"
        data = model.to_dict()
        with open(filepath, "w") as f:
            json.dump(data, f)

        with open(filepath, "r") as f:
            loaded_data = json.load(f)
        loaded_model = CircuitModel.from_dict(loaded_data)

        assert len(loaded_model.wires) == 1


class TestMultipleWireDeletion:
    """Deleting multiple wires in sequence preserves correct indices."""

    def test_delete_multiple_wires(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (200, 0))
        r3 = ctrl.add_component("Resistor", (400, 0))
        ctrl.add_wire(r1.component_id, 1, r2.component_id, 0)
        ctrl.add_wire(r2.component_id, 1, r3.component_id, 0)
        assert len(model.wires) == 2

        # Delete second wire first (higher index), then first
        cmd2 = DeleteWireCommand(ctrl, 1)
        ctrl.execute_command(cmd2)
        assert len(model.wires) == 1

        cmd1 = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd1)
        assert len(model.wires) == 0

    def test_undo_multiple_wire_deletions(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (200, 0))
        r3 = ctrl.add_component("Resistor", (400, 0))
        ctrl.add_wire(r1.component_id, 1, r2.component_id, 0)
        ctrl.add_wire(r2.component_id, 1, r3.component_id, 0)

        cmd2 = DeleteWireCommand(ctrl, 1)
        ctrl.execute_command(cmd2)
        cmd1 = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd1)
        assert len(model.wires) == 0

        # Undo both
        ctrl.undo()
        assert len(model.wires) == 1
        ctrl.undo()
        assert len(model.wires) == 2


class TestObserverNotification:
    """Controller must fire wire_removed when deleting wires."""

    def test_wire_removed_event_fires(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()
        events = []

        def observer(event, data):
            events.append((event, data))

        ctrl.add_observer(observer)

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)

        wire_removed_events = [(e, d) for e, d in events if e == "wire_removed"]
        assert len(wire_removed_events) == 1
        assert wire_removed_events[0][1] == 0  # wire index

    def test_undo_fires_wire_added_event(self):
        model, ctrl, r1, r2 = _make_circuit_with_wire()

        cmd = DeleteWireCommand(ctrl, 0)
        ctrl.execute_command(cmd)

        events = []

        def observer(event, data):
            events.append((event, data))

        ctrl.add_observer(observer)
        ctrl.undo()

        wire_added_events = [(e, d) for e, d in events if e == "wire_added"]
        assert len(wire_added_events) == 1
