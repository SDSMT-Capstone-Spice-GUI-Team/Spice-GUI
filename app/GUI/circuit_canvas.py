import logging

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QInputDialog,
    QLineEdit,
    QRubberBand,
)

logger = logging.getLogger(__name__)
from models.clipboard import ClipboardData

from .annotation_item import AnnotationItem
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
    statusMessage = pyqtSignal(str, int)  # (message, timeout_ms) — relay for scene items

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller  # CircuitController reference for observer pattern
        self._scene = QGraphicsScene()
        if self._scene is None:
            exit()
        self.setScene(self._scene)
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

        # Probe overlay (owns probe_mode, probe_results, hit-testing)
        from GUI.canvas_probe_overlay import CanvasProbeOverlay

        self.probe_overlay = CanvasProbeOverlay(self)

        # Label visibility settings
        self.show_component_labels = True  # Toggle for component IDs (R1, V1, etc.)
        self.show_component_values = True  # Toggle for component values (1k, 5V, etc.)
        self.show_node_labels = True  # Toggle for node labels (n1, n2, etc.)

        # Grid drawing deferred to first show for faster startup
        self._grid_drawn = False
        self._grid_items = []  # Track grid lines/labels for export toggling

        # Batched wire rerouting (dedup across group drags)
        self._pending_reroute_components = set()
        self._batch_reroute_timer = None

        # Text annotations on the canvas
        self.annotations = []

        # Wire drawing mode
        self.wire_start_comp = None
        self.wire_start_term = None
        self.temp_wire_line = None  # Temporary line while drawing wire
        self._wire_waypoints: list[QPointF] = []  # In-progress waypoints (click-to-place)
        self._wire_waypoint_markers: list = []  # Visual markers for placed waypoints

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
        self._scene.selectionChanged.connect(self.on_selection_changed)

        if self.controller:
            self.controller.add_observer(self._on_model_changed)

    def showEvent(self, event):
        """Draw grid on first show for faster startup"""
        super().showEvent(event)
        if not self._grid_drawn:
            self.draw_grid()
            self._grid_drawn = True

    # ===================================================================
    # Observer Pattern
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
            "wire_lock_changed": self._handle_wire_lock_changed,
            "wire_reroute_requested": self._handle_wire_reroute_requested,
            "circuit_cleared": self._handle_circuit_cleared,
            "nodes_rebuilt": self._handle_nodes_rebuilt,
            "model_loaded": self._handle_model_loaded,
            "annotation_added": self._handle_annotation_added,
            "annotation_removed": self._handle_annotation_removed,
            "annotation_updated": self._handle_annotation_updated,
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

    def _sync_nodes_from_model(self) -> None:
        """Sync local node references from the controller's model.

        The controller's model is the single source of truth for node
        connectivity.  The canvas only keeps shallow copies for rendering
        (node labels, OP annotations, probe lookups).
        """
        if self.controller:
            self.nodes, self.terminal_to_node = self.controller.get_nodes_and_terminal_map()

    def _handle_component_added(self, component_data) -> None:
        """Create graphics item when component added to model"""
        comp = ComponentGraphicsItem.from_dict(component_data.to_dict())
        comp.canvas = self
        self._scene.addItem(comp)
        self.components[component_data.component_id] = comp

        # Model already handled ground node registration in add_component();
        # sync our local node references so rendering stays current.
        if component_data.component_type == "Ground":
            self._sync_nodes_from_model()

        self._scene.update()

    def _handle_component_removed(self, component_id: str) -> None:
        """Remove graphics item when component removed from model"""
        comp = self.components.get(component_id)
        if comp:
            self._scene.removeItem(comp)
            del self.components[component_id]
            self._scene.update()

    def _handle_component_moved(self, component_data) -> None:
        """Update graphics item position - disable change flag to prevent recursion"""
        from PyQt6.QtWidgets import QGraphicsItem

        comp = self.components.get(component_data.component_id)
        if comp:
            # Disable ItemSendsGeometryChanges to prevent infinite recursion
            comp.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
            comp.setPos(*component_data.position)
            comp.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

            # Batch reroute: collect component, defer actual rerouting
            self._pending_reroute_components.add(comp)
            self._schedule_batch_reroute()

    def _schedule_batch_reroute(self):
        """Schedule deferred batch reroute on next event loop iteration."""
        if self._batch_reroute_timer is not None:
            return  # Already scheduled
        self._batch_reroute_timer = QTimer()
        self._batch_reroute_timer.setSingleShot(True)
        self._batch_reroute_timer.timeout.connect(self._do_batch_reroute)
        self._batch_reroute_timer.start(0)  # Fire on next event loop tick

    def _do_batch_reroute(self):
        """Reroute each unique affected wire exactly once."""
        components = self._pending_reroute_components
        self._pending_reroute_components = set()
        self._batch_reroute_timer = None

        wires_to_reroute = set()
        for comp in components:
            for wire in self.wires:
                if wire.start_comp is comp or wire.end_comp is comp:
                    wires_to_reroute.add(wire)

        for wire in wires_to_reroute:
            wire.update_position()

        if wires_to_reroute:
            self._scene.update()
            if self.viewport():
                self.viewport().update()

    def _handle_component_rotated(self, component_data) -> None:
        """Update graphics item rotation from authoritative model data."""
        comp = self.components.get(component_data.component_id)
        if comp:
            comp.sync_from_data(component_data)
            comp.update_terminals()
            comp.update()
            self.reroute_connected_wires(comp)

    def _handle_component_flipped(self, component_data) -> None:
        """Update graphics item flip from authoritative model data."""
        comp = self.components.get(component_data.component_id)
        if comp:
            comp.sync_from_data(component_data)
            comp.update_terminals()
            comp.update()
            self.reroute_connected_wires(comp)

    def _handle_component_value_changed(self, component_data) -> None:
        """Update graphics item value display from authoritative model data."""
        comp = self.components.get(component_data.component_id)
        if comp:
            comp.sync_from_data(component_data)
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
            self._scene.addItem(wire)
            self.wires.append(wire)
            # Model already updated its node graph in add_wire(); sync here.
            self._sync_nodes_from_model()

    def _handle_wire_removed(self, wire_index: int) -> None:
        """Remove wire graphics item and reroute neighboring wires."""
        if 0 <= wire_index < len(self.wires):
            wire = self.wires[wire_index]
            # Save connected components before removing, so we can reroute neighbors
            affected_components = {wire.start_comp, wire.end_comp}
            self._scene.removeItem(wire)
            del self.wires[wire_index]
            # Model already rebuilt affected nodes in remove_wire(); sync here.
            self._sync_nodes_from_model()
            # Reroute remaining wires connected to the same components —
            # they may have been routed around the now-deleted wire.
            self._reroute_wires_near_components(affected_components)
            # Force full repaint so foreground node labels/dots are refreshed.
            # Without this, stale node annotations remain as ghost artifacts
            # when the deleted wire's node is removed from the model.
            self._scene.update()

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

    def _handle_wire_lock_changed(self, data) -> None:
        """Update wire visual when lock state changes."""
        wire_index, wire = data
        if 0 <= wire_index < len(self.wires):
            self.wires[wire_index].update()

    def _handle_wire_reroute_requested(self, wire_index) -> None:
        """Force fresh pathfinding on a wire."""
        if 0 <= wire_index < len(self.wires):
            wire = self.wires[wire_index]
            wire.update_position()
            # Sync the new waypoints back through controller
            waypoints = [(wp.x(), wp.y()) for wp in wire.waypoints]
            self.controller.update_wire_waypoints(wire_index, waypoints)

    # ===================================================================
    # Scene item callbacks (avoid hierarchy climbing in items)
    # ===================================================================

    def on_routing_failed(self, message: str) -> None:
        """Relay a routing-failure message from a wire item to the UI."""
        self.statusMessage.emit(message, 5000)

    def on_wire_waypoints_changed(self, wire_item, waypoints=None) -> None:
        """Handle manual waypoint adjustment from a wire item."""
        if self.controller and wire_item in self.wires:
            idx = self.wires.index(wire_item)
            wps = waypoints if waypoints is not None else wire_item.model.waypoints
            self.controller.update_wire_waypoints(idx, wps)
            self.controller.set_wire_locked(idx, True)

    def on_wire_routing_complete(self, wire_item, waypoints, runtime=0.0, iterations=0, routing_failed=False):
        """Persist pathfinding results from a wire item through the controller."""
        if self.controller and wire_item in self.wires:
            idx = self.wires.index(wire_item)
            self.controller.update_wire_routing_result(idx, waypoints, runtime, iterations, routing_failed)
        else:
            # Construction-time initialisation: wire not yet registered with
            # the controller, so we populate the model as part of object setup.
            # Once the wire enters controller.add_wire() this path is never hit.
            wire_item.model.waypoints = waypoints
            wire_item.model.runtime = runtime
            wire_item.model.iterations = iterations
            wire_item.model.routing_failed = routing_failed

    def _handle_annotation_added(self, annotation_data) -> None:
        """Create AnnotationItem when annotation added to model."""
        ann = AnnotationItem(
            text=annotation_data.text,
            x=annotation_data.x,
            y=annotation_data.y,
            font_size=annotation_data.font_size,
            bold=annotation_data.bold,
            color=annotation_data.color,
        )
        ann.canvas = self
        self._scene.addItem(ann)
        self.annotations.append(ann)
        self._scene.update()

    def _handle_annotation_removed(self, index: int) -> None:
        """Remove AnnotationItem when annotation removed from model."""
        if 0 <= index < len(self.annotations):
            ann = self.annotations.pop(index)
            self._scene.removeItem(ann)
            self._scene.update()

    def _handle_annotation_updated(self, annotation_data) -> None:
        """Update AnnotationItem text when annotation updated in model."""
        # Find matching annotation by identity in controller's list
        idx = None
        for i, ann_data in enumerate(self.controller.get_annotations()):
            if ann_data is annotation_data:
                idx = i
                break
        if idx is not None and idx < len(self.annotations):
            self.annotations[idx].setPlainText(annotation_data.text)
            self._scene.update()

    def _handle_circuit_cleared(self, data: None) -> None:
        """Clear all graphics items when circuit cleared"""
        self._scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.annotations = []
        # Model already cleared its node graph; sync here.
        self._sync_nodes_from_model()

    def _handle_nodes_rebuilt(self, data: None) -> None:
        """Rebuild node visualization from model"""
        self._sync_nodes_from_model()
        self._scene.update()

    def _handle_model_loaded(self, data: None) -> None:
        """Rebuild entire canvas when model loaded from file"""
        if not self.controller:
            return

        # Clear and rebuild everything
        self._scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.annotations = []

        # Restore components
        for comp_data in self.controller.get_components().values():
            self._handle_component_added(comp_data)

        # Restore wires
        for wire_data in self.controller.get_wires():
            self._handle_wire_added(wire_data)

        # Rebuild nodes
        self._handle_nodes_rebuilt(None)

        # Restore annotations
        for ann_data in self.controller.get_annotations():
            self._handle_annotation_added(ann_data)

        # Restore component counter
        self.component_counter = self.controller.get_component_counter()

    # ===================================================================
    # End Observer Pattern Handlers
    # ===================================================================

    def refresh_theme(self):
        """Redraw grid and repaint all items to reflect the current theme."""
        if self._scene is None:
            return
        # Set scene background
        bg = theme_manager.color("background_primary")
        self._scene.setBackgroundBrush(QBrush(bg))

        # Remove old grid items and redraw
        for item in self._grid_items:
            self._scene.removeItem(item)
        self._grid_items.clear()
        self.draw_grid()

        # Update all wire pens with current theme color
        default_wire_color = theme_manager.color("wire_default")
        for wire in self.wires:
            wire.layer_color = default_wire_color
            if not wire.isSelected():
                wire.setPen(QPen(default_wire_color, 2))

        # Force full repaint of all items (components pick up theme in paint())
        self._scene.update()

    def draw_grid(self):
        """Draw background grid with major grid lines labeled with position values"""
        if self._scene is None:
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
            line = self._scene.addLine(x, -GRID_EXTENT, x, GRID_EXTENT, pen)
            line.setZValue(-1)
            self._grid_items.append(line)

            # Add label for major grid lines
            if is_major:
                label = QGraphicsTextItem(str(x))
                label.setDefaultTextColor(grid_label_color)
                label.setFont(grid_label_font)
                label.setPos(x - 15, -GRID_EXTENT)  # Position at top
                label.setZValue(-1)  # Draw behind components
                self._scene.addItem(label)
                self._grid_items.append(label)

        # Draw horizontal lines
        for y in range(-GRID_EXTENT, GRID_EXTENT + 1, GRID_SIZE):
            is_major = y % MAJOR_GRID_INTERVAL == 0
            pen = major_pen if is_major else minor_pen
            line = self._scene.addLine(-GRID_EXTENT, y, GRID_EXTENT, y, pen)
            line.setZValue(-1)
            self._grid_items.append(line)

            # Add label for major grid lines
            if is_major:
                label = QGraphicsTextItem(str(y))
                label.setDefaultTextColor(grid_label_color)
                label.setFont(grid_label_font)
                label.setPos(-GRID_EXTENT, y - 10)  # Position at left
                label.setZValue(-1)  # Draw behind components
                self._scene.addItem(label)
                self._grid_items.append(label)

    def reroute_connected_wires(self, component):
        """Reroute all wires connected to a component.

        For wires where both endpoints are selected (co-selected group drag),
        only the endpoint with the lower component_id triggers the reroute.
        This prevents the same wire being rerouted twice per drag event.
        """
        wire_count = 0
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                # Skip locked wires (user pinned the path)
                if wire.model.locked:
                    continue
                # Skip if both endpoints are co-selected and the other has lower ID
                # (that endpoint's reroute call will handle this wire)
                other = wire.end_comp if wire.start_comp == component else wire.start_comp
                if component.isSelected() and other.isSelected() and other.component_id < component.component_id:
                    continue
                wire.update_position()
                wire_count += 1

        # Force a full scene update to ensure wires are redrawn
        if wire_count > 0:
            self._scene.update()
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

    def _reroute_wires_near_components(self, components):
        """Reroute remaining wires connected to any of the given components.

        Called after wire deletion so that neighboring wires can find
        shorter paths now that the deleted wire is no longer an obstacle.
        """
        rerouted = 0
        for wire in self.wires:
            if wire.start_comp in components or wire.end_comp in components:
                if wire.model.locked:
                    continue
                wire.update_position()
                rerouted += 1
        if rerouted > 0:
            self._scene.update()

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
        """Handle component drop from palette."""
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

            from controllers.commands import AddComponentCommand

            cmd = AddComponentCommand(self.controller, component_type, (grid_x, grid_y))
            self.controller.execute_command(cmd)
            if cmd.component_id:
                self.componentAdded.emit(cmd.component_id)

            event.acceptProposedAction()

    def add_component_at_center(self, component_type):
        """Add a component at the center of the visible canvas area."""
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

        from controllers.commands import AddComponentCommand

        cmd = AddComponentCommand(self.controller, component_type, (grid_x, grid_y))
        self.controller.execute_command(cmd)
        if cmd.component_id:
            self.componentAdded.emit(cmd.component_id)

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
                        status.showMessage(
                            "No simulation results available. Run a simulation first.",
                            3000,
                        )
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
                        self._scene.addItem(self.temp_wire_line)

                        # Show crosshair cursor while drawing a wire
                        self.setCursor(Qt.CursorShape.CrossCursor)

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
                                # Build manual waypoints if the user clicked intermediate points
                                manual_wps = None
                                if self._wire_waypoints:
                                    start_pos = self.wire_start_comp.get_terminal_pos(self.wire_start_term)
                                    end_pos = clicked_component.get_terminal_pos(target_term)
                                    manual_wps = (
                                        [(start_pos.x(), start_pos.y())]
                                        + [(wp.x(), wp.y()) for wp in self._wire_waypoints]
                                        + [(end_pos.x(), end_pos.y())]
                                    )

                                from controllers.commands import AddWireCommand

                                cmd = AddWireCommand(
                                    self.controller,
                                    self.wire_start_comp.component_id,
                                    self.wire_start_term,
                                    clicked_component.component_id,
                                    target_term,
                                    waypoints=manual_wps,
                                )
                                self.controller.execute_command(cmd)
                                self.wireAdded.emit(
                                    self.wire_start_comp.component_id,
                                    clicked_component.component_id,
                                )
                            else:
                                # Fallback to old method if no controller (shouldn't happen)
                                logger.warning("Wire created without controller — node graph may be stale")
                                wire = WireItem(
                                    self.wire_start_comp,
                                    self.wire_start_term,
                                    clicked_component,
                                    target_term,
                                    canvas=self,
                                    algorithm="idastar",
                                )
                                self._scene.addItem(wire)
                                self.wires.append(wire)
                                self.wireAdded.emit(
                                    self.wire_start_comp.component_id,
                                    clicked_component.component_id,
                                )

                    # Clean up temporary wire line
                    self.cancel_wire_drawing()

                    # Wire completed, allow normal behavior to continue
                    # Don't accept - let event propagate for other handling

            # If we're in wire drawing mode but clicked elsewhere, place a waypoint
            elif self.wire_start_comp is not None:
                snapped = QPointF(
                    round(scene_pos.x() / GRID_SIZE) * GRID_SIZE,
                    round(scene_pos.y() / GRID_SIZE) * GRID_SIZE,
                )
                self._wire_waypoints.append(snapped)
                self._add_waypoint_marker(snapped)
                event.accept()
                return

            # If we didn't click a terminal, check if we clicked an empty area
            else:
                item = self.itemAt(event.position().toPoint())
                if item is None:
                    self.canvasClicked.emit()
                    # Start rubber band selection on empty space
                    if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                        self._scene.clearSelection()
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
            # Update temporary wire to follow mouse from last waypoint (or start terminal)
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            if self._wire_waypoints:
                anchor = self._wire_waypoints[-1]
            else:
                anchor = self.wire_start_comp.get_terminal_pos(self.wire_start_term)
            self.temp_wire_line.setLine(anchor.x(), anchor.y(), scene_pos.x(), scene_pos.y())
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
            for item in self._scene.items(scene_rect, Qt.ItemSelectionMode.IntersectsItemShape):
                if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem)):
                    item.setSelected(True)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def cancel_wire_drawing(self):
        """Cancel any in-progress wire drawing and clean up the preview line."""
        was_drawing = self.wire_start_comp is not None
        if self.temp_wire_line:
            self._scene.removeItem(self.temp_wire_line)
            self.temp_wire_line = None
        self.wire_start_comp = None
        self.wire_start_term = None
        self._wire_waypoints.clear()
        self._remove_waypoint_markers()
        # Restore default cursor when wire drawing ends
        if was_drawing:
            self.unsetCursor()

    def _add_waypoint_marker(self, pos: QPointF):
        """Draw a small dot at a placed waypoint during wire drawing."""
        from PyQt6.QtWidgets import QGraphicsEllipseItem

        r = 4
        marker = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
        marker.setPos(pos)
        marker.setBrush(QBrush(theme_manager.color("wire_preview")))
        marker.setPen(QPen(Qt.PenStyle.NoPen))
        marker.setZValue(101)
        self._scene.addItem(marker)
        self._wire_waypoint_markers.append(marker)

    def _remove_waypoint_markers(self):
        """Remove all placed-waypoint visual markers."""
        for marker in self._wire_waypoint_markers:
            self._scene.removeItem(marker)
        self._wire_waypoint_markers.clear()

    def focusOutEvent(self, event):
        """Cancel wire drawing when the canvas loses focus (e.g. modal dialog opens)."""
        self.cancel_wire_drawing()
        super().focusOutEvent(event)

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
                self.cancel_wire_drawing()
                event.accept()
                return
            # Deselect all if not wiring
            self._scene.clearSelection()
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

    def set_default_zoom(self, percent):
        """Set the zoom level to the given percentage (e.g. 100 = 100%).

        Used to apply the user's preferred default zoom level when
        opening a new circuit or launching the application.
        """
        scale_factor = percent / 100.0
        # Clamp to allowed zoom range
        scale_factor = max(ZOOM_MIN, min(ZOOM_MAX, scale_factor))
        self.resetTransform()
        self.scale(scale_factor, scale_factor)
        self.zoomChanged.emit(self.get_zoom_level())

    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.resetTransform()
        self.zoomChanged.emit(1.0)

    def zoom_fit(self):
        """Fit all circuit components in view with padding."""
        items = [item for item in self._scene.items() if isinstance(item, ComponentGraphicsItem)]
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
        """Show context menu for the item under *position*."""
        from GUI.canvas_context_menu import build_context_menu

        menu = build_context_menu(self, self.mapToScene(position))
        if not menu.isEmpty():
            menu.exec(self.mapToGlobal(position))

    def delete_selected(self):
        """Delete all selected items as a single undoable operation."""
        selected_items = self._scene.selectedItems()
        if not selected_items:
            return
        if not self.controller:
            return

        from controllers.commands import (
            CompoundCommand,
            DeleteAnnotationCommand,
            DeleteComponentCommand,
            DeleteWireCommand,
        )

        components_to_delete = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]
        wires_to_delete = [item for item in selected_items if isinstance(item, WireItem)]
        annotations_to_delete = [item for item in selected_items if isinstance(item, AnnotationItem)]

        # Collect component IDs being deleted so we skip their cascaded wires
        deleting_comp_ids = {comp.component_id for comp in components_to_delete}

        commands = []

        # Collect standalone wire indices (skip wires that will cascade from component deletion)
        wire_indices = []
        for wire in wires_to_delete:
            if wire in self.wires:
                wire_model = self.controller.model.wires[self.wires.index(wire)]
                if (
                    wire_model.start_component_id in deleting_comp_ids
                    or wire_model.end_component_id in deleting_comp_ids
                ):
                    continue  # Will be cascade-deleted with the component
                wire_indices.append(self.wires.index(wire))

        # Sort wire indices descending so higher indices are deleted first,
        # preventing earlier deletions from shifting later indices (#821)
        for idx in sorted(wire_indices, reverse=True):
            commands.append(DeleteWireCommand(self.controller, idx))

        for comp in components_to_delete:
            commands.append(DeleteComponentCommand(self.controller, comp.component_id))

        # Sort annotation indices descending for the same reason
        ann_indices = []
        for ann in annotations_to_delete:
            if ann in self.annotations:
                ann_indices.append(self.annotations.index(ann))
        for idx in sorted(ann_indices, reverse=True):
            commands.append(DeleteAnnotationCommand(self.controller, idx))

        if len(commands) == 1:
            self.controller.execute_command(commands[0])
        elif commands:
            compound = CompoundCommand(commands, f"Delete {len(commands)} items")
            self.controller.execute_command(compound)

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

    def toggle_wire_lock(self, wire, locked):
        """Lock or unlock a wire's path via undo/redo command."""
        if wire is None:
            return
        if not self.controller:
            logger.warning("Cannot toggle wire lock: no controller available")
            return
        if wire not in self.wires:
            return

        from controllers.commands import ToggleWireLockCommand

        wire_index = self.wires.index(wire)
        cmd = ToggleWireLockCommand(self.controller, wire_index, locked)
        self.controller.execute_command(cmd)

    def reroute_wire(self, wire):
        """Reroute a single wire via undo/redo command."""
        if wire is None:
            return
        if not self.controller:
            logger.warning("Cannot reroute wire: no controller available")
            return
        if wire not in self.wires:
            return

        from controllers.commands import RerouteWireCommand

        wire_index = self.wires.index(wire)
        cmd = RerouteWireCommand(self.controller, wire_index)
        self.controller.execute_command(cmd)

    def reroute_selected_wires(self, selected_wires):
        """Reroute multiple selected wires as a single undoable operation."""
        if not self.controller:
            logger.warning("Cannot reroute wires: no controller available")
            return

        from controllers.commands import CompoundCommand, RerouteWireCommand

        commands = []
        for wire in selected_wires:
            if wire in self.wires:
                wire_index = self.wires.index(wire)
                commands.append(RerouteWireCommand(self.controller, wire_index))

        if commands:
            compound = CompoundCommand(commands, f"Reroute {len(commands)} wires")
            self.controller.execute_command(compound)

    def rotate_component(self, component, clockwise=True):
        """Rotate a single component via undo/redo command."""
        if component is None or not isinstance(component, ComponentGraphicsItem):
            return
        if not self.controller:
            logger.warning("Cannot rotate component: no controller available")
            return

        from controllers.commands import RotateComponentCommand

        cmd = RotateComponentCommand(self.controller, component.component_id, clockwise)
        self.controller.execute_command(cmd)

    def rotate_selected(self, clockwise=True):
        """Rotate all selected components as a single undoable operation."""
        if not self.controller:
            return
        selected_items = self._scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]
        if not components:
            return

        from controllers.commands import CompoundCommand, RotateComponentCommand

        commands = [RotateComponentCommand(self.controller, comp.component_id, clockwise) for comp in components]
        if len(commands) == 1:
            self.controller.execute_command(commands[0])
        else:
            compound = CompoundCommand(commands, f"Rotate {len(commands)} components")
            self.controller.execute_command(compound)

    def flip_component(self, component, horizontal=True):
        """Flip a single component via undo/redo command."""
        if component is None or not isinstance(component, ComponentGraphicsItem):
            return
        if not self.controller:
            logger.warning("Cannot flip component: no controller available")
            return

        from controllers.commands import FlipComponentCommand

        cmd = FlipComponentCommand(self.controller, component.component_id, horizontal)
        self.controller.execute_command(cmd)

    def flip_selected(self, horizontal=True):
        """Flip all selected components as a single undoable operation."""
        if not self.controller:
            return
        selected_items = self._scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]
        if not components:
            return

        from controllers.commands import CompoundCommand, FlipComponentCommand

        commands = [FlipComponentCommand(self.controller, comp.component_id, horizontal) for comp in components]
        if len(commands) == 1:
            self.controller.execute_command(commands[0])
        else:
            compound = CompoundCommand(commands, f"Flip {len(commands)} components")
            self.controller.execute_command(compound)

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
            if self.controller:
                from controllers.commands import AddAnnotationCommand
                from models.annotation import AnnotationData

                ann_data = AnnotationData(text=text, x=x, y=y)
                cmd = AddAnnotationCommand(self.controller, ann_data)
                self.controller.execute_command(cmd)
            else:
                ann = AnnotationItem(text=text, x=x, y=y)
                self._scene.addItem(ann)
                self.annotations.append(ann)

    def _delete_annotation(self, ann):
        """Remove an annotation from the canvas via undo-able command."""
        if self.controller and ann in self.annotations:
            from controllers.commands import DeleteAnnotationCommand

            index = self.annotations.index(ann)
            cmd = DeleteAnnotationCommand(self.controller, index)
            self.controller.execute_command(cmd)
        else:
            self._scene.removeItem(ann)
            if ann in self.annotations:
                self.annotations.remove(ann)

    def _edit_annotation(self, ann):
        """Edit an annotation's text via undo-able command."""
        old_text = ann.toPlainText()
        text, ok = QInputDialog.getText(None, "Edit Annotation", "Text:", text=old_text)
        if ok and text and text != old_text:
            if self.controller and ann in self.annotations:
                from controllers.commands import EditAnnotationCommand

                index = self.annotations.index(ann)
                cmd = EditAnnotationCommand(self.controller, index, text)
                self.controller.execute_command(cmd)
            else:
                ann.setPlainText(text)

    def select_all(self):
        """Select all components and wires on the canvas."""
        for item in self._scene.items():
            if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem)):
                item.setSelected(True)

    def on_selection_changed(self):
        """Handle selection changes in the scene"""
        selected_items = self._scene.selectedItems()
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
        return [item.component_id for item in self._scene.selectedItems() if isinstance(item, ComponentGraphicsItem)]

    def copy_selected_components(self, component_ids: list[str]) -> bool:
        """Copy selected components and internal wires to clipboard.

        Delegates to the controller so model and view clipboards stay in sync.
        """
        if not component_ids:
            return False

        if self.controller:
            copied = self.controller.copy_components(component_ids)
        else:
            copied = False

        if copied:
            main_window = self.window()
            if main_window and hasattr(main_window, "statusBar"):
                status = main_window.statusBar()
                if status:
                    n = len(component_ids)
                    status.showMessage(f"Copied {n} component{'s' if n != 1 else ''}", 2000)

        return copied

    def cut_selected_components(self, component_ids: list[str]) -> bool:
        """Cut: copy to clipboard, then delete originals via controller."""
        copied = self.copy_selected_components(component_ids)
        if copied:
            for comp_id in list(component_ids):
                comp_item = self.components.get(comp_id)
                if comp_item is not None:
                    self.delete_component(comp_item)
        return copied

    def paste_components(self) -> None:
        """Paste clipboard contents with offset and new IDs.

        Delegates to the controller so that the model (including node
        graph) stays in sync.  The controller fires component_added /
        wire_added events which the observer handlers turn into graphics
        items automatically.
        """
        if not self.controller:
            logger.warning("Cannot paste: no controller available")
            return

        # Use controller clipboard if it has content; otherwise fall back
        # to the canvas's own clipboard for backward compatibility.
        if self.controller.has_clipboard_content():
            new_components, new_wires = self.controller.paste_components()
        elif not self._clipboard.is_empty():
            # Sync canvas clipboard to controller via public API, then paste
            self.controller.set_clipboard(
                ClipboardData(
                    components=list(self._clipboard.components),
                    wires=list(self._clipboard.wires),
                    paste_count=self._clipboard.paste_count,
                )
            )
            new_components, new_wires = self.controller.paste_components()
            # Keep canvas clipboard paste_count in sync
            self._clipboard.paste_count = self.controller.get_clipboard_paste_count()
        else:
            return

        # Select newly pasted items
        self._scene.clearSelection()
        new_ids = {c.component_id for c in new_components}
        for comp_id, comp_item in self.components.items():
            if comp_id in new_ids:
                comp_item.setSelected(True)

        if new_components:
            self.componentAdded.emit(new_components[0].component_id)

        # Sync component counter from controller
        self.component_counter = self.controller.get_component_counter()

        main_window = self.window()
        if main_window and hasattr(main_window, "statusBar"):
            status = main_window.statusBar()
            if status:
                n = len(new_components)
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
                pos = self._get_node_position(node)
                if pos:
                    label = node.get_label()
                    self._draw_label_box(painter, pos, label, y_above=True)

        # Draw OP voltage annotations (distinct style)
        if show_op:
            from utils.format_utils import format_si

            op_pen = theme_manager.pen("op_voltage")
            op_brush = theme_manager.brush("op_annotation_bg")
            op_font = theme_manager.font("op_annotation")
            painter.setPen(op_pen)
            painter.setBrush(op_brush)
            painter.setFont(op_font)

            for node in self.nodes:
                pos = self._get_node_position(node)
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
        self._scene.update()

    def clear_node_voltages(self):
        """Clear displayed node voltages."""
        self.node_voltages = {}
        self.branch_currents = {}
        self.show_node_voltages = False
        self._scene.update()

    def set_op_results(self, voltages_dict, currents_dict=None):
        """Set DC operating point results (voltages and branch currents)."""
        self.node_voltages = voltages_dict
        self.branch_currents = currents_dict or {}
        self.show_node_voltages = True
        self._scene.update()

    def clear_op_results(self):
        """Clear all operating point annotations."""
        self.node_voltages = {}
        self.branch_currents = {}
        self.show_node_voltages = False
        self._scene.update()

    # -- Probe subsystem (delegated to self.probe_overlay) ---------------

    @property
    def probe_mode(self):
        return self.probe_overlay.probe_mode

    @probe_mode.setter
    def probe_mode(self, value):
        self.probe_overlay.probe_mode = value

    @property
    def probe_results(self):
        return self.probe_overlay.probe_results

    @probe_results.setter
    def probe_results(self, value):
        self.probe_overlay.probe_results = value

    def set_probe_mode(self, active):
        """Enable or disable probe mode."""
        self.probe_overlay.set_probe_mode(active)

    def clear_probes(self):
        """Remove all probe annotations."""
        self.probe_overlay.clear_probes()

    def _probe_at_position(self, scene_pos):
        return self.probe_overlay.probe_at_position(scene_pos)

    def _probe_node(self, node):
        return self.probe_overlay._probe_node(node)

    def _probe_component(self, comp_item):
        return self.probe_overlay._probe_component(comp_item)

    def display_node_voltages(self):
        self.probe_overlay.display_node_voltages()

    def hide_node_voltages(self):
        self.probe_overlay.hide_node_voltages()

    def _get_node_position(self, node):
        return self.probe_overlay._get_node_position(node)

    def find_node_at_position(self, scene_pos):
        return self.probe_overlay.find_node_at_position(scene_pos)

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
            if not self.controller:
                logger.warning("Cannot set net name: no controller available")
                return
            self.controller.set_net_name(node, new_label)
            self._scene.update()
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

        # Completing a wire — delegate duplicate check to controller
        start_id = self.wire_start_comp.component_id
        start_term = self.wire_start_term
        end_id = component.component_id
        end_term = terminal_index

        if self.controller and self.controller.has_duplicate_wire(start_id, start_term, end_id, end_term):
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

    def clear_circuit(self):
        """Clear all components, wires, and annotations"""
        self._scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.annotations = []
        self.component_counter = DEFAULT_COMPONENT_COUNTER.copy()
        if self.controller:
            self._sync_nodes_from_model()
        else:
            self.nodes = []
            self.terminal_to_node = {}

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
            rect = self._scene.sceneRect()

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
        self._scene.render(painter, QRectF(0, 0, width, height), source_rect)
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
        self._scene.render(painter, QRectF(0, 0, width, height), source_rect)
        painter.end()

    # --- Protocol wrapper methods (CircuitCanvasProtocol) ---

    def handle_observer_event(self, event: str, data) -> None:
        """Public alias for _on_model_changed (CircuitCanvasProtocol)."""
        return self._on_model_changed(event, data)

    def clear_selection(self) -> None:
        """Deselect all items (CircuitCanvasProtocol)."""
        self._scene.clearSelection()

    def select_components(self, component_ids: list[str]) -> None:
        """Programmatically select the given components (CircuitCanvasProtocol)."""
        for comp_id, comp_item in self.components.items():
            comp_item.setSelected(comp_id in component_ids)

    def set_show_component_labels(self, show: bool) -> None:
        """Toggle component ID label visibility (CircuitCanvasProtocol)."""
        self.show_component_labels = show
        self._scene.update()

    def set_show_component_values(self, show: bool) -> None:
        """Toggle component value label visibility (CircuitCanvasProtocol)."""
        self.show_component_values = show
        self._scene.update()

    def set_show_node_labels(self, show: bool) -> None:
        """Toggle node label visibility (CircuitCanvasProtocol)."""
        self.show_node_labels = show
        self._scene.update()


# Backward compatibility alias
CircuitCanvas = CircuitCanvasView
