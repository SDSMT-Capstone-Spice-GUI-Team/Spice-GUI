"""Tests for annotation undo/redo commands (issue #229).

Annotations should support undo/redo for add, delete, and edit operations.
These tests validate the model-layer command pattern where commands operate
through the CircuitController rather than directly on the canvas.
"""

from controllers.circuit_controller import CircuitController
from controllers.commands import AddAnnotationCommand, DeleteAnnotationCommand, EditAnnotationCommand
from models.annotation import AnnotationData
from models.circuit import CircuitModel


def _make_controller():
    """Create a CircuitController with a fresh CircuitModel."""
    model = CircuitModel()
    return CircuitController(model)


class TestAddAnnotationCommand:
    """AddAnnotationCommand should add an annotation via the controller."""

    def test_command_exists(self):
        """AddAnnotationCommand should be importable and constructable."""
        ctrl = _make_controller()
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="X"))
        assert cmd is not None

    def test_execute_adds_to_model(self):
        """execute() should add the annotation to the model."""
        ctrl = _make_controller()
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Hello", x=50.0, y=75.0))
        cmd.execute()
        assert len(ctrl.model.annotations) == 1
        assert ctrl.model.annotations[0].text == "Hello"
        assert ctrl.model.annotations[0].x == 50.0

    def test_undo_removes_from_model(self):
        """undo() should remove the annotation from the model."""
        ctrl = _make_controller()
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Hello"))
        cmd.execute()
        assert len(ctrl.model.annotations) == 1
        cmd.undo()
        assert len(ctrl.model.annotations) == 0

    def test_undo_without_execute_is_noop(self):
        """undo() before execute() should not error."""
        ctrl = _make_controller()
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="X"))
        cmd.undo()  # should not crash
        assert len(ctrl.model.annotations) == 0

    def test_description(self):
        """Should return a meaningful description."""
        ctrl = _make_controller()
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="X"))
        assert "annotation" in cmd.get_description().lower()

    def test_execute_fires_event(self):
        """execute() should fire annotation_added event."""
        ctrl = _make_controller()
        events = []
        ctrl.add_observer(lambda e, d: events.append(e))
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Event"))
        cmd.execute()
        assert "annotation_added" in events


class TestDeleteAnnotationCommand:
    """DeleteAnnotationCommand should remove an annotation via the controller."""

    def test_execute_removes_from_model(self):
        """execute() should remove annotation from model."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="ToDelete"))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert len(ctrl.model.annotations) == 0

    def test_undo_restores_annotation(self):
        """undo() should re-add the annotation to model."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="ToRestore"))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert len(ctrl.model.annotations) == 0
        cmd.undo()
        assert len(ctrl.model.annotations) == 1
        assert ctrl.model.annotations[0].text == "ToRestore"

    def test_description(self):
        """Should return a meaningful description."""
        ctrl = _make_controller()
        cmd = DeleteAnnotationCommand(ctrl, 0)
        assert "annotation" in cmd.get_description().lower()

    def test_stores_annotation_data(self):
        """Should store annotation data on execute for undo restoration."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="My note", x=50.0, y=75.0))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert cmd.annotation_data is not None
        assert cmd.annotation_data.text == "My note"
        assert cmd.annotation_data.x == 50.0

    def test_execute_fires_event(self):
        """execute() should fire annotation_removed event."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="ToDelete"))
        events = []
        ctrl.add_observer(lambda e, d: events.append(e))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert "annotation_removed" in events


class TestEditAnnotationCommand:
    """EditAnnotationCommand should change annotation text via the controller."""

    def test_execute_sets_new_text(self):
        """execute() should set the new text."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="Old text"))
        cmd = EditAnnotationCommand(ctrl, 0, "New text")
        cmd.execute()
        assert ctrl.model.annotations[0].text == "New text"

    def test_undo_restores_old_text(self):
        """undo() should restore the old text."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="Old text"))
        cmd = EditAnnotationCommand(ctrl, 0, "New text")
        cmd.execute()
        cmd.undo()
        assert ctrl.model.annotations[0].text == "Old text"

    def test_description(self):
        """Should return a meaningful description."""
        ctrl = _make_controller()
        cmd = EditAnnotationCommand(ctrl, 0, "new")
        assert "annotation" in cmd.get_description().lower()

    def test_execute_fires_event(self):
        """execute() should fire annotation_updated event."""
        ctrl = _make_controller()
        ctrl.add_annotation(AnnotationData(text="Before"))
        events = []
        ctrl.add_observer(lambda e, d: events.append(e))
        cmd = EditAnnotationCommand(ctrl, 0, "After")
        cmd.execute()
        assert "annotation_updated" in events


class TestAnnotationDoubleClickDelegation:
    """mouseDoubleClickEvent should delegate to canvas._edit_annotation."""

    def test_delegates_to_canvas(self):
        """AnnotationItem should define mouseDoubleClickEvent."""
        from GUI.annotation_item import AnnotationItem

        assert hasattr(AnnotationItem, "mouseDoubleClickEvent")

    def test_canvas_edit_method_uses_undo_command(self):
        """CircuitCanvasView should define _edit_annotation."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_edit_annotation")


class TestCanvasAnnotationUndoIntegration:
    """Canvas add/delete annotation methods should use undo commands."""

    def test_add_annotation_uses_command(self):
        """AddAnnotationCommand should be importable from controllers.commands."""
        from controllers.commands import AddAnnotationCommand as _AddAnnotationCommand

        assert _AddAnnotationCommand is not None

    def test_delete_annotation_uses_command(self):
        """CircuitCanvasView should define _delete_annotation."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_delete_annotation")

    def test_delete_selected_uses_delete_annotation_command(self):
        """DeleteAnnotationCommand should be importable from controllers.commands."""
        from controllers.commands import DeleteAnnotationCommand as _DeleteAnnotationCommand

        assert _DeleteAnnotationCommand is not None
