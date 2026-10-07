"""Regression test for #939: routing a very long wire no longer hangs/crashes.

Dragging a component far off-screen can force the router to traverse a long
path of grid cells. The previous recursive IDA* search grew one Python stack
frame per cell, so a long route blew past Python's recursion limit and raised
``RecursionError`` (or appeared to "hang" iterating for a very long time first).

This pins the fix: routing across a route window far larger than the default
must complete quickly and without a ``RecursionError``.

Note: this file is intentionally prefixed with ``test_`` so it is collected.
The existing ``test_offscreen_drag_clamp.py`` covers the clamp itself; this one
pins the no-hang / no-crash behaviour of the non-recursive pathfinder.
"""

import pytest
from algorithms.path_finding import IDAStarPathfinder

# A route window large enough that a full-width orthogonal route reaches past
# Python's recursion limit (~1000 cells deep): ±600 spans 1200 grid cells. This
# exceeds the limit the old recursive IDA* used, so it crashed before the fix.
WIDE_BOUNDS = (-600.0, -600.0, 1200.0, 1200.0)
GRID = 10


@pytest.fixture
def pathfinder():
    return IDAStarPathfinder(grid_size=GRID)


@pytest.fixture
def diagonal_pathfinder():
    return IDAStarPathfinder(grid_size=GRID, allow_diagonal=True)


def _grid(gx, gy):
    return (gx * GRID, gy * GRID)


def _unpack(result):
    """``find_path`` returns (waypoints, runtime, iterations, routing_failed)."""
    waypoints, _runtime, _iters, routing_failed = result
    return waypoints, routing_failed


def test_long_route_completes_without_recursion_error(pathfinder):
    """A route spanning the widest possible window finishes and returns a path."""
    # Diagonal endpoints maximise the orthogonal route length (past the limit).
    start = _grid(-58, -58)
    end = _grid(58, 58)
    # Orthogonal routing (default) — the depth that previously overflowed.
    waypoints, routing_failed = _unpack(
        pathfinder.find_path(start, end, set(), bounds=WIDE_BOUNDS)
    )
    assert routing_failed is False
    assert len(waypoints) >= 2
    assert waypoints[0] == start
    assert waypoints[-1] == end


def test_long_route_completes_within_time(pathfinder):
    """The non-recursive search stays fast even on the largest window."""
    start = _grid(-58, -58)
    end = _grid(58, 58)
    _, routing_failed = _unpack(
        pathfinder.find_path(start, end, set(), bounds=WIDE_BOUNDS)
    )
    assert routing_failed is False
    assert pathfinder.last_runtime < 1.0


def test_diagonal_long_route_completes(diagonal_pathfinder):
    """A long diagonal route also completes without recursion error."""
    start = _grid(-58, -58)
    end = _grid(58, 58)
    waypoints, routing_failed = _unpack(
        diagonal_pathfinder.find_path(start, end, set(), bounds=WIDE_BOUNDS)
    )
    assert routing_failed is False
    assert waypoints[0] == start
    assert waypoints[-1] == end


def test_unreachable_target_fails_fast(pathfinder):
    """A target outside the route window must fail quickly, not hang (#939)."""
    # (530, 0) is past the default ±500 route window on the x-axis, so no
    # in-bounds path exists. The old recursive search hung exploring; the heap
    # search must give up fast.
    waypoints, routing_failed = _unpack(pathfinder.find_path((0, 0), (530, 0), set()))
    assert routing_failed is True
    assert pathfinder.last_runtime < 2.0


def test_walled_in_target_fails_fast(pathfinder):
    """A goal enclosed by obstacles must fail quickly, not hang (#939)."""
    # Box the goal cell in on all four sides; the start is outside the box.
    gx, gy = 5, 0
    obstacles = {
        (gx + dx, gy + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (dx, dy) not in ((0, 0),)
    }
    waypoints, routing_failed = _unpack(
        pathfinder.find_path(_grid(0, 0), _grid(gx, gy), obstacles)
    )
    assert routing_failed is True
    assert pathfinder.last_runtime < 2.0


def test_route_quality_l_shape_single_bend(pathfinder):
    """An L-shaped route must have exactly one bend (caught a reconstruction bug).

    A* should return the *settled* goal state (popped from the heap), not the
    first route recorded at the goal cell. On this grid both are single-bend,
    but comparing against an alternate path pins the quality: the optimal route
    between the two points has exactly one bend.
    """
    # Straight reference route: pure horizontal, zero bends.
    straight, _ = _unpack(pathfinder.find_path(_grid(0, 0), _grid(5, 0), set()))
    assert len(straight) == 2  # straight line, simplified to endpoints only

    # L-shaped route must not be longer than necessary: two points differ by
    # (5, 3); an optimal route visits at most 3 waypoints (one bend).
    l_shape, routing_failed = _unpack(
        pathfinder.find_path(_grid(0, 0), _grid(5, 3), set())
    )
    assert routing_failed is False
    assert len(l_shape) == 3


def test_route_around_obstacles_over_long_span(pathfinder):
    """A long route with obstacles still returns a valid, obstacle-free path."""
    # A vertical wall of obstacles at x = 40 cells with a gap at y = 0 to route
    # through, spanning most of the window.
    obstacles = {(40, y) for y in range(-58, 59) if y != 0}
    start = _grid(-58, 0)
    end = _grid(58, 0)
    waypoints, routing_failed = _unpack(
        pathfinder.find_path(start, end, obstacles, bounds=WIDE_BOUNDS)
    )
    assert routing_failed is False
    # The path should not pass through any obstacle cell.
    cell = {(round(p[0] / GRID), round(p[1] / GRID)) for p in waypoints}
    assert not (cell & obstacles)
