from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QPainterPath
from .path_finding import GridPathfinder, get_component_obstacles

# from . import GRID_SIZE
GRID_SIZE = 10

class WireItem(QGraphicsPathItem):
    """Wire connecting components with A* pathfinding"""
    
    def __init__(self, start_comp, start_term, end_comp, end_term, canvas=None):
        super().__init__()
        self.start_comp = start_comp
        self.start_term = start_term
        self.end_comp = end_comp
        self.end_term = end_term
        self.node = None  # Reference to the Node this wire belongs to
        self.canvas = canvas  # Reference to canvas for pathfinding
        
        self.waypoints = []  # List of QPointF waypoints
        
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_position()
    
    def update_position(self):
        """Update wire path using A* pathfinding"""
        # print(f"      WireItem.update_position() called") #TODO: remove debug statements

        # Get old bounding rect for invalidation
        old_rect = self.boundingRect()

        # Prepare for update by invalidating current bounds
        self.prepareGeometryChange()

        start = self.start_comp.get_terminal_pos(self.start_term)
        end = self.end_comp.get_terminal_pos(self.end_term)

        # Get obstacles from canvas
        if self.canvas:
            # Don't exclude connected components entirely, but only clear their terminal areas
            # This prevents wires from crossing through component bodies
            terminal_clearance = {self.start_comp.component_id, self.end_comp.component_id}

            # Specify the exact terminals this wire is using - these MUST be cleared for pathfinding
            active_terminals = [
                (self.start_comp.component_id, self.start_term),
                (self.end_comp.component_id, self.end_term)
            ]

            print(f"      Routing wire from {self.start_comp.component_id}[{self.start_term}] to {self.end_comp.component_id}[{self.end_term}]")
            print(f"      Active terminals: {active_terminals}")

            obstacles = get_component_obstacles(self.canvas.components, GRID_SIZE,
                                               padding=0,
                                               terminal_clearance_only=terminal_clearance,
                                               active_terminals=active_terminals)

            # Debug: Check if start/end positions are in obstacles
            start_grid = (round(start.x() / GRID_SIZE), round(start.y() / GRID_SIZE))
            end_grid = (round(end.x() / GRID_SIZE), round(end.y() / GRID_SIZE))
            print(f"      Start grid: {start_grid}, in obstacles: {start_grid in obstacles}")
            print(f"      End grid: {end_grid}, in obstacles: {end_grid in obstacles}")
            print(f"      Total obstacles: {len(obstacles)}")

            # Debug: Check if there's a clear path out from both terminals
            manhattan_dist = abs(end_grid[0] - start_grid[0]) + abs(end_grid[1] - start_grid[1])
            print(f"      Manhattan distance: {manhattan_dist}")

            pathfinder = GridPathfinder(GRID_SIZE)
            self.waypoints = pathfinder.find_path(start, end, obstacles)
        else:
            # Fallback to direct line
            self.waypoints = [start, end]

        # Create path from waypoints
        path = QPainterPath()
        if self.waypoints:
            path.moveTo(self.waypoints[0])
            for waypoint in self.waypoints[1:]:
                path.lineTo(waypoint)

        self.setPath(path)

        # Force updates on both old and new regions
        if self.scene():
            self.scene().update(old_rect)
            self.scene().update(self.boundingRect())

        self.update()  # Force item redraw
        print(f"      Wire updated with {len(self.waypoints)} waypoints from {start} to {end}")
    
    def paint(self, painter, option=None, widget=None):
        """Override paint to show selection highlight"""
        if painter is None:
            return
        
        # Draw wire
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.yellow, 4))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
        
        painter.drawPath(self.path())
    
    def get_terminals(self):
        """Get both terminal identifiers for this wire"""
        return [
            (self.start_comp.component_id, self.start_term),
            (self.end_comp.component_id, self.end_term)
        ]
    
    def to_dict(self):
        """Serialize wire to dictionary"""
        return {
            'start_comp': self.start_comp.component_id,
            'start_term': self.start_term,
            'end_comp': self.end_comp.component_id,
            'end_term': self.end_term
        }
