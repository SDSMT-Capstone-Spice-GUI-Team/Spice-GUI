"""
pathfinding.py

Multiple pathfinding algorithms for grid-aligned wire routing in circuit schematics:
- A* (primary): Heuristic-based optimal pathfinding
- IDA* (Iterative Deepening A*): Memory-efficient variant
- Dijkstra: Guaranteed shortest path without heuristics
"""

import heapq
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple

from PyQt6.QtCore import QPointF


class WeightedPathfinder(ABC):
    """
    Abstract base class for pathfinding algorithms with weighted edges.

    This class defines the interface for pathfinding algorithms that support:
    - Edge weight calculation (bend penalties, crossing costs, etc.)
    - Obstacle avoidance
    - Performance tracking
    - Multiple algorithm implementations

    Subclasses must implement:
    - find_path(): Main pathfinding method
    - _calculate_edge_cost(): Edge weight calculation logic
    """

    def __init__(self, grid_size=20):
        """
        Initialize the pathfinder with grid configuration and weight parameters.

        Args:
            grid_size: Size of grid cells in pixels
        """
        self.grid_size = grid_size

        # Edge weight parameters
        self.bend_penalty_base = 2  # Exponential base for bend penalties (2^n)
        self.crossing_penalty = 20  # Penalty for crossing different nets
        self.same_net_cost = 0.1  # Low cost for same-net bundling
        self.body_crossing_penalty = float("inf")  # Component body crossing (blocked)
        self.non_net_crossing_penalty = float("inf")  # Non-net terminal crossing (blocked)

        # Performance tracking
        self.last_runtime = 0
        self.last_iterations = 0
        self.last_nodes_explored = 0

    @abstractmethod
    def find_path(
        self,
        start_pos,
        end_pos,
        obstacles,
        bounds=(-500, -500, 1000, 1000),
        algorithm="astar",
        existing_wires=None,
        current_net=None,
    ) -> Tuple[List[Tuple[int, int]], float, int]:
        """
        Find path from start_pos to end_pos avoiding obstacles.

        Args:
            start_pos: QPointF - starting position
            end_pos: QPointF - ending position
            obstacles: set of (grid_x, grid_y) tuples representing blocked cells
            bounds: tuple (min_x, min_y, width, height) for valid routing area
            algorithm: str - algorithm identifier (e.g., 'astar', 'dijkstra')
            existing_wires: list of wire paths for edge weight calculation (optional)
            current_net: identifier for current net for bundling optimization (optional)

        Returns:
            tuple: (waypoints, runtime, iterations)
                - waypoints: list of QPointF representing the path
                - runtime: float, time taken in seconds
                - iterations: int, number of algorithm iterations
        """
        ...

    @abstractmethod
    def _calculate_edge_cost(
        self, current, neighbor, direction, bend_count, existing_wires=None, current_net=None
    ) -> int:
        """
        Calculate the cost of traversing an edge in the grid.

        Args:
            current: (x, y) tuple - current grid position
            neighbor: (x, y) tuple - neighbor grid position
            direction: (dx, dy) tuple - current movement direction
            bend_count: int - number of bends so far in the path
            existing_wires: list of wire paths (optional)
            current_net: identifier for current net (optional)

        Returns:
            float: Edge cost (base cost + penalties)
        """
        ...

    def _grid_to_pos(self, grid_coord):
        """
        Convert grid coordinates to scene position.

        Args:
            grid_coord: (x, y) tuple in grid space

        Returns:
            QPointF in scene coordinates
        """
        return QPointF(grid_coord[0] * self.grid_size, grid_coord[1] * self.grid_size)

    def _pos_to_grid(self, pos) -> Tuple[int, int]:
        """
        Convert scene position to grid coordinates.

        Args:
            pos: QPointF in scene coordinates

        Returns:
            (x, y) tuple in grid space
        """
        return (round(pos.x() / self.grid_size), round(pos.y() / self.grid_size))

    def _heuristic(self, a, b):
        """
        Manhattan distance heuristic for A* algorithms.

        Args:
            a: (x, y) tuple - start position
            b: (x, y) tuple - goal position

        Returns:
            float: Manhattan distance
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _reconstruct_path(self, came_from, current):
        """
        Reconstruct path from came_from mapping.

        Args:
            came_from: dict mapping grid position to previous position
            current: final grid position

        Returns:
            list of (x, y) tuples from start to goal
        """
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _simplify_path(self, waypoints):
        """
        Remove unnecessary waypoints (collinear points).

        Args:
            waypoints: list of QPointF

        Returns:
            list of QPointF with collinear points removed
        """
        if len(waypoints) <= 2:
            return waypoints

        simplified = [waypoints[0]]

        for i in range(1, len(waypoints) - 1):
            prev = waypoints[i - 1]
            current = waypoints[i]
            next_point = waypoints[i + 1]

            # Check if current point is on the same line as prev and next
            dx1 = current.x() - prev.x()
            dy1 = current.y() - prev.y()
            dx2 = next_point.x() - current.x()
            dy2 = next_point.y() - current.y()

            # If not collinear (direction changes), keep the waypoint
            if not self._same_direction(dx1, dy1, dx2, dy2):
                simplified.append(current)

        simplified.append(waypoints[-1])
        return simplified

    def _same_direction(self, dx1, dy1, dx2, dy2):
        """
        Check if two direction vectors point the same way.

        Args:
            dx1, dy1: first direction vector
            dx2, dy2: second direction vector

        Returns:
            bool: True if directions are the same
        """

        def sign(x):
            return 0 if x == 0 else (1 if x > 0 else -1)

        return sign(dx1) == sign(dx2) and sign(dy1) == sign(dy2)


class AStarPathfinder(WeightedPathfinder):
    """A* pathfinding algorithm with heuristic-based optimal path finding"""

    def __init__(self, grid_size=20):
        super().__init__(grid_size)
        self.last_g_score = {}  # Store g_score from last pathfinding run for visualization

    def find_path(
        self,
        start_pos,
        end_pos,
        obstacles,
        bounds=(-500, -500, 1000, 1000),
        algorithm="astar",
        existing_wires=None,
        current_net=None,
    ):
        """
        Find path using A* algorithm.

        Args:
            start_pos: QPointF - starting position
            end_pos: QPointF - ending position
            obstacles: set of (grid_x, grid_y) tuples representing blocked cells
            bounds: tuple (min_x, min_y, width, height) for valid area
            algorithm: str - ignored (always uses A*)
            existing_wires: list of wire paths (optional)
            current_net: identifier for current net (optional)

        Returns:
            tuple: (waypoints, runtime, iterations)
        """
        start_time = time.time()
        waypoints = self._find_path_impl(start_pos, end_pos, obstacles, bounds, existing_wires, current_net)
        self.last_runtime = time.time() - start_time
        return waypoints, self.last_runtime, self.last_iterations

    def _calculate_edge_cost(self, current, neighbor, direction, bend_count, existing_wires=None, current_net=None):
        """
        Calculate edge cost with bend penalties.

        Args:
            current: (x, y) tuple
            neighbor: (x, y) tuple
            direction: (dx, dy) tuple - movement direction
            bend_count: int - number of bends so far

        Returns:
            float: Edge cost
        """
        return 1  # Base cost (bend penalty added separately in algorithm)

    def _find_path_impl(self, start_pos, end_pos, obstacles, bounds, existing_wires=None, current_net=None):
        """
        A* algorithm implementation with edge weight system

        Returns:
            list of QPointF representing waypoints along the path
        """
        # Convert positions to grid coordinates
        start_grid = self._pos_to_grid(start_pos)
        end_grid = self._pos_to_grid(end_pos)

        # Debug: Check if start has any valid neighbors
        start_neighbors_blocked = 0
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (start_grid[0] + dx, start_grid[1] + dy)
            if neighbor in obstacles:
                start_neighbors_blocked += 1

        # A* algorithm with edge weights
        open_set = []
        heapq.heappush(open_set, (0, start_grid, None))  # (f_score, position, direction)

        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, end_grid)}
        direction_map: Dict[tuple[int, int], tuple[int, int] | None] = {
            start_grid: None
        }  # Track direction for bend penalty
        bend_count = {start_grid: 0}  # Track number of bends

        min_x, min_y, width, height = bounds
        max_x = min_x + width
        max_y = min_y + height

        iterations = 0
        max_iterations = 10000  # Safety limit

        while open_set and iterations < max_iterations:
            iterations += 1
            _, current, current_dir = heapq.heappop(open_set)

            if current == end_grid:
                # Reconstruct path
                path = self._reconstruct_path(came_from, current)
                # Convert grid coordinates back to scene positions
                waypoints = [self._grid_to_pos(grid_pos) for grid_pos in path]
                # Simplify path (remove unnecessary waypoints)
                waypoints = self._simplify_path(waypoints)
                self.last_iterations = iterations
                # Store g_score for cost map visualization
                self.last_g_score = dict(g_score)
                return waypoints

            # Check all 4 neighbors (up, down, left, right)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                new_direction = (dx, dy)

                # Check bounds
                neighbor_pos = self._grid_to_pos(neighbor)
                if not (min_x <= neighbor_pos.x() <= max_x and min_y <= neighbor_pos.y() <= max_y):
                    continue

                # Check if blocked by obstacle
                if neighbor in obstacles:
                    continue

                # Calculate edge cost with bend penalty
                edge_cost = 1  # Base movement cost
                new_bend_count = bend_count.get(current, 0)

                # Add bend penalty if direction changes
                if current_dir is not None and current_dir != new_direction:
                    new_bend_count += 1
                    edge_cost += self.bend_penalty_base**new_bend_count

                # Calculate tentative g_score
                tentative_g_score = g_score[current] + edge_cost

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, end_grid)
                    direction_map[neighbor] = new_direction
                    bend_count[neighbor] = new_bend_count
                    heapq.heappush(open_set, (f_score[neighbor], neighbor, new_direction))

        # No path found - return direct line as fallback
        self.last_iterations = iterations
        # Store g_score even on failure for visualization
        self.last_g_score = dict(g_score)
        return [start_pos, end_pos]


class DijkstraPathfinder(WeightedPathfinder):
    """Dijkstra's algorithm - guaranteed shortest path without heuristics"""

    def __init__(self, grid_size=20):
        super().__init__(grid_size)

    def find_path(
        self,
        start_pos,
        end_pos,
        obstacles,
        bounds=(-500, -500, 1000, 1000),
        algorithm="dijkstra",
        existing_wires=None,
        current_net=None,
    ):
        """
        Find path using Dijkstra's algorithm.

        Returns:
            tuple: (waypoints, runtime, iterations)
        """
        start_time = time.time()
        waypoints = self._find_path_impl(start_pos, end_pos, obstacles, bounds, existing_wires, current_net)
        self.last_runtime = time.time() - start_time
        return waypoints, self.last_runtime, self.last_iterations

    def _calculate_edge_cost(self, current, neighbor, direction, bend_count, existing_wires=None, current_net=None):
        """Calculate edge cost (same as A* but without heuristic)"""
        return 1  # Base cost

    def _find_path_impl(self, start_pos, end_pos, obstacles, bounds, existing_wires=None, current_net=None):
        """
        Dijkstra's algorithm implementation - guaranteed shortest path without heuristics

        Returns:
            list of QPointF representing waypoints along the path
        """
        # Convert positions to grid coordinates
        start_grid = self._pos_to_grid(start_pos)
        end_grid = self._pos_to_grid(end_pos)

        # Priority queue: (cost, position, direction)
        open_set = []
        heapq.heappush(open_set, (0, start_grid, None))

        came_from = {}
        cost = {start_grid: 0}
        bend_count = {start_grid: 0}

        min_x, min_y, width, height = bounds
        max_x = min_x + width
        max_y = min_y + height

        iterations = 0
        max_iterations = 10000

        while open_set and iterations < max_iterations:
            iterations += 1
            current_cost, current, current_dir = heapq.heappop(open_set)

            # Skip if we've already found a better path to this node
            if current in cost and current_cost > cost[current]:
                continue

            if current == end_grid:
                path = self._reconstruct_path(came_from, current)
                waypoints = [self._grid_to_pos(grid_pos) for grid_pos in path]
                waypoints = self._simplify_path(waypoints)
                self.last_iterations = iterations
                return waypoints

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                new_direction = (dx, dy)

                neighbor_pos = self._grid_to_pos(neighbor)
                if not (min_x <= neighbor_pos.x() <= max_x and min_y <= neighbor_pos.y() <= max_y):
                    continue

                if neighbor in obstacles:
                    continue

                edge_cost = 1
                new_bend_count = bend_count.get(current, 0)

                if current_dir is not None and current_dir != new_direction:
                    new_bend_count += 1
                    edge_cost += self.bend_penalty_base**new_bend_count

                tentative_cost = current_cost + edge_cost

                if neighbor not in cost or tentative_cost < cost[neighbor]:
                    came_from[neighbor] = current
                    cost[neighbor] = tentative_cost
                    bend_count[neighbor] = new_bend_count
                    heapq.heappush(open_set, (tentative_cost, neighbor, new_direction))

        self.last_iterations = iterations
        return [start_pos, end_pos]


