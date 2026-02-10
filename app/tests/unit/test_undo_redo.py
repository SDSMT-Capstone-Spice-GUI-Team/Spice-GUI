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
    RotateComponentCommand,
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
