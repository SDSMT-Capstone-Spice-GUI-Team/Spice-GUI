"""Tests for issue #442 -- Ctrl+click multi-select tearing during group drag.

Verifies that wire drag-preview updates are suppressed for follower
components during group movement to prevent visual tearing artifacts.
"""

from unittest.mock import MagicMock

from GUI.component_item import ComponentGraphicsItem, Resistor
from GUI.styles import GRID_SIZE
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsScene


def _add_resistor(scene, comp_id, x, y):
    """Add a resistor to the scene at position (x, y), bypassing snap."""
    comp = Resistor(comp_id)
    scene.addItem(comp)
    comp.setFlag(ComponentGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
    comp.setPos(x, y)
    comp.setFlag(ComponentGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
    return comp


class TestWirePreviewSuppression:
    """Verify that followers skip wire preview during group drag (#442)."""

    def test_group_moving_guard_in_position_has_changed(self):
        """ComponentGraphicsItem must have a _group_moving attribute for the guard."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)
        assert hasattr(comp, "_group_moving"), "ComponentGraphicsItem must have a _group_moving attribute"
        assert comp._group_moving is False, "_group_moving must default to False"
        assert hasattr(comp, "itemChange"), "ComponentGraphicsItem must have an itemChange method"

    def test_show_drag_preview_only_called_when_not_group_moving(self):
        """show_drag_preview on wires should NOT be called while _group_moving is True."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        # Attach a mock canvas with a mock wire
        mock_wire = MagicMock()
        mock_canvas = MagicMock()
        mock_canvas.wires = [mock_wire]
        mock_wire.start_component = comp
        mock_wire.end_component = MagicMock()
        comp.canvas = mock_canvas

        # Simulate the _group_moving guard being active
        comp._group_moving = True
        # Manually invoke the position-changed branch of itemChange
        change = ComponentGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
        comp.itemChange(change, QPointF(GRID_SIZE, 0))

        mock_wire.show_drag_preview.assert_not_called()

    def test_follower_group_moving_flag_during_setpos(self):
        """Follower's _group_moving should be True when leader moves it."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 200, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        # Track _group_moving state during follower's itemChange
        captured_states = []
        orig_itemChange = ComponentGraphicsItem.itemChange

        def tracking_itemChange(self_item, change, value):
            if self_item is follower:
                captured_states.append(self_item._group_moving)
            return orig_itemChange(self_item, change, value)

        ComponentGraphicsItem.itemChange = tracking_itemChange
        try:
            # Move leader, which should move follower with _group_moving=True
            leader.setPos(QPointF(100 + GRID_SIZE, 0))
        finally:
            ComponentGraphicsItem.itemChange = orig_itemChange

        # At least one callback should have seen _group_moving=True
        assert any(captured_states), "follower was never called during group drag"
        assert any(s is True for s in captured_states), "follower's _group_moving was never True during group drag"

    def test_leader_group_moving_stays_false(self):
        """Leader's _group_moving should remain False during its own movement."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 200, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        leader_states = []
        orig_itemChange = ComponentGraphicsItem.itemChange

        def tracking_itemChange(self_item, change, value):
            if self_item is leader:
                leader_states.append(self_item._group_moving)
            return orig_itemChange(self_item, change, value)

        ComponentGraphicsItem.itemChange = tracking_itemChange
        try:
            leader.setPos(QPointF(100 + GRID_SIZE, 0))
        finally:
            ComponentGraphicsItem.itemChange = orig_itemChange

        # Leader should never have _group_moving=True
        assert all(s is False for s in leader_states), "leader's _group_moving was True during its own drag"