class IDAStarPathfinder(WeightedPathfinder):
    """IDA* (Iterative Deepening A*) algorithm - memory-efficient A* variant"""

    def __init__(self, grid_size=20):
        super().__init__(grid_size)

    def find_path(
        self,
        start_pos,
        end_pos,
        obstacles,
        bounds=(-500, -500, 1000, 1000),
        algorithm="idastar",
        existing_wires=None,
        current_net=None,
    ):
        """
        Find path using IDA* algorithm.

        Returns:
            tuple: (waypoints, runtime, iterations)
        """
        start_time = time.time()
        waypoints = self._find_path_impl(start_pos, end_pos, obstacles, bounds, existing_wires, current_net)
        self.last_runtime = time.time() - start_time
        return waypoints, self.last_runtime, self.last_iterations

    def _calculate_edge_cost(self, current, neighbor, direction, bend_count, existing_wires=None, current_net=None):
        """Calculate edge cost"""
        return 1  # Base cost

    def _find_path_impl(self, start_pos, end_pos, obstacles, bounds, existing_wires=None, current_net=None):
        """
        IDA* (Iterative Deepening A*) algorithm - memory-efficient A* variant

        Returns:
            list of QPointF representing waypoints along the path
        """
        start_grid = self._pos_to_grid(start_pos)
        end_grid = self._pos_to_grid(end_pos)

        min_x, min_y, width, height = bounds
        max_x = min_x + width
        max_y = min_y + height

        iterations = 0
        max_iterations = 10000

        # Initial threshold is the heuristic estimate
        threshold = self._heuristic(start_grid, end_grid)

        while iterations < max_iterations:
            result = self._idastar_search(
                start_grid, end_grid, 0, threshold, None, 0, obstacles, min_x, max_x, min_y, max_y, {}
            )
            iterations += 1

            if isinstance(result, list):
                # Found path
                waypoints = [self._grid_to_pos(grid_pos) for grid_pos in result]
                waypoints = self._simplify_path(waypoints)
                self.last_iterations = iterations
                return waypoints
            elif result == float("inf"):
                # No path exists
                break
                pass
            else:
                # Increase threshold and continue
                threshold = result

        self.last_iterations = iterations
        return [start_pos, end_pos]

    def _idastar_search(
        self, current, goal, g_score, threshold, direction, bend_count, obstacles, min_x, max_x, min_y, max_y, visited
    ):
        """
        Recursive depth-first search for IDA*

        Returns:
            - list of grid positions if path found
            - new threshold (float) if path not found within threshold
            - float('inf') if no path exists
        """
        f_score = g_score + self._heuristic(current, goal)

        if f_score > threshold:
            return f_score

        if current == goal:
            return [current]

        visited_key = (current, direction)
        if visited_key in visited and visited[visited_key] <= g_score:
            return float("inf")
        visited[visited_key] = g_score

        min_threshold = float("inf")

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (current[0] + dx, current[1] + dy)
            new_direction = (dx, dy)

            neighbor_pos = self._grid_to_pos(neighbor)
            if not (min_x <= neighbor_pos.x() <= max_x and min_y <= neighbor_pos.y() <= max_y):
                continue

            if neighbor in obstacles:
                continue

            edge_cost = 1
            new_bend_count = bend_count

            if direction is not None and direction != new_direction:
                new_bend_count += 1
                edge_cost += self.bend_penalty_base**new_bend_count

            result = self._idastar_search(
                neighbor,
                goal,
                g_score + edge_cost,
                threshold,
                new_direction,
                new_bend_count,
                obstacles,
                min_x,
                max_x,
                min_y,
                max_y,
                visited,
            )

            if isinstance(result, list):
                return [current] + result
            elif result < min_threshold:
                min_threshold = result

        return min_threshold


