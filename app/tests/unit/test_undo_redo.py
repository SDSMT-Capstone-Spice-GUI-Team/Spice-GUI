"""Tests for undo/redo system."""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import (
    AddComponentCommand,
    AddWireCommand,
    ChangeValueCommand,
    CompoundCommand,
    DeleteComponentCommand,
    DeleteWireCommand,
    FlipComponentCommand,
    MoveComponentCommand,
    PasteCommand,
    RerouteWireCommand,
    RotateComponentCommand,
    SetRotationCommand,
    ToggleWireLockCommand,
    UpdateInitialConditionCommand,
    UpdateWaveformCommand,
)
from controllers.undo_manager import UndoManager
from models.circuit import CircuitModel


class TestUndoManager:
    """Test the UndoManager class."""

    def test_initial_state(self):
        """Test that undo manager starts with empty stacks."""
        manager = UndoManager()
        assert not manager.can_undo()
        assert not manager.can_redo()
        assert manager.get_undo_count() == 0
        assert manager.get_redo_count() == 0

    def test_max_depth(self):
        """Test that undo stack respects max depth limit."""
        manager = UndoManager(max_depth=3)
        model = CircuitModel()
        controller = CircuitController(model)
        controller.undo_manager = manager

        # Add 5 components (exceeds max depth of 3)
        for i in range(5):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10, 0))
            manager.execute(cmd)

        # Should only keep last 3 commands
        assert manager.get_undo_count() == 3

    def test_redo_cleared_on_new_action(self):
        """Test that redo stack is cleared when a new action is performed."""
        manager = UndoManager()
        model = CircuitModel()
        controller = CircuitController(model)
        controller.undo_manager = manager

        # Execute command, undo it
        cmd1 = AddComponentCommand(controller, "Resistor", (0, 0))
        manager.execute(cmd1)
        manager.undo()

        assert manager.can_redo()

        # Execute new command - redo stack should be cleared
        cmd2 = AddComponentCommand(controller, "Capacitor", (10, 0))
        manager.execute(cmd2)

        assert not manager.can_redo()
        assert manager.get_redo_count() == 0

    def test_undo_description(self):
        """Test getting description of undoable command."""
        manager = UndoManager()
        model = CircuitModel()
        controller = CircuitController(model)
        controller.undo_manager = manager

        cmd = AddComponentCommand(controller, "Resistor", (0, 0))
        manager.execute(cmd)

        desc = manager.get_undo_description()
        assert desc == "Add Resistor"

    def test_clear(self):
        """Test clearing undo/redo history."""
        manager = UndoManager()
        model = CircuitModel()
        controller = CircuitController(model)
        controller.undo_manager = manager

        cmd = AddComponentCommand(controller, "Resistor", (0, 0))
        manager.execute(cmd)
        manager.undo()

        # After undo, command is in redo stack
        assert not manager.can_undo()  # Undo stack is empty
        assert manager.can_redo()  # Redo stack has the command

        manager.clear()

        assert not manager.can_undo()
        assert not manager.can_redo()


class TestAddComponentCommand:
    """Test adding components with undo."""

    def test_execute_and_undo(self):
        """Test adding and removing a component."""
        model = CircuitModel()
        controller = CircuitController(model)

        cmd = AddComponentCommand(controller, "Resistor", (0, 0))
        cmd.execute()

        # Component should be added
        assert len(model.components) == 1
        assert cmd.component_id is not None
        assert cmd.component_id in model.components

        # Undo should remove it
        cmd.undo()
        assert len(model.components) == 0


class TestDeleteComponentCommand:
    """Test deleting components with undo."""

    def test_execute_and_undo(self):
        """Test deleting and restoring a component."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add a component first
        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Delete it via command
        cmd = DeleteComponentCommand(controller, comp_id)
        cmd.execute()

        assert len(model.components) == 0

        # Undo should restore it
        cmd.undo()
        assert len(model.components) == 1
        assert comp_id in model.components

    def test_delete_with_wires(self):
        """Test that deleting a component also handles connected wires."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add components and wire
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (10, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)

        # Delete first component (should also delete wire)
        cmd = DeleteComponentCommand(controller, r1.component_id)
        cmd.execute()

        assert len(model.components) == 1  # Only r2 remains
        assert len(model.wires) == 0  # Wire was deleted

        # Undo should restore both component and wire
        cmd.undo()
        assert len(model.components) == 2
        assert len(model.wires) == 1


