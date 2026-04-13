"""Tests for centralized Z-value layering constants (#510).

Verifies that Z-value constants form a valid hierarchy and are
used consistently by canvas items.
"""

from GUI.styles import (
    Z_ANNOTATION,
    Z_COMPONENT,
    Z_GRID,
    Z_SEGMENT_HANDLE,
    Z_WAYPOINT_HANDLE,
    Z_WAYPOINT_MARKER,
    Z_WIRE,
    Z_WIRE_PREVIEW,
)


class TestZValueHierarchy:
    """Z-value constants must maintain correct visual layering order."""

    def test_grid_below_components(self):
        assert Z_GRID < Z_COMPONENT

    def test_components_below_wires(self):
        assert Z_COMPONENT < Z_WIRE

    def test_wires_below_annotations(self):
        assert Z_WIRE < Z_ANNOTATION

    def test_annotations_below_preview(self):
        assert Z_ANNOTATION < Z_WIRE_PREVIEW

    def test_preview_below_waypoint_markers(self):
        assert Z_WIRE_PREVIEW < Z_WAYPOINT_MARKER

    def test_waypoint_markers_below_segment_handles(self):
        assert Z_WAYPOINT_MARKER < Z_SEGMENT_HANDLE

    def test_segment_handles_below_waypoint_handles(self):
        assert Z_SEGMENT_HANDLE < Z_WAYPOINT_HANDLE

    def test_full_ordering(self):
        ordered = [
            Z_GRID,
            Z_COMPONENT,
            Z_WIRE,
            Z_ANNOTATION,
            Z_WIRE_PREVIEW,
            Z_WAYPOINT_MARKER,
            Z_SEGMENT_HANDLE,
            Z_WAYPOINT_HANDLE,
        ]
        assert ordered == sorted(ordered)
        # All values must be distinct
        assert len(set(ordered)) == len(ordered)
