"""Tests for grid snapping during group drag (#193).

Verifies that group drag uses the raw (unsnapped) mouse delta for followers
so each follower snaps independently to its nearest grid point, rather than
inheriting the leader's grid-aligned jump.
"""

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


class TestRawDeltaBehavior:
    """Verify that group drag uses raw (unsnapped) delta for followers."""

    def test_follower_snaps_independently_not_by_snapped_delta(self, qtbot):
        """Follower should snap to its own nearest grid point, not be displaced by snapped delta.

        If snapped delta were used instead of raw delta, the follower would land at a
        different grid point than the one nearest to (follower_pos + raw_delta).
        """
        scene = QGraphicsScene()
        # Leader on-grid at 100; follower off-grid at 125
        leader = _add_resistor(scene, "R1", 100, 0)
        follower = _add_resistor(scene, "R2", 125, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        # Leader proposed=106 → snaps to 110 (snapped_delta=10)
        # Raw delta = 106 - 100 = 6
        # Follower with raw delta:    125 + 6  = 131 → snaps to 130  (correct)
        # Follower with snapped delta: 125 + 10 = 135 → snaps to 140  (wrong)
        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(106, 0),
        )

        fx = follower.pos().x()
        assert fx == 130, f"Expected follower at 130 (raw delta), got {fx}"

    def test_two_off_grid_followers_each_snap_to_own_nearest(self, qtbot):
        """Each follower snaps to its own nearest grid, not a shared snapped delta.

        Two followers at different off-grid positions should land at their own
        nearest grid points after the drag, demonstrating independent snapping.
        """
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 0)
        # f1 at 113: raw_delta 6 → 119 → snaps to 120; snapped_delta 10 → 123 → snaps to 120 (same here)
        # f2 at 127: raw_delta 6 → 133 → snaps to 130; snapped_delta 10 → 137 → snaps to 140 (diverges)
        f1 = _add_resistor(scene, "R2", 113, 0)
        f2 = _add_resistor(scene, "R3", 127, 0)

        leader.setSelected(True)
        f1.setSelected(True)
        f2.setSelected(True)

        # Leader proposed=106 → raw_delta=6, snapped_delta=10
        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(106, 0),
        )

        assert f1.pos().x() % GRID_SIZE == 0, f"f1 not on grid: {f1.pos().x()}"
        # f2 must land at 130, not 140 — proves raw delta was used
        assert f2.pos().x() == 130, f"Expected f2 at 130 (raw delta), got {f2.pos().x()}"

    def test_raw_delta_used_not_snapped_delta_on_reverse_drag(self, qtbot):
        """Raw delta should also be used correctly when dragging in the negative direction."""
        scene = QGraphicsScene()
        # Leader on-grid at 110; follower off-grid at 123
        leader = _add_resistor(scene, "R1", 110, 0)
        follower = _add_resistor(scene, "R2", 123, 0)

        leader.setSelected(True)
        follower.setSelected(True)

        # Leader proposed=104 → snaps to 100 (snapped_delta=-10)
        # Raw delta = 104 - 110 = -6
        # Follower with raw delta:    123 + (-6)  = 117 → snaps to 120  (correct)
        # Follower with snapped delta: 123 + (-10) = 113 → snaps to 110  (wrong)
        leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(104, 0),
        )

        fx = follower.pos().x()
        assert fx == 120, f"Expected follower at 120 (raw delta), got {fx}"


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
        assert follower_x - leader_x == 50, f"Expected offset 50, got {follower_x - leader_x}"


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

        assert leader.pos().x() == 100, "Leader should not move when follower has _group_moving"

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