class TestMoveComponentCommand:
    """Test moving components with undo."""

    def test_execute_and_undo(self):
        """Test moving a component and undoing the move."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Move component
        cmd = MoveComponentCommand(controller, comp_id, (100, 100))
        cmd.execute()

        assert model.components[comp_id].position == (100, 100)

        # Undo should restore original position
        cmd.undo()
        assert model.components[comp_id].position == (0, 0)


class TestRotateComponentCommand:
    """Test rotating components with undo."""

    def test_execute_and_undo(self):
        """Test rotating a component and undoing the rotation."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Initial rotation is 0
        assert model.components[comp_id].rotation == 0

        # Rotate clockwise
        cmd = RotateComponentCommand(controller, comp_id, clockwise=True)
        cmd.execute()

        assert model.components[comp_id].rotation == 90

        # Undo should rotate back
        cmd.undo()
        assert model.components[comp_id].rotation == 0


class TestFlipComponentCommand:
    """Test flipping components with undo."""

    def test_execute_and_undo_horizontal(self):
        """Test flipping a component horizontally."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        assert not model.components[comp_id].flip_h

        # Flip horizontally
        cmd = FlipComponentCommand(controller, comp_id, horizontal=True)
        cmd.execute()

        assert model.components[comp_id].flip_h

        # Undo should flip back
        cmd.undo()
        assert not model.components[comp_id].flip_h


class TestChangeValueCommand:
    """Test changing component values with undo."""

    def test_execute_and_undo(self):
        """Test changing a component value and undoing the change."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id
        original_value = comp.value

        # Change value
        cmd = ChangeValueCommand(controller, comp_id, "10k")
        cmd.execute()

        assert model.components[comp_id].value == "10k"

        # Undo should restore original value
        cmd.undo()
        assert model.components[comp_id].value == original_value


class TestWireCommands:
    """Test wire add/delete commands."""

    def test_add_wire_and_undo(self):
        """Test adding and removing a wire."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add components first
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (10, 0))

        # Add wire via command
        cmd = AddWireCommand(controller, r1.component_id, 0, r2.component_id, 0)
        cmd.execute()

        assert len(model.wires) == 1

        # Undo should remove wire
        cmd.undo()
        assert len(model.wires) == 0

    def test_delete_wire_and_undo(self):
        """Test deleting and restoring a wire."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add components and wire
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (10, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)

        assert len(model.wires) == 1

        # Delete wire via command
        cmd = DeleteWireCommand(controller, 0)
        cmd.execute()

        assert len(model.wires) == 0

        # Undo should restore wire
        cmd.undo()
        assert len(model.wires) == 1

    def test_delete_wire_undo_rebuilds_node_graph(self):
        """Test that undoing a wire deletion rebuilds terminal_to_node."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add components and wire
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (10, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)

        # Capture the node graph state before deletion
        nodes_before = len(model.nodes)
        t2n_before = dict(model.terminal_to_node)

        # Delete wire
        cmd = DeleteWireCommand(controller, 0)
        cmd.execute()

        # After deletion the connected terminals should no longer share a node
        assert len(model.wires) == 0

        # Undo should restore wire AND rebuild node graph
        cmd.undo()
        assert len(model.wires) == 1
        assert len(model.nodes) == nodes_before
        # The same terminal pairs should be mapped to nodes again
        for key in t2n_before:
            assert key in model.terminal_to_node, f"terminal {key} missing from terminal_to_node after undo"

    def test_delete_wire_undo_preserves_topology_for_simulation(self):
        """Test that delete-wire-undo cycle preserves node topology for simulation."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Build a simple circuit: R1 -- R2 -- GND
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (10, 0))
        controller.add_wire(r1.component_id, 1, r2.component_id, 0)

        # Snapshot state
        original_t2n = dict(model.terminal_to_node)

        # Delete and undo
        cmd = DeleteWireCommand(controller, 0)
        cmd.execute()
        cmd.undo()

        # Node graph should be equivalent to the original
        restored_t2n = dict(model.terminal_to_node)
        assert set(restored_t2n.keys()) == set(original_t2n.keys())


