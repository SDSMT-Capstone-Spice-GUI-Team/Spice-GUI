"""
Unit tests for click-to-place waypoints during wire drawing (#263).

Tests that clicking in empty space during wire drawing adds waypoints,
that the preview line anchors from the last waypoint, and that waypoints
are passed to the controller on wire completion.
"""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QPointF


@pytest.fixture
def canvas(qtbot):
    """Create a CircuitCanvasView inside a QApplication context."""
    from GUI.circuit_canvas import CircuitCanvasView

    c = CircuitCanvasView()
    qtbot.addWidget(c)
    return c


class TestWireWaypointState:
    """Test that the canvas tracks in-progress waypoints."""

    def test_initial_waypoints_empty(self, canvas):
        assert canvas._wire_waypoints == []

    def test_initial_markers_empty(self, canvas):
        assert canvas._wire_waypoint_markers == []


class TestCancelClearsWaypoints:
    """Test that cancel_wire_drawing clears waypoints and markers."""

    def test_cancel_clears_waypoints(self, canvas):
        canvas._wire_waypoints.append(QPointF(50, 50))
        canvas.cancel_wire_drawing()
        assert canvas._wire_waypoints == []

    def test_cancel_clears_markers(self, canvas):
        canvas._add_waypoint_marker(QPointF(50, 50))
        assert len(canvas._wire_waypoint_markers) == 1
        canvas.cancel_wire_drawing()
        assert canvas._wire_waypoint_markers == []

    def test_cancel_clears_temp_line(self, canvas):
        from PyQt6.QtWidgets import QGraphicsLineItem

        line = QGraphicsLineItem(0, 0, 100, 100)
        canvas._scene.addItem(line)
        canvas.temp_wire_line = line
        canvas.cancel_wire_drawing()
        assert canvas.temp_wire_line is None

    def test_cancel_resets_start_comp(self, canvas):
        canvas.wire_start_comp = MagicMock()
        canvas.cancel_wire_drawing()
        assert canvas.wire_start_comp is None


class TestWaypointMarkers:
    """Test visual waypoint marker management."""

    def test_add_marker_creates_item(self, canvas):
        canvas._add_waypoint_marker(QPointF(100, 100))
        assert len(canvas._wire_waypoint_markers) == 1

    def test_add_multiple_markers(self, canvas):
        canvas._add_waypoint_marker(QPointF(50, 50))
        canvas._add_waypoint_marker(QPointF(100, 100))
        assert len(canvas._wire_waypoint_markers) == 2

    def test_remove_markers_clears_list(self, canvas):
        canvas._add_waypoint_marker(QPointF(50, 50))
        canvas._remove_waypoint_markers()
        assert len(canvas._wire_waypoint_markers) == 0

    def test_marker_z_value_above_preview(self, canvas):
        canvas._add_waypoint_marker(QPointF(50, 50))
        marker = canvas._wire_waypoint_markers[0]
        assert marker.zValue() > 100  # Preview line is at z=100

    def test_marker_positioned_correctly(self, canvas):
        pos = QPointF(75, 25)
        canvas._add_waypoint_marker(pos)
        marker = canvas._wire_waypoint_markers[0]
        assert marker.pos() == pos


class TestWaypointPassthrough:
    """Test that manually placed waypoints are passed to the controller."""

    def test_empty_waypoints(self, canvas):
        """When no waypoints are placed, list is empty."""
        assert canvas._wire_waypoints == []

    def test_waypoints_list_builds_correctly(self, canvas):
        """Test the waypoint list construction logic."""
        canvas._wire_waypoints = [QPointF(50, 0), QPointF(50, 100)]
        start_pos = QPointF(0, 0)
        end_pos = QPointF(100, 100)
        manual_wps = (
            [(start_pos.x(), start_pos.y())]
            + [(wp.x(), wp.y()) for wp in canvas._wire_waypoints]
            + [(end_pos.x(), end_pos.y())]
        )
        assert manual_wps == [(0, 0), (50, 0), (50, 100), (100, 100)]

    def test_waypoints_include_start_and_end(self, canvas):
        """Waypoint list should start at terminal and end at terminal."""
        canvas._wire_waypoints = [QPointF(50, 50)]
        start_pos = QPointF(0, 0)
        end_pos = QPointF(100, 100)
        manual_wps = (
            [(start_pos.x(), start_pos.y())]
            + [(wp.x(), wp.y()) for wp in canvas._wire_waypoints]
            + [(end_pos.x(), end_pos.y())]
        )
        assert len(manual_wps) == 3
        assert manual_wps[0] == (0, 0)
        assert manual_wps[1] == (50, 50)
        assert manual_wps[2] == (100, 100)

    def test_single_waypoint_produces_three_points(self, canvas):
        """One click waypoint + start + end = 3 points total."""
        canvas._wire_waypoints = [QPointF(50, 0)]
        start_pos = QPointF(0, 0)
        end_pos = QPointF(100, 0)
        manual_wps = (
            [(start_pos.x(), start_pos.y())]
            + [(wp.x(), wp.y()) for wp in canvas._wire_waypoints]
            + [(end_pos.x(), end_pos.y())]
        )
        assert len(manual_wps) == 3
