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


def _terminals_in_window(comp):
    """True if *every* terminal of the component stays inside the route window.

    This is the invariant the clamp must actually guarantee. The pathfinding
    window constrains terminal positions (the component's ``pos()`` plus its
    rotated terminal offset), not the component origin. A component whose
    terminals extend past its origin, if clamped to the origin at
    +/-GRID_EXTENT, would leave a terminal outside the window -- the
    off-screen-hang bug this suite targets. The clamp therefore pulls the
    origin inward by the terminal extent so the extreme terminal still lands at
    the window edge.
    """
    return all(_in_window(comp.get_terminal_pos(i)) for i in range(len(comp.terminals)))


def _clamp_edge(comp, axis):
    """The origin the clamp returns when dragging that axis fully off-screen.

    Equal to +/- (GRID_EXTENT - terminal_extent) for that axis, where
    terminal_extent is how far the extreme terminal sits from the origin.
    """
    coord_key = "x" if axis == "x" else "y"
    extent = max(abs(getattr(comp.terminals[i], coord_key)()) for i in range(len(comp.terminals)))
    return GRID_EXTENT - extent


class TestClampToFixedRouteWindow:
    """Dragging a component off-screen keeps its terminals inside the window."""

    def test_far_offscreen_drag_clamps_keeping_terminals_in_window(self, qtbot):
        """Dragging far off-screen clamps so both terminals land in-window."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(100000, 100000))

        # The origin clamps inward by the terminal extent on each axis so the
        # extreme terminal still lands at exactly GRID_EXTENT.
        assert result.x() == _clamp_edge(comp, "x"), f"got {result.x()}"
        assert result.y() == _clamp_edge(comp, "y"), f"got {result.y()}"
        assert _terminals_in_window(comp)

    def test_far_negative_drag_clamps_keeping_terminals_in_window(self, qtbot):
        """Dragging far negative clamps so terminals land in-window."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(-999999, -999999))

        assert result.x() == -_clamp_edge(comp, "x")
        assert result.y() == -_clamp_edge(comp, "y")
        assert _terminals_in_window(comp)

    def test_asymmetric_offscreen_drag_clamps_each_axis(self, qtbot):
        """Each axis is clamped independently (one may be in-bounds)."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(750, -600))

        assert result.x() == _clamp_edge(comp, "x")  # x off-screen -> clamped
        assert result.y() == -_clamp_edge(comp, "y")  # y off-screen -> clamped
        assert _terminals_in_window(comp)

    def test_in_bounds_drag_returns_unchanged(self, qtbot):
        """A drag within the route window passes through unchanged."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(70, 200))

        assert result.x() == 70
        assert result.y() == 200
        assert _in_window(result)
        assert _terminals_in_window(comp)

    def test_just_outside_boundary_clamps_in(self, qtbot):
        """A value just outside the boundary clamps back inside."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)

        result = _drag(comp, QPointF(GRID_EXTENT + 1, 450))

        # The +1 pushes x past the window; the +30 terminal would sit at
        # GRID_EXTENT + 1 + 30, so the origin clamps inward to GRID_EXTENT - 30.
        assert result.x() == GRID_EXTENT - 30, f"got {result.x()}"
        assert result.y() == 450  # comfortably inside the route window -> unchanged
        assert _terminals_in_window(comp)


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

        assert result.x() == _clamp_edge(follower, "x"), f"Follower x not clamped: {result.x()}"
        assert result.y() == _clamp_edge(follower, "y"), f"Follower y not clamped: {result.y()}"
        assert _terminals_in_window(follower)

    def test_leader_itemChange_clamps_offscreen(self, qtbot):
        """The leader's accepted position clamps when dragged off-screen."""
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 100, 100)

        result = leader.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(100000, 100000),
        )

        assert result.x() == _clamp_edge(leader, "x"), f"Leader x not clamped: {result.x()}"
        assert result.y() == _clamp_edge(leader, "y"), f"Leader y not clamped: {result.y()}"
        assert _terminals_in_window(leader)


