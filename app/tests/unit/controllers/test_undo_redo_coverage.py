"""Tests to cover remaining branches in commands.py and undo_manager.py.

Targets the specific uncovered lines identified in issue #706.
No Qt imports — pure model/controller logic only.
"""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import (
    AddAnnotationCommand,
    AddComponentCommand,
    AddWireCommand,
    ChangeValueCommand,
    Command,
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

# ---------------------------------------------------------------------------
# Command base class  (lines 25, 30, 34)
# ---------------------------------------------------------------------------


class _MinimalCommand(Command):
    """Concrete subclass that delegates to the ABC body."""

    def execute(self):
        super().execute()

    def undo(self):
        super().undo()


class TestCommandBaseClass:
    def test_execute_pass(self):
        """Cover the abstract execute() body (line 25)."""
        _MinimalCommand().execute()

    def test_undo_pass(self):
        """Cover the abstract undo() body (line 30)."""
        _MinimalCommand().undo()

    def test_default_get_description(self):
        """Cover default get_description() returning class name (line 34)."""
        assert _MinimalCommand().get_description() == "_MinimalCommand"


# ---------------------------------------------------------------------------
# get_description() methods  (lines 103, 179-180, 212-213, 250, 299, 442)
# ---------------------------------------------------------------------------


class TestCommandDescriptions:
    def setup_method(self):
        self.model = CircuitModel()
        self.ctrl = CircuitController(self.model)

    def test_delete_component_description(self):
        """Line 103: DeleteComponentCommand.get_description()."""
        cmd = DeleteComponentCommand(self.ctrl, "R1")
        assert cmd.get_description() == "Delete R1"

    def test_rotate_clockwise_description(self):
        """Lines 179-180: RotateComponentCommand.get_description() clockwise."""
        comp = self.ctrl.add_component("Resistor", (0, 0))
        cmd = RotateComponentCommand(self.ctrl, comp.component_id, clockwise=True)
        assert "clockwise" in cmd.get_description()

    def test_rotate_counter_clockwise_description(self):
        """Lines 179-180: RotateComponentCommand.get_description() counter-clockwise."""
        comp = self.ctrl.add_component("Resistor", (0, 0))
        cmd = RotateComponentCommand(self.ctrl, comp.component_id, clockwise=False)
        assert "counter-clockwise" in cmd.get_description()

    def test_flip_horizontal_description(self):
        """Lines 212-213: FlipComponentCommand.get_description() horizontal."""
        comp = self.ctrl.add_component("Resistor", (0, 0))
        cmd = FlipComponentCommand(self.ctrl, comp.component_id, horizontal=True)
        assert "horizontal" in cmd.get_description()

    def test_flip_vertical_description(self):
        """Lines 212-213: FlipComponentCommand.get_description() vertical."""
        comp = self.ctrl.add_component("Resistor", (0, 0))
        cmd = FlipComponentCommand(self.ctrl, comp.component_id, horizontal=False)
        assert "vertical" in cmd.get_description()

    def test_change_value_description(self):
        """Line 250: ChangeValueCommand.get_description()."""
        cmd = ChangeValueCommand(self.ctrl, "R1", "10k")
        assert cmd.get_description() == "Change R1 value"

    def test_add_wire_description(self):
        """Line 299: AddWireCommand.get_description()."""
        cmd = AddWireCommand(self.ctrl, "R1", 0, "R2", 0)
        assert cmd.get_description() == "Add wire R1-R2"

    def test_paste_description(self):
        """Line 442: PasteCommand.get_description()."""
        cmd = PasteCommand(self.ctrl)
        # Before execution, pasted_component_ids is empty
        assert cmd.get_description() == "Paste 0 components"


# ---------------------------------------------------------------------------
# Early-return / guard branches
# ---------------------------------------------------------------------------


class TestMoveComponentUndoEarlyReturn:
    def test_undo_when_old_position_is_none(self):
        """Line 137: MoveComponentCommand.undo() returns early when old_position is falsy."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (10, 20))

        cmd = MoveComponentCommand(ctrl, comp.component_id, (50, 50))
        # Force old_position to be None (simulate never-executed path)
        cmd.old_position = None
        cmd.undo()  # should return early without error

        # Position unchanged
        assert model.components[comp.component_id].position == (10, 20)


class TestChangeValueUndoEarlyReturn:
    def test_undo_when_old_value_is_none(self):
        """Line 240: ChangeValueCommand.undo() returns when old_value is None."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        cmd = ChangeValueCommand(ctrl, comp.component_id, "10k")
        # Don't execute — old_value stays None
        cmd.undo()  # should return early

        assert model.components[comp.component_id].value == comp.value


class TestDeleteWireUndoEarlyReturn:
    def test_undo_when_wire_data_is_none(self):
        """Line 325: DeleteWireCommand.undo() returns when wire_data is None."""
        ctrl = CircuitController(CircuitModel())
        cmd = DeleteWireCommand(ctrl, 0)
        # wire_data is None by default (never executed on valid wire)
        cmd.undo()  # should not raise


# ---------------------------------------------------------------------------
# PasteCommand.undo() wire cleanup  (lines 431-432)
# ---------------------------------------------------------------------------


class TestPasteUndoWireCleanup:
    def test_undo_removes_pasted_wires(self):
        """Lines 431-432: PasteCommand.undo() removes pasted wires by index."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire(r1.component_id, 0, r2.component_id, 0)
        ctrl.copy_components([r1.component_id, r2.component_id])

        cmd = PasteCommand(ctrl, offset=(40, 40))
        cmd.execute()

        assert len(cmd.pasted_component_ids) == 2
        assert len(cmd.pasted_wire_indices) == 1

        total_wires_before = len(model.wires)
        cmd.undo()
        assert len(model.wires) == total_wires_before - 1

    def test_undo_skips_out_of_range_wire(self):
        """Lines 431-432: wire_idx >= len(wires) is safely skipped."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        r1 = ctrl.add_component("Resistor", (0, 0))
        ctrl.copy_components([r1.component_id])

        cmd = PasteCommand(ctrl, offset=(40, 40))
        cmd.execute()

        # Artificially inject an out-of-range wire index
        cmd.pasted_wire_indices = [999]
        cmd.undo()  # should not raise


# ---------------------------------------------------------------------------
# Annotation command stale-state guards
# ---------------------------------------------------------------------------


class TestAddAnnotationUndoOutOfRange:
    def test_undo_out_of_range_index(self):
        """Lines 460-464: AddAnnotationCommand.undo() with stale index."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        ann = AnnotationData(text="test", x=0, y=0)

        cmd = AddAnnotationCommand(ctrl, ann)
        cmd.execute()
        assert len(model.annotations) == 1

        # Manually clear annotations to simulate stale state
        model.annotations.clear()
        cmd.undo()  # index out of range, should not raise


class TestDeleteAnnotationExecuteOutOfRange:
    def test_execute_out_of_range_index(self):
        """Lines 481-485: DeleteAnnotationCommand.execute() with invalid index."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        cmd = DeleteAnnotationCommand(ctrl, 99)
        cmd.execute()  # should not raise
        assert cmd.annotation_data is None


class TestDeleteAnnotationUndoGuards:
    def test_undo_when_data_is_none(self):
        """Line 492: DeleteAnnotationCommand.undo() returns when data is None."""
        ctrl = CircuitController(CircuitModel())
        cmd = DeleteAnnotationCommand(ctrl, 0)
        # annotation_data is None (never executed successfully)
        cmd.undo()  # should not raise

    def test_undo_out_of_range_index(self):
        """Lines 494-498: DeleteAnnotationCommand.undo() with stale index."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        # Add then delete annotation
        ann = AnnotationData(text="note", x=10, y=20)
        model.annotations.append(ann)
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert len(model.annotations) == 0

        # Now make the stored index invalid (index=0, but annotations list
        # will have items inserted that make 0 > len)
        # Actually: stored index is 0, list is empty, 0 > 0 is False,
        # so it would succeed. We need index > len.
        cmd.annotation_index = 5
        cmd.undo()  # 5 > len(model.annotations) → warning + skip
        assert len(model.annotations) == 0


class TestEditAnnotationExecuteOutOfRange:
    def test_execute_out_of_range_index(self):
        """Lines 517-521: EditAnnotationCommand.execute() with invalid index."""
        ctrl = CircuitController(CircuitModel())
        cmd = EditAnnotationCommand(ctrl, 99, "new text")
        cmd.execute()  # should not raise
        assert cmd.old_text is None


class TestEditAnnotationUndoGuards:
    def test_undo_when_old_text_is_none(self):
        """Line 527: EditAnnotationCommand.undo() returns when old_text is None."""
        ctrl = CircuitController(CircuitModel())
        cmd = EditAnnotationCommand(ctrl, 0, "new text")
        # Don't execute — old_text stays None
        cmd.undo()  # should not raise

    def test_undo_out_of_range_index(self):
        """Lines 529-533: EditAnnotationCommand.undo() with stale index."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        ann = AnnotationData(text="original", x=0, y=0)
        model.annotations.append(ann)

        cmd = EditAnnotationCommand(ctrl, 0, "edited")
        cmd.execute()
        assert model.annotations[0].text == "edited"

        # Remove the annotation to simulate stale state
        model.annotations.clear()
        cmd.undo()  # index out of range, should not raise


# ---------------------------------------------------------------------------
# UndoManager  (lines 102, 111-113)
# ---------------------------------------------------------------------------


class TestUndoManagerDescriptions:
    def test_get_undo_description_empty(self):
        """Line 102: get_undo_description() returns None when stack is empty."""
        manager = UndoManager()
        assert manager.get_undo_description() is None

    def test_get_redo_description_with_value(self):
        """Lines 111-112: get_redo_description() returns description."""
        manager = UndoManager()
        model = CircuitModel()
        ctrl = CircuitController(model)

        cmd = AddComponentCommand(ctrl, "Resistor", (0, 0))
        manager.execute(cmd)
        manager.undo()

        desc = manager.get_redo_description()
        assert desc == "Add Resistor"

    def test_get_redo_description_empty(self):
        """Line 113: get_redo_description() returns None when stack is empty."""
        manager = UndoManager()
        assert manager.get_redo_description() is None

    def test_undo_empty_returns_false(self):
        """Line 61: undo() returns False when stack is empty."""
        manager = UndoManager()
        assert manager.undo() is False

    def test_redo_empty_returns_false(self):
        """Line 77: redo() returns False when stack is empty."""
        manager = UndoManager()
        assert manager.redo() is False


class TestDeleteWireDescription:
    def test_get_description(self):
        """Line 337: DeleteWireCommand.get_description()."""
        ctrl = CircuitController(CircuitModel())
        cmd = DeleteWireCommand(ctrl, 0)
        assert cmd.get_description() == "Delete wire"