class TestPasteCommand:
    """Test paste command with undo."""

    def test_execute_and_undo(self):
        """Test pasting components and undoing the paste."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add and copy a component
        r1 = controller.add_component("Resistor", (0, 0))
        controller.copy_components([r1.component_id])

        # Paste via command
        cmd = PasteCommand(controller, offset=(40, 40))
        cmd.execute()

        # Should have original + pasted component
        assert len(model.components) == 2

        # Undo should remove pasted component
        cmd.undo()
        assert len(model.components) == 1
        assert r1.component_id in model.components


class TestCompoundCommand:
    """Test compound commands that group multiple operations."""

    def test_execute_and_undo_multiple(self):
        """Test executing and undoing multiple commands as one."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Create compound command with multiple adds
        commands = [
            AddComponentCommand(controller, "Resistor", (0, 0)),
            AddComponentCommand(controller, "Capacitor", (10, 0)),
            AddComponentCommand(controller, "Inductor", (20, 0)),
        ]
        compound = CompoundCommand(commands, "Add 3 components")

        # Execute all at once
        compound.execute()
        assert len(model.components) == 3

        # Undo all at once
        compound.undo()
        assert len(model.components) == 0


class TestCircuitControllerIntegration:
    """Test undo/redo integration with CircuitController."""

    def test_execute_command_through_controller(self):
        """Test executing commands through the controller."""
        model = CircuitModel()
        controller = CircuitController(model)

        cmd = AddComponentCommand(controller, "Resistor", (0, 0))
        controller.execute_command(cmd)

        # Command should be in undo stack
        assert controller.can_undo()
        assert len(model.components) == 1

        # Undo through controller
        controller.undo()
        assert not controller.can_undo()
        assert len(model.components) == 0

    def test_undo_redo_workflow(self):
        """Test a complete undo/redo workflow."""
        model = CircuitModel()
        controller = CircuitController(model)

        # Add components
        cmd1 = AddComponentCommand(controller, "Resistor", (0, 0))
        cmd2 = AddComponentCommand(controller, "Capacitor", (10, 0))

        controller.execute_command(cmd1)
        controller.execute_command(cmd2)

        assert len(model.components) == 2

        # Undo both
        controller.undo()
        assert len(model.components) == 1
        controller.undo()
        assert len(model.components) == 0

        # Redo both
        controller.redo()
        assert len(model.components) == 1
        controller.redo()
        assert len(model.components) == 2

    def test_clear_undo_history(self):
        """Test clearing undo history."""
        model = CircuitModel()
        controller = CircuitController(model)

        cmd = AddComponentCommand(controller, "Resistor", (0, 0))
        controller.execute_command(cmd)

        assert controller.can_undo()

        controller.clear_undo_history()

        assert not controller.can_undo()
        assert not controller.can_redo()


