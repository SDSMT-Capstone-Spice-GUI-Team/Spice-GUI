from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QPainterPath, QColor
from .path_finding import AStarPathfinder, IDAStarPathfinder, get_component_obstacles
from .styles import GRID_SIZE, theme_manager

class WireItem(QGraphicsPathItem):
    """Wire connecting components with multi-algorithm pathfinding support"""

    def __init__(self, start_comp, start_term, end_comp, end_term, canvas=None, algorithm='astar', layer_color=None):
        super().__init__()
        self.start_comp = start_comp
        self.start_term = start_term
        self.end_comp = end_comp
        self.end_term = end_term
        self.node = None  # Reference to the Node this wire belongs to
        self.canvas = canvas  # Reference to canvas for pathfinding

        # Algorithm layer support
        self.algorithm = algorithm  # Which algorithm generated this wire
        self.layer_color = layer_color if layer_color else QColor(Qt.GlobalColor.black)
        self.runtime = 0.0  # Time taken to route this wire
        self.iterations = 0  # Iterations used by algorithm

        self.waypoints = []  # List of QPointF waypoints

        self.setPen(QPen(self.layer_color, 2))
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_position()
    
    def update_position(self):
        """Update wire path using selected algorithm"""
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

            print(f"      Routing wire ({self.algorithm}) from {self.start_comp.component_id}[{self.start_term}] to {self.end_comp.component_id}[{self.end_term}]")

            # Get all existing wires in the circuit for wire-to-wire obstacle detection
            # Only consider wires from the SAME algorithm layer for fair comparison
            # Wires from the same node won't be treated as obstacles (allows bundling)
            all_wires = self.canvas.wires if hasattr(self.canvas, 'wires') else []
            existing_wires = [w for w in all_wires if w.algorithm == self.algorithm]

            obstacles = get_component_obstacles(
                self.canvas.components,
                GRID_SIZE,
                terminal_clearance_only=terminal_clearance,
                active_terminals=active_terminals,
                existing_wires=existing_wires,
                current_node=self.node
            )

            pathfinder = IDAStarPathfinder(GRID_SIZE)
            result = pathfinder.find_path(start, end, obstacles, algorithm=self.algorithm)

            # Unpack result (waypoints, runtime, iterations)
            self.waypoints, self.runtime, self.iterations = result
            pass
        else:
            # Fallback to direct line
            self.waypoints = [start, end]
            self.runtime = 0.0
            self.iterations = 0

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
        # print(f"      Wire ({self.algorithm}) updated: {len(self.waypoints)} waypoints, {self.runtime*1000:.2f}ms, {self.iterations} iterations")
        # print(f"          Waypoints: {self.waypoints}")
    
    def paint(self, painter, option=None, widget=None):
        """Override paint to show selection highlight and layer color"""
        if painter is None:
            return

        # Draw wire with layer color
        if self.isSelected():
            painter.setPen(theme_manager.pen('wire_selected'))
        else:
            painter.setPen(QPen(self.layer_color, 2))

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
