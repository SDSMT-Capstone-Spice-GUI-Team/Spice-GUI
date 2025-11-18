from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsLineItem,
                             QMenu, QLineEdit, QInputDialog)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QAction
from .component_item import ComponentItem, create_component
from .wire_item import WireItem
from .circuit_node import Node

# from . import GRID_SIZE, COMPONENTS
# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
}

GRID_SIZE = 10

class CircuitCanvas(QGraphicsView):
    """Main circuit drawing canvas"""
    
    # Signals for component and wire operations
    componentAdded = pyqtSignal(str)  # component_id
    wireAdded = pyqtSignal(str, str)  # start_comp_id, end_comp_id
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        if self.scene is None:
            exit()
        self.setScene(self.scene)
        self.setSceneRect(-500, -500, 1000, 1000)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        # Fix dragging artifacts by forcing full viewport updates
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        self.components = {}  # id -> ComponentItem
        self.wires = []
        self.nodes = []  # List of Node objects
        self.terminal_to_node = {}  # (comp_id, term_idx) -> Node
        self.component_counter = {'R': 0, 'C': 0, 'L': 0, 'V': 0, 'I': 0, 'GND': 0}
        
        # Simulation results storage
        self.node_voltages = {}  # node_label -> voltage value
        self.show_node_voltages = False  # Toggle for showing voltage values
        
        # Drawing grid
        self.draw_grid()
        
        # Wire drawing mode
        self.wire_start_comp = None
        self.wire_start_term = None
        self.temp_wire_line = None  # Temporary line while drawing wire
        
        self.setAcceptDrops(True)
        self.setMouseTracking(True)  # Enable mouse tracking for wire preview
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    # unsuccessful attempt to get rid of red squiggles
    # def views(self) -> list | None:
    #     views = super().views() if super().views() else None
    #     return views
    
    def draw_grid(self):
        """Draw background grid"""
        if self.scene is None:
            return
        pen = QPen(QColor(200, 200, 200), 0.5)
        pen.setCosmetic(True)  # Ensure grid doesn't scale with zoom
        for x in range(-500, 501, GRID_SIZE):
            self.scene.addLine(x, -500, x, 500, pen)
        for y in range(-500, 501, GRID_SIZE):
            self.scene.addLine(-500, y, 500, y, pen)
    
    def reroute_connected_wires(self, component):
        """Reroute all wires connected to a component"""
        print(f"  Checking {len(self.wires)} wires for connections to {component.component_id}")
        wire_count = 0
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                print(f"    Found wire: {wire.start_comp.component_id} -> {wire.end_comp.component_id}")
                wire.update_position()
                wire_count += 1

        print(f"  Rerouted {wire_count} wires")

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
    
    def mousePressEvent(self, event):
        """Handle wire drawing and component selection"""
        if event is None:
            return
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            scene_pos = self.mapToScene(pos)
            
            # Check all components for terminal proximity
            clicked_terminal = None
            clicked_component = None
            clicked_term_index = None
            
            for comp in self.components.values():
                terminals = [comp.get_terminal_pos(i) for i in range(len(comp.terminals))]
                for i, term_pos in enumerate(terminals):
                    distance = (term_pos - scene_pos).manhattanLength()
                    if distance < 20:  # Within 20 pixels of terminal
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
                        pen = QPen(Qt.GlobalColor.blue, 3)
                        pen.setStyle(Qt.PenStyle.DashLine)
                        self.temp_wire_line.setPen(pen)
                        self.temp_wire_line.setZValue(100)  # Draw on top
                        self.scene.addItem(self.temp_wire_line)
                        
                        # Accept event only when we successfully started wire drawing
                        event.accept()
                        return
                else:
                    # Complete the wire
                    if clicked_component != self.wire_start_comp:
                        can_connect = False
                        target_term = 0
                        
                        if self.is_terminal_available(clicked_component, clicked_term_index):
                            can_connect = True
                            target_term = clicked_term_index
                        
                        if can_connect:
                            # Create wire with path finding
                            wire = WireItem(self.wire_start_comp, self.wire_start_term, 
                                          clicked_component, target_term, canvas=self)
                            self.scene.addItem(wire)
                            self.wires.append(wire)
                            
                            # UPDATE NODE CONNECTIVITY
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
            if self.wire_start_comp is not None:
                if self.temp_wire_line:
                    self.scene.removeItem(self.temp_wire_line)
                    self.temp_wire_line = None
                self.wire_start_comp = None
                self.wire_start_term = None
                # Wire canceled, allow normal behavior
                # Don't accept - let event propagate
        
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
        elif event.key() == Qt.Key.Key_R:
            # Rotate selected components clockwise
            self.rotate_selected(clockwise=True)
        elif event.key() == Qt.Key.Key_R and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Rotate selected components counter-clockwise
            self.rotate_selected(clockwise=False)
        else:
            super().keyPressEvent(event)
    
    def show_context_menu(self, position):
        """Show context menu for delete operations"""
        item = self.itemAt(position)
        scene_pos = self.mapToScene(position)
        
        menu = QMenu()
        
        if isinstance(item, ComponentItem):
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
            
        elif isinstance(item, WireItem):
            delete_action = QAction("Delete Wire", self)
            delete_action.triggered.connect(lambda: self.delete_wire(item))
            menu.addAction(delete_action)
            
            if item.node:
                menu.addSeparator()
                label_action = QAction(f"Label Node ({item.node.get_label()})", self)
                label_action.triggered.connect(lambda: self.label_node(item.node))
                menu.addAction(label_action)
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
                selected_components = [i for i in selected_items if isinstance(i, ComponentItem)]
                if selected_components:
                    menu.addSeparator()
                    rotate_cw_action = QAction("Rotate Selected Clockwise", self)
                    rotate_cw_action.triggered.connect(lambda: self.rotate_selected(True))
                    menu.addAction(rotate_cw_action)
                    
                    rotate_ccw_action = QAction("Rotate Selected Counter-Clockwise", self)
                    rotate_ccw_action.triggered.connect(lambda: self.rotate_selected(False))
                    menu.addAction(rotate_ccw_action)
        
        if not menu.isEmpty():
            menu.exec(self.mapToGlobal(position))
    
    def delete_selected(self):
        """Delete all selected items"""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return
        
        components_to_delete = [item for item in selected_items if isinstance(item, ComponentItem)]
        wires_to_delete = [item for item in selected_items if isinstance(item, WireItem)]
        
        for comp in components_to_delete:
            self.delete_component(comp)
        
        for wire in wires_to_delete:
            if wire in self.wires:
                self.delete_wire(wire)
    
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
        if component is None or not isinstance(component, ComponentItem):
            return
        
        component.rotate_component(clockwise)
        
        # Update all connected wires with path finding
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                wire.update_position()
    
    def rotate_selected(self, clockwise=True):
        """Rotate all selected components"""
        selected_items = self.scene.selectedItems()
        components = [item for item in selected_items if isinstance(item, ComponentItem)]
        
        for comp in components:
            self.rotate_component(comp, clockwise)
    
    def drawForeground(self, painter, rect):
        """Draw node labels and voltages on top of everything"""
        if painter is None:
            return
        
        painter.setPen(QPen(QColor(255, 0, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        for node in self.nodes:
            pos = node.get_position(self.components)
            if pos:
                label = node.get_label()
                
                display_text = label
                if self.show_node_voltages and label in self.node_voltages:
                    voltage = self.node_voltages[label]
                    display_text = f"{label}\n{voltage:.3f}V"
                
                metrics = painter.fontMetrics()
                lines = display_text.split('\n')
                max_width = max(metrics.horizontalAdvance(line) for line in lines)
                text_height = metrics.height() * len(lines)
                
                label_rect = QRectF(pos.x() - max_width/2 - 2, pos.y() - text_height - 2,
                                   max_width + 4, text_height + 4)
                painter.drawRect(label_rect)
                
                painter.setPen(QPen(QColor(255, 0, 255)))
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
                print("viewPort is None. Can't update")
            else:
                viewPort.update()
    
    def is_terminal_available(self, component, terminal_index):
        """Check if a component's terminal is available for connection"""
        if component.component_type == 'Ground':
            return True
        
        connection_count = 0
        for wire in self.wires:
            if (wire.start_comp == component and wire.start_term == terminal_index) or \
               (wire.end_comp == component and wire.end_term == terminal_index):
                connection_count += 1
        
        return connection_count == 0
    
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
        """Clear all components and wires"""
        self.scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.nodes = []
        self.terminal_to_node = {}
        self.component_counter = {'R': 0, 'C': 0, 'L': 0, 'V': 0, 'I': 0, 'GND': 0}
        Node._node_counter = 0
    
    def to_dict(self):
        """Serialize circuit to dictionary"""
        return {
            'components': [comp.to_dict() for comp in self.components.values()],
            'wires': [wire.to_dict() for wire in self.wires],
            'counters': self.component_counter.copy()
        }
    
    def from_dict(self, data):
        """Deserialize circuit from dictionary"""
        self.clear_circuit()
        
        self.component_counter = data.get('counters', self.component_counter)
        
        for comp_data in data['components']:
            comp = ComponentItem.from_dict(comp_data)
            self.scene.addItem(comp)
            self.components[comp.component_id] = comp
        
        for wire_data in data['wires']:
            start_comp = self.components[wire_data['start_comp']]
            end_comp = self.components[wire_data['end_comp']]
            wire = WireItem(start_comp, wire_data['start_term'],
                          end_comp, wire_data['end_term'], canvas=self)
            self.scene.addItem(wire)
            self.wires.append(wire)
        
        # Rebuild node connectivity
        self.rebuild_all_nodes()