class TestToggleWireLockCommand:
    """Test wire lock/unlock command with undo."""

    def _setup_circuit_with_wire(self):
        """Helper to create a circuit with two components and one wire."""
        model = CircuitModel()
        controller = CircuitController(model)
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (100, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)
        return model, controller

    def test_lock_wire(self):
        """Locking a wire sets locked=True."""
        model, controller = self._setup_circuit_with_wire()
        assert not model.wires[0].locked

        cmd = ToggleWireLockCommand(controller, 0, True)
        cmd.execute()
        assert model.wires[0].locked

    def test_unlock_wire(self):
        """Unlocking a wire sets locked=False."""
        model, controller = self._setup_circuit_with_wire()
        model.wires[0].locked = True

        cmd = ToggleWireLockCommand(controller, 0, False)
        cmd.execute()
        assert not model.wires[0].locked

    def test_undo_lock(self):
        """Undo restores previous locked state."""
        model, controller = self._setup_circuit_with_wire()

        cmd = ToggleWireLockCommand(controller, 0, True)
        cmd.execute()
        assert model.wires[0].locked

        cmd.undo()
        assert not model.wires[0].locked

    def test_undo_unlock(self):
        """Undo of unlock re-locks the wire."""
        model, controller = self._setup_circuit_with_wire()
        model.wires[0].locked = True

        cmd = ToggleWireLockCommand(controller, 0, False)
        cmd.execute()
        assert not model.wires[0].locked

        cmd.undo()
        assert model.wires[0].locked

    def test_description_lock(self):
        """Lock command has correct description."""
        model, controller = self._setup_circuit_with_wire()
        cmd = ToggleWireLockCommand(controller, 0, True)
        assert cmd.get_description() == "Lock wire"

    def test_description_unlock(self):
        """Unlock command has correct description."""
        model, controller = self._setup_circuit_with_wire()
        cmd = ToggleWireLockCommand(controller, 0, False)
        assert cmd.get_description() == "Unlock wire"

    def test_invalid_wire_index_no_op(self):
        """Toggle on invalid wire index does nothing."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = ToggleWireLockCommand(controller, 99, True)
        cmd.execute()  # Should not raise
        cmd.undo()  # Should not raise

    def test_lock_via_controller_undoable(self):
        """Lock executed through controller is undoable."""
        model, controller = self._setup_circuit_with_wire()

        cmd = ToggleWireLockCommand(controller, 0, True)
        controller.execute_command(cmd)

        assert model.wires[0].locked
        assert controller.can_undo()

        controller.undo()
        assert not model.wires[0].locked


class TestRerouteWireCommand:
    """Test reroute wire command with undo."""

    def _setup_circuit_with_wire(self):
        """Helper to create a circuit with two components and one wire with waypoints."""
        model = CircuitModel()
        controller = CircuitController(model)
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (100, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)
        # Simulate existing waypoints on the wire
        model.wires[0].waypoints = [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]
        return model, controller

    def test_execute_clears_waypoints(self):
        """Reroute command clears waypoints to trigger fresh pathfinding."""
        model, controller = self._setup_circuit_with_wire()
        assert model.wires[0].waypoints == [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]

        cmd = RerouteWireCommand(controller, 0)
        cmd.execute()

        # Waypoints cleared (canvas handler would run pathfinding)
        assert model.wires[0].waypoints == []

    def test_undo_restores_old_waypoints(self):
        """Undo restores the waypoints that existed before reroute."""
        model, controller = self._setup_circuit_with_wire()
        original_waypoints = [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]

        cmd = RerouteWireCommand(controller, 0)
        cmd.execute()

        # Undo should restore original waypoints
        cmd.undo()
        assert model.wires[0].waypoints == original_waypoints

    def test_redo_clears_waypoints_again(self):
        """Redo after undo clears waypoints again."""
        model, controller = self._setup_circuit_with_wire()

        cmd = RerouteWireCommand(controller, 0)
        cmd.execute()
        cmd.undo()
        assert model.wires[0].waypoints == [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]

        cmd.execute()
        assert model.wires[0].waypoints == []

    def test_description(self):
        """Command has correct description."""
        model, controller = self._setup_circuit_with_wire()
        cmd = RerouteWireCommand(controller, 0)
        assert cmd.get_description() == "Reroute wire"

    def test_invalid_wire_index_no_op(self):
        """Reroute with invalid index does nothing."""
        model = CircuitModel()
        controller = CircuitController(model)

        cmd = RerouteWireCommand(controller, 99)
        cmd.execute()  # Should not raise
        cmd.undo()  # Should not raise

    def test_reroute_preserves_other_wire_data(self):
        """Reroute only affects waypoints, not connection endpoints."""
        model, controller = self._setup_circuit_with_wire()
        wire = model.wires[0]
        start_comp = wire.start_component_id
        start_term = wire.start_terminal
        end_comp = wire.end_component_id
        end_term = wire.end_terminal

        cmd = RerouteWireCommand(controller, 0)
        cmd.execute()

        assert wire.start_component_id == start_comp
        assert wire.start_terminal == start_term
        assert wire.end_component_id == end_comp
        assert wire.end_terminal == end_term

    def test_reroute_via_controller_is_undoable(self):
        """Reroute executed through controller can be undone with controller.undo()."""
        model, controller = self._setup_circuit_with_wire()
        original_waypoints = [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]

        cmd = RerouteWireCommand(controller, 0)
        controller.execute_command(cmd)

        assert controller.can_undo()

        controller.undo()
        assert model.wires[0].waypoints == original_waypoints

    def test_compound_reroute_multiple_wires(self):
        """Rerouting multiple wires as a compound command is undoable as one step."""
        model = CircuitModel()
        controller = CircuitController(model)
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (100, 0))
        r3 = controller.add_component("Resistor", (200, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)
        controller.add_wire(r2.component_id, 1, r3.component_id, 0)
        model.wires[0].waypoints = [(0.0, 0.0), (100.0, 0.0)]
        model.wires[1].waypoints = [(100.0, 0.0), (200.0, 0.0)]

        commands = [
            RerouteWireCommand(controller, 0),
            RerouteWireCommand(controller, 1),
        ]
        compound = CompoundCommand(commands, "Reroute 2 wires")
        controller.execute_command(compound)

        assert model.wires[0].waypoints == []
        assert model.wires[1].waypoints == []

        controller.undo()
        assert model.wires[0].waypoints == [(0.0, 0.0), (100.0, 0.0)]
        assert model.wires[1].waypoints == [(100.0, 0.0), (200.0, 0.0)]


# ===========================================================================
# Stale State Validation  (#505)
# ===========================================================================


class TestStaleStateValidation:
    """Issue #505: commands must not crash when model state is stale."""

    def test_delete_missing_component_skips(self):
        """DeleteComponentCommand on non-existent component should not crash."""
        controller = CircuitController()
        cmd = DeleteComponentCommand(controller, "BOGUS")
        cmd.execute()
        assert cmd.component_data is None

    def test_move_missing_component_skips(self):
        """MoveComponentCommand on non-existent component should not crash."""
        controller = CircuitController()
        cmd = MoveComponentCommand(controller, "BOGUS", (50, 50))
        cmd.execute()  # should not raise

    def test_move_undo_missing_component_skips(self):
        """MoveComponentCommand.undo after component deleted should not crash."""
        controller = CircuitController()
        comp = controller.add_component("Resistor", (0, 0))
        cmd = MoveComponentCommand(controller, comp.component_id, (50, 50))
        cmd.execute()
        controller.remove_component(comp.component_id)
        cmd.undo()  # component gone; should not crash

    def test_rotate_missing_component_skips(self):
        """RotateComponentCommand on non-existent component should not crash."""
        controller = CircuitController()
        cmd = RotateComponentCommand(controller, "BOGUS")
        cmd.execute()
        cmd.undo()

    def test_flip_missing_component_skips(self):
        """FlipComponentCommand on non-existent component should not crash."""
        controller = CircuitController()
        cmd = FlipComponentCommand(controller, "BOGUS")
        cmd.execute()
        cmd.undo()

    def test_change_value_missing_component_skips(self):
        """ChangeValueCommand on non-existent component should not crash."""
        controller = CircuitController()
        cmd = ChangeValueCommand(controller, "BOGUS", "10k")
        cmd.execute()
        assert cmd.old_value is None

    def test_change_value_undo_missing_component_skips(self):
        """ChangeValueCommand.undo after component deleted should not crash."""
        controller = CircuitController()
        comp = controller.add_component("Resistor", (0, 0))
        cmd = ChangeValueCommand(controller, comp.component_id, "10k")
        cmd.execute()
        controller.remove_component(comp.component_id)
        cmd.undo()  # component gone; should not crash

    def test_add_wire_missing_endpoint_skips(self):
        """AddWireCommand with non-existent endpoint should not crash."""
        controller = CircuitController()
        controller.add_component("Resistor", (0, 0))
        cmd = AddWireCommand(controller, "R1", 0, "BOGUS", 0)
        cmd.execute()
        assert cmd.wire_index is None

    def test_delete_wire_out_of_range_skips(self):
        """DeleteWireCommand with out-of-range index should not crash."""
        controller = CircuitController()
        cmd = DeleteWireCommand(controller, 99)
        cmd.execute()
        assert cmd.wire_data is None

    def test_delete_wire_undo_missing_endpoint_skips(self):
        """DeleteWireCommand.undo when endpoint component was deleted should not crash."""
        controller = CircuitController()
        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (100, 0))
        controller.add_wire(r1.component_id, 0, r2.component_id, 0)
        cmd = DeleteWireCommand(controller, 0)
        cmd.execute()
        controller.remove_component(r2.component_id)
        cmd.undo()  # R2 gone; should not crash, wire not restored
        assert len(controller.model.wires) == 0

    def test_toggle_wire_lock_out_of_range_skips(self):
        """ToggleWireLockCommand with out-of-range index should not crash."""
        controller = CircuitController()
        cmd = ToggleWireLockCommand(controller, 99, True)
        cmd.execute()
        cmd.undo()

    def test_reroute_wire_out_of_range_skips(self):
        """RerouteWireCommand with out-of-range index should not crash."""
        controller = CircuitController()
        cmd = RerouteWireCommand(controller, 99)
        cmd.execute()
        cmd.undo()


