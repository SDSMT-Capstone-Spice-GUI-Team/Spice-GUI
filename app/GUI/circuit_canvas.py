import logging

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QRubberBand,
)

logger = logging.getLogger(__name__)
from models.clipboard import ClipboardData

from .annotation_item import AnnotationItem
from .circuit_node import Node
from .component_item import ComponentGraphicsItem
from .styles import (
    COMPONENTS,
    DEFAULT_COMPONENT_COUNTER,
    GRID_EXTENT,
    GRID_SIZE,
    MAJOR_GRID_INTERVAL,
    TERMINAL_CLICK_RADIUS,
    ZOOM_FACTOR,
    ZOOM_FIT_PADDING,
    ZOOM_MAX,
    ZOOM_MIN,
    theme_manager,
)
from .wire_item import WireGraphicsItem, WireItem


class CircuitCanvasView(QGraphicsView):
    """Main circuit drawing canvas view"""

    # Signals for component and wire operations
    componentAdded = pyqtSignal(str)  # component_id
    wireAdded = pyqtSignal(str, str)  # start_comp_id, end_comp_id
    selectionChanged = pyqtSignal(object)  # selected component (or None)
    componentRightClicked = pyqtSignal(object, object)  # component, global position
    canvasClicked = pyqtSignal()
    zoomChanged = pyqtSignal(float)  # current zoom level (1.0 = 100%)
    probeRequested = pyqtSignal(str, str)  # (signal_name, probe_type: "node"|"component")

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller  # CircuitController reference for observer pattern
        self.scene = QGraphicsScene()
        if self.scene is None:
            exit()
        self.setScene(self.scene)
        self.setSceneRect(-GRID_EXTENT, -GRID_EXTENT, GRID_EXTENT * 2, GRID_EXTENT * 2)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        # Use MinimalViewportUpdate for better performance; dragging artifacts
        # are prevented by targeted update() calls in ComponentGraphicsItem.itemChange
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)

        self.components = {}  # id -> ComponentGraphicsItem
        self.wires = []  # All wires (for backward compatibility)
        self.nodes = []  # List of Node objects
        self.terminal_to_node = {}  # (comp_id, term_idx) -> Node
        self.component_counter = DEFAULT_COMPONENT_COUNTER.copy()

        # Simulation results storage
        self.node_voltages = {}  # node_label -> voltage value
        self.branch_currents = {}  # device_ref -> current value
        self.show_node_voltages = False  # Toggle for showing voltage values
        self.show_op_annotations = True  # Toggle for OP result annotations

        # Probe mode state
        self.probe_mode = False  # Whether probe tool is active
        self.probe_results = []  # List of probe result dicts for display

        # Label visibility settings
        self.show_component_labels = True  # Toggle for component IDs (R1, V1, etc.)
        self.show_component_values = True  # Toggle for component values (1k, 5V, etc.)
        self.show_node_labels = True  # Toggle for node labels (n1, n2, etc.)

        # Debug visualization
        self.show_obstacle_boundaries = False  # Toggle for showing obstacle boundaries
        self.obstacle_boundary_items = []  # Store obstacle boundary graphics items

        # Grid drawing deferred to first show for faster startup
        self._grid_drawn = False
        self._grid_items = []  # Track grid lines/labels for export toggling

        # Text annotations on the canvas
        self.annotations = []

        # Wire drawing mode
        self.wire_start_comp = None
        self.wire_start_term = None
        self.temp_wire_line = None  # Temporary line while drawing wire

        # Rubber band selection
        self._rubber_band = None
        self._rubber_band_origin = QPoint()

        # Internal clipboard for copy/paste
        self._clipboard = ClipboardData()

        self.setAcceptDrops(True)
        self.setMouseTracking(True)  # Enable mouse tracking for wire preview
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Connect scene selection changes to our signal
        self.scene.selectionChanged.connect(self.on_selection_changed)

        # Register as observer of controller events (Phase 5)
        if self.controller:
            self.controller.add_observer(self._on_model_changed)

    def showEvent(self, event):
        """Draw grid on first show for faster startup"""
        super().showEvent(event)
        if not self._grid_drawn:
            self.draw_grid()
            self._grid_drawn = True

    # ===================================================================
    # Observer Pattern (Phase 5)
    # ===================================================================

    def _on_model_changed(self, event: str, data) -> None:
        """
        Dispatch model change events to specific handlers.

        This method is called by CircuitController when the model changes.
        It routes events to appropriate handler methods for automatic canvas updates.
        """
        handlers = {
            "component_added": self._handle_component_added,
            "component_removed": self._handle_component_removed,
            "component_moved": self._handle_component_moved,
            "component_rotated": self._handle_component_rotated,
            "component_flipped": self._handle_component_flipped,
            "component_value_changed": self._handle_component_value_changed,
            "wire_added": self._handle_wire_added,
            "wire_removed": self._handle_wire_removed,
            "wire_routed": self._handle_wire_routed,
            "circuit_cleared": self._handle_circuit_cleared,
            "nodes_rebuilt": self._handle_nodes_rebuilt,
            "model_loaded": self._handle_model_loaded,
        }

        handler = handlers.get(event)
        if handler:
            try:
                handler(data)
            except (AttributeError, KeyError, TypeError) as e:
                logger.error(f"Error handling event '{event}': {e}")
        else:
            logger.debug(f"Unhandled observer event: {event}")

        # Clear stale OP annotations when circuit is modified
        _stale_events = {
            "component_added",
            "component_removed",
            "wire_added",
            "wire_removed",
            "component_value_changed",
            "circuit_cleared",
        }
        if event in _stale_events and self.node_voltages:
            self.node_voltages = {}
            self.branch_currents = {}
            self.show_node_voltages = False
            self.probe_results = []

    def _handle_component_added(self, component_data) -> None:
        """Create graphics item when component added to model"""
        comp = ComponentGraphicsItem.from_dict(component_data.to_dict())
        self.scene.addItem(comp)
        self.components[component_data.component_id] = comp

        # Handle ground special case
        if component_data.component_type == "Ground":
            self.handle_ground_added(comp)

        self.scene.update()

    def _handle_component_removed(self, component_id: str) -> None:
        """Remove graphics item when component removed from model"""
        comp = self.components.get(component_id)
        if comp:
            self.scene.removeItem(comp)
            del self.components[component_id]
            self.scene.update()

    def _handle_component_moved(self, component_data) -> None:
        """Update graphics item position - disable change flag to prevent recursion"""
        from PyQt6.QtWidgets import QGraphicsItem

        comp = self.components.get(component_data.component_id)
        if comp:
            # Disable ItemSendsGeometryChanges to prevent infinite recursion
            comp.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
            comp.setPos(*component_data.position)
            comp.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

            # Reroute connected wires
            self.reroute_connected_wires(comp)

    def _handle_component_rotated(self, component_data) -> None:
        """Update graphics item rotation"""
        comp = self.components.get(component_data.component_id)
        if comp:
            comp.rotation_angle = component_data.rotation
            comp.update_terminals()
            comp.update()
            self.reroute_connected_wires(comp)

    def _handle_component_flipped(self, component_data) -> None:
        """Update graphics item flip"""
        comp = self.components.get(component_data.component_id)
        if comp:
            comp.update_terminals()
            comp.update()
            self.reroute_connected_wires(comp)

    def _handle_component_value_changed(self, component_data) -> None:
        """Update graphics item value display"""
        comp = self.components.get(component_data.component_id)
        if comp:
            comp.value = component_data.value
            comp.update()

    def _handle_wire_added(self, wire_data) -> None:
        """Create wire graphics item when wire added to model"""
        start_comp = self.components.get(wire_data.start_component_id)
        end_comp = self.components.get(wire_data.end_component_id)

        if start_comp and end_comp:
            wire = WireGraphicsItem(
                start_comp,
                wire_data.start_terminal,
                end_comp,
                wire_data.end_terminal,
                canvas=self,
                model=wire_data,
            )
            self.scene.addItem(wire)
            self.wires.append(wire)
            # Note: Node updates handled by nodes_rebuilt event

    def _handle_wire_removed(self, wire_index: int) -> None:
        """Remove wire graphics item (wires removed in reverse order)"""
        if 0 <= wire_index < len(self.wires):
            wire = self.wires[wire_index]
            self.scene.removeItem(wire)
            del self.wires[wire_index]

    def _handle_wire_routed(self, data) -> None:
        """Update wire waypoints"""
        from PyQt6.QtCore import QPointF

        wire_index, wire_data = data
        if 0 <= wire_index < len(self.wires):
            wire = self.wires[wire_index]
            # Convert waypoints to QPointF if they exist
            if hasattr(wire_data, "waypoints") and wire_data.waypoints:
                wire.waypoints = [QPointF(x, y) for x, y in wire_data.waypoints]
                if hasattr(wire, "update_path"):
                    wire.update_path()

    def _handle_circuit_cleared(self, data: None) -> None:
        """Clear all graphics items when circuit cleared"""
        self.scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.nodes = []
        self.terminal_to_node = {}
        self.annotations = []
        Node._node_counter = 0

    def _handle_nodes_rebuilt(self, data: None) -> None:
        """Rebuild node visualization from model"""
        if not self.controller:
            return

        self.nodes = []
        self.terminal_to_node = {}

        # Convert NodeData to Node (Qt objects)
        for node_data in self.controller.model.nodes:
            node = Node.from_node_data(node_data)
            self.nodes.append(node)

        # Rebuild terminal mapping
        for (
            comp_id,
            term_idx,
        ), node_data in self.controller.model.terminal_to_node.items():
            # Find corresponding Qt Node
            qt_node = next((n for n in self.nodes if n.matches_node_data(node_data)), None)
            if qt_node:
                self.terminal_to_node[(comp_id, term_idx)] = qt_node

        self.scene.update()

    def _handle_model_loaded(self, data: None) -> None:
        """Rebuild entire canvas when model loaded from file"""
        if not self.controller:
            return

        # Clear and rebuild everything
        self.scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.annotations = []

        # Restore components
        for comp_data in self.controller.model.components.values():
            self._handle_component_added(comp_data)

        # Restore wires
        for wire_data in self.controller.model.wires:
            self._handle_wire_added(wire_data)

        # Rebuild nodes
        self._handle_nodes_rebuilt(None)

        # Restore component counter
        self.component_counter = self.controller.model.component_counter.copy()

    # ===================================================================
    # End Observer Pattern Handlers
    # ===================================================================

    # unsuccessful attempt to get rid of red squiggles
    # def views(self) -> list | None:
    #     views = super().views() if super().views() else None
    #     return views

    def refresh_theme(self):
        """Redraw grid and repaint all items to reflect the current theme."""
        if self.scene is None:
            return
        # Set scene background
        bg = theme_manager.color("background_primary")
        self.scene.setBackgroundBrush(QBrush(bg))

        # Remove old grid items and redraw
        for item in self._grid_items:
            self.scene.removeItem(item)
        self._grid_items.clear()
        self.draw_grid()

        # Update all wire pens with current theme color
        default_wire_color = theme_manager.color("wire_default")
        for wire in self.wires:
            wire.layer_color = default_wire_color
            if not wire.isSelected():
                wire.setPen(QPen(default_wire_color, 2))

        # Force full repaint of all items (components pick up theme in paint())
        self.scene.update()

    def draw_grid(self):
        """Draw background grid with major grid lines labeled with position values"""
        if self.scene is None:
            return

        # Grid pens from theme
        minor_pen = theme_manager.pen("grid_minor")
        major_pen = theme_manager.pen("grid_major")
        grid_label_color = theme_manager.color("grid_label")
        grid_label_font = theme_manager.font("grid_label")

        # Draw vertical lines
        for x in range(-GRID_EXTENT, GRID_EXTENT + 1, GRID_SIZE):
            is_major = x % MAJOR_GRID_INTERVAL == 0
            pen = major_pen if is_major else minor_pen
            line = self.scene.addLine(x, -GRID_EXTENT, x, GRID_EXTENT, pen)
            self._grid_items.append(line)

            # Add label for major grid lines
            if is_major:
                label = QGraphicsTextItem(str(x))
                label.setDefaultTextColor(grid_label_color)
                label.setFont(grid_label_font)
                label.setPos(x - 15, -GRID_EXTENT)  # Position at top
                label.setZValue(-1)  # Draw behind components
                self.scene.addItem(label)
                self._grid_items.append(label)

        # Draw horizontal lines
        for y in range(-GRID_EXTENT, GRID_EXTENT + 1, GRID_SIZE):
            is_major = y % MAJOR_GRID_INTERVAL == 0
            pen = major_pen if is_major else minor_pen
            line = self.scene.addLine(-GRID_EXTENT, y, GRID_EXTENT, y, pen)
            self._grid_items.append(line)

            # Add label for major grid lines
            if is_major:
                label = QGraphicsTextItem(str(y))
                label.setDefaultTextColor(grid_label_color)
                label.setFont(grid_label_font)
                label.setPos(-GRID_EXTENT, y - 10)  # Position at left
                label.setZValue(-1)  # Draw behind components
                self.scene.addItem(label)
                self._grid_items.append(label)

    def reroute_connected_wires(self, component):
        """Reroute all wires connected to a component"""
        wire_count = 0
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                wire.update_position()
                wire_count += 1

        # Force a full scene update to ensure wires are redrawn
        if wire_count > 0:
            self.scene.update()
            if self.viewport():
                self.viewport().update()

        # Show status message if rerouted wires
        if wire_count > 0:
            # Try to update status bar if main window is available
            main_window = self.window()
            if main_window and hasattr(main_window, "statusBar"):
                status = main_window.statusBar()
                if status:
                    status.showMessage(
                        f"Rerouted {wire_count} wire{'s' if wire_count != 1 else ''} connected to {component.component_id}",
                        1000,
                    )

    def dragEnterEvent(self, event):
        if event is None:
            return
        mimeData = event.mimeData()
        if mimeData is None:
            return
        if mimeData.hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event is None:
            return
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle component drop from palette - Phase 5: uses controller"""
        if event is None:
            return
        if not self.controller:
            logger.warning("Cannot drop component: no controller available")
            return

        mimeData = event.mimeData()
        if mimeData is None:
            return
        component_type = mimeData.text()
        if component_type in COMPONENTS:
            # Position at drop location (snapped to grid)
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            grid_x = round(scene_pos.x() / GRID_SIZE) * GRID_SIZE
            grid_y = round(scene_pos.y() / GRID_SIZE) * GRID_SIZE

            # Controller handles component creation, observer creates graphics item
            component_data = self.controller.add_component(component_type, (grid_x, grid_y))
            self.componentAdded.emit(component_data.component_id)

            event.acceptProposedAction()

    def add_component_at_center(self, component_type):
        """Add a component at the center of the visible canvas area - Phase 5: uses controller"""
        if component_type not in COMPONENTS:
            return
        if not self.controller:
            logger.warning("Cannot add component: no controller available")
            return

        # Get viewport center in scene coordinates
        viewport_center = self.viewport().rect().center()
        scene_pos = self.mapToScene(viewport_center)

        # Snap to grid
        grid_x = round(scene_pos.x() / GRID_SIZE) * GRID_SIZE
        grid_y = round(scene_pos.y() / GRID_SIZE) * GRID_SIZE

        # Controller handles component creation, observer creates graphics item
        component_data = self.controller.add_component(component_type, (grid_x, grid_y))
        self.componentAdded.emit(component_data.component_id)

    def mousePressEvent(self, event):
        """Handle wire drawing, probe mode, and component selection"""
        if event is None:
            return

        # Probe mode: intercept left clicks to probe nodes/components
        if self.probe_mode and event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            result = self._probe_at_position(scene_pos)
            if result is None and not self.node_voltages:
                main_window = self.window()
                if main_window and hasattr(main_window, "statusBar"):
                    status = main_window.statusBar()
                    if status:
                        status.showMessage("No simulation results available. Run a simulation first.", 3000)
            event.accept()
            return

        clicked_terminal = None  # Initialize here

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)

            # Check all components for terminal proximity
            clicked_component = None
            clicked_term_index = None

            for comp in self.components.values():
                terminals = [comp.get_terminal_pos(i) for i in range(len(comp.terminals))]
                for i, term_pos in enumerate(terminals):
                    distance = (term_pos - scene_pos).manhattanLength()
                    if distance < TERMINAL_CLICK_RADIUS:
                        clicked_terminal = term_pos
                        clicked_component = comp
                        clicked_term_index = i
                        break
                if clicked_terminal:
                    break

            # If we clicked near a terminal
            if clicked_terminal and clicked_component:
                if self.wire_start_comp is None:
                    # Start drawing wire
                    if self.is_terminal_available(clicked_component, clicked_term_index):
                        self.wire_start_comp = clicked_component
                        self.wire_start_term = clicked_term_index

                    if self.wire_start_comp:
                        # Create temporary wire line for visual feedback
                        start_pos = self.wire_start_comp.get_terminal_pos(self.wire_start_term)
                        self.temp_wire_line = QGraphicsLineItem(
                            start_pos.x(), start_pos.y(), start_pos.x(), start_pos.y()
                        )
                        self.temp_wire_line.setPen(theme_manager.pen("wire_preview"))
                        self.temp_wire_line.setZValue(100)  # Draw on top
                        self.scene.addItem(self.temp_wire_line)

                        # Accept event only when we successfully started wire drawing
                        event.accept()
                        return
                    pass
                else:
                    # Complete the wire
                    if clicked_component != self.wire_start_comp:
                        can_connect = False
                        target_term = 0

                        if self.is_terminal_available(clicked_component, clicked_term_index):
                            can_connect = True
                            target_term = clicked_term_index

                        if can_connect:
                            if self.controller:
                                # Controller creates wire, observer creates graphics item
                                self.controller.add_wire(
                                    self.wire_start_comp.component_id,
                                    self.wire_start_term,
                                    clicked_component.component_id,
                                    target_term,
                                )
                                self.wireAdded.emit(
                                    self.wire_start_comp.component_id,
                                    clicked_component.component_id,
                                )
                            else:
                                # Fallback to old method if no controller (shouldn't happen)
                                wire = WireItem(
                                    self.wire_start_comp,
                                    self.wire_start_term,
                                    clicked_component,
                                    target_term,
                                    canvas=self,
                                    algorithm="idastar",
                                )
                                self.scene.addItem(wire)
                                self.wires.append(wire)
                                self.update_nodes_for_wire(wire)
                                self.wireAdded.emit(
                                    self.wire_start_comp.component_id,
                                    clicked_component.component_id,
                                )

                    # Clean up temporary wire line
                    if self.temp_wire_line:
                        self.scene.removeItem(self.temp_wire_line)
                        self.temp_wire_line = None

                    self.wire_start_comp = None
                    self.wire_start_term = None

                    # Wire completed, allow normal behavior to continue
                    # Don't accept - let event propagate for other handling

            # If we're in wire drawing mode but clicked elsewhere, cancel it
            elif self.wire_start_comp is not None:
                if self.temp_wire_line:
                    self.scene.removeItem(self.temp_wire_line)
                    self.temp_wire_line = None
                self.wire_start_comp = None
                self.wire_start_term = None

            # If we didn't click a terminal, check if we clicked an empty area
            else:
                item = self.itemAt(event.position().toPoint())
                if item is None:
                    self.canvasClicked.emit()
                    # Start rubber band selection on empty space
                    if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                        self.scene.clearSelection()
                    self._rubber_band_origin = event.position().toPoint()
                    if self._rubber_band is None:
                        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
                    self._rubber_band.setGeometry(QRect(self._rubber_band_origin, self._rubber_band_origin))
                    self._rubber_band.show()
                    event.accept()
                    return

        # Normal selection/movement behavior
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Update temporary wire line or rubber band while drawing"""
        if event is None:
            return

        if self.wire_start_comp is not None and self.temp_wire_line is not None:
            # Update temporary wire to follow mouse
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            start_pos = self.wire_start_comp.get_terminal_pos(self.wire_start_term)
            self.temp_wire_line.setLine(start_pos.x(), start_pos.y(), scene_pos.x(), scene_pos.y())
            self.temp_wire_line.update()
            event.accept()
            return

        # Update rubber band rectangle
        if self._rubber_band is not None and self._rubber_band.isVisible():
            self._rubber_band.setGeometry(QRect(self._rubber_band_origin, event.position().toPoint()).normalized())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release — finalize rubber band selection"""
        if event is None:
            return

        if self._rubber_band is not None and self._rubber_band.isVisible():
            self._rubber_band.hide()
            # Map rubber band rect to scene coordinates and select enclosed items
            rb_rect = self._rubber_band.geometry()
            scene_rect = QRectF(
                self.mapToScene(rb_rect.topLeft()),
                self.mapToScene(rb_rect.bottomRight()),
            )
            for item in self.scene.items(scene_rect, Qt.ItemSelectionMode.IntersectsItemShape):
                if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem)):
                    item.setSelected(True)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle Escape to cancel wire drawing; forward other keys.

        All keyboard shortcuts (Delete, Ctrl+C/X/V, R, F, Ctrl+A, etc.) are
        handled by QAction shortcuts on the menu bar, so no duplicate
        handling is needed here.
        """
        if event is None:
            return
        if event.key() == Qt.Key.Key_Escape:
            if self.probe_mode:
                self.set_probe_mode(False)
                self.clear_probes()
                # Notify main window to uncheck the action
                main_window = self.window()
                if main_window and hasattr(main_window, "probe_action"):
                    main_window.probe_action.setChecked(False)
                event.accept()
                return
            if self.wire_start_comp is not None:
                if self.temp_wire_line:
                    self.scene.removeItem(self.temp_wire_line)
                    self.temp_wire_line = None
                self.wire_start_comp = None
                self.wire_start_term = None
                event.accept()
                return
            # Deselect all if not wiring
            self.scene.clearSelection()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """Zoom with Ctrl+Scroll wheel, centered on cursor."""
        if event is None:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in(event.position().toPoint())
            elif delta < 0:
                self.zoom_out(event.position().toPoint())
            event.accept()
        else:
            super().wheelEvent(event)

    def get_zoom_level(self):
        """Return the current zoom level as a float (1.0 = 100%)."""
        return self.transform().m11()

    def zoom_in(self, center_point=None):
        """Zoom in by one step, optionally centered on a point."""
        self._apply_zoom(ZOOM_FACTOR, center_point)

    def zoom_out(self, center_point=None):
        """Zoom out by one step, optionally centered on a point."""
        self._apply_zoom(1.0 / ZOOM_FACTOR, center_point)

    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.resetTransform()
        self.zoomChanged.emit(1.0)

    def zoom_fit(self):
        """Fit all circuit components in view with padding."""
        items = [item for item in self.scene.items() if isinstance(item, ComponentGraphicsItem)]
        if not items:
            self.zoom_reset()
            return

        # Calculate bounding rect of all components
        rect = items[0].sceneBoundingRect()
        for item in items[1:]:
            rect = rect.united(item.sceneBoundingRect())

        # Add padding
        rect.adjust(-ZOOM_FIT_PADDING, -ZOOM_FIT_PADDING, ZOOM_FIT_PADDING, ZOOM_FIT_PADDING)

        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

        # Clamp to min/max zoom
        level = self.get_zoom_level()
        if level < ZOOM_MIN:
            self.resetTransform()
            self.scale(ZOOM_MIN, ZOOM_MIN)
        elif level > ZOOM_MAX:
            self.resetTransform()
            self.scale(ZOOM_MAX, ZOOM_MAX)

        self.zoomChanged.emit(self.get_zoom_level())

    def _apply_zoom(self, factor, center_point=None):
        """Apply a zoom factor, clamping to min/max limits."""
        current = self.get_zoom_level()
        new_level = current * factor

        if new_level < ZOOM_MIN or new_level > ZOOM_MAX:
            return

        if center_point is not None:
            # Zoom centered on cursor
            old_pos = self.mapToScene(center_point)
            self.scale(factor, factor)
            new_pos = self.mapToScene(center_point)
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
        else:
            self.scale(factor, factor)

        self.zoomChanged.emit(self.get_zoom_level())

    def show_context_menu(self, position):
        """Show context menu for delete operations and component properties"""
        item = self.itemAt(position)

        # If a component is right-clicked, emit a signal to show properties
        if isinstance(item, ComponentGraphicsItem):
            self.componentRightClicked.emit(item, self.mapToGlobal(position))

        scene_pos = self.mapToScene(position)

        menu = QMenu()

        if isinstance(item, ComponentGraphicsItem):
            delete_action = QAction(f"Delete {item.component_id}", self)
            delete_action.triggered.connect(lambda: self.delete_component(item))
            menu.addAction(delete_action)

            menu.addSeparator()

            rotate_cw_action = QAction("Rotate Clockwise (R)", self)
            rotate_cw_action.triggered.connect(lambda: self.rotate_component(item, True))
            menu.addAction(rotate_cw_action)

            rotate_ccw_action = QAction("Rotate Counter-Clockwise (Shift+R)", self)
            rotate_ccw_action.triggered.connect(lambda: self.rotate_component(item, False))
            menu.addAction(rotate_ccw_action)

            menu.addSeparator()

            flip_h_action = QAction("Flip Horizontal (F)", self)
            flip_h_action.triggered.connect(lambda: self.flip_component(item, True))
            menu.addAction(flip_h_action)

            flip_v_action = QAction("Flip Vertical (Shift+F)", self)
            flip_v_action.triggered.connect(lambda: self.flip_component(item, False))
            menu.addAction(flip_v_action)

        elif isinstance(item, AnnotationItem):
            delete_action = QAction("Delete Annotation", self)
            delete_action.triggered.connect(lambda: self._delete_annotation(item))
            menu.addAction(delete_action)

            edit_action = QAction("Edit Annotation", self)
            edit_action.triggered.connect(lambda: item.mouseDoubleClickEvent(None))
            menu.addAction(edit_action)

        elif isinstance(item, WireItem):
            delete_action = QAction("Delete Wire", self)
            delete_action.triggered.connect(lambda: self.delete_wire(item))
            menu.addAction(delete_action)

            if item.node:
                menu.addSeparator()
                current = item.node.get_label()
                label_action = QAction(f"Set Net Name ({current})...", self)
                label_action.triggered.connect(lambda: self.label_node(item.node))
                menu.addAction(label_action)
            pass
        else:
            # Check if we clicked near a terminal to set its net name
            clicked_node = self.find_node_at_position(scene_pos)
            if clicked_node:
                current = clicked_node.get_label()
                label_action = QAction(f"Set Net Name ({current})...", self)
                label_action.triggered.connect(lambda: self.label_node(clicked_node))
                menu.addAction(label_action)
                menu.addSeparator()

            # No specific item, offer to delete all selected
            selected_items = self.scene.selectedItems()
            if selected_items:
                delete_action = QAction(f"Delete Selected ({len(selected_items)} items)", self)
                delete_action.triggered.connect(self.delete_selected)
                menu.addAction(delete_action)

                # Check if any components are selected
                selected_components = [i for i in selected_items if isinstance(i, ComponentGraphicsItem)]
                if selected_components:
                    menu.addSeparator()
                    rotate_cw_action = QAction("Rotate Selected Clockwise", self)
                    rotate_cw_action.triggered.connect(lambda: self.rotate_selected(True))
                    menu.addAction(rotate_cw_action)

                    rotate_ccw_action = QAction("Rotate Selected Counter-Clockwise", self)
                    rotate_ccw_action.triggered.connect(lambda: self.rotate_selected(False))
                    menu.addAction(rotate_ccw_action)

                    flip_h_action = QAction("Flip Selected Horizontal", self)
                    flip_h_action.triggered.connect(lambda: self.flip_selected(True))
                    menu.addAction(flip_h_action)

                    flip_v_action = QAction("Flip Selected Vertical", self)
                    flip_v_action.triggered.connect(lambda: self.flip_selected(False))
                    menu.addAction(flip_v_action)

                    menu.addSeparator()
                    sel_ids = [c.component_id for c in selected_components]
                    copy_action = QAction(
                        f"Copy ({len(selected_components)} component{'s' if len(selected_components) != 1 else ''})",
                        self,
                    )
                    copy_action.triggered.connect(lambda checked=False, ids=sel_ids: self.copy_selected_components(ids))
                    menu.addAction(copy_action)

                    cut_action = QAction(
                        f"Cut ({len(selected_components)} component{'s' if len(selected_components) != 1 else ''})",
                        self,
                    )
                    cut_action.triggered.connect(lambda checked=False, ids=sel_ids: self.cut_selected_components(ids))
                    menu.addAction(cut_action)

        if not self._clipboard.is_empty():
            paste_action = QAction("Paste", self)
            paste_action.triggered.connect(self.paste_components)
            menu.addAction(paste_action)

        # Always offer "Add Annotation" on empty-area right-click
        menu.addSeparator()
        add_ann_action = QAction("Add Annotation", self)
        add_ann_action.triggered.connect(lambda: self.add_annotation(scene_pos))
        menu.addAction(add_ann_action)

        if not menu.isEmpty():
            menu.exec(self.mapToGlobal(position))

    def delete_selected(self):
        """Delete all selected items"""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        components_to_delete = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]
        wires_to_delete = [item for item in selected_items if isinstance(item, WireItem)]
        annotations_to_delete = [item for item in selected_items if isinstance(item, AnnotationItem)]

        for comp in components_to_delete:
            self.delete_component(comp)

        for wire in wires_to_delete:
            if wire in self.wires:
                self.delete_wire(wire)

        for ann in annotations_to_delete:
            self.scene.removeItem(ann)
            if ann in self.annotations:
                self.annotations.remove(ann)

    def delete_component(self, component):
        """Delete a component and all connected wires via undo/redo command."""
        if component is None:
            return
        if not self.controller:
            logger.warning("Cannot delete component: no controller available")
            return

        from controllers.commands import DeleteComponentCommand

        cmd = DeleteComponentCommand(self.controller, component.component_id)
        self.controller.execute_command(cmd)

    def delete_wire(self, wire):
        """Delete a wire via undo/redo command (updates model and supports Ctrl+Z)."""
        if wire is None:
            return
        if not self.controller:
            logger.warning("Cannot delete wire: no controller available")
            return
        if wire not in self.wires:
            return

        from controllers.commands import DeleteWireCommand

        wire_index = self.wires.index(wire)
        cmd = DeleteWireCommand(self.controller, wire_index)
        self.controller.execute_command(cmd)

    def rotate_component(self, component, clockwise=True):
        """Rotate a single component - Phase 5: uses controller"""
        if component is None or not isinstance(component, ComponentGraphicsItem):
            return
        if not self.controller:
            logger.warning("Cannot rotate component: no controller available")
            return

        # Controller handles rotation, observer updates graphics and wires
        self.controller.rotate_component(component.component_id, clockwise)

    def rotate_selected(self, clockwise=True):
        """Rotate all selected components"""
        selected_items = self.scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]

        for comp in components:
            self.rotate_component(comp, clockwise)

    def flip_component(self, component, horizontal=True):
        """Flip a single component - uses controller"""
        if component is None or not isinstance(component, ComponentGraphicsItem):
            return
        if not self.controller:
            logger.warning("Cannot flip component: no controller available")
            return

        self.controller.flip_component(component.component_id, horizontal)

    def flip_selected(self, horizontal=True):
        """Flip all selected components"""
        selected_items = self.scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]

        for comp in components:
            self.flip_component(comp, horizontal)

    def add_annotation(self, scene_pos=None):
        """Add a text annotation at the given scene position (or viewport center)."""
        if scene_pos is None:
            viewport_center = self.viewport().rect().center()
            scene_pos = self.mapToScene(viewport_center)

        # Snap to grid
        x = round(scene_pos.x() / GRID_SIZE) * GRID_SIZE
        y = round(scene_pos.y() / GRID_SIZE) * GRID_SIZE

        text, ok = QInputDialog.getText(None, "Add Annotation", "Text:")
        if ok and text:
            ann = AnnotationItem(text=text, x=x, y=y)
            self.scene.addItem(ann)
            self.annotations.append(ann)

    def _delete_annotation(self, ann):
        """Remove an annotation from the canvas."""
        self.scene.removeItem(ann)
        if ann in self.annotations:
            self.annotations.remove(ann)

    def select_all(self):
        """Select all components and wires on the canvas."""
        for item in self.scene.items():
            if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem)):
                item.setSelected(True)

    def on_selection_changed(self):
        """Handle selection changes in the scene"""
        selected_items = self.scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]

        if len(components) > 1:
            # Multi-selection: emit the list
            self.selectionChanged.emit(components)
        elif len(components) == 1:
            self.selectionChanged.emit(components[0])
        else:
            self.selectionChanged.emit(None)

    # --- Clipboard operations ---

    def get_selected_component_ids(self) -> list[str]:
        """Return component IDs for all selected ComponentItems."""
        return [item.component_id for item in self.scene.selectedItems() if isinstance(item, ComponentGraphicsItem)]

    def copy_selected_components(self, component_ids: list[str]) -> bool:
        """Copy selected components and internal wires to internal clipboard."""
        if not component_ids:
            return False

        selected_set = set(component_ids)

        comp_dicts = []
        for comp_id in component_ids:
            comp_item = self.components.get(comp_id)
            if comp_item is not None:
                comp_dicts.append(comp_item.to_dict())

        if not comp_dicts:
            return False

        wire_dicts = []
        for wire in self.wires:
            if wire.start_comp.component_id in selected_set and wire.end_comp.component_id in selected_set:
                wire_dicts.append(wire.to_dict())

        self._clipboard = ClipboardData(
            components=comp_dicts,
            wires=wire_dicts,
            paste_count=0,
        )

        main_window = self.window()
        if main_window and hasattr(main_window, "statusBar"):
            status = main_window.statusBar()
            if status:
                n = len(comp_dicts)
                w = len(wire_dicts)
                status.showMessage(
                    f"Copied {n} component{'s' if n != 1 else ''} and {w} wire{'s' if w != 1 else ''}",
                    2000,
                )
        return True

    def cut_selected_components(self, component_ids: list[str]) -> bool:
        """Cut: copy to clipboard, then delete originals."""
        copied = self.copy_selected_components(component_ids)
        if copied:
            for comp_id in list(component_ids):
                comp_item = self.components.get(comp_id)
                if comp_item is not None:
                    self.delete_component(comp_item)
        return copied

    def paste_components(self) -> None:
        """Paste clipboard contents with offset and new IDs."""
        if self._clipboard.is_empty():
            return

        self._clipboard.paste_count += 1
        multiplier = self._clipboard.paste_count
        dx = 40.0 * multiplier
        dy = 40.0 * multiplier

        id_map: dict[str, str] = {}
        new_comp_items: list[ComponentGraphicsItem] = []

        for comp_dict in self._clipboard.components:
            # Create visual item from serialized data
            comp_item = ComponentGraphicsItem.from_dict(comp_dict)
            component_type = comp_item.component_type

            # Generate new unique ID (same pattern as dropEvent)
            symbol = COMPONENTS[component_type]["symbol"]
            if symbol not in self.component_counter:
                self.component_counter[symbol] = 0
            self.component_counter[symbol] += 1
            new_id = f"{symbol}{self.component_counter[symbol]}"

            old_id = comp_dict["id"]
            id_map[old_id] = new_id

            # Update the component with its new ID
            comp_item.component_id = new_id
            comp_item.model.component_id = new_id

            # Offset position
            old_x = comp_item.pos().x()
            old_y = comp_item.pos().y()
            comp_item.setPos(old_x + dx, old_y + dy)
            comp_item.model.position = (old_x + dx, old_y + dy)

            self.scene.addItem(comp_item)
            self.components[new_id] = comp_item

            if component_type == "Ground":
                self.handle_ground_added(comp_item)

            new_comp_items.append(comp_item)

        # Re-create internal wires with remapped component IDs
        for wire_dict in self._clipboard.wires:
            new_start = id_map.get(wire_dict["start_comp"])
            new_end = id_map.get(wire_dict["end_comp"])

            if new_start is None or new_end is None:
                continue

            start_comp = self.components.get(new_start)
            end_comp = self.components.get(new_end)
            if start_comp is None or end_comp is None:
                continue

            wire = WireItem(
                start_comp,
                wire_dict["start_term"],
                end_comp,
                wire_dict["end_term"],
                canvas=self,
            )
            self.scene.addItem(wire)
            self.wires.append(wire)
            self.update_nodes_for_wire(wire)

        # Select newly pasted items
        self.scene.clearSelection()
        for comp_item in new_comp_items:
            comp_item.setSelected(True)

        if new_comp_items:
            self.componentAdded.emit(new_comp_items[0].component_id)

        main_window = self.window()
        if main_window and hasattr(main_window, "statusBar"):
            status = main_window.statusBar()
            if status:
                n = len(new_comp_items)
                status.showMessage(f"Pasted {n} component{'s' if n != 1 else ''}", 2000)

    def drawForeground(self, painter, rect):
        """Draw node labels, voltages, and OP annotations on top of everything."""
        if painter is None:
            return

        show_op = self.show_op_annotations and self.show_node_voltages and self.node_voltages
        has_content = self.show_node_labels or show_op

        if not has_content:
            return

        # Draw node labels (always use node_label style)
        if self.show_node_labels:
            painter.setPen(theme_manager.pen("node_label_outline"))
            painter.setBrush(theme_manager.brush("node_label_bg"))
            painter.setFont(theme_manager.font("node_label"))

            for node in self.nodes:
                pos = node.get_position(self.components)
                if pos:
                    label = node.get_label()
                    self._draw_label_box(painter, pos, label, y_above=True)

        # Draw OP voltage annotations (distinct style)
        if show_op:
            from simulation.result_parser import format_si

            op_pen = theme_manager.pen("op_voltage")
            op_brush = theme_manager.brush("op_annotation_bg")
            op_font = theme_manager.font("op_annotation")
            painter.setPen(op_pen)
            painter.setBrush(op_brush)
            painter.setFont(op_font)

            for node in self.nodes:
                pos = node.get_position(self.components)
                if pos:
                    label = node.get_label()
                    if label in self.node_voltages:
                        voltage = self.node_voltages[label]
                        text = format_si(voltage, "V")
                        # Offset below the node (or below the node label)
                        offset_y = 14 if self.show_node_labels else 0
                        from PyQt6.QtCore import QPointF

                        draw_pos = QPointF(pos.x(), pos.y() + offset_y)
                        self._draw_label_box(painter, draw_pos, text, y_above=False, pen=op_pen)

            # Draw branch current annotations along components
            if self.branch_currents:
                cur_pen = theme_manager.pen("op_current")
                painter.setPen(cur_pen)

                for comp_id, comp_item in self.components.items():
                    # Match component ref (e.g., "r1", "v1") to branch currents
                    comp_ref = getattr(comp_item, "component_id", comp_id).lower()
                    if comp_ref in self.branch_currents:
                        current = self.branch_currents[comp_ref]
                        text = format_si(current, "A")
                        # Position at center of component, offset to the right
                        comp_rect = comp_item.boundingRect()
                        center = comp_item.mapToScene(comp_rect.center())
                        from PyQt6.QtCore import QPointF

                        draw_pos = QPointF(center.x() + comp_rect.width() / 2 + 5, center.y())
                        self._draw_label_box(painter, draw_pos, text, y_above=False, pen=cur_pen)

        # Draw probe annotations (always on top, visually distinct)
        if self.probe_results:
            probe_v_pen = theme_manager.pen("probe_voltage")
            probe_brush = theme_manager.brush("probe_bg")
            probe_font = theme_manager.font("probe_label")
            painter.setFont(probe_font)
            painter.setBrush(probe_brush)

            for probe in self.probe_results:
                pos = probe["pos"]
                if probe["type"] == "node":
                    text = probe["voltage"]
                    painter.setPen(probe_v_pen)
                    self._draw_label_box(painter, pos, text, y_above=False, pen=probe_v_pen)
                elif probe["type"] == "component":
                    text = probe["text"]
                    painter.setPen(probe_v_pen)
                    self._draw_label_box(painter, pos, text, y_above=False, pen=probe_v_pen)

    def _draw_label_box(self, painter, pos, text, y_above=True, pen=None):
        """Draw a text label with background box at the given position."""
        metrics = painter.fontMetrics()
        lines = text.split("\n")
        max_width = max(metrics.horizontalAdvance(line) for line in lines)
        text_height = metrics.height() * len(lines)

        if y_above:
            label_rect = QRectF(
                pos.x() - max_width / 2 - 2,
                pos.y() - text_height - 2,
                max_width + 4,
                text_height + 4,
            )
        else:
            label_rect = QRectF(
                pos.x() - max_width / 2 - 2,
                pos.y() - 2,
                max_width + 4,
                text_height + 4,
            )

        painter.drawRect(label_rect)

        if pen:
            painter.setPen(pen)
        if y_above:
            y_offset = int(pos.y() - 4)
        else:
            y_offset = int(pos.y() + metrics.ascent())

        for line in lines:
            text_width = metrics.horizontalAdvance(line)
            painter.drawText(int(pos.x() - text_width / 2), y_offset, line)
            y_offset += metrics.height()

    def set_node_voltages(self, voltages_dict):
        """Set node voltages from simulation results."""
        self.node_voltages = voltages_dict
        self.show_node_voltages = True
        self.scene.update()

    def clear_node_voltages(self):
        """Clear displayed node voltages."""
        self.node_voltages = {}
        self.branch_currents = {}
        self.show_node_voltages = False
        self.scene.update()

    def set_op_results(self, voltages_dict, currents_dict=None):
        """Set DC operating point results (voltages and branch currents)."""
        self.node_voltages = voltages_dict
        self.branch_currents = currents_dict or {}
        self.show_node_voltages = True
        self.scene.update()

    def clear_op_results(self):
        """Clear all operating point annotations."""
        self.node_voltages = {}
        self.branch_currents = {}
        self.show_node_voltages = False
        self.scene.update()

    def set_probe_mode(self, active):
        """Enable or disable probe mode."""
        self.probe_mode = active
        if active:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()
        self.scene.update()

    def clear_probes(self):
        """Remove all probe annotations."""
        self.probe_results = []
        self.scene.update()

    def _probe_at_position(self, scene_pos):
        """Probe the node or component at scene_pos and store result."""
        # Check if we clicked on a component first
        item = self.itemAt(self.mapFromScene(scene_pos))
        if isinstance(item, ComponentGraphicsItem):
            if self.node_voltages:
                return self._probe_component(item)
            # No OP data - request sweep probe for this component
            comp_ref = item.component_id.lower()
            self.probeRequested.emit(comp_ref, "component")
            return None

        # Otherwise try to find a node near the click
        node = self.find_node_at_position(scene_pos)
        if node:
            if self.node_voltages:
                return self._probe_node(node)
            # No OP data - request sweep probe for this node
            self.probeRequested.emit(node.get_label(), "node")
            return None

        return None

    def _probe_node(self, node):
        """Create a probe result for a node."""
        from PyQt6.QtCore import QPointF
        from simulation.result_parser import format_si

        label = node.get_label()
        if label not in self.node_voltages:
            return None

        voltage = self.node_voltages[label]
        pos = node.get_position(self.components)
        if not pos:
            return None

        result = {
            "type": "node",
            "label": label,
            "voltage": format_si(voltage, "V"),
            "pos": QPointF(pos.x(), pos.y()),
        }
        self.probe_results.append(result)
        self.scene.update()
        return result

    def _probe_component(self, comp_item):
        """Create a probe result for a component."""
        from PyQt6.QtCore import QPointF
        from simulation.result_parser import format_si

        comp_id = comp_item.component_id
        comp_ref = comp_id.lower()

        lines = [comp_id]

        # Voltage across terminals
        term_voltages = []
        for term_idx in range(len(comp_item.terminals)):
            terminal_key = (comp_id, term_idx)
            node = self.terminal_to_node.get(terminal_key)
            if node:
                node_label = node.get_label()
                if node_label in self.node_voltages:
                    v = self.node_voltages[node_label]
                    term_voltages.append((term_idx, node_label, v))

        if len(term_voltages) >= 2:
            v_across = term_voltages[0][2] - term_voltages[1][2]
            lines.append(f"V: {format_si(v_across, 'V')}")
        elif len(term_voltages) == 1:
            lines.append(f"V({term_voltages[0][1]}): {format_si(term_voltages[0][2], 'V')}")

        # Branch current
        if comp_ref in self.branch_currents:
            current = self.branch_currents[comp_ref]
            lines.append(f"I: {format_si(current, 'A')}")

        # Power dissipation (if both voltage and current known)
        if len(term_voltages) >= 2 and comp_ref in self.branch_currents:
            v_across = term_voltages[0][2] - term_voltages[1][2]
            power = abs(v_across * self.branch_currents[comp_ref])
            lines.append(f"P: {format_si(power, 'W')}")

        comp_rect = comp_item.boundingRect()
        center = comp_item.mapToScene(comp_rect.center())
        result = {
            "type": "component",
            "label": comp_id,
            "text": "\n".join(lines),
            "pos": QPointF(center.x() + comp_rect.width() / 2 + 10, center.y()),
        }
        self.probe_results.append(result)
        self.scene.update()
        return result

    def display_node_voltages(self):
        """Enable display of node voltages."""
        self.show_node_voltages = True
        self.scene.update()

    def hide_node_voltages(self):
        """Disable display of node voltages."""
        self.show_node_voltages = False
        self.scene.update()

    def find_node_at_position(self, scene_pos):
        """Find a node near the given scene position"""
        for comp_id, comp in self.components.items():
            for term_idx in range(len(comp.terminals)):
                term_pos = comp.get_terminal_pos(term_idx)
                distance = (term_pos - scene_pos).manhattanLength()
                if distance < 20:
                    terminal_key = (comp_id, term_idx)
                    return self.terminal_to_node.get(terminal_key)
        return None

    def label_node(self, node):
        """Open dialog to set a net name for a node."""
        if node is None:
            return

        current_label = node.custom_label if node.custom_label else ""

        text, ok = QInputDialog.getText(
            None,
            "Set Net Name",
            f"Enter a net name for this node (e.g. Vout, Vcc).\nCurrent: {node.get_label()}",
            QLineEdit.EchoMode.Normal,
            current_label,
        )

        if ok:
            new_label = text.strip() if text else None
            # Use public controller API to set net name and notify observers
            if self.controller:
                self.controller.set_net_name(node, new_label)
            else:
                node.set_custom_label(new_label)
            self.scene.update()
            viewPort = self.viewport()
            if viewPort is None:
                logger.warning("Viewport is None, cannot update after node label change")
            else:
                viewPort.update()

    def is_terminal_available(self, component, terminal_index):
        """Check if a terminal can accept a new wire connection.

        Multi-wire terminals are allowed (junctions are valid in SPICE).
        However, duplicate wires between the exact same terminal pair are
        rejected — this is checked when completing the wire, not when
        starting it.  When starting a wire, any terminal is valid.
        """
        if self.wire_start_comp is None:
            # Starting a wire — any terminal is valid
            return True

        # Completing a wire — check for duplicate wire
        start_id = self.wire_start_comp.component_id
        start_term = self.wire_start_term
        end_id = component.component_id
        end_term = terminal_index

        for wire in self.wires:
            same_fwd = (
                wire.model.start_component_id == start_id
                and wire.model.start_terminal == start_term
                and wire.model.end_component_id == end_id
                and wire.model.end_terminal == end_term
            )
            same_rev = (
                wire.model.start_component_id == end_id
                and wire.model.start_terminal == end_term
                and wire.model.end_component_id == start_id
                and wire.model.end_terminal == start_term
            )
            if same_fwd or same_rev:
                logger.info(
                    "Duplicate wire rejected: %s[%s] -> %s[%s]",
                    start_id,
                    start_term,
                    end_id,
                    end_term,
                )
                main_window = self.window() if hasattr(self, "window") else None
                if main_window and hasattr(main_window, "statusBar"):
                    status = main_window.statusBar()
                    if status:
                        status.showMessage("Wire already exists between these terminals", 3000)
                return False

        return True

    def handle_ground_added(self, ground_comp):
        """Handle adding a ground component"""
        terminal_key = (ground_comp.component_id, 0)

        ground_node = None
        for node in self.nodes:
            if node.is_ground:
                ground_node = node
                break

        if ground_node is None:
            ground_node = Node(is_ground=True)
            self.nodes.append(ground_node)

        ground_node.add_terminal(ground_comp.component_id, 0)
        self.terminal_to_node[terminal_key] = ground_node

    def update_nodes_for_wire(self, wire):
        """Update node connectivity when a wire is added"""
        start_terminal = (wire.start_comp.component_id, wire.start_term)
        end_terminal = (wire.end_comp.component_id, wire.end_term)

        start_node = self.terminal_to_node.get(start_terminal)
        end_node = self.terminal_to_node.get(end_terminal)

        if start_node is None and end_node is None:
            new_node = Node()
            new_node.add_terminal(*start_terminal)
            new_node.add_terminal(*end_terminal)
            new_node.add_wire(wire)
            wire.node = new_node

            self.nodes.append(new_node)
            self.terminal_to_node[start_terminal] = new_node
            self.terminal_to_node[end_terminal] = new_node

            if wire.start_comp.component_type == "Ground" or wire.end_comp.component_type == "Ground":
                new_node.set_as_ground()

        elif start_node is None and end_node is not None:
            end_node.add_terminal(*start_terminal)
            end_node.add_wire(wire)
            wire.node = end_node
            self.terminal_to_node[start_terminal] = end_node

            if wire.start_comp.component_type == "Ground":
                end_node.set_as_ground()

        elif end_node is None and start_node is not None:
            start_node.add_terminal(*end_terminal)
            start_node.add_wire(wire)
            wire.node = start_node
            self.terminal_to_node[end_terminal] = start_node

            if wire.end_comp.component_type == "Ground":
                start_node.set_as_ground()

        elif start_node is not None and end_node is not None and start_node != end_node:
            start_node.merge_with(end_node)
            start_node.add_wire(wire)
            wire.node = start_node

            for terminal in end_node.terminals:
                self.terminal_to_node[terminal] = start_node

            self.nodes.remove(end_node)

        self.scene.update()

    def update_nodes_after_wire_deletion(self, wire):
        """Recalculate nodes after a wire is deleted"""
        if wire.node is None:
            return

        old_node = wire.node
        old_node.remove_wire(wire)

        start_terminal = (wire.start_comp.component_id, wire.start_term)
        end_terminal = (wire.end_comp.component_id, wire.end_term)

        old_node.remove_terminal(*start_terminal)
        old_node.remove_terminal(*end_terminal)

        if old_node in self.nodes:
            self.nodes.remove(old_node)

        terminals_to_clear = list(self.terminal_to_node.keys())
        for terminal in terminals_to_clear:
            if self.terminal_to_node.get(terminal) == old_node:
                del self.terminal_to_node[terminal]

        self.rebuild_all_nodes()

        self.scene.update()

    def rebuild_all_nodes(self):
        """Rebuild all nodes from scratch based on current wires"""
        self.nodes.clear()
        self.terminal_to_node.clear()
        Node._node_counter = 0

        for comp in self.components.values():
            if comp.component_type == "Ground":
                self.handle_ground_added(comp)

        for wire in self.wires:
            wire.node = None
            self.update_nodes_for_wire(wire)

    def clear_circuit(self):
        """Clear all components, wires, and annotations"""
        self.scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.nodes = []
        self.terminal_to_node = {}
        self.annotations = []
        self.component_counter = DEFAULT_COMPONENT_COUNTER.copy()
        Node._node_counter = 0

    def toggle_obstacle_boundaries(self, show=None):
        """
        Toggle or set obstacle boundary visualization

        Args:
            show: If None, toggle; if bool, set to that value

        Returns:
            bool: New state of obstacle boundary display
        """
        if show is None:
            self.show_obstacle_boundaries = not self.show_obstacle_boundaries
            pass
        else:
            self.show_obstacle_boundaries = show

        if self.show_obstacle_boundaries:
            self.draw_obstacle_boundaries()
            pass
        else:
            self.clear_obstacle_boundaries()

        return self.show_obstacle_boundaries

    def clear_obstacle_boundaries(self):
        """Remove all obstacle boundary visualization items"""
        for item in self.obstacle_boundary_items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
        self.obstacle_boundary_items.clear()

    def draw_obstacle_boundaries(self):
        """Draw obstacle boundaries for all components"""
        # Clear existing boundary items
        self.clear_obstacle_boundaries()

        if not self.components:
            return

        # Draw custom polygon boundaries for each component
        # Shows the actual obstacle boundary matching component visual shape
        import math

        for comp in self.components.values():
            pos = comp.pos()

            # Get custom obstacle shape from component
            if hasattr(comp, "get_obstacle_shape"):
                polygon_points = comp.get_obstacle_shape()
                pass
            else:
                # Fallback to bounding rect
                rect = comp.boundingRect()
                polygon_points = [
                    (rect.left(), rect.top()),
                    (rect.right(), rect.top()),
                    (rect.right(), rect.bottom()),
                    (rect.left(), rect.bottom()),
                ]

            # Helper function to transform polygon points
            def transform_polygon(points, inset_distance=0):
                """Transform polygon points: apply inset, rotation, translation"""
                rad = math.radians(comp.rotation_angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                transformed = []
                for x, y in points:
                    # Apply inset (move toward center)
                    if inset_distance > 0:
                        center_x = sum(p[0] for p in points) / len(points)
                        center_y = sum(p[1] for p in points) / len(points)
                        dx = center_x - x
                        dy = center_y - y
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > 0:
                            x += (dx / dist) * inset_distance
                            y += (dy / dist) * inset_distance

                    # Rotate
                    rotated_x = x * cos_a - y * sin_a
                    rotated_y = x * sin_a + y * cos_a

                    # Translate
                    world_x = pos.x() + rotated_x
                    world_y = pos.y() + rotated_y

                    transformed.append((world_x, world_y))
                return transformed

            # Draw full shape (red - connected components)
            obstacle_full_pen = theme_manager.pen("obstacle_full")
            full_points = transform_polygon(polygon_points, inset_distance=0)
            for i in range(len(full_points)):
                p1 = full_points[i]
                p2 = full_points[(i + 1) % len(full_points)]
                line = self.scene.addLine(p1[0], p1[1], p2[0], p2[1], obstacle_full_pen)
                line.setZValue(50)
                self.obstacle_boundary_items.append(line)

            # Draw inset shape (blue - non-connected components)
            obstacle_inset_pen = theme_manager.pen("obstacle_inset")
            inset_pixels = 1.5 * GRID_SIZE
            inset_points = transform_polygon(polygon_points, inset_distance=inset_pixels)
            for i in range(len(inset_points)):
                p1 = inset_points[i]
                p2 = inset_points[(i + 1) % len(inset_points)]
                line = self.scene.addLine(p1[0], p1[1], p2[0], p2[1], obstacle_inset_pen)
                line.setZValue(50)
                self.obstacle_boundary_items.append(line)

            # Draw terminal markers
            terminal_pen = theme_manager.pen("terminal_marker")
            terminal_brush = theme_manager.brush("terminal_fill")
            for i in range(len(comp.terminals)):
                term_pos = comp.get_terminal_pos(i)
                terminal_circle = self.scene.addEllipse(
                    term_pos.x() - 5,
                    term_pos.y() - 5,
                    10,
                    10,
                    terminal_pen,
                    terminal_brush,
                )
                terminal_circle.setZValue(100)
                self.obstacle_boundary_items.append(terminal_circle)

        # Add legend
        legend_y = -480
        legend_x = -480
        obstacle_full_color = theme_manager.color("obstacle_full")
        obstacle_inset_color = theme_manager.color("obstacle_inset")
        terminal_color = theme_manager.color("terminal_highlight")

        # Full boundary legend (red solid frame)
        full_legend_rect = self.scene.addRect(
            legend_x,
            legend_y,
            30,
            15,
            theme_manager.pen("obstacle_full"),
            QBrush(Qt.BrushStyle.NoBrush),
        )
        full_legend_rect.setZValue(1000)
        self.obstacle_boundary_items.append(full_legend_rect)

        full_legend_text = self.scene.addText("Custom Shape (Connected)")
        full_legend_text.setPos(legend_x + 35, legend_y - 5)
        full_legend_text.setDefaultTextColor(obstacle_full_color)
        full_legend_text.setZValue(1000)
        self.obstacle_boundary_items.append(full_legend_text)

        # Inset boundary legend (blue dotted frame)
        inset_legend_rect = self.scene.addRect(
            legend_x,
            legend_y + 25,
            30,
            15,
            theme_manager.pen("obstacle_inset"),
            QBrush(Qt.BrushStyle.NoBrush),
        )
        inset_legend_rect.setZValue(1000)
        self.obstacle_boundary_items.append(inset_legend_rect)

        inset_legend_text = self.scene.addText("Custom Shape (Inset)")
        inset_legend_text.setPos(legend_x + 35, legend_y + 20)
        inset_legend_text.setDefaultTextColor(obstacle_inset_color)
        inset_legend_text.setZValue(1000)
        self.obstacle_boundary_items.append(inset_legend_text)

        # Terminal legend
        terminal_legend_circle = self.scene.addEllipse(
            legend_x + 7.5,
            legend_y + 52.5,
            10,
            10,
            theme_manager.pen("terminal_marker"),
            theme_manager.brush("terminal_fill"),
        )
        terminal_legend_circle.setZValue(1000)
        self.obstacle_boundary_items.append(terminal_legend_circle)

        terminal_legend_text = self.scene.addText("Terminals (Active=Clear, Inactive=Obstacle)")
        terminal_legend_text.setPos(legend_x + 35, legend_y + 45)
        terminal_legend_text.setDefaultTextColor(terminal_color)
        terminal_legend_text.setZValue(1000)
        self.obstacle_boundary_items.append(terminal_legend_text)

    def get_model_components(self):
        """Return dict of component_id -> ComponentData for simulation use."""
        for comp_item in self.components.values():
            comp_item.model.position = (comp_item.pos().x(), comp_item.pos().y())
        return {comp_id: comp_item.model for comp_id, comp_item in self.components.items()}

    def get_model_wires(self):
        """Return list of WireData for simulation use."""
        from models.wire import WireData

        return [
            WireData(
                start_component_id=wire.start_comp.component_id,
                start_terminal=wire.start_term,
                end_component_id=wire.end_comp.component_id,
                end_terminal=wire.end_term,
            )
            for wire in self.wires
        ]

    def get_model_nodes_and_terminal_map(self):
        """Return (list of NodeData, terminal_to_node dict) for simulation use.

        The terminal_to_node dict maps (comp_id, term_idx) -> NodeData,
        sharing the same NodeData objects as the returned list.
        """
        from models.node import NodeData

        qt_to_model = {}  # id(Qt Node) -> NodeData
        node_data_list = []
        for node in self.nodes:
            nd = NodeData(
                terminals=set(node.terminals),
                is_ground=node.is_ground,
                custom_label=node.custom_label,
                auto_label=node.auto_label,
            )
            qt_to_model[id(node)] = nd
            node_data_list.append(nd)

        terminal_to_node = {}
        for key, qt_node in self.terminal_to_node.items():
            nd = qt_to_model.get(id(qt_node))
            if nd is not None:
                terminal_to_node[key] = nd

        return node_data_list, terminal_to_node

    def export_image(self, filepath, include_grid=True):
        """Export the circuit scene to an image file (PNG or SVG).

        Args:
            filepath: Output file path. Extension determines format (.svg or .png).
            include_grid: Whether to include grid lines in the export.
        """
        # Hide grid items if requested
        if not include_grid:
            for item in self._grid_items:
                item.setVisible(False)

        # Calculate bounding rect of circuit items (components + wires)
        circuit_items = list(self.components.values()) + self.wires
        if circuit_items:
            rect = circuit_items[0].sceneBoundingRect()
            for item in circuit_items[1:]:
                rect = rect.united(item.sceneBoundingRect())
            rect.adjust(-ZOOM_FIT_PADDING, -ZOOM_FIT_PADDING, ZOOM_FIT_PADDING, ZOOM_FIT_PADDING)
        else:
            rect = self.scene.sceneRect()

        try:
            if filepath.lower().endswith(".svg"):
                self._export_svg(filepath, rect)
            else:
                self._export_png(filepath, rect)
        finally:
            # Restore grid visibility
            if not include_grid:
                for item in self._grid_items:
                    item.setVisible(True)

    def _export_png(self, filepath, source_rect):
        """Render the scene to a PNG file at 2x resolution."""
        from PyQt6.QtGui import QImage, QPainter

        scale = 2
        width = int(source_rect.width() * scale)
        height = int(source_rect.height() * scale)

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.scene.render(painter, QRectF(0, 0, width, height), source_rect)
        painter.end()

        image.save(filepath)

    def _export_svg(self, filepath, source_rect):
        """Render the scene to an SVG file."""
        from PyQt6.QtCore import QRect, QSize
        from PyQt6.QtGui import QPainter
        from PyQt6.QtSvg import QSvgGenerator

        width = int(source_rect.width())
        height = int(source_rect.height())

        svg = QSvgGenerator()
        svg.setFileName(filepath)
        svg.setSize(QSize(width, height))
        svg.setViewBox(QRect(0, 0, width, height))
        svg.setTitle("Circuit Diagram")

        painter = QPainter()
        painter.begin(svg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(painter, QRectF(0, 0, width, height), source_rect)
        painter.end()

    def to_dict(self):
        """Serialize circuit to dictionary"""
        data = {
            "components": [comp.to_dict() for comp in self.components.values()],
            "wires": [wire.to_dict() for wire in self.wires],
            "counters": self.component_counter.copy(),
        }
        if self.annotations:
            data["annotations"] = [ann.to_dict() for ann in self.annotations]
        return data

    @staticmethod
    def _validate_circuit_data(data):
        """Validate JSON structure before loading. Raises ValueError on problems."""
        if not isinstance(data, dict):
            raise ValueError("File does not contain a valid circuit object.")

        if "components" not in data or not isinstance(data["components"], list):
            raise ValueError("Missing or invalid 'components' list.")
        if "wires" not in data or not isinstance(data["wires"], list):
            raise ValueError("Missing or invalid 'wires' list.")

        comp_ids = set()
        for i, comp in enumerate(data["components"]):
            for key in ("id", "type", "value", "pos"):
                if key not in comp:
                    raise ValueError(f"Component #{i + 1} is missing required field '{key}'.")
            pos = comp["pos"]
            if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
                raise ValueError(f"Component '{comp.get('id', i)}' has invalid position data.")
            if not isinstance(pos["x"], (int, float)) or not isinstance(pos["y"], (int, float)):
                raise ValueError(f"Component '{comp['id']}' position values must be numeric.")
            comp_ids.add(comp["id"])

        for i, wire in enumerate(data["wires"]):
            for key in ("start_comp", "end_comp", "start_term", "end_term"):
                if key not in wire:
                    raise ValueError(f"Wire #{i + 1} is missing required field '{key}'.")
            if wire["start_comp"] not in comp_ids:
                raise ValueError(f"Wire #{i + 1} references unknown component '{wire['start_comp']}'.")
            if wire["end_comp"] not in comp_ids:
                raise ValueError(f"Wire #{i + 1} references unknown component '{wire['end_comp']}'.")

    def from_dict(self, data):
        """Deserialize circuit from dictionary"""
        self._validate_circuit_data(data)
        self.clear_circuit()

        self.component_counter = data.get("counters", self.component_counter)

        for comp_data in data["components"]:
            comp = ComponentGraphicsItem.from_dict(comp_data)
            self.scene.addItem(comp)
            self.components[comp.component_id] = comp

        for wire_data in data["wires"]:
            start_comp = self.components[wire_data["start_comp"]]
            end_comp = self.components[wire_data["end_comp"]]
            wire = WireItem(
                start_comp,
                wire_data["start_term"],
                end_comp,
                wire_data["end_term"],
                canvas=self,
            )
            self.scene.addItem(wire)
            self.wires.append(wire)

        # Load annotations
        for ann_data in data.get("annotations", []):
            ann = AnnotationItem.from_dict(ann_data)
            self.scene.addItem(ann)
            self.annotations.append(ann)

        # Rebuild node connectivity
        self.rebuild_all_nodes()

    # Phase 5: sync_to_model() and sync_from_model() methods DELETED
    # Observer pattern handles all synchronization automatically


# Backward compatibility alias
CircuitCanvas = CircuitCanvasView
