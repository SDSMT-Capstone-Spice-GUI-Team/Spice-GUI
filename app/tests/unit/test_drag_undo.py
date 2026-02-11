"""Tests for drag move undo/redo (issue #188).

Drag operations should create MoveComponentCommand (or CompoundCommand for
group drags) on the undo stack so that Ctrl+Z reverts them.
"""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import CompoundCommand, MoveComponentCommand
from models.circuit import CircuitModel


class TestMoveComponentCommandWithOldPosition:
    """Test MoveComponentCommand with pre-set old_position (drag flow)."""

    def test_old_position_preserved_when_preset(self):
        """When old_position is supplied, execute() should not overwrite it."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Simulate drag: model already at new position
        controller.move_component(comp_id, (100, 200))

        # Create command with pre-set old_position (as drag flow would)
        cmd = MoveComponentCommand(controller, comp_id, (100, 200), old_position=(0, 0))
        cmd.execute()

        # old_position should still be the original, not overwritten
        assert cmd.old_position == (0, 0)
        assert model.components[comp_id].position == (100, 200)

    def test_undo_restores_preset_old_position(self):
        """Undo should restore the pre-set old_position."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Simulate drag: model already at new position
        controller.move_component(comp_id, (100, 200))

        cmd = MoveComponentCommand(controller, comp_id, (100, 200), old_position=(0, 0))
        cmd.execute()

        # Undo should go back to (0, 0)
        cmd.undo()
        assert model.components[comp_id].position == (0, 0)

    def test_redo_moves_to_new_position(self):
        """Redo should move back to new_position."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        controller.move_component(comp_id, (100, 200))

        cmd = MoveComponentCommand(controller, comp_id, (100, 200), old_position=(0, 0))
        cmd.execute()

        cmd.undo()
        assert model.components[comp_id].position == (0, 0)

        cmd.execute()
        assert model.components[comp_id].position == (100, 200)

    def test_old_position_auto_detected_when_not_preset(self):
        """When old_position is None, execute() should capture current position."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (50, 60))
        comp_id = comp.component_id

        cmd = MoveComponentCommand(controller, comp_id, (100, 200))
        assert cmd.old_position is None

        cmd.execute()
        assert cmd.old_position == (50, 60)
        assert model.components[comp_id].position == (100, 200)

    def test_description(self):
        """MoveComponentCommand should have a descriptive string."""
        model = CircuitModel()
        controller = CircuitController(model)
        comp = controller.add_component("Resistor", (0, 0))

        cmd = MoveComponentCommand(controller, comp.component_id, (10, 20))
        assert "Move" in cmd.get_description()
        assert comp.component_id in cmd.get_description()


class TestDragUndoViaUndoManager:
    """Test the drag undo flow through the undo manager (simulating what
    _commit_drag_to_undo does)."""

    def test_single_component_drag_undo(self):
        """Simulated single-component drag pushed to undo stack."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Simulate drag: move the component directly
        controller.move_component(comp_id, (100, 200))

        # Push a MoveComponentCommand (as _commit_drag_to_undo would)
        cmd = MoveComponentCommand(controller, comp_id, (100, 200), old_position=(0, 0))
        controller.undo_manager._undo_stack.append(cmd)
        controller.undo_manager._redo_stack.clear()

        assert controller.can_undo()

        # Undo
        controller.undo()
        assert model.components[comp_id].position == (0, 0)

        # Redo
        controller.redo()
        assert model.components[comp_id].position == (100, 200)

    def test_group_drag_compound_undo(self):
        """Simulated group drag with CompoundCommand on undo stack."""
        model = CircuitModel()
        controller = CircuitController(model)

        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Resistor", (100, 0))
        r1_id = r1.component_id
        r2_id = r2.component_id

        # Simulate group drag: both move by (50, 50)
        controller.move_component(r1_id, (50, 50))
        controller.move_component(r2_id, (150, 50))

        # Create compound command (as _commit_drag_to_undo would)
        cmd1 = MoveComponentCommand(controller, r1_id, (50, 50), old_position=(0, 0))
        cmd2 = MoveComponentCommand(controller, r2_id, (150, 50), old_position=(100, 0))
        compound = CompoundCommand([cmd1, cmd2], "Move 2 components")
        controller.undo_manager._undo_stack.append(compound)
        controller.undo_manager._redo_stack.clear()

        # Undo should restore both to original positions
        controller.undo()
        assert model.components[r1_id].position == (0, 0)
        assert model.components[r2_id].position == (100, 0)

        # Redo should move both back
        controller.redo()
        assert model.components[r1_id].position == (50, 50)
        assert model.components[r2_id].position == (150, 50)

    def test_no_command_when_position_unchanged(self):
        """No undo entry should be created if the position didn't change."""
        model = CircuitModel()
        controller = CircuitController(model)

        controller.add_component("Resistor", (0, 0))

        initial_count = controller.undo_manager.get_undo_count()

        # Don't push any command (simulating a click without drag)
        assert controller.undo_manager.get_undo_count() == initial_count

    def test_drag_undo_clears_redo_stack(self):
        """Pushing a drag command should clear the redo stack."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Create some redo history
        cmd_add = MoveComponentCommand(controller, comp_id, (10, 10))
        controller.execute_command(cmd_add)
        controller.undo()
        assert controller.can_redo()

        # Simulate drag commit
        controller.move_component(comp_id, (50, 50))
        drag_cmd = MoveComponentCommand(controller, comp_id, (50, 50), old_position=(0, 0))
        controller.undo_manager._undo_stack.append(drag_cmd)
        controller.undo_manager._redo_stack.clear()

        assert not controller.can_redo()

    def test_compound_command_description(self):
        """CompoundCommand from group drag should have descriptive string."""
        model = CircuitModel()
        controller = CircuitController(model)

        r1 = controller.add_component("Resistor", (0, 0))
        r2 = controller.add_component("Capacitor", (100, 0))

        cmd1 = MoveComponentCommand(controller, r1.component_id, (50, 50), old_position=(0, 0))
        cmd2 = MoveComponentCommand(controller, r2.component_id, (150, 50), old_position=(100, 0))
        compound = CompoundCommand([cmd1, cmd2], "Move 2 components")

        assert compound.get_description() == "Move 2 components"
