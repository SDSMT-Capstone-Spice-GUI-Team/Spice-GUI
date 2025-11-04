"""
Circuit Design GUI Prototype
Python + Qt6 + PySpice

Requirements:
pip install PyQt6 PySpice matplotlib

This prototype implements:
- Component palette with drag-and-drop
- Grid-aligned canvas
- Save/Load (JSON with visual layout)
- SPICE netlist generation
- SPICE simulation
- Results display
"""

import sys
import json
import os
import subprocess
import tempfile
import platform
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsLineItem,
                             QPushButton, QFileDialog, QMessageBox, QTextEdit,
                             QSplitter, QLabel, QListWidgetItem, QGraphicsEllipseItem,
                             QMenu, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
                             QInputDialog)
from PyQt6.QtCore import Qt, QPointF, QRectF, QMimeData, pyqtSignal
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QDrag, QAction, QKeySequence

# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
    'Node': {'symbol': 'N', 'terminals': 1, 'color': '#FF00FF'},
}

# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
}

GRID_SIZE = 20


class Node:
    """Represents an electrical node - a set of electrically connected terminals"""
    
    _node_counter = 0  # Class variable for generating node labels
    
    def __init__(self, is_ground=False, custom_label=None):
        self.terminals = set()  # Set of (component_id, terminal_index) tuples
        self.wires = set()  # Set of WireItem objects
        self.is_ground = is_ground
        self.custom_label = custom_label
        
        if is_ground:
            self.auto_label = "0"
        elif custom_label:
            self.auto_label = custom_label
        else:
            # Generate auto label: nodeA, nodeB, nodeC...
            Node._node_counter += 1
            label_index = Node._node_counter - 1
            self.auto_label = self._generate_label(label_index)
    
    @staticmethod
    def _generate_label(index):
        """Generate label like nodeA, nodeB, ..., nodeZ, nodeAA, nodeAB..."""
        label = "node"
        if index < 26:
            label += chr(ord('A') + index)
        else:
            # For more than 26 nodes, use AA, AB, AC...
            first = (index // 26) - 1
            second = index % 26
            label += chr(ord('A') + first) + chr(ord('A') + second)
        return label
    
    def set_custom_label(self, label):
        """Set a custom label for this node"""
        self.custom_label = label
        # If currently ground, the (ground) suffix will be added by get_label()
    
    def get_label(self):
        """Get the display label for this node"""
        if self.custom_label:
            if self.is_ground:
                return f"{self.custom_label} (ground)"
            return self.custom_label
        return self.auto_label
    
    def add_terminal(self, component_id, terminal_index):
        """Add a terminal to this node"""
        self.terminals.add((component_id, terminal_index))
    
    def remove_terminal(self, component_id, terminal_index):
        """Remove a terminal from this node"""
        self.terminals.discard((component_id, terminal_index))
    
    def add_wire(self, wire):
        """Add a wire to this node"""
        self.wires.add(wire)
    
    def remove_wire(self, wire):
        """Remove a wire from this node"""
        self.wires.discard(wire)
    
    def merge_with(self, other_node):
        """Merge another node into this one"""
        self.terminals.update(other_node.terminals)
        self.wires.update(other_node.wires)
        
        # Handle ground merging
        if other_node.is_ground:
            self.is_ground = True
            if self.custom_label:
                self.custom_label = f"{self.custom_label}"  # Will add (ground) in get_label()
            else:
                self.auto_label = "0"
    
    def set_as_ground(self):
        """Mark this node as ground (node 0)"""
        self.is_ground = True
        if not self.custom_label:
            self.auto_label = "0"
    
    def unset_ground(self):
        """Remove ground designation from this node"""
        was_ground = self.is_ground
        self.is_ground = False
        
        if was_ground:
            if self.custom_label:
                # Remove (ground) suffix if present
                self.custom_label = self.custom_label.replace(" (ground)", "")
            else:
                # Re-generate auto label
                Node._node_counter += 1
                label_index = Node._node_counter - 1
                self.auto_label = self._generate_label(label_index)
    
    def get_position(self, components):
        """Get a representative position for label placement (near a junction)"""
        if not self.terminals:
            return None
        
        # Find the average position of all terminals in this node
        positions = []
        for comp_id, term_idx in self.terminals:
            if comp_id in components:
                comp = components[comp_id]
                pos = comp.get_terminal_pos(term_idx)
                positions.append(pos)
        
        if not positions:
            return None
        
        # Return average position
        avg_x = sum(p.x() for p in positions) / len(positions)
        avg_y = sum(p.y() for p in positions) / len(positions)
        return QPointF(avg_x, avg_y)


class AnalysisDialog(QDialog):
    """Dialog for configuring analysis parameters"""
    
    def __init__(self, analysis_type, parent=None):
        super().__init__(parent)
        self.analysis_type = analysis_type
        self.parameters = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle(f"{self.analysis_type} Parameters")
        layout = QVBoxLayout(self)
        
        # Create form layout for parameters
        form_layout = QFormLayout()
        
        if self.analysis_type == "DC Sweep":
            self.min_field = QLineEdit("0")
            self.max_field = QLineEdit("10")
            self.step_field = QLineEdit("0.1")
            
            form_layout.addRow("Minimum Voltage (V):", self.min_field)
            form_layout.addRow("Maximum Voltage (V):", self.max_field)
            form_layout.addRow("Step Size (V):", self.step_field)
            
        elif self.analysis_type == "AC Sweep":
            self.min_field = QLineEdit("1")
            self.max_field = QLineEdit("1000000")
            self.points_field = QLineEdit("100")
            
            form_layout.addRow("Start Frequency (Hz):", self.min_field)
            form_layout.addRow("Stop Frequency (Hz):", self.max_field)
            form_layout.addRow("Points per Decade:", self.points_field)
            
        elif self.analysis_type == "Transient":
            self.duration_field = QLineEdit("1")
            self.step_field = QLineEdit("0.001")
            
            form_layout.addRow("Duration (s):", self.duration_field)
            form_layout.addRow("Time Step (s):", self.step_field)
        
        layout.addLayout(form_layout)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_parameters(self):
        """Get the parameters from the dialog"""
        if self.analysis_type == "DC Sweep":
            try:
                return {
                    'min': float(self.min_field.text()),
                    'max': float(self.max_field.text()),
                    'step': float(self.step_field.text())
                }
            except ValueError:
                return None
                
        elif self.analysis_type == "AC Sweep":
            try:
                return {
                    'fstart': float(self.min_field.text()),
                    'fstop': float(self.max_field.text()),
                    'points': int(self.points_field.text())
                }
            except ValueError:
                return None
                
        elif self.analysis_type == "Transient":
            try:
                return {
                    'duration': float(self.duration_field.text()),
                    'step': float(self.step_field.text())
                }
            except ValueError:
                return None
        
        return {}


class ComponentItem(QGraphicsItem):
    """Graphical component on the canvas"""
    
    def __init__(self, component_type, component_id):
        super().__init__()
        self.component_type = component_type
        self.component_id = component_id
        self.value = "1k" if component_type == 'Resistor' else "1u"
        self.rotation_angle = 0  # Rotation in degrees (0, 90, 180, 270)
        self.terminals = []
        self.connections = []  # Store wire connections
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Create terminals based on component type
        self.update_terminals()
    
    def boundingRect(self):
        return QRectF(-40, -30, 80, 60)
    
    def update_terminals(self):
        """Update terminal positions based on rotation"""
        terminal_count = COMPONENTS[self.component_type]['terminals']
        
        # Base terminal positions (horizontal orientation)
        if terminal_count == 2:
            base_terminals = [QPointF(-30, 0), QPointF(30, 0)]
        elif terminal_count == 1:
            base_terminals = [QPointF(0, 0)]
        else:
            base_terminals = []
        
        # Rotate terminals based on rotation_angle
        import math
        rad = math.radians(self.rotation_angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        self.terminals = []
        for term in base_terminals:
            # Rotate point around origin
            new_x = term.x() * cos_a - term.y() * sin_a
            new_y = term.x() * sin_a + term.y() * cos_a
            self.terminals.append(QPointF(new_x, new_y))
    
    def rotate_component(self, clockwise=True):
        """Rotate component by 90 degrees"""
        if clockwise:
            self.rotation_angle = (self.rotation_angle + 90) % 360
        else:
            self.rotation_angle = (self.rotation_angle - 90) % 360
        
        self.update_terminals()
        self.update()  # Trigger repaint
    
    def paint(self, painter, option=None, widget=None):
        if painter is None:
            return
        color = QColor(COMPONENTS[self.component_type]['color'])
        
        # Save painter state
        painter.save()
        
        # Apply rotation
        painter.rotate(self.rotation_angle)
        
        # Highlight if selected
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.yellow, 3))
            painter.drawRect(QRectF(-40, -20, 80, 40))
        
        # Draw component body
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        
        if self.component_type == 'Ground':
            # Draw ground symbol
            painter.drawLine(-15, 0, 15, 0)
            painter.drawLine(-10, 5, 10, 5)
            painter.drawLine(-5, 10, 5, 10)
        elif self.component_type in ['Voltage Source', 'Current Source']:
            # Draw circle for sources
            painter.drawEllipse(-15, -15, 30, 30)
            if self.component_type == 'Voltage Source':
                painter.drawText(-5, 5, 'V')
            else:
                painter.drawText(-5, 5, 'I')
        elif self.component_type == 'Resistor':
            # Draw resistor zigzag
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(-15, 0, -10, -8)
            painter.drawLine(-10, -8, -5, 8)
            painter.drawLine(-5, 8, 0, -8)
            painter.drawLine(0, -8, 5, 8)
            painter.drawLine(5, 8, 10, -8)
            painter.drawLine(10, -8, 15, 0)
            painter.drawLine(15, 0, 30, 0)
        elif self.component_type == 'Capacitor':
            # Draw capacitor plates
            painter.drawLine(-30, 0, -5, 0)
            painter.drawLine(-5, -12, -5, 12)
            painter.drawLine(5, -12, 5, 12)
            painter.drawLine(5, 0, 30, 0)
        elif self.component_type == 'Inductor':
            # Draw inductor coils
            painter.drawLine(-30, 0, -20, 0)
            for i in range(-20, 20, 8):
                painter.drawArc(i, -5, 8, 10, 0, 180*16)
            painter.drawLine(20, 0, 30, 0)
        
        # Draw label (skip for nodes since they have custom label)
        if self.component_type != 'Node':
            painter.setPen(QPen(Qt.GlobalColor.black))
            label = f"{COMPONENTS[self.component_type]['symbol']}{self.component_id}"
            painter.drawText(-20, -25, f"{label} ({self.value})")
        
        # Restore painter state
        painter.restore()
        
        # Draw terminals in scene coordinates (not rotated)
        painter.setPen(QPen(Qt.GlobalColor.red, 4))
        for terminal in self.terminals:
            painter.drawEllipse(terminal, 3, 3)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Snap to grid
            new_pos = value
            grid_x = round(new_pos.x() / GRID_SIZE) * GRID_SIZE
            grid_y = round(new_pos.y() / GRID_SIZE) * GRID_SIZE
            return QPointF(grid_x, grid_y)
        return super().itemChange(change, value)
    
    def get_terminal_pos(self, index):
        """Get global position of terminal"""
        return self.pos() + self.terminals[index]
    
    def to_dict(self):
        """Serialize component to dictionary"""
        data = {
            'type': self.component_type,
            'id': self.component_id,
            'value': self.value,
            'pos': {'x': self.pos().x(), 'y': self.pos().y()},
            'rotation': self.rotation_angle
        }
        return data
    
    @staticmethod
    def from_dict(data):
        """Deserialize component from dictionary"""
        comp = ComponentItem(data['type'], data['id'])
        comp.value = data['value']
        comp.setPos(data['pos']['x'], data['pos']['y'])
        if 'rotation' in data:
            comp.rotation_angle = data['rotation']
            comp.update_terminals()
        return comp


