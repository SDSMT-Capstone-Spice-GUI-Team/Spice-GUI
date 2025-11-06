from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QPainterPath
from .path_finding import GridPathfinder, get_component_obstacles

# from . import GRID_SIZE
GRID_SIZE = 20

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
        print(f"      WireItem.update_position() called")
        start = self.start_comp.get_terminal_pos(self.start_term)
        end = self.end_comp.get_terminal_pos(self.end_term)
        
        # Get obstacles from canvas
        if self.canvas:
            # Exclude the components we're connecting from obstacles
            exclude_ids = {self.start_comp.component_id, self.end_comp.component_id}
            
            obstacles = get_component_obstacles(self.canvas.components, GRID_SIZE, 
                                               padding=0, exclude_ids=exclude_ids)
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
        self.update()  # Force redraw
        print(f"      Wire updated with {len(self.waypoints)} waypoints")
    
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
