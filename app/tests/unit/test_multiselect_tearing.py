"""Tests for issue #442 — Ctrl+click multi-select tearing during group drag.

Verifies that wire drag-preview updates are suppressed for follower
components during group movement to prevent visual tearing artifacts.
"""

import inspect

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

    # AUDIT(testing): inspect.getsource() string matching on itemChange is an implementation test — tests will break on variable rename even if behavior is correct
    def test_group_moving_guard_in_position_has_changed(self):
        """ItemPositionHasChanged handler must check _group_moving before wire preview."""
        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        # The handler should contain both the enum and the guard
        assert "ItemPositionHasChanged" in source
        assert "not self._group_moving" in source

    def test_show_drag_preview_only_called_when_not_group_moving(self):
        """show_drag_preview should only appear inside the not _group_moving block."""
        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        lines = source.split("\n")
        # Find the line with _group_moving guard and the line with show_drag_preview
        guard_line = None
        preview_line = None
        for i, line in enumerate(lines):
            if "not self._group_moving" in line:
                guard_line = i
            if "show_drag_preview" in line:
                preview_line = i
        assert guard_line is not None, "_group_moving guard not found"
        assert preview_line is not None, "show_drag_preview not found"
        # The preview call must come AFTER the guard
        assert preview_line > guard_line

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
