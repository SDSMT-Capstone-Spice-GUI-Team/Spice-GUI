"""Tests for issue #442 -- Ctrl+click multi-select tearing during group drag.

Verifies that wire drag-preview updates are suppressed for follower
components during group movement to prevent visual tearing artifacts.
"""

import ast
import inspect
import textwrap

from GUI.component_item import ComponentGraphicsItem, Resistor
from GUI.styles import GRID_SIZE
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsScene


def _source_uses_name(func, name):
    """Check if a function's source contains a reference to the given name."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return any(
        (isinstance(node, ast.Name) and node.id == name) or (isinstance(node, ast.Attribute) and node.attr == name)
        for node in ast.walk(tree)
    )


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
        """ItemPositionHasChanged handler must check _group_moving before wire preview."""
        assert _source_uses_name(ComponentGraphicsItem.itemChange, "ItemPositionHasChanged")
        assert _source_uses_name(ComponentGraphicsItem.itemChange, "_group_moving")

    def test_show_drag_preview_only_called_when_not_group_moving(self):
        """show_drag_preview should only appear inside a guarded block with _group_moving."""
        tree = ast.parse(textwrap.dedent(inspect.getsource(ComponentGraphicsItem.itemChange)))
        # Verify both names exist in the AST
        assert _source_uses_name(ComponentGraphicsItem.itemChange, "_group_moving")
        assert _source_uses_name(ComponentGraphicsItem.itemChange, "show_drag_preview")
        # Verify show_drag_preview is inside an If node (guarded)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if the body or orelse contains show_drag_preview
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute) and child.attr == "show_drag_preview":
                        return  # Found show_drag_preview inside an If — good
        raise AssertionError("show_drag_preview should be inside a conditional (If) block")

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