class WireItem(QGraphicsLineItem):
    """Wire connecting components"""
    
    def __init__(self, start_comp, start_term, end_comp, end_term):
        super().__init__()
        self.start_comp = start_comp
        self.start_term = start_term
        self.end_comp = end_comp
        self.end_term = end_term
        self.node = None  # Reference to the Node this wire belongs to
        
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setFlag(QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_position()
    
    def update_position(self):
        """Update wire position based on component positions"""
        start = self.start_comp.get_terminal_pos(self.start_term)
        end = self.end_comp.get_terminal_pos(self.end_term)
        self.setLine(start.x(), start.y(), end.x(), end.y())
    
    def paint(self, painter, option=None, widget=None):
        """Override paint to show selection highlight"""
        if painter is None:
            return
        
        # Draw wire
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.yellow, 4))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
        
        painter.drawLine(self.line())
    
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
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
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
            
            component = ComponentItem(component_type, comp_id)
            
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
                    if clicked_component.component_type == 'Node':
                        self.wire_start_comp = clicked_component
                        self.wire_start_term = 0
                    elif self.is_terminal_available(clicked_component, clicked_term_index):
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
                        print(f"Started wire from {self.wire_start_comp.component_id} terminal {self.wire_start_term}")  # Debug
                    
                    # Don't propagate - we're in wire mode
                    event.accept()
                    return
                else:
                    # Complete the wire
                    if clicked_component != self.wire_start_comp:
                        can_connect = False
                        target_term = 0
                        
                        if clicked_component.component_type == 'Node':
                            can_connect = True
                            target_term = 0
                        elif self.is_terminal_available(clicked_component, clicked_term_index):
                            can_connect = True
                            target_term = clicked_term_index
                        
                        if can_connect:
                            # Create wire
                            wire = WireItem(self.wire_start_comp, self.wire_start_term, 
                                          clicked_component, target_term)
                            self.scene.addItem(wire)
                            self.wires.append(wire)
                            
                            print(f"Completed wire from {self.wire_start_comp.component_id} to {clicked_component.component_id}")
                            
                            # UPDATE NODE CONNECTIVITY - THIS IS CRITICAL!
                            self.update_nodes_for_wire(wire)
                            
                            self.wireAdded.emit(self.wire_start_comp.component_id, clicked_component.component_id)
                        else:
                            print(f"Cannot connect - terminal not available")  # Debug
                    else:
                        print(f"Clicked same component - cancelling")  # Debug
                    
                    # Clean up temporary wire line
                    if self.temp_wire_line:
                        self.scene.removeItem(self.temp_wire_line)
                        self.temp_wire_line = None
                    
                    self.wire_start_comp = None
                    self.wire_start_term = None
                    
                    # Don't propagate - we completed wire drawing
                    event.accept()
                    return
            
            # If we're in wire drawing mode but clicked elsewhere, cancel it
            if self.wire_start_comp is not None:
                print(f"Cancelling wire drawing")  # Debug
                if self.temp_wire_line:
                    self.scene.removeItem(self.temp_wire_line)
                    self.temp_wire_line = None
                self.wire_start_comp = None
                self.wire_start_term = None
                event.accept()
                return
        
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
            # Force update
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
        # Get item at position
        item = self.itemAt(position)
        scene_pos = self.mapToScene(position)
        
        menu = QMenu()
        
        if isinstance(item, ComponentItem):
            # Component-specific actions
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
            # Wire-specific actions
            delete_action = QAction("Delete Wire", self)
            delete_action.triggered.connect(lambda: self.delete_wire(item))
            menu.addAction(delete_action)
            
            # Add node labeling option
            print(f"Wire clicked: start={item.start_comp.component_id}[{item.start_term}], end={item.end_comp.component_id}[{item.end_term}]")
            print(f"Wire.node: {item.node}")
            print(f"Total nodes in scene: {len(self.nodes)}")
            print(f"Terminal to node map size: {len(self.terminal_to_node)}")
            
            if item.node:
                menu.addSeparator()
                label_action = QAction(f"Label Node ({item.node.get_label()})", self)
                label_action.triggered.connect(lambda: self.label_node(item.node))
                menu.addAction(label_action)
            else:
                # Wire has no node reference - try to find it
                print("Wire has no node, attempting to find...")
                start_terminal = (item.start_comp.component_id, item.start_term)
                end_terminal = (item.end_comp.component_id, item.end_term)
                print(f"Looking for start terminal: {start_terminal}")
                print(f"Looking for end terminal: {end_terminal}")
                
                found_node = self.terminal_to_node.get(start_terminal)
                print(f"Found node from start terminal: {found_node}")
                
                if found_node:
                    print(f"Found node: {found_node.get_label()}")
                    item.node = found_node  # Update the reference
                    menu.addSeparator()
                    label_action = QAction(f"Label Node ({found_node.get_label()})", self)
                    label_action.triggered.connect(lambda: self.label_node(found_node))
                    menu.addAction(label_action)
                else:
                    print("Could not find node for this wire!")
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
        
        # Separate components and wires
        components_to_delete = [item for item in selected_items if isinstance(item, ComponentItem)]
        wires_to_delete = [item for item in selected_items if isinstance(item, WireItem)]
        
        # Delete components (this will also delete connected wires)
        for comp in components_to_delete:
            self.delete_component(comp)
        
        # Delete remaining wires
        for wire in wires_to_delete:
            if wire in self.wires:  # Check if not already deleted
                self.delete_wire(wire)
    
    def delete_component(self, component):
        """Delete a component and all connected wires"""
        if component is None:
            return
        
        # Find and delete all wires connected to this component
        wires_to_delete = []
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                wires_to_delete.append(wire)
        
        for wire in wires_to_delete:
            self.delete_wire(wire)
        
        # Remove component from scene and tracking
        self.scene.removeItem(component)
        if component.component_id in self.components:
            del self.components[component.component_id]
    
    def delete_wire(self, wire):
        """Delete a wire"""
        if wire is None:
            return
        
        # Update node connectivity before removing wire
        self.update_nodes_after_wire_deletion(wire)
        
        # Remove from scene and tracking
        self.scene.removeItem(wire)
        if wire in self.wires:
            self.wires.remove(wire)
    
    def rotate_component(self, component, clockwise=True):
        """Rotate a single component"""
        if component is None or not isinstance(component, ComponentItem):
            return
        
        component.rotate_component(clockwise)
        
        # Update all connected wires
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
        
        painter.setPen(QPen(QColor(255, 0, 255), 1))  # Magenta for node labels
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))  # Semi-transparent white background
        
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        # Draw each node label once
        for node in self.nodes:
            pos = node.get_position(self.components)
            if pos:
                label = node.get_label()
                
                # Add voltage value if available and enabled
                display_text = label
                if self.show_node_voltages and label in self.node_voltages:
                    voltage = self.node_voltages[label]
                    display_text = f"{label}\n{voltage:.3f}V"
                
                # Draw background rectangle
                metrics = painter.fontMetrics()
                lines = display_text.split('\n')
                max_width = max(metrics.horizontalAdvance(line) for line in lines)
                text_height = metrics.height() * len(lines)
                
                label_rect = QRectF(pos.x() - max_width/2 - 2, pos.y() - text_height - 2,
                                   max_width + 4, text_height + 4)
                painter.drawRect(label_rect)
                
                # Draw text
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
        """Find a node near the given scene position (near a terminal)"""
        for comp_id, comp in self.components.items():
            for term_idx in range(len(comp.terminals)):
                term_pos = comp.get_terminal_pos(term_idx)
                distance = (term_pos - scene_pos).manhattanLength()
                if distance < 20:  # Within 20 pixels
                    terminal_key = (comp_id, term_idx)
                    return self.terminal_to_node.get(terminal_key)
        return None
    
    def label_node(self, node):
        """Open dialog to label a node"""
        if node is None:
            print("Error: node is None")
            return
        
        print(f"Labeling node: {node.get_label()}, is_ground: {node.is_ground}")  # Debug
        
        # Get current label (without ground suffix)
        current_label = node.custom_label if node.custom_label else node.auto_label
        if node.is_ground and " (ground)" in current_label:
            current_label = current_label.replace(" (ground)", "")
        
        print(f"Current label for editing: {current_label}")  # Debug
        
        # Show input dialog
        text, ok = QInputDialog.getText(
            None,
            "Label Node",
            f"Enter label for node (currently: {node.get_label()}):",
            QLineEdit.EchoMode.Normal,
            current_label
        )
        
        print(f"Dialog result: ok={ok}, text={text}")  # Debug
        
        if ok and text:
            # Set the custom label
            node.set_custom_label(text.strip())
            print(f"Node labeled: {node.get_label()}")  # Debug
            # Redraw to show new label
            self.scene.update()
            self.viewport().update()  # Force viewport update
    
    def is_terminal_available(self, component, terminal_index):
        """Check if a component's terminal is available for connection"""
        # Ground can have unlimited connections
        if component.component_type == 'Ground':
            return True
        
        # Count existing connections to this terminal
        connection_count = 0
        for wire in self.wires:
            if (wire.start_comp == component and wire.start_term == terminal_index) or \
               (wire.end_comp == component and wire.end_term == terminal_index):
                connection_count += 1
        
        # Most components have 2 terminals, each can only have one connection
        return connection_count == 0
    
    def handle_ground_added(self, ground_comp):
        """Handle adding a ground component - create or update node 0"""
        terminal_key = (ground_comp.component_id, 0)
        
        # Check if we already have a ground node
        ground_node = None
        for node in self.nodes:
            if node.is_ground:
                ground_node = node
                break
        
        if ground_node is None:
            # Create new ground node
            ground_node = Node(is_ground=True)
            self.nodes.append(ground_node)
        
        # Add this ground terminal to the ground node
        ground_node.add_terminal(ground_comp.component_id, 0)
        self.terminal_to_node[terminal_key] = ground_node
    
    def update_nodes_for_wire(self, wire):
        """Update node connectivity when a wire is added"""
        print(f"\n=== update_nodes_for_wire called ===")
        print(f"Wire: {wire.start_comp.component_id}[{wire.start_term}] -> {wire.end_comp.component_id}[{wire.end_term}]")
        
        start_terminal = (wire.start_comp.component_id, wire.start_term)
        end_terminal = (wire.end_comp.component_id, wire.end_term)
        
        print(f"Start terminal: {start_terminal}")
        print(f"End terminal: {end_terminal}")
        
        start_node = self.terminal_to_node.get(start_terminal)
        end_node = self.terminal_to_node.get(end_terminal)
        
        print(f"Start node: {start_node}")
        print(f"End node: {end_node}")
        
        # Case 1: Both terminals are unwired - create new node
        if start_node is None and end_node is None:
            print("Case 1: Both unwired - creating new node")
            new_node = Node()
            new_node.add_terminal(*start_terminal)
            new_node.add_terminal(*end_terminal)
            new_node.add_wire(wire)
            wire.node = new_node
            
            self.nodes.append(new_node)
            self.terminal_to_node[start_terminal] = new_node
            self.terminal_to_node[end_terminal] = new_node
            
            print(f"Created node: {new_node.get_label()}")
            print(f"Wire.node set to: {wire.node.get_label() if wire.node else 'None'}")
            
            # Check if either component is ground
            if wire.start_comp.component_type == 'Ground' or wire.end_comp.component_type == 'Ground':
                new_node.set_as_ground()
                print("Set node as ground")
        
        # Case 2: Start unwired, end wired - add start to end's node
        elif start_node is None and end_node is not None:
            print("Case 2: Start unwired, end wired")
            end_node.add_terminal(*start_terminal)
            end_node.add_wire(wire)
            wire.node = end_node
            self.terminal_to_node[start_terminal] = end_node
            
            print(f"Added to node: {end_node.get_label()}")
            
            # Check if start is ground
            if wire.start_comp.component_type == 'Ground':
                end_node.set_as_ground()
                print("Set node as ground")
        
        # Case 3: End unwired, start wired - add end to start's node
        elif end_node is None and start_node is not None:
            print("Case 3: End unwired, start wired")
            start_node.add_terminal(*end_terminal)
            start_node.add_wire(wire)
            wire.node = start_node
            self.terminal_to_node[end_terminal] = start_node
            
            print(f"Added to node: {start_node.get_label()}")
            
            # Check if end is ground
            if wire.end_comp.component_type == 'Ground':
                start_node.set_as_ground()
                print("Set node as ground")
        
        # Case 4: Both wired - merge nodes
        elif start_node is not None and end_node is not None and start_node != end_node:
            print("Case 4: Both wired - merging nodes")
            # Merge end_node into start_node
            start_node.merge_with(end_node)
            start_node.add_wire(wire)
            wire.node = start_node
            
            print(f"Merged into node: {start_node.get_label()}")
            
            # Update all terminals that pointed to end_node
            for terminal in end_node.terminals:
                self.terminal_to_node[terminal] = start_node
            
            # Remove end_node from nodes list
            self.nodes.remove(end_node)
        
        print(f"Final: wire.node = {wire.node.get_label() if wire.node else 'None'}")
        print(f"Total nodes: {len(self.nodes)}")
        print(f"Terminal map entries: {len(self.terminal_to_node)}")
        print("=== end update_nodes_for_wire ===\n")
        
        # Redraw to show updated node labels
        self.scene.update()
    
    def update_nodes_after_wire_deletion(self, wire):
        """Recalculate nodes after a wire is deleted"""
        if wire.node is None:
            return
        
        old_node = wire.node
        old_node.remove_wire(wire)
        
        # Remove the two terminals from the old node
        start_terminal = (wire.start_comp.component_id, wire.start_term)
        end_terminal = (wire.end_comp.component_id, wire.end_term)
        
        old_node.remove_terminal(*start_terminal)
        old_node.remove_terminal(*end_terminal)
        
        # Now we need to recalculate connectivity
        # Remove old node and rebuild from remaining wires
        if old_node in self.nodes:
            self.nodes.remove(old_node)
        
        # Clear terminal mappings for this node
        terminals_to_clear = list(self.terminal_to_node.keys())
        for terminal in terminals_to_clear:
            if self.terminal_to_node.get(terminal) == old_node:
                del self.terminal_to_node[terminal]
        
        # Rebuild nodes from all remaining wires
        self.rebuild_all_nodes()
        
        self.scene.update()
    
    def rebuild_all_nodes(self):
        """Rebuild all nodes from scratch based on current wires"""
        # Clear existing nodes (except preserve ground components)
        self.nodes.clear()
        self.terminal_to_node.clear()
        Node._node_counter = 0
        
        # Re-add ground components first
        for comp in self.components.values():
            if comp.component_type == 'Ground':
                self.handle_ground_added(comp)
        
        # Process all wires to rebuild nodes
        for wire in self.wires:
            wire.node = None  # Clear old node reference
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
        
        # Restore counters
        self.component_counter = data.get('counters', self.component_counter)
        
        # Restore components
        for comp_data in data['components']:
            comp = ComponentItem.from_dict(comp_data)
            self.scene.addItem(comp)
            self.components[comp.component_id] = comp
        
        # Restore wires
        for wire_data in data['wires']:
            start_comp = self.components[wire_data['start_comp']]
            end_comp = self.components[wire_data['end_comp']]
            wire = WireItem(start_comp, wire_data['start_term'],
                          end_comp, wire_data['end_term'])
            self.scene.addItem(wire)
            self.wires.append(wire)