# ============================================================================
# Standalone Helper Functions
# ============================================================================


def polygon_to_grid_filled(
    polygon_points, position, rotation_angle, grid_size, inset=0, active_terminal_positions=None
):
    """
    Convert a polygon shape to grid cells filling the entire interior.
    Used for connected components to block wires from passing through.

    Args:
        polygon_points: List of (x, y) tuples in local coordinates
        position: Component position (QPointF)
        rotation_angle: Rotation in degrees
        grid_size: Grid cell size
        inset: Inset distance in grid cells (for non-connected components)
        active_terminal_positions: Set of grid positions to exclude

    Returns:
        Set of (grid_x, grid_y) tuples filling the polygon interior
    """
    import math

    if active_terminal_positions is None:
        active_terminal_positions = set()

    obstacles = set()

    # Rotate and translate polygon points to world coordinates
    rad = math.radians(rotation_angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    world_points = []
    for x, y in polygon_points:
        # Apply inset if specified (shrink polygon)
        if inset > 0:
            inset_px = inset * grid_size
            center_x = sum(p[0] for p in polygon_points) / len(polygon_points)
            center_y = sum(p[1] for p in polygon_points) / len(polygon_points)
            dx = center_x - x
            dy = center_y - y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                x += (dx / dist) * inset_px
                y += (dy / dist) * inset_px

        # Rotate
        rotated_x = x * cos_a - y * sin_a
        rotated_y = x * sin_a + y * cos_a

        # Translate to world position
        world_x = position.x() + rotated_x
        world_y = position.y() + rotated_y

        world_points.append((world_x, world_y))

    # Find bounding box in WORLD coordinates
    min_y_world = min(p[1] for p in world_points)
    max_y_world = max(p[1] for p in world_points)

    # Convert bounding box to grid coordinates using round() to match _pos_to_grid()
    # Add margin to ensure we don't miss edge cells
    min_grid_y = round(min_y_world / grid_size) - 1
    max_grid_y = round(max_y_world / grid_size) + 1

    # Scanline fill algorithm in WORLD space
    # For each grid row, check which grid cells are inside the polygon
    debug_first = True
    for grid_y in range(min_grid_y, max_grid_y + 1):
        # Scanline at the CENTER of the grid cell to match round() behavior
        # Grid cell Y has center at grid_y * grid_size (when using round())
        scan_y_world = grid_y * grid_size
        intersections = []

        # Find intersections of scanline with polygon edges IN WORLD SPACE
        num_points = len(world_points)
        for i in range(num_points):
            p1 = world_points[i]
            p2 = world_points[(i + 1) % num_points]

            # Skip horizontal edges
            if abs(p1[1] - p2[1]) < 0.001:
                continue

            # Check if edge crosses scanline (exclusive of upper endpoint to avoid double-counting vertices)
            y_min = min(p1[1], p2[1])
            y_max = max(p1[1], p2[1])

            if y_min <= scan_y_world < y_max:
                # Calculate x coordinate of intersection in WORLD space
                # Linear interpolation: x = x1 + (scan_y - y1) * (x2 - x1) / (y2 - y1)
                x_intersect_world = p1[0] + (scan_y_world - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                intersections.append(x_intersect_world)

        if debug_first and len(obstacles) < 20:
            if intersections:
                pass

        # Sort intersections and fill between pairs
        intersections.sort()

        # DEBUG: Check for odd number of intersections (should never happen with correct polygon)
        if len(intersections) % 2 != 0:
            # Skip this scanline to avoid errors
            continue

        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                # Get the range of X coordinates to fill
                x_start_world = intersections[i]
                x_end_world = intersections[i + 1]

                # Fill by converting each world X position using round() to match _pos_to_grid()
                # This ensures obstacle coordinates exactly match the pathfinding grid system
                # Sample at small intervals to catch all grid cells that overlap the filled region
                step = grid_size / 4.0  # Sample 4 times per grid cell to ensure coverage
                x_current = x_start_world
                while x_current <= x_end_world:
                    grid_x = round(x_current / grid_size)
                    if (grid_x, grid_y) not in active_terminal_positions:
                        obstacles.add((grid_x, grid_y))
                    x_current += step

                # Also ensure we get the endpoints
                grid_x_start = round(x_start_world / grid_size)
                grid_x_end = round(x_end_world / grid_size)
                if (grid_x_start, grid_y) not in active_terminal_positions:
                    obstacles.add((grid_x_start, grid_y))
                if (grid_x_end, grid_y) not in active_terminal_positions:
                    obstacles.add((grid_x_end, grid_y))
    return obstacles


def polygon_to_grid_frame(polygon_points, position, rotation_angle, grid_size, inset=0, active_terminal_positions=None):
    """
    Convert a polygon shape to grid cells forming a perimeter frame.
    Used for non-connected components to allow wires near them.

    Args:
        polygon_points: List of (x, y) tuples in local coordinates
        position: Component position (QPointF)
        rotation_angle: Rotation in degrees
        grid_size: Grid cell size
        inset: Inset distance in grid cells (for non-connected components)
        active_terminal_positions: Set of grid positions to exclude

    Returns:
        Set of (grid_x, grid_y) tuples forming the polygon perimeter
    """
    import math

    if active_terminal_positions is None:
        active_terminal_positions = set()

    obstacles: Set[Tuple[int, int]] = set()

    # Rotate and translate polygon points to world coordinates
    rad = math.radians(rotation_angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    world_points = []
    for x, y in polygon_points:
        # Apply inset if specified (shrink polygon)
        if inset > 0:
            # Simple inset: move points toward polygon center
            # (This is approximate - proper polygon insetting is complex)
            inset_px = inset * grid_size
            center_x = sum(p[0] for p in polygon_points) / len(polygon_points)
            center_y = sum(p[1] for p in polygon_points) / len(polygon_points)
            dx = center_x - x
            dy = center_y - y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                x += (dx / dist) * inset_px
                y += (dy / dist) * inset_px

        # Rotate
        rotated_x = x * cos_a - y * sin_a
        rotated_y = x * sin_a + y * cos_a

        # Translate to world position
        world_x = position.x() + rotated_x
        world_y = position.y() + rotated_y

        world_points.append((world_x, world_y))

    # Rasterize polygon edges to grid cells
    num_points = len(world_points)
    for i in range(num_points):
        p1 = world_points[i]
        p2 = world_points[(i + 1) % num_points]  # Next point (wrap around)

        # Bresenham's line algorithm to get grid cells along edge
        x1, y1 = int(p1[0] / grid_size), int(p1[1] / grid_size)
        x2, y2 = int(p2[0] / grid_size), int(p2[1] / grid_size)

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1
        while True:
            # Add grid cell if not an active terminal
            if (x, y) not in active_terminal_positions:
                obstacles.add((x, y))

            if x == x2 and y == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    return obstacles


def get_wire_obstacles(wires, current_node, grid_size=20):
    """
    Get set of grid cells blocked by wires from OTHER nodes.
    Wires from the same node are not obstacles (allows bundling).

    Args:
        wires: list of WireItem objects (all wires in the circuit)
        current_node: Node object that the current wire belongs to (or None)
        grid_size: size of grid cells

    Returns:
        set of (grid_x, grid_y) tuples
    """
    obstacles = set()

    if not wires:
        return obstacles

    for wire in wires:
        # Skip wires that belong to the same node (same net)
        # This allows bundling of wires in the same net
        if wire.node is not None and wire.node == current_node:
            continue

        # Convert wire waypoints to grid cells
        # Each wire segment becomes a line of grid cells that blocks other nets
        if wire.waypoints and len(wire.waypoints) >= 2:
            for i in range(len(wire.waypoints) - 1):
                p1 = wire.waypoints[i]
                p2 = wire.waypoints[i + 1]

                # Convert waypoints to grid coordinates
                x1 = round(p1.x() / grid_size)
                y1 = round(p1.y() / grid_size)
                x2 = round(p2.x() / grid_size)
                y2 = round(p2.y() / grid_size)

                # Use Bresenham's algorithm to rasterize the line segment
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                sx = 1 if x1 < x2 else -1
                sy = 1 if y1 < y2 else -1
                err = dx - dy

                x, y = x1, y1
                while True:
                    obstacles.add((x, y))

                    if x == x2 and y == y2:
                        break

                    e2 = 2 * err
                    if e2 > -dy:
                        err -= dy
                        x += sx
                    if e2 < dx:
                        err += dx
                        y += sy
    return obstacles


def get_component_obstacles(
    components,
    grid_size=20,
    padding=2,
    exclude_ids=None,
    terminal_clearance_only=None,
    active_terminals=None,
    existing_wires=None,
    current_node=None,
):
    """
    Get set of grid cells blocked by components and wires from other nodes.

    Args:
        components: dict of ComponentGraphicsItem objects
        grid_size: size of grid cells
        padding: extra grid cells around each component (negative values shrink boundary inward)
        exclude_ids: set of component IDs to exclude from obstacles (optional) - DEPRECATED
        terminal_clearance_only: set of component IDs where only terminal areas should be cleared (not entire body)
        active_terminals: list of (component_id, terminal_index) tuples that must be cleared for pathfinding
        existing_wires: list of WireItem objects (for wire-to-wire obstacle detection)
        current_node: Node object that current wire belongs to (for same-net detection)

    Returns:
        set of (grid_x, grid_y) tuples
    """
    obstacles = set()

    # if exclude_ids is None:
    #     exclude_ids = set()

    # if terminal_clearance_only is None:
    #     terminal_clearance_only = set()

    if active_terminals is None:
        active_terminals = []

    # Convert active_terminals to a set for faster lookup
    active_terminals_set = set(active_terminals)

    for comp in components.values():
        pos = comp.pos()

        # Get all terminal positions and identify which are active
        terminal_info = []
        for i in range(len(comp.terminals)):
            term_pos = comp.get_terminal_pos(i)
            term_grid = (round(term_pos.x() / grid_size), round(term_pos.y() / grid_size))
            terminal_key = (comp.component_id, i)
            is_active = terminal_key in active_terminals_set
            terminal_info.append({"grid": term_grid, "pos": term_pos, "is_active": is_active})

        # Get active terminal positions for exclusion from body obstacles
        active_terminal_positions = {t["grid"] for t in terminal_info if t["is_active"]}

        # ALL COMPONENTS get FILLED body obstacles
        # This prevents wires from routing through ANY component body
        if hasattr(comp, "get_obstacle_shape"):
            # Use custom polygon shape from component
            polygon_points = comp.get_obstacle_shape()

            # ALWAYS use filled interior for all components
            # This ensures wires cannot pass through component bodies
            shape_obstacles = polygon_to_grid_filled(
                polygon_points,
                pos,
                comp.rotation_angle,
                grid_size,
                inset=0,
                active_terminal_positions=active_terminal_positions,
            )

            obstacles.update(shape_obstacles)

            # IMPORTANT: Add ALL non-active terminals as obstacles (infinite cost)
            # This prevents wires from routing through terminals not being used by this wire
            for t in terminal_info:
                if not t["is_active"]:
                    obstacles.add(t["grid"])

    # Add wire obstacles from OTHER nodes (different nets)
    # Wires from the same node are skipped to allow bundling
    if existing_wires is not None:
        wire_obstacles = get_wire_obstacles(existing_wires, current_node, grid_size)
        obstacles.update(wire_obstacles)

    # Clear areas around ACTIVE terminals to ensure wire connectivity
    for comp in components.values():
        # Skip components that are fully excluded (legacy support)
        if exclude_ids is not None and comp.component_id in exclude_ids:
            continue

        for i in range(len(comp.terminals)):
            term_pos = comp.get_terminal_pos(i)
            # Use same conversion as pathfinding uses
            term_grid_x = round(term_pos.x() / grid_size)
            term_grid_y = round(term_pos.y() / grid_size)

            terminal_key = (comp.component_id, i)
            is_active_terminal = terminal_key in active_terminals_set

            if is_active_terminal:
                # PRIORITY 1: Active terminal - clear paths in ALL directions
                # This ensures the wire being routed can always reach its endpoints
                # Clear 3 cells in all 4 directions from terminal for maximum connectivity
                obstacles.discard((term_grid_x, term_grid_y))
                for direction_dx, direction_dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    for step in range(1, 4):
                        clear_pos = (term_grid_x + direction_dx * step, term_grid_y + direction_dy * step)
                        obstacles.discard(clear_pos)
            # Non-active terminals are left as obstacles (already added above)
            # This creates infinite cost for routing through unused terminals

    return obstacles
