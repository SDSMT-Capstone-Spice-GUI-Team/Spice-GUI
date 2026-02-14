"""Tests for path_finding.py — IDA* wire routing algorithm."""

import pytest
from GUI.path_finding import IDAStarPathfinder
from PyQt6.QtCore import QPointF

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GRID = 20  # default grid size used in pathfinder


@pytest.fixture
def pathfinder():
    """Yield the IDA* pathfinder implementation."""
    return IDAStarPathfinder(grid_size=GRID)


# Small bounds that keep tests fast
BOUNDS = (-200, -200, 400, 400)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _grid(gx, gy):
    """Shorthand: grid coords -> QPointF in scene coordinates."""
    return QPointF(gx * GRID, gy * GRID)


def _to_grid_tuples(waypoints):
    """Convert list of QPointF waypoints to list of (gx, gy) grid tuples."""
    return [(round(p.x() / GRID), round(p.y() / GRID)) for p in waypoints]


# ===========================================================================
# 1. Grid conversion helpers
# ===========================================================================


class TestGridConversion:
    def test_pos_to_grid(self, pathfinder):
        assert pathfinder._pos_to_grid(QPointF(0, 0)) == (0, 0)
        assert pathfinder._pos_to_grid(QPointF(40, 60)) == (2, 3)

    def test_grid_to_pos(self, pathfinder):
        pos = pathfinder._grid_to_pos((2, 3))
        assert pos.x() == 40
        assert pos.y() == 60

    def test_round_trip(self, pathfinder):
        for gx, gy in [(0, 0), (5, -3), (-10, 7)]:
            assert pathfinder._pos_to_grid(pathfinder._grid_to_pos((gx, gy))) == (
                gx,
                gy,
            )

    def test_pos_to_grid_rounds(self, pathfinder):
        """Positions that aren't exactly on grid should round to nearest cell."""
        assert pathfinder._pos_to_grid(QPointF(11, 29)) == (1, 1)
        assert pathfinder._pos_to_grid(QPointF(9, 31)) == (0, 2)


# ===========================================================================
# 2. Heuristic
# ===========================================================================


class TestHeuristic:
    def test_same_point(self, pathfinder):
        assert pathfinder._heuristic((0, 0), (0, 0)) == 0

    def test_manhattan_distance(self, pathfinder):
        assert pathfinder._heuristic((0, 0), (3, 4)) == 7
        assert pathfinder._heuristic((-2, -3), (2, 3)) == 10


# ===========================================================================
# 3. Path simplification
# ===========================================================================


class TestSimplifyPath:
    def test_two_points_unchanged(self, pathfinder):
        pts = [_grid(0, 0), _grid(5, 0)]
        assert pathfinder._simplify_path(pts) == pts

    def test_collinear_points_removed(self, pathfinder):
        # Three horizontal points — middle one should be removed
        pts = [_grid(0, 0), _grid(1, 0), _grid(2, 0)]
        result = pathfinder._simplify_path(pts)
        assert len(result) == 2
        assert result[0] == pts[0]
        assert result[-1] == pts[-1]

    def test_bend_preserved(self, pathfinder):
        # L-shaped path — corner must stay
        pts = [_grid(0, 0), _grid(3, 0), _grid(3, 3)]
        result = pathfinder._simplify_path(pts)
        assert len(result) == 3


# ===========================================================================
# 4. Same-direction helper
# ===========================================================================


class TestSameDirection:
    def test_same(self, pathfinder):
        assert pathfinder._same_direction(1, 0, 1, 0) is True

    def test_different(self, pathfinder):
        assert pathfinder._same_direction(1, 0, 0, 1) is False

    def test_opposite(self, pathfinder):
        assert pathfinder._same_direction(1, 0, -1, 0) is False


# ===========================================================================
# 5. Basic routing
# ===========================================================================