# ===========================================================================
# Full Workflow Integration Tests (#814)
# ===========================================================================


class TestFullUndoRedoWorkflow:
    """Issue #814: verify all model-mutating operations are undoable via controller."""

    def test_add_component_undoable(self):
        """Adding a component via execute_command is fully undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        cmd = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(cmd)

        assert len(model.components) == 1
        assert ctrl.can_undo()

        ctrl.undo()
        assert len(model.components) == 0

        ctrl.redo()
        assert len(model.components) == 1

    def test_add_wire_undoable(self):
        """Adding a wire via execute_command is fully undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (200, 0))

        cmd = AddWireCommand(ctrl, r1.component_id, 1, r2.component_id, 0)
        ctrl.execute_command(cmd)

        assert len(model.wires) == 1
        assert len(model.nodes) == 1

        ctrl.undo()
        assert len(model.wires) == 0
        assert len(model.nodes) == 0

        ctrl.redo()
        assert len(model.wires) == 1
        assert len(model.nodes) == 1

    def test_add_wire_with_waypoints_undoable(self):
        """Wire undo must preserve original waypoints on redo."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (200, 0))

        waypoints = [(0.0, 0.0), (50.0, 50.0), (200.0, 0.0)]
        cmd = AddWireCommand(ctrl, r1.component_id, 1, r2.component_id, 0, waypoints=waypoints)
        ctrl.execute_command(cmd)

        assert model.wires[0].waypoints == waypoints

        ctrl.undo()
        assert len(model.wires) == 0

        ctrl.redo()
        assert len(model.wires) == 1
        assert model.wires[0].waypoints == waypoints

    def test_rotate_component_undoable(self):
        """Rotating a component via execute_command is fully undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        cmd = RotateComponentCommand(ctrl, comp.component_id, clockwise=True)
        ctrl.execute_command(cmd)
        assert model.components[comp.component_id].rotation == 90

        ctrl.undo()
        assert model.components[comp.component_id].rotation == 0

        ctrl.redo()
        assert model.components[comp.component_id].rotation == 90

    def test_flip_component_undoable(self):
        """Flipping a component via execute_command is fully undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        cmd = FlipComponentCommand(ctrl, comp.component_id, horizontal=True)
        ctrl.execute_command(cmd)
        assert model.components[comp.component_id].flip_h is True

        ctrl.undo()
        assert model.components[comp.component_id].flip_h is False

        ctrl.redo()
        assert model.components[comp.component_id].flip_h is True

    def test_change_value_undoable(self):
        """Changing a value via execute_command is fully undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))
        original = comp.value

        cmd = ChangeValueCommand(ctrl, comp.component_id, "47k")
        ctrl.execute_command(cmd)
        assert model.components[comp.component_id].value == "47k"

        ctrl.undo()
        assert model.components[comp.component_id].value == original

        ctrl.redo()
        assert model.components[comp.component_id].value == "47k"

    def test_paste_undoable(self):
        """Pasting components via execute_command is fully undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        ctrl.copy_components([r1.component_id])

        cmd = PasteCommand(ctrl, offset=(40, 40))
        ctrl.execute_command(cmd)
        assert len(model.components) == 2

        ctrl.undo()
        assert len(model.components) == 1

        ctrl.redo()
        assert len(model.components) == 2

    def test_compound_rotate_multiple_undoable(self):
        """Rotating multiple components in a compound command undoes as one step."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (200, 0))

        commands = [
            RotateComponentCommand(ctrl, r1.component_id, clockwise=True),
            RotateComponentCommand(ctrl, r2.component_id, clockwise=True),
        ]
        compound = CompoundCommand(commands, "Rotate 2 components")
        ctrl.execute_command(compound)

        assert model.components[r1.component_id].rotation == 90
        assert model.components[r2.component_id].rotation == 90

        ctrl.undo()
        assert model.components[r1.component_id].rotation == 0
        assert model.components[r2.component_id].rotation == 0

    def test_compound_delete_undoable(self):
        """Deleting multiple items in a compound command undoes as one step."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (200, 0))
        ctrl.add_wire(r1.component_id, 1, r2.component_id, 0)

        commands = [
            DeleteComponentCommand(ctrl, r1.component_id),
            DeleteComponentCommand(ctrl, r2.component_id),
        ]
        compound = CompoundCommand(commands, "Delete 2 components")
        ctrl.execute_command(compound)

        assert len(model.components) == 0
        assert len(model.wires) == 0

        ctrl.undo()
        assert len(model.components) == 2

    def test_undo_state_changed_notification(self):
        """execute_command, undo, and redo all fire undo_state_changed."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        events = []
        ctrl.add_observer(lambda event, data: events.append(event))

        cmd = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(cmd)
        assert "undo_state_changed" in events

        events.clear()
        ctrl.undo()
        assert "undo_state_changed" in events

        events.clear()
        ctrl.redo()
        assert "undo_state_changed" in events

    def test_mixed_operation_undo_stack_order(self):
        """Multiple different operations undo in correct LIFO order."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        # 1. Add component
        cmd1 = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(cmd1)
        comp_id = cmd1.component_id

        # 2. Change its value
        cmd2 = ChangeValueCommand(ctrl, comp_id, "10k")
        ctrl.execute_command(cmd2)

        # 3. Rotate it
        cmd3 = RotateComponentCommand(ctrl, comp_id, clockwise=True)
        ctrl.execute_command(cmd3)

        # Undo in reverse: rotation, value, addition
        ctrl.undo()  # undo rotate
        assert model.components[comp_id].rotation == 0

        ctrl.undo()  # undo value change
        assert model.components[comp_id].value != "10k"

        ctrl.undo()  # undo add
        assert len(model.components) == 0


# ===========================================================================
# Properties Panel Undo Commands  (#819)
# ===========================================================================


class TestSetRotationCommand:
    """Test SetRotationCommand for properties-panel rotation changes."""

    def test_execute_and_undo(self):
        """Setting rotation to exact value is undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        assert model.components[comp_id].rotation == 0

        cmd = SetRotationCommand(ctrl, comp_id, 270)
        cmd.execute()
        assert model.components[comp_id].rotation == 270

        cmd.undo()
        assert model.components[comp_id].rotation == 0

    def test_via_controller_undoable(self):
        """SetRotationCommand through controller is fully undoable/redoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        cmd = SetRotationCommand(ctrl, comp_id, 180)
        ctrl.execute_command(cmd)
        assert model.components[comp_id].rotation == 180
        assert ctrl.can_undo()

        ctrl.undo()
        assert model.components[comp_id].rotation == 0

        ctrl.redo()
        assert model.components[comp_id].rotation == 180

    def test_normalizes_rotation(self):
        """Rotation values are normalized mod 360."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        cmd = SetRotationCommand(ctrl, comp.component_id, 450)
        cmd.execute()
        assert model.components[comp.component_id].rotation == 90

    def test_missing_component_skips(self):
        """SetRotationCommand on non-existent component should not crash."""
        ctrl = CircuitController()
        cmd = SetRotationCommand(ctrl, "BOGUS", 90)
        cmd.execute()
        assert cmd.old_rotation is None
        cmd.undo()  # should not crash

    def test_undo_missing_component_skips(self):
        """SetRotationCommand.undo after component deleted should not crash."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        cmd = SetRotationCommand(ctrl, comp.component_id, 90)
        cmd.execute()
        ctrl.remove_component(comp.component_id)
        cmd.undo()  # component gone; should not crash

    def test_description(self):
        """Command has descriptive get_description."""
        ctrl = CircuitController()
        cmd = SetRotationCommand(ctrl, "R1", 270)
        assert "R1" in cmd.get_description()
        assert "270" in cmd.get_description()


class TestUpdateWaveformCommand:
    """Test UpdateWaveformCommand for properties-panel waveform changes."""

    def test_execute_and_undo(self):
        """Updating waveform is undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Waveform Source", (0, 0))
        comp_id = comp.component_id

        old_type = model.components[comp_id].waveform_type
        old_value = model.components[comp_id].value

        cmd = UpdateWaveformCommand(ctrl, comp_id, "PULSE", {"v1": "0", "v2": "5"})
        cmd.execute()
        assert model.components[comp_id].waveform_type == "PULSE"

        cmd.undo()
        assert model.components[comp_id].waveform_type == old_type
        assert model.components[comp_id].value == old_value

    def test_via_controller_undoable(self):
        """UpdateWaveformCommand through controller is fully undoable/redoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Waveform Source", (0, 0))
        comp_id = comp.component_id
        old_type = model.components[comp_id].waveform_type

        cmd = UpdateWaveformCommand(ctrl, comp_id, "PULSE", {"v1": "0", "v2": "3.3"})
        ctrl.execute_command(cmd)
        assert model.components[comp_id].waveform_type == "PULSE"
        assert ctrl.can_undo()

        ctrl.undo()
        assert model.components[comp_id].waveform_type == old_type

        ctrl.redo()
        assert model.components[comp_id].waveform_type == "PULSE"

    def test_missing_component_skips(self):
        """UpdateWaveformCommand on non-existent component should not crash."""
        ctrl = CircuitController()
        cmd = UpdateWaveformCommand(ctrl, "BOGUS", "SIN", {"amp": "1"})
        cmd.execute()
        assert cmd.old_waveform_type is None
        cmd.undo()

    def test_undo_missing_component_skips(self):
        """UpdateWaveformCommand.undo after component deleted should not crash."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Waveform Source", (0, 0))
        cmd = UpdateWaveformCommand(ctrl, comp.component_id, "PULSE", {"v1": "0"})
        cmd.execute()
        ctrl.remove_component(comp.component_id)
        cmd.undo()  # should not crash

    def test_description(self):
        """Command has descriptive get_description."""
        ctrl = CircuitController()
        cmd = UpdateWaveformCommand(ctrl, "VW1", "PULSE", {})
        assert "VW1" in cmd.get_description()


