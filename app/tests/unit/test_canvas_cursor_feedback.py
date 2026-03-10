"""
Unit tests for Issue #511: Canvas interaction modes cursor feedback.

Tests that the canvas sets appropriate cursors when entering/exiting
wire-drawing mode and probe mode.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from GUI.canvas_probe_overlay import CanvasProbeOverlay
from PyQt6.QtCore import Qt


class TestWireDrawingCursor:
    """Test cursor changes during wire drawing mode."""

    @pytest.fixture
    def canvas(self):
        """Create a mock CircuitCanvasView with relevant state."""
        with patch("GUI.circuit_canvas.QGraphicsScene"):
            from GUI.circuit_canvas import CircuitCanvasView

            canvas = CircuitCanvasView.__new__(CircuitCanvasView)
            # Manually initialise only the attributes the tests touch
            canvas.probe_overlay = CanvasProbeOverlay(canvas)
            canvas.wire_start_comp = None
            canvas.wire_start_term = None
            canvas.temp_wire_line = None
            canvas._wire_waypoints = []
            canvas._wire_waypoint_markers = []
            canvas.probe_mode = False
            canvas.scene = MagicMock()
            canvas.setCursor = MagicMock()
            canvas.unsetCursor = MagicMock()
            return canvas

    def test_cancel_wire_drawing_resets_cursor_when_was_drawing(self, canvas):
        """Cursor should be unset when wire drawing is cancelled."""
        canvas.wire_start_comp = MagicMock()  # Simulate active wire drawing
        canvas.cancel_wire_drawing()
        canvas.unsetCursor.assert_called_once()

    def test_cancel_wire_drawing_no_reset_when_not_drawing(self, canvas):
        """No cursor reset should happen if there was no active wire drawing."""
        canvas.wire_start_comp = None
        canvas.cancel_wire_drawing()
        canvas.unsetCursor.assert_not_called()

    def test_cancel_clears_wire_state(self, canvas):
        """cancel_wire_drawing must clear all wire-drawing state."""
        canvas.wire_start_comp = MagicMock()
        canvas.wire_start_term = 0
        canvas._wire_waypoints = [MagicMock()]
        canvas.cancel_wire_drawing()
        assert canvas.wire_start_comp is None
        assert canvas.wire_start_term is None
        assert canvas._wire_waypoints == []


class TestProbeModeCursor:
    """Test cursor changes for probe mode."""

    @pytest.fixture
    def canvas(self):
        with patch("GUI.circuit_canvas.QGraphicsScene"):
            from GUI.circuit_canvas import CircuitCanvasView

            canvas = CircuitCanvasView.__new__(CircuitCanvasView)
            canvas.probe_overlay = CanvasProbeOverlay(canvas)
            canvas.wire_start_comp = None
            canvas.wire_start_term = None
            canvas.temp_wire_line = None
            canvas._wire_waypoints = []
            canvas._wire_waypoint_markers = []
            canvas.probe_mode = False
            canvas.scene = MagicMock()
            canvas.setCursor = MagicMock()
            canvas.unsetCursor = MagicMock()
            canvas.probe_results = []
            return canvas

    def test_probe_mode_active_sets_cross_cursor(self, canvas):
        """Activating probe mode should set CrossCursor."""
        canvas.set_probe_mode(True)
        canvas.setCursor.assert_called_once_with(Qt.CursorShape.CrossCursor)

    def test_probe_mode_inactive_unsets_cursor(self, canvas):
        """Deactivating probe mode should unset cursor."""
        canvas.probe_mode = True
        canvas.set_probe_mode(False)
        canvas.unsetCursor.assert_called_once()

    def test_probe_mode_cancels_wire_drawing(self, canvas):
        """Entering probe mode while wire drawing should cancel wire drawing."""
        canvas.wire_start_comp = MagicMock()
        canvas.wire_start_term = 0
        canvas.set_probe_mode(True)
        # Wire drawing should be cancelled
        assert canvas.wire_start_comp is None
        assert canvas.wire_start_term is None

    def test_probe_mode_sets_flag(self, canvas):
        """set_probe_mode should update the probe_mode flag."""
        canvas.set_probe_mode(True)
        assert canvas.probe_mode is True
        canvas.set_probe_mode(False)
        assert canvas.probe_mode is False
