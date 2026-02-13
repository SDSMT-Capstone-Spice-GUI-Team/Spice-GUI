"""Tests for undo/redo system."""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import (
    AddAnnotationCommand,
    AddComponentCommand,
    AddWireCommand,
    ChangeValueCommand,
    CompoundCommand,
    DeleteAnnotationCommand,
    DeleteComponentCommand,
    DeleteWireCommand,
    EditAnnotationCommand,
    FlipComponentCommand,
    MoveComponentCommand,
    PasteCommand,
    RotateComponentCommand,
)
from controllers.undo_manager import UndoManager
from models.annotation import AnnotationData
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


class TestCommandEdgeCasesOnNonexistentEntities:
    """Error-boundary tests: commands targeting nonexistent or stale entities."""

    def test_delete_component_command_nonexistent(self):
        """DeleteComponentCommand on nonexistent ID does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = DeleteComponentCommand(controller, "GHOST")
        cmd.execute()
        # component_data should be None since GHOST does not exist
        assert cmd.component_data is None
        # Undo should also be safe
        cmd.undo()

    def test_move_component_command_nonexistent(self):
        """MoveComponentCommand on nonexistent ID does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = MoveComponentCommand(controller, "GHOST", (100, 200))
        cmd.execute()
        # old_position should remain None since the component was not found
        assert cmd.old_position is None
        # Undo should be safe (old_position is None so it skips)
        cmd.undo()

    def test_rotate_component_command_nonexistent(self):
        """RotateComponentCommand on nonexistent ID does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = RotateComponentCommand(controller, "GHOST", clockwise=True)
        cmd.execute()
        cmd.undo()

    def test_flip_component_command_nonexistent(self):
        """FlipComponentCommand on nonexistent ID does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = FlipComponentCommand(controller, "GHOST", horizontal=True)
        cmd.execute()
        cmd.undo()

    def test_change_value_command_nonexistent(self):
        """ChangeValueCommand on nonexistent ID does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = ChangeValueCommand(controller, "GHOST", "100k")
        cmd.execute()
        # old_value should remain None
        assert cmd.old_value is None
        cmd.undo()

    def test_delete_wire_command_out_of_bounds(self):
        """DeleteWireCommand with out-of-bounds index does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = DeleteWireCommand(controller, 999)
        cmd.execute()
        # wire_data should remain None
        assert cmd.wire_data is None
        cmd.undo()

    def test_delete_annotation_command_out_of_bounds(self):
        """DeleteAnnotationCommand with out-of-bounds index does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = DeleteAnnotationCommand(controller, 999)
        cmd.execute()
        assert cmd.annotation_data is None
        cmd.undo()

    def test_edit_annotation_command_out_of_bounds(self):
        """EditAnnotationCommand with out-of-bounds index does not crash."""
        model = CircuitModel()
        controller = CircuitController(model)
        cmd = EditAnnotationCommand(controller, 999, "New text")
        cmd.execute()
        assert cmd.old_text is None
        cmd.undo()

    def test_delete_component_command_stale_entity(self):
        """DeleteComponentCommand on a component deleted before execute."""
        model = CircuitModel()
        controller = CircuitController(model)
        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Create command targeting the component
        cmd = DeleteComponentCommand(controller, comp_id)
        # Delete the component before executing the command
        controller.remove_component(comp_id)
        assert comp_id not in model.components

        # Execute should handle the missing component gracefully
        cmd.execute()
        cmd.undo()

    def test_move_command_after_component_removed(self):
        """MoveComponentCommand targeting a removed component is safe."""
        model = CircuitModel()
        controller = CircuitController(model)
        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        cmd = MoveComponentCommand(controller, comp_id, (50, 50))
        controller.remove_component(comp_id)

        cmd.execute()
        cmd.undo()

    def test_compound_command_with_nonexistent_targets(self):
        """CompoundCommand containing commands for nonexistent entities is safe."""
        model = CircuitModel()
        controller = CircuitController(model)
        commands = [
            MoveComponentCommand(controller, "GHOST1", (10, 10)),
            RotateComponentCommand(controller, "GHOST2", clockwise=True),
            FlipComponentCommand(controller, "GHOST3", horizontal=False),
        ]
        compound = CompoundCommand(commands, "Ghost operations")
        compound.execute()
        compound.undo()


def _snapshot_model(model):
    """Return a hashable snapshot of the circuit model state.

    Captures components (sorted by id), wires, and annotations so that
    two snapshots can be compared for equality.  This includes component
    IDs and is suitable for tests that do not undo/redo AddComponentCommand
    (since re-executing an add generates a new component ID).
    """
    comp_tuples = tuple(
        sorted(
            (
                c.component_id,
                c.component_type,
                c.value,
                c.position,
                c.rotation,
                c.flip_h,
                c.flip_v,
            )
            for c in model.components.values()
        )
    )
    wire_tuples = tuple(
        (w.start_component_id, w.start_terminal, w.end_component_id, w.end_terminal) for w in model.wires
    )
    ann_tuples = tuple((a.text, a.x, a.y) for a in model.annotations)
    return (comp_tuples, wire_tuples, ann_tuples)


def _structural_snapshot(model):
    """Return a hashable snapshot ignoring component IDs.

    Compares component properties (type, value, position, rotation, flips)
    sorted by (type, position) and wire count / annotation data.
    Use this when AddComponentCommand undo+redo causes ID regeneration.
    """
    comp_tuples = tuple(
        sorted(
            (
                c.component_type,
                c.value,
                c.position,
                c.rotation,
                c.flip_h,
                c.flip_v,
            )
            for c in model.components.values()
        )
    )
    wire_count = len(model.wires)
    ann_tuples = tuple(sorted((a.text, a.x, a.y) for a in model.annotations))
    return (comp_tuples, wire_count, ann_tuples)


class TestUndoRedoStress:
    """Stress tests for the undo/redo system.

    Covers large operation sequences, depth limiting, interleaved
    undo/redo cycling, CompoundCommand stress, and model integrity
    verification after full undo/redo cycles.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_env():
        """Create a fresh model, controller, and undo manager."""
        model = CircuitModel()
        controller = CircuitController(model)
        manager = controller.undo_manager
        return model, controller, manager

    # ------------------------------------------------------------------
    # 1. 50+ mixed operations, undo all the way back to empty, redo all
    # ------------------------------------------------------------------

    def test_large_mixed_sequence_undo_all_redo_all(self):
        """50+ mixed ops: undo non-add ops preserves state, undo all to empty."""
        model, controller, manager = self._make_env()

        # Track component ids for later operations
        comp_ids = []

        # Phase 1: add 20 components (20 ops)
        for i in range(20):
            ctype = ["Resistor", "Capacitor", "Inductor"][i % 3]
            cmd = AddComponentCommand(controller, ctype, (i * 10.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        # Phase 2: add wires between consecutive components (19 ops)
        for i in range(19):
            cmd = AddWireCommand(controller, comp_ids[i], 1, comp_ids[i + 1], 0)
            manager.execute(cmd)

        # Take snapshot after adds + wires (before mutations)
        snap_after_build = _snapshot_model(model)
        add_wire_ops = 20 + 19  # 39 ops for adds + wires

        # Phase 3: move some components (7 ops: indices 0,3,6,9,12,15,18)
        for i in range(0, 20, 3):
            cmd = MoveComponentCommand(controller, comp_ids[i], (i * 10.0 + 5.0, 5.0))
            manager.execute(cmd)

        # Phase 4: change values (5 ops: indices 0,4,8,12,16)
        for i in range(0, 20, 4):
            cmd = ChangeValueCommand(controller, comp_ids[i], f"{i * 100}")
            manager.execute(cmd)

        # Phase 5: rotate and flip (4+4 = 8 ops)
        for i in range(0, 20, 5):
            cmd = RotateComponentCommand(controller, comp_ids[i], clockwise=True)
            manager.execute(cmd)
        for i in range(1, 20, 5):
            cmd = FlipComponentCommand(controller, comp_ids[i], horizontal=True)
            manager.execute(cmd)

        total_ops = manager.get_undo_count()
        mutation_ops = total_ops - add_wire_ops
        assert total_ops >= 50  # Verify we have enough operations

        # Undo just the mutation ops (moves, values, rotates, flips)
        # This keeps adds/wires intact so IDs are preserved
        for _ in range(mutation_ops):
            manager.undo()
        assert _snapshot_model(model) == snap_after_build

        # Redo mutation ops restores exact state (IDs unchanged)
        for _ in range(mutation_ops):
            manager.redo()

        # Now undo ALL operations to reach empty circuit
        while manager.can_undo():
            manager.undo()
        assert len(model.components) == 0
        assert len(model.wires) == 0

        # Redo all restores correct counts
        redo_count = 0
        while manager.can_redo():
            manager.redo()
            redo_count += 1
        assert redo_count == total_ops
        assert len(model.components) == 20
        assert len(model.wires) == 19

    # ------------------------------------------------------------------
    # 2. Depth limit correctly evicts oldest commands
    # ------------------------------------------------------------------

    def test_depth_limit_evicts_oldest(self):
        """Depth limit (default 100) correctly evicts oldest commands."""
        model = CircuitModel()
        controller = CircuitController(model)
        max_depth = 100
        manager = UndoManager(max_depth=max_depth)
        controller.undo_manager = manager

        # Execute 150 commands (50 more than max depth)
        for i in range(150):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)

        # Undo stack should be capped at max_depth
        assert manager.get_undo_count() == max_depth

        # We should have 150 components in the model
        assert len(model.components) == 150

        # Undo all 100 times
        for _ in range(max_depth):
            assert manager.can_undo()
            manager.undo()

        # Should not be able to undo further
        assert not manager.can_undo()

        # 50 components should remain (oldest 50 commands were evicted)
        assert len(model.components) == 50

    def test_small_depth_limit_eviction(self):
        """Small depth limit (5) evicts correctly with mixed operations."""
        model, controller, _ = self._make_env()
        manager = UndoManager(max_depth=5)
        controller.undo_manager = manager

        # Add 10 components
        for i in range(10):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)

        assert manager.get_undo_count() == 5
        assert len(model.components) == 10

        # Undo 5 times should leave 5 components
        for _ in range(5):
            manager.undo()
        assert len(model.components) == 5
        assert not manager.can_undo()

    # ------------------------------------------------------------------
    # 3. Rapid undo/redo cycling produces consistent state
    # ------------------------------------------------------------------

    def test_rapid_undo_redo_cycling(self):
        """Undo 10, redo 5, undo 3, redo 8 produces consistent state.

        Note: AddComponentCommand.execute regenerates IDs on redo, so we
        compare component counts and structural snapshots (no IDs).
        """
        model, controller, manager = self._make_env()

        # Add 20 components and record structural snapshots at each step
        snapshots = [_structural_snapshot(model)]  # snapshot[0] = empty
        for i in range(20):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)
            snapshots.append(_structural_snapshot(model))

        # After 20 adds, we are at snapshot[20]
        assert len(model.components) == 20

        # Undo 10 -> should be at snapshot[10]
        for _ in range(10):
            manager.undo()
        assert _structural_snapshot(model) == snapshots[10]
        assert len(model.components) == 10

        # Redo 5 -> snapshot[15]
        for _ in range(5):
            manager.redo()
        assert _structural_snapshot(model) == snapshots[15]
        assert len(model.components) == 15

        # Undo 3 -> snapshot[12]
        for _ in range(3):
            manager.undo()
        assert _structural_snapshot(model) == snapshots[12]
        assert len(model.components) == 12

        # Redo 8 -> snapshot[20]
        for _ in range(8):
            manager.redo()
        assert _structural_snapshot(model) == snapshots[20]
        assert len(model.components) == 20

    def test_undo_redo_cycling_with_mixed_operations(self):
        """Interleaved undo/redo with add, move, value-change commands."""
        model, controller, manager = self._make_env()

        # Build up: add component, move it, change value
        cmd1 = AddComponentCommand(controller, "Resistor", (0, 0))
        manager.execute(cmd1)
        comp_id = cmd1.component_id
        snap_after_add = _snapshot_model(model)

        cmd2 = MoveComponentCommand(controller, comp_id, (50, 50))
        manager.execute(cmd2)
        snap_after_move = _snapshot_model(model)

        cmd3 = ChangeValueCommand(controller, comp_id, "4.7k")
        manager.execute(cmd3)
        snap_after_value = _snapshot_model(model)

        # Undo value change
        manager.undo()
        assert _snapshot_model(model) == snap_after_move

        # Redo value change
        manager.redo()
        assert _snapshot_model(model) == snap_after_value

        # Undo value + move
        manager.undo()
        manager.undo()
        assert _snapshot_model(model) == snap_after_add

        # Redo move only
        manager.redo()
        assert _snapshot_model(model) == snap_after_move

    # ------------------------------------------------------------------
    # 4. CompoundCommand with 10+ sub-commands undoes atomically
    # ------------------------------------------------------------------

    def test_compound_command_10_subcommands(self):
        """CompoundCommand with 10+ sub-commands undoes/redoes atomically."""
        model, controller, manager = self._make_env()

        sub_commands = [AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0)) for i in range(15)]
        compound = CompoundCommand(sub_commands, "Add 15 resistors")
        manager.execute(compound)

        assert len(model.components) == 15
        assert manager.get_undo_count() == 1  # Single compound command

        # Undo atomically removes all 15
        manager.undo()
        assert len(model.components) == 0
        assert manager.get_undo_count() == 0

        # Redo atomically restores all 15
        manager.redo()
        assert len(model.components) == 15

    def test_compound_command_mixed_operations(self):
        """CompoundCommand with mixed add/move/rotate operations."""
        model, controller, manager = self._make_env()

        # Pre-add a component to operate on
        pre_comp = controller.add_component("Capacitor", (0, 0))
        pre_id = pre_comp.component_id
        snap_before = _snapshot_model(model)

        sub_commands = [
            AddComponentCommand(controller, "Resistor", (100, 0)),
            AddComponentCommand(controller, "Inductor", (200, 0)),
            MoveComponentCommand(controller, pre_id, (50, 50)),
            RotateComponentCommand(controller, pre_id, clockwise=True),
            FlipComponentCommand(controller, pre_id, horizontal=True),
            ChangeValueCommand(controller, pre_id, "22u"),
        ]
        compound = CompoundCommand(sub_commands, "Mixed operations")
        manager.execute(compound)

        assert len(model.components) == 3
        assert model.components[pre_id].position == (50, 50)
        assert model.components[pre_id].rotation == 90
        assert model.components[pre_id].flip_h is True
        assert model.components[pre_id].value == "22u"

        # Single undo reverts everything
        manager.undo()
        assert _snapshot_model(model) == snap_before

    def test_compound_command_stress_20_subcommands(self):
        """CompoundCommand with 20 sub-commands across multiple types."""
        model, controller, manager = self._make_env()

        sub_commands = []
        # Add 10 components
        for i in range(10):
            sub_commands.append(AddComponentCommand(controller, "Resistor", (i * 20.0, 0.0)))

        compound = CompoundCommand(sub_commands, "Add 10 resistors")
        manager.execute(compound)
        assert len(model.components) == 10

        # Build second compound: move + rotate all 10
        comp_ids = list(model.components.keys())
        sub_commands2 = []
        for cid in comp_ids:
            sub_commands2.append(MoveComponentCommand(controller, cid, (999, 999)))
            sub_commands2.append(RotateComponentCommand(controller, cid, clockwise=True))

        compound2 = CompoundCommand(sub_commands2, "Move and rotate all")
        manager.execute(compound2)

        # Verify all moved and rotated
        for cid in comp_ids:
            assert model.components[cid].position == (999, 999)
            assert model.components[cid].rotation == 90

        # Undo compound2
        manager.undo()
        for i, cid in enumerate(comp_ids):
            assert model.components[cid].position == (i * 20.0, 0.0)
            assert model.components[cid].rotation == 0

        # Undo compound1
        manager.undo()
        assert len(model.components) == 0

    # ------------------------------------------------------------------
    # 5. Model state checksums match at corresponding undo/redo positions
    # ------------------------------------------------------------------

    def test_model_checksums_match_at_each_undo_position(self):
        """Snapshots taken during forward execution match on undo walk-back.

        Undo preserves component IDs so full snapshots are compared at each
        step during the reverse walk.
        """
        model, controller, manager = self._make_env()

        forward_snapshots = [_snapshot_model(model)]

        # Execute 30 mixed operations
        comp_ids = []
        for i in range(10):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)
            forward_snapshots.append(_snapshot_model(model))

        for i in range(10):
            cmd = MoveComponentCommand(controller, comp_ids[i], (i * 10.0 + 1.0, 1.0))
            manager.execute(cmd)
            forward_snapshots.append(_snapshot_model(model))

        for i in range(10):
            cmd = ChangeValueCommand(controller, comp_ids[i], f"{(i + 1) * 100}")
            manager.execute(cmd)
            forward_snapshots.append(_snapshot_model(model))

        # Total 30 ops, 31 snapshots (including initial empty)
        assert len(forward_snapshots) == 31

        # Walk back verifying each position (undo preserves IDs)
        for step in range(30, 0, -1):
            assert _snapshot_model(model) == forward_snapshots[step]
            manager.undo()
        assert _snapshot_model(model) == forward_snapshots[0]

    def test_model_checksums_match_on_redo_within_mutations(self):
        """Redo of mutation commands (move, value) restores exact snapshots.

        Only non-add commands are undone/redone so IDs remain stable.
        """
        model, controller, manager = self._make_env()

        # Add 10 components (not undone in this test)
        comp_ids = []
        for i in range(10):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        snap_base = _snapshot_model(model)
        mutation_snapshots = [snap_base]

        # 10 moves + 10 value changes = 20 mutation ops
        for i in range(10):
            cmd = MoveComponentCommand(controller, comp_ids[i], (i * 10.0 + 1.0, 1.0))
            manager.execute(cmd)
            mutation_snapshots.append(_snapshot_model(model))

        for i in range(10):
            cmd = ChangeValueCommand(controller, comp_ids[i], f"{(i + 1) * 100}")
            manager.execute(cmd)
            mutation_snapshots.append(_snapshot_model(model))

        # Undo all 20 mutations
        for _ in range(20):
            manager.undo()
        assert _snapshot_model(model) == snap_base

        # Redo all 20 mutations, verifying at each step
        for step in range(1, 21):
            manager.redo()
            assert _snapshot_model(model) == mutation_snapshots[step]

    # ------------------------------------------------------------------
    # 6. Redo invalidation after new command mid-stack
    # ------------------------------------------------------------------

    def test_redo_invalidation_after_new_command(self):
        """Executing a new command mid-stack clears the redo stack."""
        model, controller, manager = self._make_env()

        # Add 20 components
        for i in range(20):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)

        # Undo 10
        for _ in range(10):
            manager.undo()
        assert manager.get_redo_count() == 10
        assert len(model.components) == 10

        # Execute a new command -- redo stack should be cleared
        cmd = AddComponentCommand(controller, "Capacitor", (999, 999))
        manager.execute(cmd)
        assert manager.get_redo_count() == 0
        assert len(model.components) == 11

    # ------------------------------------------------------------------
    # 7. Wire index consistency under interleaved add/delete
    # ------------------------------------------------------------------

    def test_wire_index_consistency_interleaved(self):
        """Wire indices remain valid after interleaved add/delete undo/redo."""
        model, controller, manager = self._make_env()

        # Create a chain of 5 components with 4 wires
        comp_ids = []
        for i in range(5):
            cmd = AddComponentCommand(controller, "Resistor", (i * 50.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        for i in range(4):
            cmd = AddWireCommand(controller, comp_ids[i], 1, comp_ids[i + 1], 0)
            manager.execute(cmd)

        assert len(model.wires) == 4
        snap_4_wires = _snapshot_model(model)

        # Delete wire at index 1 (second wire)
        cmd_del = DeleteWireCommand(controller, 1)
        manager.execute(cmd_del)
        assert len(model.wires) == 3

        # Undo delete -> back to 4 wires
        manager.undo()
        assert len(model.wires) == 4
        assert _snapshot_model(model) == snap_4_wires

        # Redo delete -> back to 3 wires
        manager.redo()
        assert len(model.wires) == 3

        # Undo all the way
        while manager.can_undo():
            manager.undo()
        assert len(model.components) == 0
        assert len(model.wires) == 0

        # Redo all the way
        while manager.can_redo():
            manager.redo()
        assert len(model.wires) == 3  # Still has the delete applied

    # ------------------------------------------------------------------
    # 8. 500+ command stress test
    # ------------------------------------------------------------------

    def test_500_command_sequence(self):
        """500+ command sequence with default depth limit of 100."""
        model, controller, manager = self._make_env()

        # Execute 500 add commands
        for i in range(500):
            cmd = AddComponentCommand(controller, "Resistor", (i * 5.0, 0.0))
            manager.execute(cmd)

        # Depth limit of 100 should cap undo stack
        assert manager.get_undo_count() == 100
        assert len(model.components) == 500

        # Undo 100 times
        for _ in range(100):
            manager.undo()

        assert not manager.can_undo()
        assert len(model.components) == 400  # 500 - 100

        # Redo all 100
        for _ in range(100):
            manager.redo()
        assert len(model.components) == 500

    # ------------------------------------------------------------------
    # 9. Delete component with wires - undo/redo cycle
    # ------------------------------------------------------------------

    def test_delete_component_with_wires_full_cycle(self):
        """Delete components with wires, undo all, verify full restoration."""
        model, controller, manager = self._make_env()

        # Build a small network: 6 components, wires forming a chain
        comp_ids = []
        for i in range(6):
            cmd = AddComponentCommand(controller, "Resistor", (i * 50.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        for i in range(5):
            cmd = AddWireCommand(controller, comp_ids[i], 1, comp_ids[i + 1], 0)
            manager.execute(cmd)

        assert len(model.components) == 6
        assert len(model.wires) == 5

        # Delete middle component (index 3) -- should delete 2 wires
        cmd_del = DeleteComponentCommand(controller, comp_ids[3])
        manager.execute(cmd_del)
        assert len(model.components) == 5
        assert len(model.wires) == 3  # Wires 2 and 3 removed

        # Undo should restore component and wires
        manager.undo()
        assert len(model.components) == 6
        assert len(model.wires) == 5

        # Verify the component data is correct
        restored = model.components[comp_ids[3]]
        assert restored.component_type == "Resistor"
        assert restored.position == (150.0, 0.0)

    # ------------------------------------------------------------------
    # 10. Annotation commands in stress sequence
    # ------------------------------------------------------------------

    def test_annotation_commands_in_sequence(self):
        """Annotations interleaved with component ops undo/redo correctly."""
        model, controller, manager = self._make_env()

        # Add components
        for i in range(5):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)

        # Add annotations
        for i in range(5):
            ann = AnnotationData(text=f"Note {i}", x=i * 10.0, y=20.0)
            cmd = AddAnnotationCommand(controller, ann)
            manager.execute(cmd)

        assert len(model.annotations) == 5
        snap_with_anns = _snapshot_model(model)

        # Undo all annotations
        for _ in range(5):
            manager.undo()
        assert len(model.annotations) == 0

        # Redo all annotations
        for _ in range(5):
            manager.redo()
        assert _snapshot_model(model) == snap_with_anns

    # ------------------------------------------------------------------
    # 11. Undo/redo has no effect on empty stacks
    # ------------------------------------------------------------------

    def test_undo_redo_on_empty_stacks(self):
        """Undo/redo on empty stacks returns False and does not crash."""
        model, controller, manager = self._make_env()

        # Spam undo/redo on empty manager
        for _ in range(50):
            assert manager.undo() is False
            assert manager.redo() is False

        assert len(model.components) == 0

    # ------------------------------------------------------------------
    # 12. Rapid cycling stress: many short undo/redo bursts
    # ------------------------------------------------------------------

    def test_rapid_cycling_many_bursts(self):
        """Rapid undo/redo cycling in many short bursts is stable."""
        model, controller, manager = self._make_env()

        # Add 30 components
        for i in range(30):
            cmd = AddComponentCommand(controller, "Capacitor", (i * 10.0, 0.0))
            manager.execute(cmd)

        # Perform 20 bursts of: undo N, redo M (N and M vary)
        import random

        rng = random.Random(42)  # Deterministic seed
        for _ in range(20):
            n_undo = rng.randint(1, min(10, manager.get_undo_count() or 1))
            for _ in range(n_undo):
                if manager.can_undo():
                    manager.undo()

            n_redo = rng.randint(1, min(10, manager.get_redo_count() or 1))
            for _ in range(n_redo):
                if manager.can_redo():
                    manager.redo()

        # Final state should be consistent: components should equal undo position
        comp_count = len(model.components)
        assert comp_count >= 0
        assert comp_count <= 30

        # Undo everything that's undoable
        while manager.can_undo():
            manager.undo()

        # Redo everything
        while manager.can_redo():
            manager.redo()

        # Should be back at 30
        assert len(model.components) == 30

    # ------------------------------------------------------------------
    # 13. Paste command undo/redo in large sequence
    # ------------------------------------------------------------------

    def test_paste_command_in_sequence(self):
        """PasteCommand undo/redo works correctly in a larger sequence."""
        model, controller, manager = self._make_env()

        # Add a source component, copy it, then paste 5 times
        cmd_add = AddComponentCommand(controller, "Resistor", (0, 0))
        manager.execute(cmd_add)
        source_id = cmd_add.component_id

        controller.copy_components([source_id])

        paste_cmds = []
        for _ in range(5):
            cmd = PasteCommand(controller, offset=(40, 40))
            manager.execute(cmd)
            paste_cmds.append(cmd)

        # 1 original + 5 pasted
        assert len(model.components) == 6

        # Undo all pastes
        for _ in range(5):
            manager.undo()
        assert len(model.components) == 1
        assert source_id in model.components

        # Redo all pastes
        for _ in range(5):
            manager.redo()
        assert len(model.components) == 6

    # ------------------------------------------------------------------
    # 14. Full round-trip: build complex circuit, undo to empty, redo back
    # ------------------------------------------------------------------

    def test_full_round_trip_complex_circuit(self):
        """Build a complex circuit, undo mutations, verify, undo all to empty."""
        model, controller, manager = self._make_env()

        comp_ids = []
        # Add 10 resistors
        for i in range(10):
            cmd = AddComponentCommand(controller, "Resistor", (i * 50.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        # Add 5 capacitors
        for i in range(5):
            cmd = AddComponentCommand(controller, "Capacitor", (i * 50.0, 100.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        add_ops = 15

        # Wire resistors in a chain
        for i in range(9):
            cmd = AddWireCommand(controller, comp_ids[i], 1, comp_ids[i + 1], 0)
            manager.execute(cmd)

        # Wire capacitors to resistors
        for i in range(5):
            cmd = AddWireCommand(controller, comp_ids[i], 1, comp_ids[10 + i], 0)
            manager.execute(cmd)

        wire_ops = 14
        snap_after_build = _snapshot_model(model)

        # Move some components (8 ops: indices 0,2,4,6,8,10,12,14)
        for i in range(0, 15, 2):
            cmd = MoveComponentCommand(controller, comp_ids[i], (i * 50.0 + 10.0, 10.0))
            manager.execute(cmd)

        # Change some values (4 ops: indices 0,3,6,9)
        for i in range(0, 10, 3):
            cmd = ChangeValueCommand(controller, comp_ids[i], f"{i}k")
            manager.execute(cmd)

        # Rotate and flip some (4+4 = 8 ops)
        for i in range(0, 15, 4):
            cmd = RotateComponentCommand(controller, comp_ids[i], clockwise=True)
            manager.execute(cmd)
        for i in range(1, 15, 4):
            cmd = FlipComponentCommand(controller, comp_ids[i], horizontal=True)
            manager.execute(cmd)

        total_ops = manager.get_undo_count()
        mutation_ops = total_ops - add_ops - wire_ops
        final_snapshot = _snapshot_model(model)

        # Undo mutations only, keeping adds and wires intact
        for _ in range(mutation_ops):
            manager.undo()
        assert _snapshot_model(model) == snap_after_build
        assert len(model.components) == 15
        assert len(model.wires) == 14

        # Redo mutations restores exact final state (IDs preserved)
        for _ in range(mutation_ops):
            manager.redo()
        assert _snapshot_model(model) == final_snapshot

        # Undo everything to empty
        while manager.can_undo():
            manager.undo()
        assert len(model.components) == 0
        assert len(model.wires) == 0

        # Redo all restores correct counts
        while manager.can_redo():
            manager.redo()
        assert len(model.components) == 15
        assert len(model.wires) == 14

    # ------------------------------------------------------------------
    # 15. Depth limit with mixed command types
    # ------------------------------------------------------------------

    def test_depth_limit_mixed_commands(self):
        """Depth limit eviction with mixed command types preserves correctness."""
        model = CircuitModel()
        controller = CircuitController(model)
        manager = UndoManager(max_depth=10)
        controller.undo_manager = manager

        # Execute 5 adds
        comp_ids = []
        for i in range(5):
            cmd = AddComponentCommand(controller, "Resistor", (i * 10.0, 0.0))
            manager.execute(cmd)
            comp_ids.append(cmd.component_id)

        # Execute 5 moves
        for i in range(5):
            cmd = MoveComponentCommand(controller, comp_ids[i], (i * 10.0 + 1.0, 1.0))
            manager.execute(cmd)

        assert manager.get_undo_count() == 10

        # Execute 5 more value changes (should evict first 5 adds)
        for i in range(5):
            cmd = ChangeValueCommand(controller, comp_ids[i], f"{i}ohm")
            manager.execute(cmd)

        assert manager.get_undo_count() == 10

        # Undo all 10 remaining
        for _ in range(10):
            manager.undo()

        # The 5 adds were evicted, so components still exist
        assert len(model.components) == 5

        # Components should be at original positions (moves undone)
        # and have original values (value changes undone)
        for i in range(5):
            comp = model.components[comp_ids[i]]
            assert comp.position == (i * 10.0, 0.0)
            assert comp.value == "1k"  # default Resistor value
