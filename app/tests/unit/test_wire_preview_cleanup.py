"""Tests for wire preview cleanup on focus loss / cancel (issue #160).

The temp_wire_line and wire-drawing state should be cleaned up when:
- The user presses Escape
- The canvas loses focus (e.g. modal dialog opens)
- cancel_wire_drawing() is called directly
"""

from unittest.mock import MagicMock, patch


class TestCancelWireDrawing:
    """cancel_wire_drawing() should clean up preview line and reset state."""

    def _make_canvas(self):
        from GUI.circuit_canvas import CircuitCanvasView

        cancel = CircuitCanvasView.cancel_wire_drawing
        canvas = MagicMock()
        canvas.cancel_wire_drawing = lambda: cancel(canvas)
        canvas.scene = MagicMock()
        return canvas

    def test_removes_temp_wire_line(self):
        """temp_wire_line should be removed from the scene."""
        canvas = self._make_canvas()
        mock_line = MagicMock()
        canvas.temp_wire_line = mock_line

        canvas.cancel_wire_drawing()

        canvas.scene.removeItem.assert_called_once_with(mock_line)
        assert canvas.temp_wire_line is None

    def test_resets_wire_start_comp(self):
        """wire_start_comp should be set to None."""
        canvas = self._make_canvas()
        canvas.temp_wire_line = None
        canvas.wire_start_comp = MagicMock()
        canvas.wire_start_term = 0

        canvas.cancel_wire_drawing()

        assert canvas.wire_start_comp is None

    def test_resets_wire_start_term(self):
        """wire_start_term should be set to None."""
        canvas = self._make_canvas()
        canvas.temp_wire_line = None
        canvas.wire_start_comp = MagicMock()
        canvas.wire_start_term = 1

        canvas.cancel_wire_drawing()

        assert canvas.wire_start_term is None

    def test_noop_when_no_wire_drawing(self):
        """Should not error when no wire drawing is in progress."""
        canvas = self._make_canvas()
        canvas.temp_wire_line = None
        canvas.wire_start_comp = None
        canvas.wire_start_term = None

        # Should not raise
        canvas.cancel_wire_drawing()

        canvas.scene.removeItem.assert_not_called()
        assert canvas.wire_start_comp is None

    def test_cleans_up_line_and_state_together(self):
        """Both line and state should be cleaned in one call."""
        canvas = self._make_canvas()
        mock_line = MagicMock()
        canvas.temp_wire_line = mock_line
        canvas.wire_start_comp = MagicMock()
        canvas.wire_start_term = 0

        canvas.cancel_wire_drawing()

        canvas.scene.removeItem.assert_called_once_with(mock_line)
        assert canvas.temp_wire_line is None
        assert canvas.wire_start_comp is None
        assert canvas.wire_start_term is None


class TestFocusOutCancelsWireDrawing:
    """focusOutEvent should cancel wire drawing."""

    def test_focus_out_cancels_wire_drawing(self):
        """Losing focus should clean up wire drawing state."""
        import ast
        import inspect
        import textwrap

        from GUI.circuit_canvas import CircuitCanvasView

        # The focusOutEvent method should exist
        assert hasattr(CircuitCanvasView, "focusOutEvent")

        # Verify it calls cancel_wire_drawing via AST
        tree = ast.parse(textwrap.dedent(inspect.getsource(CircuitCanvasView.focusOutEvent)))
        found = any(
            (isinstance(node, ast.Attribute) and node.attr == "cancel_wire_drawing")
            or (isinstance(node, ast.Name) and node.id == "cancel_wire_drawing")
            for node in ast.walk(tree)
        )
        assert found, "cancel_wire_drawing not found in focusOutEvent"

    def test_cancel_wire_drawing_is_public_method(self):
        """cancel_wire_drawing should be a public method on CircuitCanvasView."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "cancel_wire_drawing")
        assert callable(CircuitCanvasView.cancel_wire_drawing)
