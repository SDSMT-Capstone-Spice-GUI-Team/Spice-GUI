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
        
        # A* algorithm
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, end_grid)}
        
        min_x, min_y, width, height = bounds
        max_x = min_x + width
        max_y = min_y + height
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current == end_grid:
                # Reconstruct path
                path = self._reconstruct_path(came_from, current)
                # Convert grid coordinates back to scene positions
                waypoints = [self._grid_to_pos(grid_pos) for grid_pos in path]
                # Simplify path (remove unnecessary waypoints)
                waypoints = self._simplify_path(waypoints)
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


def get_component_obstacles(components, grid_size=20, padding=2, exclude_ids=None):
    """
    Get set of grid cells blocked by components
    
    Args:
        components: dict of ComponentItem objects
        grid_size: size of grid cells
        padding: extra grid cells around each component
        exclude_ids: set of component IDs to exclude from obstacles (optional)
        
    Returns:
        set of (grid_x, grid_y) tuples
    """
    obstacles = set()
    
    if exclude_ids is None:
        exclude_ids = set()
    
    for comp in components.values():
        # Skip excluded components
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
    
    # Remove terminal positions from obstacles (we need to connect to them)
    # Clear a 3x3 area around each terminal to ensure connectivity
    for comp in components.values():
        for i in range(len(comp.terminals)):
            term_pos = comp.get_terminal_pos(i)
            # Use same conversion as pathfinding uses
            term_grid_x = round(term_pos.x() / grid_size)
            term_grid_y = round(term_pos.y() / grid_size)
            
            # Clear 3x3 area around terminal for better connectivity
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    clear_pos = (term_grid_x + dx, term_grid_y + dy)
                    obstacles.discard(clear_pos)
    
    return obstacles