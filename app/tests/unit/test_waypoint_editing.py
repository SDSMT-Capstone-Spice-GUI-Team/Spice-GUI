"""
Unit tests for manual waypoint editing (#262).

Tests that draggable handles appear at wire waypoints when the wire is
selected, that dragging a handle updates the wire path, and that the
model is synced and locked after editing.
"""

from unittest.mock import MagicMock, patch

import pytest
from models.wire import WireData
from PyQt6.QtCore import QPointF


@pytest.fixture
def mock_canvas():
    """Create a minimal canvas mock."""
    canvas = MagicMock()
    canvas.wires = []
    canvas.components = {}
    canvas.controller = MagicMock()
    return canvas


@pytest.fixture
def wire_with_waypoints(mock_canvas):
    """Create a WireGraphicsItem with pre-set waypoints (no pathfinding)."""
    from GUI.wire_item import WireGraphicsItem

    model = WireData(
        start_component_id="R1",
        start_terminal=0,
        end_component_id="R2",
        end_terminal=1,
        waypoints=[(0, 0), (50, 0), (50, 50), (100, 50)],
    )

    start_comp = MagicMock()
    start_comp.component_id = "R1"
    start_comp.get_terminal_pos.return_value = QPointF(0, 0)

    end_comp = MagicMock()
    end_comp.component_id = "R2"
    end_comp.get_terminal_pos.return_value = QPointF(100, 50)

    wire = WireGraphicsItem(
        start_comp=start_comp,
        start_term=0,
        end_comp=end_comp,
        end_term=1,
        canvas=mock_canvas,
        model=model,
    )
    return wire


