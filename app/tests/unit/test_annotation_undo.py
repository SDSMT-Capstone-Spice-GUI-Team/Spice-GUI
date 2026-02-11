"""Tests for annotation undo/redo commands (issue #229).

Annotations should support undo/redo for add, delete, and edit operations.
"""

import inspect
from unittest.mock import MagicMock, patch


def _make_mock_canvas():
    """Create a mock canvas with scene and annotations list."""
    canvas = MagicMock()
    canvas.annotations = []
    canvas.scene = MagicMock()
    return canvas


def _make_mock_annotation(text="Test note", x=100.0, y=200.0):
    """Create a mock annotation with to_dict/toPlainText support."""
    ann = MagicMock()
    ann.toPlainText.return_value = text
    ann.to_dict.return_value = {"text": text, "x": x, "y": y}
    return ann


class TestAddAnnotationCommand:
    """AddAnnotationCommand should add an annotation to the canvas."""

    @patch("controllers.commands.AddAnnotationCommand.execute")
    def test_command_exists(self, mock_exec):
        """AddAnnotationCommand should be importable."""
        from controllers.commands import AddAnnotationCommand

        canvas = _make_mock_canvas()
        cmd = AddAnnotationCommand(canvas, {"text": "X", "x": 0, "y": 0})
        assert cmd is not None

    def test_execute_adds_to_scene_and_list(self):
        """execute() should add the annotation to scene and canvas.annotations."""
        from controllers.commands import AddAnnotationCommand

        canvas = _make_mock_canvas()
        data = {"text": "Hello", "x": 50.0, "y": 75.0}
        cmd = AddAnnotationCommand(canvas, data)

        mock_ann = MagicMock()
        with patch("GUI.annotation_item.AnnotationItem") as MockAnnotationItem:
            MockAnnotationItem.from_dict.return_value = mock_ann
            cmd.execute()

        canvas.scene.addItem.assert_called_once_with(mock_ann)
        assert mock_ann in canvas.annotations

    def test_undo_removes_from_scene_and_list(self):
        """undo() should remove the annotation from scene and canvas.annotations."""
        from controllers.commands import AddAnnotationCommand

        canvas = _make_mock_canvas()
        data = {"text": "Hello", "x": 50.0, "y": 75.0}
        cmd = AddAnnotationCommand(canvas, data)

        mock_ann = MagicMock()
        with patch("GUI.annotation_item.AnnotationItem") as MockAnnotationItem:
            MockAnnotationItem.from_dict.return_value = mock_ann
            cmd.execute()

        assert len(canvas.annotations) == 1
        cmd.undo()
        canvas.scene.removeItem.assert_called_once_with(mock_ann)
        assert len(canvas.annotations) == 0

    def test_undo_without_execute_is_noop(self):
        """undo() before execute() should not error."""
        from controllers.commands import AddAnnotationCommand

        canvas = _make_mock_canvas()
        cmd = AddAnnotationCommand(canvas, {"text": "X", "x": 0, "y": 0})
        cmd.undo()
        canvas.scene.removeItem.assert_not_called()

    def test_description(self):
        """Should return a meaningful description."""
        from controllers.commands import AddAnnotationCommand

        canvas = _make_mock_canvas()
        cmd = AddAnnotationCommand(canvas, {"text": "X", "x": 0, "y": 0})
        assert "Annotation" in cmd.get_description()


class TestDeleteAnnotationCommand:
    """DeleteAnnotationCommand should remove an annotation from the canvas."""

    def test_execute_removes_from_scene_and_list(self):
        """execute() should remove annotation from scene and list."""
        from controllers.commands import DeleteAnnotationCommand

        canvas = _make_mock_canvas()
        ann = _make_mock_annotation()
        canvas.annotations.append(ann)

        cmd = DeleteAnnotationCommand(canvas, ann)
        cmd.execute()

        canvas.scene.removeItem.assert_called_once_with(ann)
        assert ann not in canvas.annotations

    def test_undo_restores_annotation(self):
        """undo() should re-add the annotation to scene and list."""
        from controllers.commands import DeleteAnnotationCommand

        canvas = _make_mock_canvas()
        ann = _make_mock_annotation()
        canvas.annotations.append(ann)

        cmd = DeleteAnnotationCommand(canvas, ann)
        cmd.execute()
        assert len(canvas.annotations) == 0

        with patch("GUI.annotation_item.AnnotationItem") as MockAnnotationItem:
            MockAnnotationItem.from_dict.return_value = MagicMock()
            cmd.undo()

        canvas.scene.addItem.assert_called_once()
        assert len(canvas.annotations) == 1

    def test_description(self):
        """Should return a meaningful description."""
        from controllers.commands import DeleteAnnotationCommand

        canvas = _make_mock_canvas()
        ann = _make_mock_annotation()
        cmd = DeleteAnnotationCommand(canvas, ann)
        assert "Annotation" in cmd.get_description()

    def test_stores_annotation_data(self):
        """Should serialize annotation data on construction for undo."""
        from controllers.commands import DeleteAnnotationCommand

        canvas = _make_mock_canvas()
        ann = _make_mock_annotation("My note", 50.0, 75.0)
        cmd = DeleteAnnotationCommand(canvas, ann)

        assert cmd.annotation_data == {"text": "My note", "x": 50.0, "y": 75.0}


class TestEditAnnotationCommand:
    """EditAnnotationCommand should change annotation text."""

    def test_execute_sets_new_text(self):
        """execute() should set the new text."""
        from controllers.commands import EditAnnotationCommand

        ann = _make_mock_annotation("Old text")
        cmd = EditAnnotationCommand(ann, "Old text", "New text")

        cmd.execute()
        ann.setPlainText.assert_called_with("New text")

    def test_undo_restores_old_text(self):
        """undo() should restore the old text."""
        from controllers.commands import EditAnnotationCommand

        ann = _make_mock_annotation("Old text")
        cmd = EditAnnotationCommand(ann, "Old text", "New text")

        cmd.execute()
        cmd.undo()
        ann.setPlainText.assert_called_with("Old text")

    def test_description(self):
        """Should return a meaningful description."""
        from controllers.commands import EditAnnotationCommand

        ann = _make_mock_annotation()
        cmd = EditAnnotationCommand(ann, "a", "b")
        assert "Annotation" in cmd.get_description()


class TestAnnotationDoubleClickDelegation:
    """mouseDoubleClickEvent should delegate to canvas._edit_annotation."""

    def test_delegates_to_canvas(self):
        """Double-click should call canvas._edit_annotation if available."""
        from GUI.annotation_item import AnnotationItem

        source = inspect.getsource(AnnotationItem.mouseDoubleClickEvent)
        assert "_edit_annotation" in source

    def test_canvas_edit_method_uses_undo_command(self):
        """Canvas._edit_annotation should use EditAnnotationCommand."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._edit_annotation)
        assert "EditAnnotationCommand" in source


class TestCanvasAnnotationUndoIntegration:
    """Canvas add/delete annotation methods should use undo commands."""

    def test_add_annotation_uses_command(self):
        """add_annotation should use AddAnnotationCommand."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView.add_annotation)
        assert "AddAnnotationCommand" in source

    def test_delete_annotation_uses_command(self):
        """_delete_annotation should use DeleteAnnotationCommand."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._delete_annotation)
        assert "DeleteAnnotationCommand" in source

    def test_delete_selected_delegates_to_delete_annotation(self):
        """delete_selected should call _delete_annotation for annotations."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView.delete_selected)
        assert "_delete_annotation" in source
