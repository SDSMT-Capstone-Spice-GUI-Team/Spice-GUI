"""Tests for MoveWaypointCommand undo/redo (issue #483).

Waypoint drags should be undoable/redoable through the command pattern.
These tests validate the model-layer command without requiring a Qt canvas.
"""

from controllers.circuit_controller import CircuitController
from controllers.commands import MoveWaypointCommand
from models.circuit import CircuitModel
from tests.conftest import make_component, make_wire


def _make_controller_with_wire():
    """Create a controller with two components and a wire between them."""
    model = CircuitModel()
    ctrl = CircuitController(model)
    ctrl.add_component("Resistor", (0.0, 0.0))
    ctrl.add_component("Resistor", (200.0, 0.0))
    comp_ids = list(model.components.keys())
    ctrl.add_wire(comp_ids[0], 0, comp_ids[1], 0)
    # Set some initial waypoints on the wire
    initial_wps = [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)]
    ctrl.update_wire_waypoints(0, initial_wps)
    return ctrl, initial_wps


class TestMoveWaypointCommand:
    """MoveWaypointCommand should record before/after waypoints for undo."""

    def test_command_exists(self):
        """MoveWaypointCommand should be importable and constructable."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        assert cmd is not None

    def test_execute_updates_waypoints(self):
        """execute() should set the new waypoints on the wire model."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        cmd.execute()
        assert ctrl.model.wires[0].waypoints == new

    def test_undo_restores_old_waypoints(self):
        """undo() should restore the old waypoints."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        cmd.execute()
        cmd.undo()
        assert ctrl.model.wires[0].waypoints == old

    def test_redo_reapplies_new_waypoints(self):
        """execute() after undo() should reapply the new waypoints."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        cmd.execute()
        cmd.undo()
        cmd.execute()
        assert ctrl.model.wires[0].waypoints == new

    def test_execute_locks_wire(self):
        """execute() should lock the wire to prevent auto-reroute."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        cmd.execute()
        assert ctrl.model.wires[0].locked is True

    def test_undo_keeps_wire_locked(self):
        """undo() should keep the wire locked (manual edit history)."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        cmd.execute()
        cmd.undo()
        assert ctrl.model.wires[0].locked is True

    def test_push_already_executed_enables_undo(self):
        """push_already_executed should allow undo without calling execute."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        # Simulate what the canvas does: sync model then push command
        ctrl.update_wire_waypoints(0, new)
        cmd = MoveWaypointCommand(ctrl, 0, old, new)
        ctrl.push_already_executed(cmd)
        # Undo should restore old waypoints
        ctrl.undo()
        assert ctrl.model.wires[0].waypoints == old

    def test_out_of_range_wire_index_is_safe(self):
        """Command should not crash with invalid wire index."""
        ctrl, old = _make_controller_with_wire()
        new = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)]
        cmd = MoveWaypointCommand(ctrl, 99, old, new)
        cmd.execute()  # Should not raise
        cmd.undo()  # Should not raise

    def test_description(self):
        """get_description() should return a meaningful string."""
        ctrl, old = _make_controller_with_wire()
        cmd = MoveWaypointCommand(ctrl, 0, old, old)
        assert "waypoint" in cmd.get_description().lower()