class TestWaypointHandleCreation:
    """Test that waypoint handles are created on selection."""

    def test_handles_list_initially_empty(self, wire_with_waypoints):
        assert wire_with_waypoints._waypoint_handles == []

    def test_show_handles_creates_interior_handles(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        # 4 waypoints, interior = index 1 and 2
        wire_with_waypoints._show_handles()
        assert len(wire_with_waypoints._waypoint_handles) == 2

    def test_hide_handles_removes_all(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        wire_with_waypoints._show_handles()
        assert len(wire_with_waypoints._waypoint_handles) == 2
        wire_with_waypoints._hide_handles()
        assert len(wire_with_waypoints._waypoint_handles) == 0

    def test_no_handles_for_two_point_wire(self, mock_canvas, qtbot):
        from GUI.wire_item import WireGraphicsItem

        model = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
            waypoints=[(0, 0), (100, 0)],
        )
        start_comp = MagicMock()
        start_comp.component_id = "R1"
        start_comp.get_terminal_pos.return_value = QPointF(0, 0)
        end_comp = MagicMock()
        end_comp.component_id = "R2"
        end_comp.get_terminal_pos.return_value = QPointF(100, 0)

        wire = WireGraphicsItem(
            start_comp=start_comp,
            start_term=0,
            end_comp=end_comp,
            end_term=1,
            canvas=mock_canvas,
            model=model,
        )
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire)
        wire._show_handles()
        assert len(wire._waypoint_handles) == 0

    def test_handles_positioned_at_waypoints(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        wire_with_waypoints._show_handles()
        handle1, handle2 = wire_with_waypoints._waypoint_handles
        assert handle1.pos() == QPointF(50, 0)
        assert handle2.pos() == QPointF(50, 50)


class TestWaypointDragging:
    """Test that dragging a handle updates the wire path."""

    def test_move_waypoint_updates_wire(self, wire_with_waypoints, qtbot):
        new_pos = QPointF(60, 10)
        wire_with_waypoints._move_waypoint(1, new_pos)
        assert wire_with_waypoints.waypoints[1] == new_pos

    def test_move_waypoint_ignores_endpoints(self, wire_with_waypoints, qtbot):
        original_start = wire_with_waypoints.waypoints[0]
        wire_with_waypoints._move_waypoint(0, QPointF(999, 999))
        assert wire_with_waypoints.waypoints[0] == original_start

    def test_finish_drag_passes_waypoints_to_canvas(self, wire_with_waypoints, qtbot):
        wire_with_waypoints._move_waypoint(1, QPointF(60, 10))
        wire_with_waypoints._finish_waypoint_drag()
        call_args = wire_with_waypoints.canvas.on_wire_waypoints_changed.call_args
        waypoints = call_args[0][1]  # second positional arg
        assert (60.0, 10.0) in waypoints

    def test_finish_drag_notifies_canvas_with_waypoints(self, wire_with_waypoints, qtbot):
        wire_with_waypoints._move_waypoint(1, QPointF(60, 10))
        wire_with_waypoints._finish_waypoint_drag()
        wire_with_waypoints.canvas.on_wire_waypoints_changed.assert_called_once()
        call_args = wire_with_waypoints.canvas.on_wire_waypoints_changed.call_args
        assert call_args[0][0] is wire_with_waypoints
        # Second arg is tuple waypoints list
        assert isinstance(call_args[0][1], list)

    def test_path_rebuilt_after_move(self, wire_with_waypoints, qtbot):
        old_path = wire_with_waypoints.path()
        old_element_count = old_path.elementCount()
        wire_with_waypoints._move_waypoint(1, QPointF(60, 10))
        new_path = wire_with_waypoints.path()
        # Path should still have same number of elements (segments)
        assert new_path.elementCount() == old_element_count


class TestWaypointDragControllerIntegration:
    """Test that waypoint drag persists through the controller without crash (#482)."""

    def test_finish_drag_waypoints_are_tuples(self, wire_with_waypoints, qtbot):
        """Waypoints sent to canvas must be (x, y) tuples, not QPointF."""
        wire_with_waypoints._move_waypoint(1, QPointF(60, 10))
        wire_with_waypoints._finish_waypoint_drag()
        call_args = wire_with_waypoints.canvas.on_wire_waypoints_changed.call_args
        waypoints = call_args[0][1]
        for wp in waypoints:
            assert isinstance(wp, tuple), f"Expected tuple, got {type(wp)}"
            assert len(wp) == 2

    def test_wire_routed_event_unpacks_without_error(self, wire_with_waypoints, qtbot):
        """Simulate wire_routed event to verify data format is (index, WireData)."""
        from controllers.circuit_controller import CircuitController

        ctrl = CircuitController()
        ctrl.add_component("Resistor", (0.0, 0.0))
        ctrl.add_component("Resistor", (100.0, 0.0))
        ctrl.add_wire("R1", 1, "R2", 0)

        recorded = []
        ctrl.add_observer(lambda name, data: recorded.append((name, data)))

        pts = [(0, 0), (60, 10), (50, 50), (100, 50)]
        ctrl.update_wire_waypoints(0, pts)

        event_name, event_data = recorded[-1]
        assert event_name == "wire_routed"
        # This must not raise ValueError
        wire_index, wire_data = event_data
        assert wire_index == 0
        assert wire_data.waypoints == pts


class TestWaypointHandleProperties:
    """Test WaypointHandle properties and behavior."""

    def test_handle_is_movable(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        wire_with_waypoints._show_handles()
        handle = wire_with_waypoints._waypoint_handles[0]
        flags = handle.flags()
        from PyQt6.QtWidgets import QGraphicsItem

        assert flags & QGraphicsItem.GraphicsItemFlag.ItemIsMovable

    def test_handle_z_value_above_wire(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        wire_with_waypoints._show_handles()
        handle = wire_with_waypoints._waypoint_handles[0]
        assert handle.zValue() > wire_with_waypoints.zValue()


class TestSelectionToggle:
    """Test that selection toggles handles via itemChange."""

    def test_selection_shows_handles(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        wire_with_waypoints.setSelected(True)
        assert len(wire_with_waypoints._waypoint_handles) == 2

    def test_deselection_hides_handles(self, wire_with_waypoints, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(wire_with_waypoints)
        wire_with_waypoints.setSelected(True)
        assert len(wire_with_waypoints._waypoint_handles) == 2
        wire_with_waypoints.setSelected(False)
        assert len(wire_with_waypoints._waypoint_handles) == 0