class ComponentPalette(QListWidget):
    """Component palette with drag support"""
    
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        
        for component_name in COMPONENTS.keys():
            item = QListWidgetItem(component_name)
            self.addItem(item)
    
    def startDrag(self, supportedActions):
        """Start drag operation"""
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)


class CircuitDesignGUI(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.setGeometry(100, 100, 1200, 800)
        self.current_file = None  # Track current file for save operations
        
        # Analysis settings
        self.analysis_type = "Operational Point"  # Default analysis
        self.analysis_params = {}
        
        # Create simulation output directory
        self.sim_output_dir = os.path.join(os.getcwd(), "simulation_output")
        os.makedirs(self.sim_output_dir, exist_ok=True)
        
        self.init_ui()
        self.create_menu_bar()
    
    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Component palette
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Component Palette"))
        self.palette = ComponentPalette()
        left_panel.addWidget(self.palette)
        
        # Instructions
        instructions = QLabel(
            "Drag components to canvas\n"
            "Left-click terminal to start wire\n"
            "Left-click another terminal to complete\n"
            "Right-click for context menu\n"
            "Press R to rotate selected"
        )
        instructions.setWordWrap(True)
        left_panel.addWidget(instructions)
        
        main_layout.addLayout(left_panel, 1)
        
        # Center - Canvas and results
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Canvas
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.addWidget(QLabel("Circuit Canvas"))
        self.canvas = CircuitCanvas()
        canvas_layout.addWidget(self.canvas)
        center_splitter.addWidget(canvas_widget)
        
        # Results display
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.addWidget(QLabel("Simulation Results"))
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        center_splitter.addWidget(results_widget)
        
        center_splitter.setSizes([500, 300])
        main_layout.addWidget(center_splitter, 3)
        
        # Right panel - Controls
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Actions"))
        
        # File operations
        self.btn_save = QPushButton("Save Circuit")
        self.btn_save.clicked.connect(self.save_circuit)
        right_panel.addWidget(self.btn_save)
        
        self.btn_load = QPushButton("Load Circuit")
        self.btn_load.clicked.connect(self.load_circuit)
        right_panel.addWidget(self.btn_load)
        
        self.btn_clear = QPushButton("Clear Canvas")
        self.btn_clear.clicked.connect(self.clear_canvas)
        right_panel.addWidget(self.btn_clear)
        
        right_panel.addWidget(QLabel(""))  # Spacer
        
        # Simulation operations
        self.btn_netlist = QPushButton("Generate Netlist")
        self.btn_netlist.clicked.connect(self.generate_netlist)
        right_panel.addWidget(self.btn_netlist)
        
        self.btn_simulate = QPushButton("Run Simulation")
        self.btn_simulate.clicked.connect(self.run_simulation)
        right_panel.addWidget(self.btn_simulate)
        
        right_panel.addStretch()
        main_layout.addLayout(right_panel, 1)
    
    def create_menu_bar(self):
        """Create menu bar with File and Edit menus"""
        menubar = self.menuBar()
        if menubar is None:
            return
        
        # File menu
        file_menu = menubar.addMenu("&File")
        if file_menu is None:
            return
        
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_circuit)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_circuit)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_circuit_quick)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_circuit)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        if edit_menu is None:
            return
        
        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        rotate_cw_action = QAction("Rotate Clockwise", self)
        rotate_cw_action.setShortcut("R")
        rotate_cw_action.triggered.connect(lambda: self.canvas.rotate_selected(True))
        edit_menu.addAction(rotate_cw_action)
        
        rotate_ccw_action = QAction("Rotate Counter-Clockwise", self)
        rotate_ccw_action.setShortcut("Shift+R")
        rotate_ccw_action.triggered.connect(lambda: self.canvas.rotate_selected(False))
        edit_menu.addAction(rotate_ccw_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction("&Clear Canvas", self)
        clear_action.triggered.connect(self.clear_canvas)
        edit_menu.addAction(clear_action)
        
        # Simulation menu
        sim_menu = menubar.addMenu("&Simulation")
        if sim_menu is None:
            return
        
        netlist_action = QAction("Generate &Netlist", self)
        netlist_action.setShortcut("Ctrl+G")
        netlist_action.triggered.connect(self.generate_netlist)
        sim_menu.addAction(netlist_action)
        
        run_action = QAction("&Run Simulation", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)
        
        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")
        if analysis_menu is None:
            return
        
        op_action = QAction("&Operational Point (.op)", self)
        op_action.setCheckable(True)
        op_action.setChecked(True)  # Default
        op_action.triggered.connect(self.set_analysis_op)
        analysis_menu.addAction(op_action)
        
        dc_action = QAction("&DC Sweep", self)
        dc_action.setCheckable(True)
        dc_action.triggered.connect(self.set_analysis_dc)
        analysis_menu.addAction(dc_action)
        
        ac_action = QAction("&AC Sweep", self)
        ac_action.setCheckable(True)
        ac_action.triggered.connect(self.set_analysis_ac)
        analysis_menu.addAction(ac_action)
        
        tran_action = QAction("&Transient", self)
        tran_action.setCheckable(True)
        tran_action.triggered.connect(self.set_analysis_transient)
        analysis_menu.addAction(tran_action)
        
        # Create action group for mutually exclusive analysis types
        from PyQt6.QtGui import QActionGroup
        self.analysis_group = QActionGroup(self)
        self.analysis_group.addAction(op_action)
        self.analysis_group.addAction(dc_action)
        self.analysis_group.addAction(ac_action)
        self.analysis_group.addAction(tran_action)
        
        # Store actions for later reference
        self.op_action = op_action
        self.dc_action = dc_action
        self.ac_action = ac_action
        self.tran_action = tran_action
    
    def new_circuit(self):
        """Create a new circuit"""
        if len(self.canvas.components) > 0:
            reply = QMessageBox.question(
                self, "New Circuit",
                "Current circuit will be lost. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.canvas.clear_circuit()
        self.current_file = None
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.results_text.clear()
    
    def delete_selected(self):
        """Delete selected items from canvas"""
        self.canvas.delete_selected()
    
    def set_analysis_op(self):
        """Set analysis type to Operational Point"""
        self.analysis_type = "Operational Point"
        self.analysis_params = {}
        self.statusBar().showMessage("Analysis: Operational Point (.op)", 3000)
    
    def set_analysis_dc(self):
        """Set analysis type to DC Sweep with parameters"""
        dialog = AnalysisDialog("DC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "DC Sweep"
                self.analysis_params = params
                self.statusBar().showMessage(
                    f"Analysis: DC Sweep (V: {params['min']}V to {params['max']}V, step {params['step']}V)", 
                    3000
                )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)  # Revert to OP
        else:
            # User cancelled, revert to previous selection
            self.op_action.setChecked(True)
    
    def set_analysis_ac(self):
        """Set analysis type to AC Sweep with parameters"""
        dialog = AnalysisDialog("AC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "AC Sweep"
                self.analysis_params = params
                self.statusBar().showMessage(
                    f"Analysis: AC Sweep ({params['fstart']}Hz to {params['fstop']}Hz, {params['points']} pts/decade)", 
                    3000
                )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)
    
    def set_analysis_transient(self):
        """Set analysis type to Transient with parameters"""
        dialog = AnalysisDialog("Transient", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "Transient"
                self.analysis_params = params
                self.statusBar().showMessage(
                    f"Analysis: Transient (duration: {params['duration']}s, step: {params['step']}s)", 
                    3000
                )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)
    
    def save_circuit_quick(self):
        """Quick save to current file"""
        if self.current_file:
            try:
                data = self.canvas.to_dict()
                with open(self.current_file, 'w') as f:
                    json.dump(data, f, indent=2)
                statusBar = self.statusBar()
                if statusBar is None:
                    return
                statusBar.showMessage(f"Saved to {self.current_file}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
        else:
            self.save_circuit()
    
    def save_circuit(self):
        """Save circuit to JSON file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Circuit", "", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                data = self.canvas.to_dict()
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                self.current_file = filename
                self.setWindowTitle(f"Circuit Design GUI - {filename}")
                QMessageBox.information(self, "Success", "Circuit saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def load_circuit(self):
        """Load circuit from JSON file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Circuit", "", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.canvas.from_dict(data)
                self.current_file = filename
                self.setWindowTitle(f"Circuit Design GUI - {filename}")
                QMessageBox.information(self, "Success", "Circuit loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
    
    def clear_canvas(self):
        """Clear the canvas"""
        reply = QMessageBox.question(
            self, "Clear Canvas", 
            "Are you sure you want to clear the canvas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_circuit()
    
    def generate_netlist(self):
        """Generate SPICE netlist"""
        try:
            netlist = self.create_netlist()
            self.results_text.setPlainText("SPICE Netlist:\n\n" + netlist)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate netlist: {str(e)}")
    
    def create_netlist(self):
        """Create SPICE netlist from circuit"""
        lines = ["* Circuit Netlist Generated by Circuit Design GUI", ""]
        
        # Add title (required as first line for some SPICE variants)
        lines[0] = "Circuit Design GUI Netlist"
        lines.append("* Generated netlist")
        lines.append("")
        
        # Build node connectivity map
        node_map = {}  # (comp_id, term_index) -> node_number
        next_node = 1
        
        # Process wires to assign nodes
        for wire in self.canvas.wires:
            start_key = (wire.start_comp.component_id, wire.start_term)
            end_key = (wire.end_comp.component_id, wire.end_term)
            
            # Check if either terminal already has a node
            start_node = node_map.get(start_key)
            end_node = node_map.get(end_key)
            
            if start_node is None and end_node is None:
                # Both are new, assign new node
                node_map[start_key] = next_node
                node_map[end_key] = next_node
                next_node += 1
            elif start_node is None:
                # Start is new, use end's node
                node_map[start_key] = end_node
            elif end_node is None:
                # End is new, use start's node
                node_map[end_key] = start_node
            else:
                # Both exist, merge nodes (use minimum)
                merged_node = min(start_node, end_node)
                for key, node in list(node_map.items()):
                    if node == max(start_node, end_node):
                        node_map[key] = merged_node
        
        # Ground nodes should be 0
        ground_comps = [c for c in self.canvas.components.values() 
                       if c.component_type == 'Ground']
        for gnd in ground_comps:
            key = (gnd.component_id, 0)
            if key in node_map:
                gnd_node = node_map[key]
                # Replace all instances of this node with 0
                for k in node_map:
                    if node_map[k] == gnd_node:
                        node_map[k] = 0
        
        # Create mapping from node numbers to node labels
        node_labels = {}  # node_number -> label
        node_comps = [c for c in self.canvas.components.values() 
                     if c.component_type == 'Node']
        for node_comp in node_comps:
            key = (node_comp.component_id, 0)
            if key in node_map:
                node_num = node_map[key]
                node_labels[node_num] = node_comp.node_label
        
        # Generate component lines
        for comp in self.canvas.components.values():
            if comp.component_type in ['Ground', 'Node']:
                continue
            
            comp_id = comp.component_id
            nodes = []
            for i in range(len(comp.terminals)):
                key = (comp_id, i)
                node_num = node_map.get(key, 999)  # 999 for unconnected
                # Use label if available, otherwise use number
                node_str = node_labels.get(node_num, str(node_num))
                nodes.append(node_str)
            
            if comp.component_type == 'Resistor':
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == 'Capacitor':
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == 'Inductor':
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == 'Voltage Source':
                lines.append(f"{comp_id} {' '.join(nodes)} DC {comp.value}")
            elif comp.component_type == 'Current Source':
                lines.append(f"{comp_id} {' '.join(nodes)} DC {comp.value}")
        
        # Add comments about labeled nodes
        if node_labels:
            lines.append("")
            lines.append("* Labeled Nodes:")
            for node_num, label in sorted(node_labels.items()):
                lines.append(f"* Node {node_num} = {label}")
        
        # Add simulation options
        lines.append("")
        lines.append("* Simulation Options")
        lines.append(".option TEMP=27")
        lines.append(".option TNOM=27")
        
        # Add analysis command
        lines.append("")
        lines.append("* Analysis Type")
        if self.analysis_type == "Operational Point":
            lines.append(".op")
            lines.append("")
            lines.append("* Control section for output")
            lines.append(".control")
            lines.append("op")
            lines.append("print all")
            lines.append(".endc")
        elif self.analysis_type == "DC Sweep":
            params = self.analysis_params
            # For DC sweep, we need to specify which source to sweep
            voltage_sources = [c for c in self.canvas.components.values() 
                             if c.component_type == 'Voltage Source']
            if voltage_sources:
                source_name = voltage_sources[0].component_id
                lines.append(f".dc {source_name} {params['min']} {params['max']} {params['step']}")
                lines.append("")
                lines.append("* Control section for output")
                lines.append(".control")
                lines.append(f"dc {source_name} {params['min']} {params['max']} {params['step']}")
                # Print voltages at all labeled nodes
                if node_labels:
                    print_nodes = " ".join([f"v({label})" for label in node_labels.values()])
                    lines.append(f"print {print_nodes}")
                else:
                    lines.append("print all")
                lines.append(".endc")
            else:
                lines.append("* Warning: DC Sweep requires a voltage source")
                lines.append(".op")
        elif self.analysis_type == "AC Sweep":
            params = self.analysis_params
            lines.append(f".ac dec {params['points']} {params['fstart']} {params['fstop']}")
            lines.append("")
            lines.append("* Control section for output")
            lines.append(".control")
            lines.append(f"ac dec {params['points']} {params['fstart']} {params['fstop']}")
            if node_labels:
                print_nodes = " ".join([f"v({label})" for label in node_labels.values()])
                lines.append(f"print {print_nodes}")
            else:
                lines.append("print all")
            lines.append(".endc")
        elif self.analysis_type == "Transient":
            params = self.analysis_params
            lines.append(f".tran {params['step']} {params['duration']}")
            lines.append("")
            lines.append("* Control section for output")
            lines.append(".control")
            lines.append(f"tran {params['step']} {params['duration']}")
            if node_labels:
                print_nodes = " ".join([f"v({label})" for label in node_labels.values()])
                lines.append(f"print {print_nodes}")
            else:
                lines.append("print all")
            lines.append(".endc")
        
        lines.append("")
        lines.append(".end")
        
        return "\n".join(lines)
    
    def run_simulation(self):
        """Run SPICE simulation using ngspice"""
        try:
            # Generate netlist
            netlist = self.create_netlist()
            
            # Create timestamped filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            netlist_filename = os.path.join(self.sim_output_dir, f"netlist_{timestamp}.cir")
            output_filename = os.path.join(self.sim_output_dir, f"output_{timestamp}.txt")
            
            # Write netlist to file
            with open(netlist_filename, 'w') as f:
                f.write(netlist)
            
            self.results_text.setPlainText(f"Netlist saved to: {netlist_filename}\n\n")
            self.results_text.append(f"Running ngspice simulation...\n")
            
            # Try to run ngspice
            try:
                # Determine ngspice command based on OS
                ngspice_cmd = None
                system = platform.system()
                
                if system == "Windows":
                    # Common Windows installation paths
                    possible_paths = [
                        'ngspice',
                        'ngspice.exe',
                        r'C:\Program Files\ngspice\bin\ngspice.exe',
                        r'C:\Program Files (x86)\ngspice\bin\ngspice.exe',
                        r'C:\ngspice\bin\ngspice.exe',
                    ]
                elif system == "Linux":
                    possible_paths = [
                        'ngspice',
                        '/usr/bin/ngspice',
                        '/usr/local/bin/ngspice',
                    ]
                elif system == "Darwin":  # macOS
                    possible_paths = [
                        'ngspice',
                        '/usr/local/bin/ngspice',
                        '/opt/homebrew/bin/ngspice',
                    ]
                else:
                    possible_paths = ['ngspice']
                
                # Try to find ngspice
                for cmd in possible_paths:
                    try:
                        # For full paths on Windows, check if file exists first
                        if system == "Windows" and '\\' in cmd:
                            if not os.path.exists(cmd):
                                continue
                            else:
                                # On Windows, if the file exists, assume it works
                                # Don't run --version as it may open a GUI
                                ngspice_cmd = cmd
                                self.results_text.append(f"Found ngspice at: {cmd}\n")
                                break
                        
                        # For commands in PATH, try running --version
                        result = subprocess.run([cmd, '--version'], 
                                              capture_output=True, 
                                              timeout=5,
                                              text=True,
                                              creationflags=subprocess.CREATE_NO_WINDOW if system == "Windows" else 0)
                        if result.returncode == 0:
                            ngspice_cmd = cmd
                            self.results_text.append(f"Found ngspice at: {cmd}\n")
                            break
                    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, Exception):
                        continue
                
                if ngspice_cmd is None:
                    self.results_text.append("ERROR: ngspice not found!\n\n")
                    self.results_text.append("Please install ngspice:\n")
                    self.results_text.append("- Windows: Download from http://ngspice.sourceforge.net/download.html\n")
                    self.results_text.append("- Linux: sudo apt-get install ngspice\n")
                    self.results_text.append("- Mac: brew install ngspice\n\n")
                    self.results_text.append(f"Netlist saved to: {netlist_filename}\n")
                    self.results_text.append("You can run it manually with: ngspice -b <netlist_file>\n")
                    return
                
                # Run ngspice in batch mode (same command works on all OS)
                self.results_text.append(f"Running command: {ngspice_cmd} -b {netlist_filename} -o {output_filename}\n\n")
                
                result = subprocess.run(
                    [ngspice_cmd, '-b', netlist_filename, '-o', output_filename],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                self.results_text.append(f"ngspice return code: {result.returncode}\n")
                
                # Always show stdout and stderr for debugging
                if result.stdout:
                    self.results_text.append(f"ngspice stdout:\n{result.stdout}\n\n")
                if result.stderr:
                    self.results_text.append(f"ngspice stderr:\n{result.stderr}\n\n")
                
                # Read and display output
                if os.path.exists(output_filename):
                    with open(output_filename, 'r') as f:
                        output = f.read()
                    
                    self.results_text.append(f"Simulation complete!\n")
                    self.results_text.append(f"Output saved to: {output_filename}\n")
                    self.results_text.append("="*60 + "\n")
                    self.results_text.append("Simulation Results:\n")
                    self.results_text.append("="*60 + "\n\n")
                    self.results_text.append(output)
                    
                    # Parse and display node voltages for OP analysis
                    if self.analysis_type == "Operational Point":
                        node_voltages = self.parse_op_results(output)
                        if node_voltages:
                            self.canvas.set_node_voltages(node_voltages)
                            self.results_text.append("\n" + "="*60 + "\n")
                            # debugging print
                            self.results_text.append("Node voltages displayed on canvas\n")
                        else:
                            self.canvas.clear_node_voltages()
                    else:
                        # For other analysis types, clear voltage display
                        self.canvas.clear_node_voltages()
                else:
                    self.results_text.append(f"Warning: Output file not created at {output_filename}\n")
                    self.results_text.append(f"Checking if file exists: {os.path.exists(output_filename)}\n")
                    self.results_text.append(f"Current directory: {os.getcwd()}\n")
                    self.results_text.append(f"Simulation output dir: {self.sim_output_dir}\n")
                
                if result.returncode != 0:
                    self.results_text.append(f"\nWarning: ngspice returned exit code {result.returncode}\n")
                    if result.stderr:
                        self.results_text.append(f"Errors:\n{result.stderr}\n")
                
            except subprocess.TimeoutExpired:
                self.results_text.append("ERROR: Simulation timed out (>30 seconds)\n")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Simulation failed: {str(e)}")
            import traceback
            self.results_text.append(f"\n\nError details:\n{traceback.format_exc()}")
    
    def parse_op_results(self, output):
        """Parse operational point analysis results to extract node voltages"""
        import re
        node_voltages = {}
        
        try:
            # Look for the node voltage table in ngspice output
            # Format: v(nodename) = voltage or nodename voltage
            lines = output.split('\n')
            
            for i, line in enumerate(lines):
                # Look for voltage output patterns
                # Pattern 1: "v(nodename) = voltage" or "v(nodename) voltage"
                match = re.search(r'v\((\w+)\)\s*[=:]\s*([-+]?[\d.]+e?[-+]?\d*)', line, re.IGNORECASE)
                if match:
                    node_name = match.group(1)
                    voltage = float(match.group(2))
                    node_voltages[node_name] = voltage
                    continue
                
                # Pattern 2: Just node name and voltage in columns
                # After finding "Node" and "Voltage" headers
                if 'node' in line.lower() and 'voltage' in line.lower():
                    # Found header, parse following lines
                    for j in range(i+1, min(i+50, len(lines))):
                        result_line = lines[j].strip()
                        if not result_line or result_line.startswith('-'):
                            continue
                        if result_line.startswith('*') or result_line.lower().startswith('source'):
                            break
                        
                        # Try to parse: nodename voltage
                        parts = result_line.split()
                        if len(parts) >= 2:
                            try:
                                node_name = parts[0].replace('v(', '').replace(')', '')
                                voltage = float(parts[1])
                                node_voltages[node_name] = voltage
                            except (ValueError, IndexError):
                                continue
            
            # Also look for the format in .print output
            # "0 voltage"
            for line in lines:
                # Match lines like:
                # V(5)                             1.000000e-06
                # V(4)                             5.000000e-07
                # V(2)                             -5.00000e-07
                # V(1)                             -1.00000e-06
                match = re.match(r'^\s*(V(\((\d+)\)|\d+))\s+([-+]?[\d.]+e?[-+]?\d*)\s*', line)
                if match:
                    node_name = match.group(1)
                    voltage = float(match.group(4))
                    node_voltages[node_name] = voltage
                    # debugging print statement
                    print("node_name:", node_name, "voltage:", voltage )
            
            return node_voltages
            
        except Exception as e:
            print(f"Error parsing OP results: {e}")
            return {}


def main():
    app = QApplication(sys.argv)
    window = CircuitDesignGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()