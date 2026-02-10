import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# path_finding imported lazily in update_position() for faster startup
from models.wire import WireData
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen
from PyQt6.QtWidgets import QGraphicsPathItem

from .styles import GRID_SIZE, WIRE_CLICK_WIDTH, theme_manager

logger = logging.getLogger(__name__)


class WireGraphicsItem(QGraphicsPathItem):
    """Wire connecting components with multi-algorithm pathfinding support.

    Each WireGraphicsItem holds a reference to a WireData model object.
    Data properties (start/end component IDs, terminals, waypoints) are
    delegated to the model. Drawing and Qt interaction stay in this class.
    """

    def __init__(
        self, start_comp, start_term, end_comp, end_term, canvas=None, algorithm="astar", layer_color=None, model=None
    ):
        super().__init__()

        # Create or accept a WireData backing object
        if model is not None:
            self.model = model
        else:
            self.model = WireData(
                start_component_id=start_comp.component_id if hasattr(start_comp, "component_id") else str(start_comp),
                start_terminal=start_term,
                end_component_id=end_comp.component_id if hasattr(end_comp, "component_id") else str(end_comp),
                end_terminal=end_term,
                algorithm=algorithm,
            )

        # Store references to actual component objects for rendering
        self.start_comp = start_comp
        self.start_term = start_term
        self.end_comp = end_comp
        self.end_term = end_term

        self.node = None  # Reference to the Node this wire belongs to
        self.canvas = canvas  # Reference to canvas for pathfinding

        # Algorithm layer support
        self.algorithm = algorithm  # Which algorithm generated this wire
        self.layer_color = layer_color if layer_color else QColor(Qt.GlobalColor.black)

        self.waypoints = []  # List of QPointF waypoints (computed during routing)

        self.setPen(QPen(self.layer_color, 2))
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_position()

    # --- Data delegation properties ---

    @property
    def runtime(self):
        return self.model.runtime

    @runtime.setter
    def runtime(self, value):
        self.model.runtime = value

    @property
    def iterations(self):
        return self.model.iterations

    @iterations.setter
    def iterations(self, value):
        self.model.iterations = value

    # --- Methods ---

    def show_drag_preview(self):
        """Show a straight-line preview during component drag.

        Much cheaper than full pathfinding — gives immediate visual
        feedback while the component is being moved.  The real route
        is recalculated by update_position() after the drag ends.
        """
        old_rect = self.boundingRect()
        self.prepareGeometryChange()

        start = self.start_comp.get_terminal_pos(self.start_term)
        end = self.end_comp.get_terminal_pos(self.end_term)

        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(end)
        self.setPath(path)

        if self.scene():
            self.scene().update(old_rect)
            self.scene().update(self.boundingRect())
        self.update()

    def update_position(self):
        """Update wire path using selected algorithm"""
        # Lazy import for faster startup - only loaded when wires are created
        from .path_finding import IDAStarPathfinder, get_component_obstacles

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
                (self.end_comp.component_id, self.end_term),
            ]

            logger.debug(
                "Routing wire (%s) from %s[%s] to %s[%s]",
                self.algorithm,
                self.start_comp.component_id,
                self.start_term,
                self.end_comp.component_id,
                self.end_term,
            )

            # Get all existing wires in the circuit for wire-to-wire obstacle detection
            # Only consider wires from the SAME algorithm layer for fair comparison
            # Wires from the same node won't be treated as obstacles (allows bundling)
            all_wires = self.canvas.wires if hasattr(self.canvas, "wires") else []
            existing_wires = [w for w in all_wires if w.algorithm == self.algorithm]

            obstacles = get_component_obstacles(
                self.canvas.components,
                GRID_SIZE,
                terminal_clearance_only=terminal_clearance,
                active_terminals=active_terminals,
                existing_wires=existing_wires,
                current_node=self.node,
            )

            pathfinder = IDAStarPathfinder(GRID_SIZE)
            result = pathfinder.find_path(start, end, obstacles, algorithm=self.algorithm)

            # Unpack result (waypoints, runtime, iterations)
            self.waypoints, runtime, iterations = result

            # Store in model
            self.model.runtime = runtime
            self.model.iterations = iterations
            # Convert QPointF waypoints to tuples for model storage
            self.model.waypoints = [(wp.x(), wp.y()) for wp in self.waypoints]
        else:
            # Fallback to direct line
            self.waypoints = [start, end]
            self.model.runtime = 0.0
            self.model.iterations = 0
            self.model.waypoints = [(start.x(), start.y()), (end.x(), end.y())]

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

    def paint(self, painter, option=None, widget=None):
        """Override paint to show selection highlight and layer color"""
        if painter is None:
            return

        # Draw wire with layer color
        if self.isSelected():
            painter.setPen(theme_manager.pen("wire_selected"))
        else:
            painter.setPen(QPen(self.layer_color, 2))

        painter.drawPath(self.path())

    def shape(self):
        """Return a wider path for easier click detection"""
        stroker = QPainterPathStroker()
        stroker.setWidth(WIRE_CLICK_WIDTH)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(self.path())

    def get_terminals(self):
        """Get both terminal identifiers for this wire"""
        return [(self.start_comp.component_id, self.start_term), (self.end_comp.component_id, self.end_term)]

    def to_dict(self):
        """Serialize wire to dictionary via the model"""
        return self.model.to_dict()

    @classmethod
    def from_dict(cls, data_dict, components_dict, canvas=None):
        """Deserialize wire from dictionary.

        Args:
            data_dict: Dictionary containing wire data
            components_dict: Dictionary mapping component_id -> ComponentGraphicsItem
            canvas: Canvas reference for pathfinding

        Returns:
            WireGraphicsItem instance
        """
        # Create model first
        wire_data = WireData.from_dict(data_dict)

        # Get component references
        start_comp = components_dict[wire_data.start_component_id]
        end_comp = components_dict[wire_data.end_component_id]

        # Create wire with model
        wire = cls(
            start_comp=start_comp,
            start_term=wire_data.start_terminal,
            end_comp=end_comp,
            end_term=wire_data.end_terminal,
            canvas=canvas,
            algorithm=wire_data.algorithm,
            model=wire_data,
        )

        return wire


# Backward compatibility alias
WireItem = WireGraphicsItem
