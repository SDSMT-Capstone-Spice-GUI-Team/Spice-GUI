import logging
from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsLineItem,
                             QMenu, QLineEdit, QInputDialog, QGraphicsTextItem)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QBrush, QPainter, QAction

logger = logging.getLogger(__name__)
from .component_item import ComponentGraphicsItem, create_component
from .wire_item import WireItem
from .circuit_node import Node
from .annotation_item import AnnotationItem
from .algorithm_layers import AlgorithmLayerManager
from .styles import (GRID_SIZE, GRID_EXTENT, MAJOR_GRID_INTERVAL,
                     COMPONENTS, DEFAULT_COMPONENT_COUNTER,
                     TERMINAL_CLICK_RADIUS, theme_manager,
                     ZOOM_FACTOR, ZOOM_MIN, ZOOM_MAX, ZOOM_FIT_PADDING)

class CircuitCanvasView(QGraphicsView):
    """Main circuit drawing canvas view"""
    
    # Signals for component and wire operations
    componentAdded = pyqtSignal(str)  # component_id
    wireAdded = pyqtSignal(str, str)  # start_comp_id, end_comp_id
    selectionChanged = pyqtSignal(object)  # selected component (or None)
    componentRightClicked = pyqtSignal(object, object)  # component, global position
    canvasClicked = pyqtSignal()
    zoomChanged = pyqtSignal(float)  # current zoom level (1.0 = 100%)
    
    
    
    def __init__(self):
        super().__init__()
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

        # Multi-algorithm layer management
        self.layer_manager = AlgorithmLayerManager()
        self.multi_algorithm_mode = False  # Disable multi-algorithm mode - use only IDA*

        # Simulation results storage
        self.node_voltages = {}  # node_label -> voltage value
        self.show_node_voltages = False  # Toggle for showing voltage values

        # Label visibility settings
        self.show_component_labels = True  # Toggle for component IDs (R1, V1, etc.)
        self.show_component_values = True  # Toggle for component values (1k, 5V, etc.)
        self.show_node_labels = True       # Toggle for node labels (n1, n2, etc.)

        # Debug visualization
        self.show_obstacle_boundaries = False  # Toggle for showing obstacle boundaries
        self.obstacle_boundary_items = []  # Store obstacle boundary graphics items

        # Grid drawing deferred to first show for faster startup
        self._grid_drawn = False

        # Text annotations on the canvas
        self.annotations = []

        # Internal clipboard for copy/paste
        self._clipboard = None  # {'components': [...], 'wires': [...]}
        
        # Wire drawing mode
        self.wire_start_comp = None
        self.wire_start_term = None
        self.temp_wire_line = None  # Temporary line while drawing wire
        
        self.setAcceptDrops(True)
        self.setMouseTracking(True)  # Enable mouse tracking for wire preview
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Connect scene selection changes to our signal
        self.scene.selectionChanged.connect(self.on_selection_changed)

    def showEvent(self, event):
        """Draw grid on first show for faster startup"""
        super().showEvent(event)
        if not self._grid_drawn:
            self.draw_grid()
            self._grid_drawn = True

    # unsuccessful attempt to get rid of red squiggles
    # def views(self) -> list | None:
    #     views = super().views() if super().views() else None
    #     return views
    
    def draw_grid(self):
        """Draw background grid with major grid lines labeled with position values"""
        if self.scene is None:
            return

        # Grid pens from theme
        minor_pen = theme_manager.pen('grid_minor')
        major_pen = theme_manager.pen('grid_major')
        grid_label_color = theme_manager.color('grid_label')
        grid_label_font = theme_manager.font('grid_label')

        # Draw vertical lines
        for x in range(-GRID_EXTENT, GRID_EXTENT + 1, GRID_SIZE):
            is_major = (x % MAJOR_GRID_INTERVAL == 0)
            pen = major_pen if is_major else minor_pen
            self.scene.addLine(x, -GRID_EXTENT, x, GRID_EXTENT, pen)

            # Add label for major grid lines
            if is_major:
                label = QGraphicsTextItem(str(x))
                label.setDefaultTextColor(grid_label_color)
                label.setFont(grid_label_font)
                label.setPos(x - 15, -GRID_EXTENT)  # Position at top
                label.setZValue(-1)  # Draw behind components
                self.scene.addItem(label)

        # Draw horizontal lines
        for y in range(-GRID_EXTENT, GRID_EXTENT + 1, GRID_SIZE):
            is_major = (y % MAJOR_GRID_INTERVAL == 0)
            pen = major_pen if is_major else minor_pen
            self.scene.addLine(-GRID_EXTENT, y, GRID_EXTENT, y, pen)

            # Add label for major grid lines
            if is_major:
                label = QGraphicsTextItem(str(y))
                label.setDefaultTextColor(grid_label_color)
                label.setFont(grid_label_font)
                label.setPos(-GRID_EXTENT, y - 10)  # Position at left
                label.setZValue(-1)  # Draw behind components
                self.scene.addItem(label)
    
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
            if main_window and hasattr(main_window, 'statusBar'):
                status = main_window.statusBar()
                if status:
                    status.showMessage(f"Rerouted {wire_count} wire{'s' if wire_count != 1 else ''} connected to {component.component_id}", 1000)
    
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
        """Handle component drop from palette"""
        if event is None:
            return
        mimeData = event.mimeData()
        if mimeData is None:
            return
        component_type = mimeData.text()
        if component_type in COMPONENTS:
            # Create new component
            symbol = COMPONENTS[component_type]['symbol']
            if symbol not in self.component_counter.keys():
                self.component_counter[symbol] = 0
            self.component_counter[symbol] += 1
            comp_id = f"{symbol}{self.component_counter[symbol]}"
            
            component = create_component(component_type, comp_id)
            
            # Position at drop location (snapped to grid)
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            grid_x = round(scene_pos.x() / GRID_SIZE) * GRID_SIZE
            grid_y = round(scene_pos.y() / GRID_SIZE) * GRID_SIZE
            component.setPos(grid_x, grid_y)
            
            self.scene.addItem(component)
            self.components[comp_id] = component
            self.componentAdded.emit(comp_id)
            
            # If this is a ground component, create/update node 0
            if component_type == 'Ground':
                self.handle_ground_added(component)
            
            event.acceptProposedAction()

    def add_component_at_center(self, component_type):
        """Add a component at the center of the visible canvas area"""
        if component_type not in COMPONENTS:
            return

        # Get viewport center in scene coordinates
        viewport_center = self.viewport().rect().center()
        scene_pos = self.mapToScene(viewport_center)

        # Snap to grid
        grid_x = round(scene_pos.x() / GRID_SIZE) * GRID_SIZE
        grid_y = round(scene_pos.y() / GRID_SIZE) * GRID_SIZE

        # Create component (same pattern as dropEvent)
        symbol = COMPONENTS[component_type]['symbol']
        if symbol not in self.component_counter.keys():
            self.component_counter[symbol] = 0
        self.component_counter[symbol] += 1
        comp_id = f"{symbol}{self.component_counter[symbol]}"

        component = create_component(component_type, comp_id)
        component.setPos(grid_x, grid_y)

        self.scene.addItem(component)
        self.components[comp_id] = component
        self.componentAdded.emit(comp_id)

        # Handle ground component special case
        if component_type == 'Ground':
            self.handle_ground_added(component)

    def mousePressEvent(self, event):
        """Handle wire drawing and component selection"""
        if event is None:
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
                        self.temp_wire_line = QGraphicsLineItem(start_pos.x(), start_pos.y(),
                                                                 start_pos.x(), start_pos.y())
                        self.temp_wire_line.setPen(theme_manager.pen('wire_preview'))
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
                            # Create wire(s) with multi-algorithm routing
                            if self.multi_algorithm_mode:
                                # Create a wire for each active algorithm
                                for algorithm in self.layer_manager.active_algorithms:
                                    layer = self.layer_manager.get_layer(algorithm)
                                    wire = WireItem(
                                        self.wire_start_comp, self.wire_start_term,
                                        clicked_component, target_term,
                                        canvas=self,
                                        algorithm=algorithm,
                                        layer_color=layer.color
                                    )
                                    self.scene.addItem(wire)
                                    self.wires.append(wire)

                                    # Add wire to layer and track performance
                                    self.layer_manager.add_wire_to_layer(
                                        wire, algorithm, wire.runtime, wire.iterations
                                    )

                                    # UPDATE NODE CONNECTIVITY (only for first wire to avoid duplicates)
                                    if algorithm == self.layer_manager.active_algorithms[0]:
                                        self.update_nodes_for_wire(wire)
                                pass
                            else:
                                # Single algorithm mode - use IDA*
                                wire = WireItem(
                                    self.wire_start_comp, self.wire_start_term,
                                    clicked_component, target_term,
                                    canvas=self,
                                    algorithm='idastar'
                                )
                                self.scene.addItem(wire)
                                self.wires.append(wire)
                                self.update_nodes_for_wire(wire)

                            self.wireAdded.emit(self.wire_start_comp.component_id, clicked_component.component_id)
                    
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
                    # Clear scene selection when clicking on background
                    self.scene.clearSelection()

        # Normal selection/movement behavior
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Update temporary wire line while drawing"""
        if event is None:
            return
        
        if self.wire_start_comp is not None and self.temp_wire_line is not None:
            # Update temporary wire to follow mouse
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            start_pos = self.wire_start_comp.get_terminal_pos(self.wire_start_term)
            self.temp_wire_line.setLine(start_pos.x(), start_pos.y(), 
                                       scene_pos.x(), scene_pos.y())
            self.temp_wire_line.update()
            event.accept()
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event is None:
            return
        
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event is None:
            return

        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.delete_selected()
        elif event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.copy_selected()
        elif event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.paste_clipboard()
        elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.cut_selected()
        elif event.key() == Qt.Key.Key_R and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Rotate selected components counter-clockwise (check Shift+R before plain R)
            self.rotate_selected(clockwise=False)
        elif event.key() == Qt.Key.Key_R:
            # Rotate selected components clockwise
            self.rotate_selected(clockwise=True)
        else:
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
        items = [item for item in self.scene.items()
                 if isinstance(item, ComponentGraphicsItem)]
        if not items:
            self.zoom_reset()
            return

        # Calculate bounding rect of all components
        rect = items[0].sceneBoundingRect()
        for item in items[1:]:
            rect = rect.united(item.sceneBoundingRect())

        # Add padding
        rect.adjust(-ZOOM_FIT_PADDING, -ZOOM_FIT_PADDING,
                     ZOOM_FIT_PADDING, ZOOM_FIT_PADDING)

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
                label_action = QAction(f"Label Node ({item.node.get_label()})", self)
                label_action.triggered.connect(lambda: self.label_node(item.node))
                menu.addAction(label_action)
            pass
        else:
            # Check if we clicked near a terminal to label its node
            clicked_node = self.find_node_at_position(scene_pos)
            if clicked_node:
                label_action = QAction(f"Label Node ({clicked_node.get_label()})", self)
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
        """Delete a component and all connected wires"""
        if component is None:
            return
        
        wires_to_delete = []
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                wires_to_delete.append(wire)
        
        for wire in wires_to_delete:
            self.delete_wire(wire)
        
        self.scene.removeItem(component)
        if component.component_id in self.components:
            del self.components[component.component_id]
    
    def delete_wire(self, wire):
        """Delete a wire"""
        if wire is None:
            return
        
        self.update_nodes_after_wire_deletion(wire)
        
        self.scene.removeItem(wire)
        if wire in self.wires:
            self.wires.remove(wire)
    
    def rotate_component(self, component, clockwise=True):
        """Rotate a single component"""
        if component is None or not isinstance(component, ComponentGraphicsItem):
            return
        
        component.rotate_component(clockwise)
        
        # Update all connected wires with path finding
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                wire.update_position()
    
    def rotate_selected(self, clockwise=True):
        """Rotate all selected components"""
        selected_items = self.scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]

        for comp in components:
            self.rotate_component(comp, clockwise)

    def copy_selected(self):
        """Copy selected components and their internal wires to the clipboard."""
        selected_items = self.scene.selectedItems()
        selected_comps = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]
        if not selected_comps:
            return

        selected_ids = {comp.component_id for comp in selected_comps}

        # Serialize components
        comp_dicts = [comp.to_dict() for comp in selected_comps]

        # Serialize only wires where BOTH endpoints are in the selection
        wire_dicts = []
        for wire in self.wires:
            if wire.start_comp.component_id in selected_ids and wire.end_comp.component_id in selected_ids:
                wire_dicts.append(wire.to_dict())

        self._clipboard = {'components': comp_dicts, 'wires': wire_dicts}

    def paste_clipboard(self):
        """Paste clipboard contents onto the canvas with new IDs and offset position."""
        if not self._clipboard:
            return

        PASTE_OFFSET = 4 * GRID_SIZE  # 40px offset

        # Build old_id -> new_id mapping and create components
        id_map = {}
        new_comps = []
        for comp_data in self._clipboard['components']:
            old_id = comp_data['id']
            comp_type = comp_data['type']

            # Generate a new unique ID
            symbol = COMPONENTS[comp_type]['symbol']
            if symbol not in self.component_counter:
                self.component_counter[symbol] = 0
            self.component_counter[symbol] += 1
            new_id = f"{symbol}{self.component_counter[symbol]}"
            id_map[old_id] = new_id

            # Clone the component data with new ID and offset position
            new_data = dict(comp_data)
            new_data['id'] = new_id
            new_data['pos'] = {
                'x': comp_data['pos']['x'] + PASTE_OFFSET,
                'y': comp_data['pos']['y'] + PASTE_OFFSET,
            }

            comp = ComponentGraphicsItem.from_dict(new_data)
            self.scene.addItem(comp)
            self.components[new_id] = comp
            new_comps.append(comp)

            if comp_type == 'Ground':
                self.handle_ground_added(comp)

            self.componentAdded.emit(new_id)

        # Recreate internal wires using the ID mapping
        for wire_data in self._clipboard['wires']:
            new_start = id_map.get(wire_data['start_comp'])
            new_end = id_map.get(wire_data['end_comp'])
            if new_start and new_end and new_start in self.components and new_end in self.components:
                start_comp = self.components[new_start]
                end_comp = self.components[new_end]
                wire = WireItem(
                    start_comp, wire_data['start_term'],
                    end_comp, wire_data['end_term'],
                    canvas=self, algorithm='idastar'
                )
                self.scene.addItem(wire)
                self.wires.append(wire)
                self.update_nodes_for_wire(wire)

        # Select only the newly pasted components
        self.scene.clearSelection()
        for comp in new_comps:
            comp.setSelected(True)

    def cut_selected(self):
        """Cut selected components: copy to clipboard then delete."""
        self.copy_selected()
        self.delete_selected()

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

    def on_selection_changed(self):
        """Handle selection changes in the scene"""
        selected_items = self.scene.selectedItems()

        # Filter for component items only
        components = [item for item in selected_items if isinstance(item, ComponentGraphicsItem)]

        # Emit signal with the first selected component (or None if no selection)
        if components:
            self.selectionChanged.emit(components[0])
        else:
            self.selectionChanged.emit(None)
    
    def drawForeground(self, painter, rect):
        """Draw node labels and voltages on top of everything"""
        if painter is None:
            return

        # Early exit if nothing to draw
        if not self.show_node_labels and not self.show_node_voltages:
            return

        painter.setPen(theme_manager.pen('node_label_outline'))
        painter.setBrush(theme_manager.brush('node_label_bg'))
        painter.setFont(theme_manager.font('node_label'))

        for node in self.nodes:
            pos = node.get_position(self.components)
            if pos:
                label = node.get_label()

                # Build display text based on visibility settings
                if self.show_node_labels:
                    display_text = label
                    if self.show_node_voltages and label in self.node_voltages:
                        voltage = self.node_voltages[label]
                        display_text = f"{label}\n{voltage:.3f}V"
                elif self.show_node_voltages and label in self.node_voltages:
                    # Only show voltage, not label
                    voltage = self.node_voltages[label]
                    display_text = f"{voltage:.3f}V"
                else:
                    continue  # Nothing to show for this node

                metrics = painter.fontMetrics()
                lines = display_text.split('\n')
                max_width = max(metrics.horizontalAdvance(line) for line in lines)
                text_height = metrics.height() * len(lines)

                label_rect = QRectF(pos.x() - max_width/2 - 2, pos.y() - text_height - 2,
                                   max_width + 4, text_height + 4)
                painter.drawRect(label_rect)

                painter.setPen(theme_manager.pen('node_label_outline'))
                y_offset = int(pos.y() - 4)
                for line in lines:
                    text_width = metrics.horizontalAdvance(line)
                    painter.drawText(int(pos.x() - text_width/2), y_offset, line)
                    y_offset += metrics.height()
    
    def set_node_voltages(self, voltages_dict):
        """Set node voltages from simulation results"""
        self.node_voltages = voltages_dict
        self.show_node_voltages = True
        self.scene.update()
    
    def clear_node_voltages(self):
        """Clear displayed node voltages"""
        self.node_voltages = {}
        self.show_node_voltages = False
        self.scene.update()

    def display_node_voltages(self):
        """enable display node voltages"""
        self.show_node_voltages = True
        self.scene.update()

    def hide_node_voltages(self):
        """disable display node voltages"""
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
        """Open dialog to label a node"""
        if node is None:
            return
        
        current_label = node.custom_label if node.custom_label else node.auto_label
        if node.is_ground and " (ground)" in current_label:
            current_label = current_label.replace(" (ground)", "")
        
        text, ok = QInputDialog.getText(
            None,
            "Label Node",
            f"Enter label for node (currently: {node.get_label()}):",
            QLineEdit.EchoMode.Normal,
            current_label
        )
        
        if ok and text:
            node.set_custom_label(text.strip())
            self.scene.update()
            viewPort = self.viewport()
            if viewPort is None:
                logger.warning("Viewport is None, cannot update after node label change")
            else:
                viewPort.update()
    
    def is_terminal_available(self, component, terminal_index):
        """Check if a component's terminal is available for connection"""
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
            
            if wire.start_comp.component_type == 'Ground' or wire.end_comp.component_type == 'Ground':
                new_node.set_as_ground()
        
        elif start_node is None and end_node is not None:
            end_node.add_terminal(*start_terminal)
            end_node.add_wire(wire)
            wire.node = end_node
            self.terminal_to_node[start_terminal] = end_node
            
            if wire.start_comp.component_type == 'Ground':
                end_node.set_as_ground()
        
        elif end_node is None and start_node is not None:
            start_node.add_terminal(*end_terminal)
            start_node.add_wire(wire)
            wire.node = start_node
            self.terminal_to_node[end_terminal] = start_node
            
            if wire.end_comp.component_type == 'Ground':
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
            if comp.component_type == 'Ground':
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
        self.layer_manager.clear_all_wires()

    def toggle_multi_algorithm_mode(self, enabled=None):
        """
        Toggle or set multi-algorithm routing mode

        Args:
            enabled: If None, toggle; if bool, set to that value

        Returns:
            bool: New state of multi-algorithm mode
        """
        if enabled is None:
            self.multi_algorithm_mode = not self.multi_algorithm_mode
            pass
        else:
            self.multi_algorithm_mode = enabled
        return self.multi_algorithm_mode

    def set_active_algorithms(self, algorithm_list):
        """
        Set which algorithms should be used for routing

        Args:
            algorithm_list: List of algorithm names ('astar', 'idastar', 'dijkstra')
        """
        self.layer_manager.set_active_algorithms(algorithm_list)

    def get_performance_report(self):
        """Get performance comparison report for all algorithms"""
        return self.layer_manager.get_performance_report()

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
            if hasattr(comp, 'get_obstacle_shape'):
                polygon_points = comp.get_obstacle_shape()
                pass
            else:
                # Fallback to bounding rect
                rect = comp.boundingRect()
                polygon_points = [
                    (rect.left(), rect.top()),
                    (rect.right(), rect.top()),
                    (rect.right(), rect.bottom()),
                    (rect.left(), rect.bottom())
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
                        dist = math.sqrt(dx*dx + dy*dy)
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
            obstacle_full_pen = theme_manager.pen('obstacle_full')
            full_points = transform_polygon(polygon_points, inset_distance=0)
            for i in range(len(full_points)):
                p1 = full_points[i]
                p2 = full_points[(i + 1) % len(full_points)]
                line = self.scene.addLine(p1[0], p1[1], p2[0], p2[1], obstacle_full_pen)
                line.setZValue(50)
                self.obstacle_boundary_items.append(line)

            # Draw inset shape (blue - non-connected components)
            obstacle_inset_pen = theme_manager.pen('obstacle_inset')
            inset_pixels = 1.5 * GRID_SIZE
            inset_points = transform_polygon(polygon_points, inset_distance=inset_pixels)
            for i in range(len(inset_points)):
                p1 = inset_points[i]
                p2 = inset_points[(i + 1) % len(inset_points)]
                line = self.scene.addLine(p1[0], p1[1], p2[0], p2[1], obstacle_inset_pen)
                line.setZValue(50)
                self.obstacle_boundary_items.append(line)

            # Draw terminal markers
            terminal_pen = theme_manager.pen('terminal_marker')
            terminal_brush = theme_manager.brush('terminal_fill')
            for i in range(len(comp.terminals)):
                term_pos = comp.get_terminal_pos(i)
                terminal_circle = self.scene.addEllipse(
                    term_pos.x() - 5, term_pos.y() - 5, 10, 10,
                    terminal_pen, terminal_brush
                )
                terminal_circle.setZValue(100)
                self.obstacle_boundary_items.append(terminal_circle)

        # Add legend
        legend_y = -480
        legend_x = -480
        obstacle_full_color = theme_manager.color('obstacle_full')
        obstacle_inset_color = theme_manager.color('obstacle_inset')
        terminal_color = theme_manager.color('terminal_highlight')

        # Full boundary legend (red solid frame)
        full_legend_rect = self.scene.addRect(
            legend_x, legend_y, 30, 15,
            theme_manager.pen('obstacle_full'),
            QBrush(Qt.BrushStyle.NoBrush)
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
            legend_x, legend_y + 25, 30, 15,
            theme_manager.pen('obstacle_inset'),
            QBrush(Qt.BrushStyle.NoBrush)
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
            legend_x + 7.5, legend_y + 52.5, 10, 10,
            theme_manager.pen('terminal_marker'),
            theme_manager.brush('terminal_fill')
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

    def to_dict(self):
        """Serialize circuit to dictionary"""
        data = {
            'components': [comp.to_dict() for comp in self.components.values()],
            'wires': [wire.to_dict() for wire in self.wires],
            'counters': self.component_counter.copy(),
        }
        if self.annotations:
            data['annotations'] = [ann.to_dict() for ann in self.annotations]
        return data
    
    @staticmethod
    def _validate_circuit_data(data):
        """Validate JSON structure before loading. Raises ValueError on problems."""
        if not isinstance(data, dict):
            raise ValueError("File does not contain a valid circuit object.")

        if 'components' not in data or not isinstance(data['components'], list):
            raise ValueError("Missing or invalid 'components' list.")
        if 'wires' not in data or not isinstance(data['wires'], list):
            raise ValueError("Missing or invalid 'wires' list.")

        comp_ids = set()
        for i, comp in enumerate(data['components']):
            for key in ('id', 'type', 'value', 'pos'):
                if key not in comp:
                    raise ValueError(
                        f"Component #{i + 1} is missing required field '{key}'.")
            pos = comp['pos']
            if not isinstance(pos, dict) or 'x' not in pos or 'y' not in pos:
                raise ValueError(
                    f"Component '{comp.get('id', i)}' has invalid position data.")
            if not isinstance(pos['x'], (int, float)) or not isinstance(pos['y'], (int, float)):
                raise ValueError(
                    f"Component '{comp['id']}' position values must be numeric.")
            comp_ids.add(comp['id'])

        for i, wire in enumerate(data['wires']):
            for key in ('start_comp', 'end_comp', 'start_term', 'end_term'):
                if key not in wire:
                    raise ValueError(
                        f"Wire #{i + 1} is missing required field '{key}'.")
            if wire['start_comp'] not in comp_ids:
                raise ValueError(
                    f"Wire #{i + 1} references unknown component '{wire['start_comp']}'.")
            if wire['end_comp'] not in comp_ids:
                raise ValueError(
                    f"Wire #{i + 1} references unknown component '{wire['end_comp']}'.")

    def from_dict(self, data):
        """Deserialize circuit from dictionary"""
        self._validate_circuit_data(data)
        self.clear_circuit()

        self.component_counter = data.get('counters', self.component_counter)

        for comp_data in data['components']:
            comp = ComponentGraphicsItem.from_dict(comp_data)
            self.scene.addItem(comp)
            self.components[comp.component_id] = comp

        for wire_data in data['wires']:
            start_comp = self.components[wire_data['start_comp']]
            end_comp = self.components[wire_data['end_comp']]
            wire = WireItem(start_comp, wire_data['start_term'],
                          end_comp, wire_data['end_term'], canvas=self)
            self.scene.addItem(wire)
            self.wires.append(wire)

        # Load annotations
        for ann_data in data.get('annotations', []):
            ann = AnnotationItem.from_dict(ann_data)
            self.scene.addItem(ann)
            self.annotations.append(ann)

        # Rebuild node connectivity
        self.rebuild_all_nodes()


# Backward compatibility alias
CircuitCanvas = CircuitCanvasView
