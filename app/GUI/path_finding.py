"""
pathfinding.py

A* pathfinding algorithm for grid-aligned wire routing in circuit schematics
"""

import heapq
from PyQt6.QtCore import QPointF


class GridPathfinder:
    """A* pathfinding for grid-aligned wires"""
    
    def __init__(self, grid_size=20):
        self.grid_size = grid_size
        
    def find_path(self, start_pos, end_pos, obstacles, bounds=(-500, -500, 1000, 1000)):
        """
        Find path from start_pos to end_pos avoiding obstacles
        
        Args:
            start_pos: QPointF - starting position
            end_pos: QPointF - ending position  
            obstacles: set of (grid_x, grid_y) tuples representing blocked cells
            bounds: tuple (min_x, min_y, width, height) for valid area
            
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
        if start_neighbors_blocked > 0:
            print(f"        WARNING: {start_neighbors_blocked}/4 neighbors of start {start_grid} are blocked")

        # A* algorithm
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, end_grid)}
        
        min_x, min_y, width, height = bounds
        max_x = min_x + width
        max_y = min_y + height
        
        iterations = 0
        max_iterations = 10000  # Safety limit

        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)[1]

            if current == end_grid:
                # Reconstruct path
                path = self._reconstruct_path(came_from, current)
                # Convert grid coordinates back to scene positions
                waypoints = [self._grid_to_pos(grid_pos) for grid_pos in path]
                # Simplify path (remove unnecessary waypoints)
                waypoints = self._simplify_path(waypoints)
                print(f"        A* found path with {len(waypoints)} waypoints after {iterations} iterations")
                return waypoints
            
            # Check all 4 neighbors (up, down, left, right)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Check bounds
                neighbor_pos = self._grid_to_pos(neighbor)
                if not (min_x <= neighbor_pos.x() <= max_x and 
                       min_y <= neighbor_pos.y() <= max_y):
                    continue
                
                # Check if blocked by obstacle
                if neighbor in obstacles:
                    continue
                
                # Calculate tentative g_score
                tentative_g_score = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, end_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        # No path found - return direct line as fallback
        print(f"        A* FAILED: No path found after {iterations} iterations. Using fallback direct line.")
        print(f"        Start: {start_grid}, End: {end_grid}")
        return [start_pos, end_pos]
    
    def _pos_to_grid(self, pos):
        """Convert scene position to grid coordinates"""
        return (round(pos.x() / self.grid_size), round(pos.y() / self.grid_size))
    
    def _grid_to_pos(self, grid):
        """Convert grid coordinates to scene position"""
        return QPointF(grid[0] * self.grid_size, grid[1] * self.grid_size)
    
    def _heuristic(self, a, b):
        """Manhattan distance heuristic for A*"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def _reconstruct_path(self, came_from, current):
        """Reconstruct path from came_from map"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def _simplify_path(self, waypoints):
        """Remove unnecessary waypoints (collinear points)"""
        if len(waypoints) <= 2:
            return waypoints
        
        simplified = [waypoints[0]]
        
        for i in range(1, len(waypoints) - 1):
            prev = waypoints[i - 1]
            current = waypoints[i]
            next_point = waypoints[i + 1]
            
            # Check if current point is on the same line as prev and next
            # If moving in same direction, we can skip this waypoint
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
        """Check if two direction vectors are the same"""
        # Normalize directions to -1, 0, or 1
        def sign(x):
            return 0 if x == 0 else (1 if x > 0 else -1)
        
        return sign(dx1) == sign(dx2) and sign(dy1) == sign(dy2)


def get_component_obstacles(components, grid_size=20, padding=2, exclude_ids=None, terminal_clearance_only=None, active_terminals=None):
    """
    Get set of grid cells blocked by components

    Args:
        components: dict of ComponentItem objects
        grid_size: size of grid cells
        padding: extra grid cells around each component
        exclude_ids: set of component IDs to exclude from obstacles (optional) - DEPRECATED
        terminal_clearance_only: set of component IDs where only terminal areas should be cleared (not entire body)
        active_terminals: list of (component_id, terminal_index) tuples that must be cleared for pathfinding

    Returns:
        set of (grid_x, grid_y) tuples
    """
    obstacles = set()

    if exclude_ids is None:
        exclude_ids = set()

    if terminal_clearance_only is None:
        terminal_clearance_only = set()

    if active_terminals is None:
        active_terminals = []

    for comp in components.values():
        # Skip fully excluded components (legacy support)
        if comp.component_id in exclude_ids:
            continue

        # Get component bounding box
        rect = comp.boundingRect()
        pos = comp.pos()

        # Convert to grid coordinates with padding
        min_x = int((pos.x() + rect.left() - padding * grid_size) / grid_size)
        max_x = int((pos.x() + rect.right() + padding * grid_size) / grid_size)
        min_y = int((pos.y() + rect.top() - padding * grid_size) / grid_size)
        max_y = int((pos.y() + rect.bottom() + padding * grid_size) / grid_size)

        # Add all grid cells in this rectangle to obstacles
        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                obstacles.add((gx, gy))

    # Convert active_terminals to a set for faster lookup
    active_terminals_set = set(active_terminals)

    # Remove terminal positions from obstacles (we need to connect to them)
    # Priority order:
    # 1. Active terminals (the ones being used by this wire) - always cleared with path
    # 2. Components in terminal_clearance_only - clear terminals with minimal path
    # 3. Other components - clear 3x3 area around all terminals
    for comp in components.values():
        if comp.component_id in exclude_ids:
            # Skip components that are fully excluded
            continue

        for i in range(len(comp.terminals)):
            term_pos = comp.get_terminal_pos(i)
            # Use same conversion as pathfinding uses
            term_grid_x = round(term_pos.x() / grid_size)
            term_grid_y = round(term_pos.y() / grid_size)

            terminal_key = (comp.component_id, i)
            is_active_terminal = terminal_key in active_terminals_set

            # Determine direction from component center to terminal (used for path clearing)
            comp_center_x = round(comp.pos().x() / grid_size)
            comp_center_y = round(comp.pos().y() / grid_size)

            dx = 0 if term_grid_x == comp_center_x else (1 if term_grid_x > comp_center_x else -1)
            dy = 0 if term_grid_y == comp_center_y else (1 if term_grid_y > comp_center_y else -1)

            if is_active_terminal:
                # PRIORITY 1: Active terminal - always clear it and paths in ALL directions
                # This ensures the wire being routed can always reach its endpoints
                obstacles.discard((term_grid_x, term_grid_y))

                # Clear paths in all 4 directions from terminal for maximum connectivity
                # This is critical for ensuring A* can find a path
                for direction_dx, direction_dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    for step in range(1, 4):
                        clear_pos = (term_grid_x + direction_dx * step, term_grid_y + direction_dy * step)
                        obstacles.discard(clear_pos)

            elif comp.component_id in terminal_clearance_only:
                # PRIORITY 2: Component in terminal_clearance_only but not active terminal
                # Only clear the terminal cell and a small path
                obstacles.discard((term_grid_x, term_grid_y))

                # Clear a path away from the component (2 cells out from terminal)
                for step in range(1, 3):
                    clear_pos = (term_grid_x + dx * step, term_grid_y + dy * step)
                    obstacles.discard(clear_pos)
            else:
                # PRIORITY 3: Other components - clear 3x3 area around terminal for better connectivity
                for dx_offset in [-1, 0, 1]:
                    for dy_offset in [-1, 0, 1]:
                        clear_pos = (term_grid_x + dx_offset, term_grid_y + dy_offset)
                        obstacles.discard(clear_pos)

    return obstacles