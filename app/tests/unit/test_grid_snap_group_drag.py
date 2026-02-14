"""Tests for grid snapping during group drag (#193).

Verifies that group drag uses the raw (unsnapped) mouse delta for followers
so each follower snaps independently to its nearest grid point, rather than
inheriting the leader's grid-aligned jump.
"""

import inspect

import pytest
from GUI.component_item import ComponentGraphicsItem, Resistor
from GUI.styles import GRID_SIZE
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsScene


def _add_resistor(scene, comp_id, x, y):
    """Add a resistor to the scene at position (x, y), bypassing snap."""
    comp = Resistor(comp_id)
    scene.addItem(comp)
    # Temporarily disable geometry change notifications to place off-grid
    comp.setFlag(ComponentGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
    comp.setPos(x, y)
    comp.setFlag(ComponentGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
    return comp


class TestRawDeltaSourceInspection:
    """Verify the itemChange source uses raw delta, not snapped delta."""

    def test_itemchange_uses_raw_delta(self):
        """itemChange should compute raw_delta from new_pos, not snapped_pos."""
        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        assert "raw_delta" in source

    def test_itemchange_raw_delta_from_new_pos(self):
        """raw_delta should be computed from new_pos (unsnapped), not snapped_pos."""
        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        assert "raw_delta = new_pos - self.pos()" in source

    def test_snapped_delta_only_used_as_guard(self):
        """snapped_delta should only be used to check if leader moved."""
        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        assert "snapped_delta" in source
        # Followers should be moved by raw_delta, not snapped_delta
        assert "item.setPos(item.pos() + raw_delta)" in source


class TestOnGridGroupDrag:
    """On-grid followers should maintain relative positions."""

    def test_on_grid_followers_stay_on_grid(self, qtbot):
        """Followers that start on-grid should remain on-grid after group drag."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 200, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(200, 0),
        )

        fx = follower.pos().x()
        fy = follower.pos().y()
        assert fx % GRID_SIZE == 0, f"Follower x={fx} not on grid"
        assert fy % GRID_SIZE == 0, f"Follower y={fy} not on grid"

    def test_on_grid_relative_offset_preserved(self, qtbot):
        """On-grid followers should maintain the same grid offset as leader."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 150, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        new_pos = leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(100 + GRID_SIZE + 3, 0),
        )

        leader_x = new_pos.x()
        follower_x = follower.pos().x()
        assert (
            follower_x - leader_x == 50
        ), f"Expected offset 50, got {follower_x - leader_x}"


class TestOffGridGroupDrag:
    """Off-grid followers should snap to their nearest grid point."""

    def test_off_grid_follower_snaps_to_grid(self, qtbot):
        """An off-grid follower should end up on-grid after group drag."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 105, 0)  # 5px off-grid

        leader.setSelected(True)
        follower.setSelected(True)

        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(106, 0),
        )

        fx = follower.pos().x()
        assert fx % GRID_SIZE == 0, f"Off-grid follower x={fx} not snapped"

    def test_off_grid_follower_snaps_to_nearest(self, qtbot):
        """Off-grid follower should snap to nearest grid, not overshoot."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        # Follower at 125, halfway between grid lines 120 and 130
        follower = _add_resistor(scene, "R2", 125, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        # Leader proposed=106 → snaps to 110 (moved +10)
        # Raw delta = 106-100 = 6
        # Follower: 125+6=131 → snaps to 130
        # (With old snapped delta=10: 125+10=135 → snaps to 140)
        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(106, 0),
        )

        fx = follower.pos().x()
        assert fx == 130, f"Expected follower at 130, got {fx}"

    def test_off_grid_follower_reverse_drag(self, qtbot):
        """Off-grid follower snaps correctly when dragging in reverse."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 110, 0)
        follower = _add_resistor(scene, "R2", 123, 0)  # off-grid

        leader.setSelected(True)
        follower.setSelected(True)

        # Leader proposed=104 → snaps to 100 (moved -10)
        # Raw delta = 104-110 = -6
        # Follower: 123+(-6)=117 → snaps to 120
        # (With old snapped delta=-10: 123+(-10)=113 → snaps to 110)
        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(104, 0),
        )

        fx = follower.pos().x()
        assert fx == 120, f"Expected follower at 120, got {fx}"


class TestGroupDragGuard:
    """Verify the guard condition prevents unnecessary processing."""

    def test_no_movement_when_leader_stays(self, qtbot):
        """Followers should not move if leader snaps back to same position."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 200, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(103, 0),  # snaps back to 100
        )

        assert follower.pos().x() == 200, "Follower should not move"

    def test_group_moving_flag_prevents_recursion(self, qtbot):
        """_group_moving flag should prevent recursive group moves."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 200, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        follower._group_moving = True
        follower.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(210, 0),
        )

        assert (
            leader.pos().x() == 100
        ), "Leader should not move when follower has _group_moving"

    def test_multiple_followers_all_snap(self, qtbot):
        """All followers in a group should snap independently to grid."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        f1 = _add_resistor(scene, "R2", 113, 0)  # off-grid
        f2 = _add_resistor(scene, "R3", 127, 0)  # off-grid

        leader.setSelected(True)
        f1.setSelected(True)
        f2.setSelected(True)

        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(106, 0),
        )

        assert f1.pos().x() % GRID_SIZE == 0, f"f1 not on grid: {f1.pos().x()}"
        assert f2.pos().x() % GRID_SIZE == 0, f"f2 not on grid: {f2.pos().x()}"