class TestBasicRouting:
    def test_same_start_and_end(self, pathfinder):
        """Same point should return a trivial path."""
        start = end = _grid(0, 0)
        waypoints, runtime, iters, _ = pathfinder.find_path(
            start, end, set(), bounds=BOUNDS
        )
        grid_pts = _to_grid_tuples(waypoints)
        assert grid_pts[0] == (0, 0)
        assert grid_pts[-1] == (0, 0)

    def test_adjacent_points(self, pathfinder):
        """Adjacent grid cells — path should be length 2."""
        start, end = _grid(0, 0), _grid(1, 0)
        waypoints, _, _, _ = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        grid_pts = _to_grid_tuples(waypoints)
        assert grid_pts[0] == (0, 0)
        assert grid_pts[-1] == (1, 0)

    def test_straight_horizontal(self, pathfinder):
        """Route along empty horizontal line."""
        start, end = _grid(0, 0), _grid(5, 0)
        waypoints, _, _, _ = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        grid_pts = _to_grid_tuples(waypoints)
        assert grid_pts[0] == (0, 0)
        assert grid_pts[-1] == (5, 0)
        # Simplified path should be just 2 points (no bends)
        assert len(waypoints) == 2

    def test_straight_vertical(self, pathfinder):
        """Route along empty vertical line."""
        start, end = _grid(0, 0), _grid(0, 5)
        waypoints, _, _, _ = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        grid_pts = _to_grid_tuples(waypoints)
        assert grid_pts[0] == (0, 0)
        assert grid_pts[-1] == (0, 5)
        assert len(waypoints) == 2

    def test_runtime_returned(self, pathfinder):
        """Runtime should be a non-negative float."""
        start, end = _grid(0, 0), _grid(3, 3)
        _, runtime, _, _ = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        assert isinstance(runtime, float)
        assert runtime >= 0


# ===========================================================================
# 6. Obstacle avoidance
# ===========================================================================


class TestObstacleAvoidance:
    def test_routes_around_single_obstacle(self, pathfinder):
        """A wall of obstacles should force a detour."""
        # Block the direct horizontal path at x=2
        obstacles = {(2, y) for y in range(-5, 6)}
        start, end = _grid(0, 0), _grid(4, 0)
        waypoints, _, _, _ = pathfinder.find_path(start, end, obstacles, bounds=BOUNDS)
        grid_pts = _to_grid_tuples(waypoints)
        assert grid_pts[0] == (0, 0)
        assert grid_pts[-1] == (4, 0)
        # Path must NOT pass through any obstacle cell
        for pt in grid_pts:
            assert pt not in obstacles

    def test_obstacle_at_midpoint(self, pathfinder):
        """Single obstacle in the direct path."""
        obstacles = {(2, 0)}
        start, end = _grid(0, 0), _grid(4, 0)
        waypoints, _, _, _ = pathfinder.find_path(start, end, obstacles, bounds=BOUNDS)
        grid_pts = _to_grid_tuples(waypoints)
        assert (2, 0) not in grid_pts
        assert grid_pts[-1] == (4, 0)


# ===========================================================================
# 7. Orthogonal paths (no diagonals)
# ===========================================================================


class TestOrthogonalPaths:
    def test_path_is_orthogonal(self, pathfinder):
        """All segments should be horizontal or vertical (no diagonals)."""
        start, end = _grid(0, 0), _grid(3, 4)
        waypoints, _, _, _ = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        for i in range(len(waypoints) - 1):
            dx = waypoints[i + 1].x() - waypoints[i].x()
            dy = waypoints[i + 1].y() - waypoints[i].y()
            # At least one of dx/dy must be zero (no diagonal movement)
            assert dx == 0 or dy == 0, f"Diagonal segment: ({dx}, {dy})"


# ===========================================================================
# 8. Performance
# ===========================================================================


class TestPerformance:
    def test_completes_within_time_limit(self, pathfinder):
        """Routing across a moderately-sized grid should finish in < 5s."""
        start, end = _grid(-8, -8), _grid(8, 8)
        _, runtime, _, _ = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        assert runtime < 5.0

    def test_performance_tracking(self, pathfinder):
        """Pathfinder should track iterations and runtime."""
        start, end = _grid(0, 0), _grid(3, 0)
        pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        assert pathfinder.last_runtime >= 0
        assert pathfinder.last_iterations >= 0


# ===========================================================================
# 9. Reconstruct path helper
# ===========================================================================


