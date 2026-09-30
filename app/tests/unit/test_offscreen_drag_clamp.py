"""Tests for dragging a component off-screen, clamped to the fixed route window.

Dragging a component beyond the route window (±GRID_EXTENT) previously let a
terminal settle outside the pathfinding route window. Pathfinding then pruned
every neighbor, fell back to a straight-line wire spanning off-screen, and the
forced viewport repaint could hang the app.

Qt uses the value an item returns from ``itemChange`` for ``ItemPositionChange``
to place the item, so we clamp there. The clamp must use a *fixed* boundary
(``±GRID_EXTENT``), not ``sceneRect()``: ``QGraphicsScene`` auto-expands
``sceneRect()`` to follow whatever is dragged, so clamping to it is a no-op and
the component escapes off-screen.

These tests pin that (a) the accepted snapped position stays within the fixed
route window, and (b) the committed ``_pending_position`` — the value actually
passed to ``move_component`` and the batch reroute — is likewise clamped.
"""

from GUI.component_item import ComponentGraphicsItem, Resistor
from GUI.styles import GRID_EXTENT
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


def _drag(comp, proposed):
    """Call itemChange with ItemPositionChange and return the accepted value."""
    return comp.itemChange(
        ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
        proposed,
    )


def _in_window(pos):
    """True if the point is within the fixed route window (±GRID_EXTENT)."""
    x, y = pos.x(), pos.y()
    return -GRID_EXTENT <= x <= GRID_EXTENT and -GRID_EXTENT <= y <= GRID_EXTENT


class TestClampToFixedRouteWindow:
    """The accepted snapped position from a drag stays within ±GRID_EXTENT."""

    def test_far_offscreen_drag_clamps_to_corner(self, qtbot):
        """Dragging far off-screen returns the clipped corner, not a huge coord."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(100000, 100000))

        assert result.x() == GRID_EXTENT, f"Expected x clamped to {GRID_EXTENT}, got {result.x()}"
        assert result.y() == GRID_EXTENT, f"Expected y clamped to {GRID_EXTENT}, got {result.y()}"
        assert _in_window(result)

    def test_far_negative_drag_clamps_to_corner(self, qtbot):
        """Dragging far negative clamps to the (-GRID_EXTENT, -GRID_EXTENT) corner."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(-999999, -999999))

        assert result.x() == -GRID_EXTENT
        assert result.y() == -GRID_EXTENT

    def test_asymmetric_offscreen_drag_clamps_each_axis(self, qtbot):
        """Each axis is clamped independently (one may be in-bounds)."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(750, -600))

        assert result.x() == GRID_EXTENT  # x off-screen -> clamped
        assert result.y() == -GRID_EXTENT  # y off-screen -> clamped
        assert _in_window(result)

    def test_in_bounds_drag_returns_unchanged(self, qtbot):
        """A drag within the route window passes through unchanged."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(70, 200))

        assert result.x() == 70
        assert result.y() == 200
        assert _in_window(result)

    def test_just_outside_boundary_clamps_in(self, qtbot):
        """A value just outside the boundary clamps back inside."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(GRID_EXTENT + 1, 450))

        assert result.x() == GRID_EXTENT, f"Expected x clamped to {GRID_EXTENT}, got {result.x()}"
        assert result.y() == 450  # comfortably inside the route window -> unchanged


class TestClampedCommittedPosition:
    """The _pending_position committed to the model is also clamped.

    This is the value passed to ``move_component`` and the batch reroute; if it
    escapes off-screen the reroute routes a terminal outside the route window,
    which is what hangs the app. The clamp must therefore constrain it too.
    """

    def test_pending_position_clamped_offscreen_drag(self, qtbot):
        """_pending_position stays within ±GRID_EXTENT on a hard drag."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        _drag(comp, QPointF(100000, 100000))

        committed = comp._pending_position
        assert committed is not None
        cx, cy = committed
        assert -GRID_EXTENT <= cx <= GRID_EXTENT, f"committed x={cx} outside window"
        assert -GRID_EXTENT <= cy <= GRID_EXTENT, f"committed y={cy} outside window"

    def test_pending_position_matches_accepted_position(self, qtbot):
        """The committed value equals the accepted (clamped) position."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        accepted = _drag(comp, QPointF(100000, -100000))
        committed = comp._pending_position

        assert committed == (accepted.x(), accepted.y())


class TestGroupDragClamp:
    """A follower that Qt drags off-screen clamps through its own itemChange."""

    def test_follower_itemChange_clamps_offscreen(self, qtbot):
        """A follower's own itemChange clamps even during a group drag."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 0, 0)
        follower = _add_resistor(scene, "R2", 100, 0)

        leader.setSelected(True)
        follower.setSelected(True)
        follower._group_moving = True  # set during group drag

        result = follower.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(999999, 999999),
        )

        assert result.x() == GRID_EXTENT, f"Follower x not clamped: {result.x()}"
        assert result.y() == GRID_EXTENT, f"Follower y not clamped: {result.y()}"

    def test_leader_itemChange_clamps_offscreen(self, qtbot):
        """The leader's accepted position clamps when dragged off-screen."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 100)

        result = leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(100000, 100000),
        )

        assert result.x() == GRID_EXTENT, f"Leader x not clamped: {result.x()}"
        assert result.y() == GRID_EXTENT, f"Leader y not clamped: {result.y()}"
