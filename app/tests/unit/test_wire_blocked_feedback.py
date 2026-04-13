"""Tests for wire routing blocked-path feedback (issue #913).

When drawing a wire, if the preview path intersects a component's bounding
rect, the preview line should turn red/dashed and a status bar message should
be emitted.
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QLineF, QPointF, QRectF


class TestWirePreviewIntersectsComponent:
    """_wire_preview_intersects_component checks line-vs-component collision."""

    def _make_canvas(self):
        from GUI.circuit_canvas import CircuitCanvasView

        method = CircuitCanvasView._wire_preview_intersects_component
        canvas = MagicMock()
        canvas._wire_preview_intersects_component = lambda p1, p2: method(canvas, p1, p2)
        return canvas

    def test_line_through_component_returns_true(self):
        """A line passing through a component bounding rect is blocked."""
        canvas = self._make_canvas()
        comp = MagicMock()
        # Component occupies (40,40)-(80,80)
        comp.sceneBoundingRect.return_value = QRectF(40, 40, 40, 40)
        canvas.wire_start_comp = MagicMock()
        canvas.components = {"other": comp}

        result = canvas._wire_preview_intersects_component(QPointF(0, 60), QPointF(100, 60))
        assert result is True

    def test_line_around_component_returns_false(self):
        """A line that doesn't cross the component is not blocked."""
        canvas = self._make_canvas()
        comp = MagicMock()
        comp.sceneBoundingRect.return_value = QRectF(40, 40, 40, 40)
        canvas.wire_start_comp = MagicMock()
        canvas.components = {"other": comp}

        result = canvas._wire_preview_intersects_component(QPointF(0, 0), QPointF(100, 0))
        assert result is False

    def test_start_component_excluded(self):
        """The component where wire drawing started should be excluded."""
        canvas = self._make_canvas()
        start_comp = MagicMock()
        start_comp.sceneBoundingRect.return_value = QRectF(0, 0, 40, 40)
        canvas.wire_start_comp = start_comp
        canvas.components = {"start": start_comp}

        # Line goes right through start_comp but should be ignored
        result = canvas._wire_preview_intersects_component(QPointF(-10, 20), QPointF(50, 20))
        assert result is False

    def test_no_components_returns_false(self):
        """Empty canvas should never report blocked."""
        canvas = self._make_canvas()
        canvas.wire_start_comp = MagicMock()
        canvas.components = {}

        result = canvas._wire_preview_intersects_component(QPointF(0, 0), QPointF(100, 100))
        assert result is False


class TestCheckWirePreviewBlocked:
    """_check_wire_preview_blocked checks full path including waypoints."""

    def _make_canvas(self):
        from GUI.circuit_canvas import CircuitCanvasView

        method = CircuitCanvasView._check_wire_preview_blocked
        intersect_method = CircuitCanvasView._wire_preview_intersects_component
        canvas = MagicMock()
        canvas._check_wire_preview_blocked = lambda pos: method(canvas, pos)
        canvas._wire_preview_intersects_component = lambda p1, p2: intersect_method(canvas, p1, p2)
        return canvas

    def test_blocked_on_first_segment(self):
        """Path blocked between start terminal and first waypoint."""
        canvas = self._make_canvas()
        start_comp = MagicMock()
        start_comp.get_terminal_pos.return_value = QPointF(0, 60)
        canvas.wire_start_comp = start_comp
        canvas.wire_start_term = 0
        canvas._wire_waypoints = [QPointF(100, 60)]

        # Obstacle in the middle
        comp = MagicMock()
        comp.sceneBoundingRect.return_value = QRectF(40, 40, 20, 40)
        canvas.components = {"blocker": comp}

        assert canvas._check_wire_preview_blocked(QPointF(200, 60)) is True

    def test_not_blocked_clear_path(self):
        """No components in the way should return False."""
        canvas = self._make_canvas()
        start_comp = MagicMock()
        start_comp.get_terminal_pos.return_value = QPointF(0, 0)
        canvas.wire_start_comp = start_comp
        canvas.wire_start_term = 0
        canvas._wire_waypoints = []
        canvas.components = {}

        assert canvas._check_wire_preview_blocked(QPointF(100, 0)) is False


class TestCancelClearsBlockedState:
    """cancel_wire_drawing should reset _wire_path_blocked."""

    def test_blocked_flag_reset(self):
        from GUI.circuit_canvas import CircuitCanvasView

        cancel = CircuitCanvasView.cancel_wire_drawing
        canvas = MagicMock()
        canvas.cancel_wire_drawing = lambda: cancel(canvas)
        canvas._scene = MagicMock()
        canvas.temp_wire_line = None
        canvas.wire_start_comp = MagicMock()
        canvas._wire_path_blocked = True

        canvas.cancel_wire_drawing()

        assert canvas._wire_path_blocked is False