class TestReconstructPath:
    def test_single_node(self, pathfinder):
        path = pathfinder._reconstruct_path({}, (0, 0))
        assert path == [(0, 0)]

    def test_chain(self, pathfinder):
        came_from = {(1, 0): (0, 0), (2, 0): (1, 0)}
        path = pathfinder._reconstruct_path(came_from, (2, 0))
        assert path == [(0, 0), (1, 0), (2, 0)]


# ===========================================================================
# 10. Routing failure detection
# ===========================================================================


class TestRoutingFailure:
    def test_successful_route_returns_false(self, pathfinder):
        """Successful pathfinding should return routing_failed=False."""
        start, end = _grid(0, 0), _grid(3, 0)
        waypoints, runtime, iterations, routing_failed = pathfinder.find_path(
            start, end, set(), bounds=BOUNDS
        )
        assert routing_failed is False
        assert len(waypoints) >= 2

    def test_blocked_route_returns_true(self, pathfinder):
        """When path is completely blocked, routing_failed should be True."""
        # Create a wall of obstacles completely surrounding the goal
        obstacles = set()
        for x in range(-10, 11):
            for y in range(-10, 11):
                if not (x == 0 and y == 0):
                    obstacles.add((x, y))
        # Only (0,0) is free, goal at (5,0) is blocked
        start, end = _grid(0, 0), _grid(5, 0)
        waypoints, runtime, iterations, routing_failed = pathfinder.find_path(
            start, end, obstacles, bounds=BOUNDS
        )
        assert routing_failed is True

    def test_failed_route_returns_straight_line(self, pathfinder):
        """Failed routing should return start and end positions as fallback."""
        # Block everything except start
        obstacles = set()
        for x in range(-10, 11):
            for y in range(-10, 11):
                if not (x == 0 and y == 0):
                    obstacles.add((x, y))
        start, end = _grid(0, 0), _grid(5, 0)
        waypoints, _, _, routing_failed = pathfinder.find_path(
            start, end, obstacles, bounds=BOUNDS
        )
        assert routing_failed is True
        assert len(waypoints) == 2
        assert waypoints[0] == start
        assert waypoints[1] == end

    def test_route_around_obstacle_succeeds(self, pathfinder):
        """A passable obstacle should not trigger routing failure."""
        # Block a single column but leave room to route around
        obstacles = {(3, y) for y in range(-2, 3)}
        start, end = _grid(0, 0), _grid(6, 0)
        waypoints, _, _, routing_failed = pathfinder.find_path(
            start, end, obstacles, bounds=BOUNDS
        )
        assert routing_failed is False
        grid_pts = _to_grid_tuples(waypoints)
        assert grid_pts[0] == (0, 0)
        assert grid_pts[-1] == (6, 0)
        for pt in grid_pts:
            assert pt not in obstacles

    def test_find_path_returns_four_tuple(self, pathfinder):
        """find_path should return a 4-tuple (waypoints, runtime, iterations, routing_failed)."""
        start, end = _grid(0, 0), _grid(2, 0)
        result = pathfinder.find_path(start, end, set(), bounds=BOUNDS)
        assert len(result) == 4
        waypoints, runtime, iterations, routing_failed = result
        assert isinstance(waypoints, list)
        assert isinstance(runtime, float)
        assert isinstance(iterations, int)
        assert isinstance(routing_failed, bool)


# ===========================================================================
# 11. WireData routing_failed flag
# ===========================================================================


class TestWireDataRoutingFailed:
    def test_default_is_false(self):
        """WireData.routing_failed should default to False."""
        from models.wire import WireData

        wire = WireData(
            start_component_id="c1",
            start_terminal=0,
            end_component_id="c2",
            end_terminal=0,
        )
        assert wire.routing_failed is False

    def test_can_set_routing_failed(self):
        """WireData.routing_failed should be settable."""
        from models.wire import WireData

        wire = WireData(
            start_component_id="c1",
            start_terminal=0,
            end_component_id="c2",
            end_terminal=0,
        )
        wire.routing_failed = True
        assert wire.routing_failed is True