class TestUpdateInitialConditionCommand:
    """Test UpdateInitialConditionCommand for properties-panel IC changes."""

    def test_execute_and_undo(self):
        """Updating initial condition is undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Capacitor", (0, 0))
        comp_id = comp.component_id

        assert model.components[comp_id].initial_condition is None

        cmd = UpdateInitialConditionCommand(ctrl, comp_id, "5V")
        cmd.execute()
        assert model.components[comp_id].initial_condition == "5V"

        cmd.undo()
        assert model.components[comp_id].initial_condition is None

    def test_via_controller_undoable(self):
        """UpdateInitialConditionCommand through controller is fully undoable/redoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Capacitor", (0, 0))
        comp_id = comp.component_id

        cmd = UpdateInitialConditionCommand(ctrl, comp_id, "3.3V")
        ctrl.execute_command(cmd)
        assert model.components[comp_id].initial_condition == "3.3V"
        assert ctrl.can_undo()

        ctrl.undo()
        assert model.components[comp_id].initial_condition is None

        ctrl.redo()
        assert model.components[comp_id].initial_condition == "3.3V"

    def test_clear_initial_condition_undoable(self):
        """Clearing an initial condition (setting to None) is undoable."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Capacitor", (0, 0))
        comp_id = comp.component_id
        model.components[comp_id].initial_condition = "2V"

        cmd = UpdateInitialConditionCommand(ctrl, comp_id, None)
        ctrl.execute_command(cmd)
        assert model.components[comp_id].initial_condition is None

        ctrl.undo()
        assert model.components[comp_id].initial_condition == "2V"

    def test_missing_component_skips(self):
        """UpdateInitialConditionCommand on non-existent component should not crash."""
        ctrl = CircuitController()
        cmd = UpdateInitialConditionCommand(ctrl, "BOGUS", "5V")
        cmd.execute()
        cmd.undo()

    def test_undo_missing_component_skips(self):
        """UpdateInitialConditionCommand.undo after component deleted should not crash."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Capacitor", (0, 0))
        cmd = UpdateInitialConditionCommand(ctrl, comp.component_id, "5V")
        cmd.execute()
        ctrl.remove_component(comp.component_id)
        cmd.undo()  # should not crash

    def test_description(self):
        """Command has descriptive get_description."""
        ctrl = CircuitController()
        cmd = UpdateInitialConditionCommand(ctrl, "C1", "5V")
        assert "C1" in cmd.get_description()
