"""Tests for Backspace removing last waypoint during wire drawing (#484).

Pressing Backspace while wire drawing is in progress should remove the
most recently placed waypoint and its visual marker.

We test via structural and model-layer checks because CircuitCanvasView
cannot be instantiated without a full MainWindow.
"""

import ast
import inspect
import textwrap

from PyQt6.QtCore import Qt


def _get_key_handler_source():
    """Return the source of CircuitCanvasView.keyPressEvent."""
    from GUI.circuit_canvas import CircuitCanvasView

    return textwrap.dedent(inspect.getsource(CircuitCanvasView.keyPressEvent))


class TestBackspaceHandlerExists:
    """Verify that the Backspace handler is present and structurally correct."""

    def test_key_backspace_referenced(self):
        """keyPressEvent should reference Key_Backspace."""
        src = _get_key_handler_source()
        assert "Key_Backspace" in src

    def test_waypoints_pop_called(self):
        """The handler should call _wire_waypoints.pop() to remove the last waypoint."""
        src = _get_key_handler_source()
        assert "_wire_waypoints.pop()" in src

    def test_marker_removed(self):
        """The handler should remove the last marker via removeItem."""
        src = _get_key_handler_source()
        assert "removeItem" in src

    def test_event_accepted(self):
        """The handler should call event.accept() after processing Backspace."""
        src = _get_key_handler_source()
        # After the Key_Backspace block, event.accept() should be called
        assert "event.accept()" in src

    def test_backspace_checks_wire_drawing_active(self):
        """Backspace should only act when wire_start_comp is not None."""
        src = _get_key_handler_source()
        tree = ast.parse(src)
        # Find the if-block that checks Key_Backspace
        found_guard = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if this if-block mentions Key_Backspace and wire_start_comp
                block_src = ast.get_source_segment(src, node)
                if block_src and "Key_Backspace" in block_src and "wire_start_comp" in block_src:
                    found_guard = True
        assert found_guard, "Backspace handler should check wire_start_comp is not None"

    def test_backspace_checks_waypoints_nonempty(self):
        """Backspace should check _wire_waypoints is non-empty before popping."""
        src = _get_key_handler_source()
        tree = ast.parse(src)
        found_guard = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                block_src = ast.get_source_segment(src, node)
                if block_src and "Key_Backspace" in block_src and "_wire_waypoints" in block_src:
                    found_guard = True
        assert found_guard, "Backspace handler should check _wire_waypoints is non-empty"

    def test_preview_line_re_anchored(self):
        """After removing a waypoint, the preview line should be re-anchored."""
        src = _get_key_handler_source()
        assert "setLine" in src, "Preview line should be updated via setLine after Backspace"