class TestGroupDragPreservesSpacing:
    """A group drag must move every selected component by the *same tightest* delta.

    The leader passes a raw (unclamped) delta to followers. When the leader is
    dragged past the route boundary, the naive behavior still sends followers the
    full mouse delta, so each follower clamps to the same edge and the selection
    collapses onto itself. The leader must instead move every selected component
    by the *same tightest* delta — the largest delta that keeps *every* component's
    terminals in bounds — so the group keeps its shape.
    """

    def test_leader_limiting_group_moves_by_leader_delta(self, qtbot):
        """When the leader is the limiting component, the group moves by +70.

        Leader at 400, follower at 300 (100 px to the left). Dragging the leader
        far off-screen (+x) would, with the raw delta, push the follower to
        x=1_000_300 (then clamped to 470) and stack it on the leader. Instead the
        leader is the limiting component (reaches its clamp edge at x=470), so
        the shared delta is +70 and the follower lands at x=370.
        """
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 400, 0)
        follower = _add_resistor(scene, "R2", 300, 0)
        leader.setSelected(True)
        follower.setSelected(True)

        _drag(leader, QPointF(1_000_000, 0))

        assert follower.x() == 370, f"follower collapsed to {follower.x()} (expected 370)"

    def test_follower_limiting_group_moves_by_follower_delta(self, qtbot):
        """When a follower is the limiting component, the group moves by +70.

        Leader at 300, follower at 400 (100 px to the right, closer to the +x
        boundary). The leader alone could reach x=470 (delta +170), but the
        follower is the tighter component: it hits its clamp edge at x=470 with
        only a +70 delta. The shared delta is the tightest (+70), so the whole
        group moves by +70 and keeps its shape — the leader can't drift past the
        follower (#939). (Note: in this unit harness only the follower's position
        is updated by the group loop; the leader's own ``pos()`` is moved by Qt.)
        """
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 300, 0)
        follower = _add_resistor(scene, "R2", 400, 0)
        leader.setSelected(True)
        follower.setSelected(True)

        _drag(leader, QPointF(1_000_000, 0))

        # Tightest delta is +70 (the follower's clamp edge at x=470), so the
        # follower lands at 470 rather than overshooting into the leader.
        assert follower.x() == 470, f"follower should move +70 (tightest), got {follower.x()}"
        assert _terminals_in_window(follower)


class TestConnectedComponentsOffscreen:
    """Two connected components dragged off-screen must stay in-window (Blake's request).

    Blake flagged that dragging one of two *connected* components off-screen crashes
    the app via the line pathing: if the moved component's terminal settles outside
    the route window, rerouting the wire between them falls back to a straight-line
    spanning off-screen. The group-drag clamp must therefore keep *every* connected
    component's terminals in-window, not just the leader's, so reroute always has an
    in-bounds path to work with.
    """

    def test_connected_pair_stays_in_window_when_leader_dragged_offscreen(self, qtbot):
        """Dragging the leader far off-screen keeps both connected components in-window.

        The two resistors are 100 px apart (leader at 400, follower at 300). Dragging
        the leader far off-screen (+x) would collapse the follower onto the leader with
        the old raw-delta behavior. With the group clamp, the shared delta is limited by
        the leader's own clamp edge (x=470, delta +70), so the follower lands at x=370.
        Crucially, *both* components' terminals must remain inside the route window —
        that is what lets the wire between them route without falling off-screen.
        """
        scene = QGraphicsScene()
        leader = _add_resistor(scene, "R1", 400, 0)
        follower = _add_resistor(scene, "R2", 300, 0)
        leader.setSelected(True)
        follower.setSelected(True)

        _drag(leader, QPointF(1_000_000, 0))

        # The group keeps its shape (follower moves +70, not collapsed onto leader).
        assert follower.x() == 370, f"follower collapsed to {follower.x()}, expected 370"
        # Both components' terminals must stay in-window so the wire between them routes.
        assert _terminals_in_window(leader), "leader terminals escaped the route window"
        assert _terminals_in_window(follower), "follower terminals escaped the route window"
