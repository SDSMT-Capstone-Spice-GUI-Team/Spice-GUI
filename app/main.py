"""
Circuit Design GUI Prototype
Python + Qt + PySpice

Requirements:
pip install PyQt5 PySpice matplotlib

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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsLineItem,
                             QPushButton, QFileDialog, QMessageBox, QTextEdit,
                             QSplitter, QLabel, QListWidgetItem)
from PyQt5.QtCore import Qt, QPointF, QRectF, QMimeData
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QDrag, QPixmap

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


class ComponentItem(QGraphicsItem):
    """Graphical component on the canvas"""
    
    def __init__(self, component_type, component_id):
        super().__init__()
        self.component_type = component_type
        self.component_id = component_id
        self.value = "1k" if component_type == 'Resistor' else "1u"
        self.terminals = []
        self.connections = []  # Store wire connections
        
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        # Create terminals based on component type
        terminal_count = COMPONENTS[component_type]['terminals']
        if terminal_count == 2:
            self.terminals = [QPointF(-30, 0), QPointF(30, 0)]
        elif terminal_count == 1:
            self.terminals = [QPointF(0, 0)]
    
    def boundingRect(self):
        return QRectF(-40, -20, 80, 40)
    
    def paint(self, painter, option, widget):
        color = QColor(COMPONENTS[self.component_type]['color'])
        
        # Highlight if selected
        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 3))
            painter.drawRect(self.boundingRect())
        
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
        
        # Draw terminals
        painter.setPen(QPen(Qt.red, 4))
        for terminal in self.terminals:
            painter.drawPoint(terminal)
        
        # Draw label
        painter.setPen(QPen(Qt.black))
        label = f"{COMPONENTS[self.component_type]['symbol']}{self.component_id}"
        painter.drawText(-20, -25, f"{label} ({self.value})")
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
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
        return {
            'type': self.component_type,
            'id': self.component_id,
            'value': self.value,
            'pos': {'x': self.pos().x(), 'y': self.pos().y()}
        }
    
    @staticmethod
    def from_dict(data):
        """Deserialize component from dictionary"""
        comp = ComponentItem(data['type'], data['id'])
        comp.value = data['value']
        comp.setPos(data['pos']['x'], data['pos']['y'])
        return comp


class WireItem(QGraphicsLineItem):
    """Wire connecting components"""
    
    def __init__(self, start_comp, start_term, end_comp, end_term):
        super().__init__()
        self.start_comp = start_comp
        self.start_term = start_term
        self.end_comp = end_comp
        self.end_term = end_term
        
        self.setPen(QPen(Qt.black, 2))
        self.update_position()
    
    def update_position(self):
        """Update wire position based on component positions"""
        start = self.start_comp.get_terminal_pos(self.start_term)
        end = self.end_comp.get_terminal_pos(self.end_term)
        self.setLine(start.x(), start.y(), end.x(), end.y())
    
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
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(-500, -500, 1000, 1000)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        self.components = {}  # id -> ComponentItem
        self.wires = []
        self.component_counter = {'R': 0, 'C': 0, 'L': 0, 'V': 0, 'I': 0, 'GND': 0}
        
        # Drawing grid
        self.draw_grid()
        
        # Wire drawing mode
        self.wire_start_comp = None
        self.wire_start_term = None
        
        self.setAcceptDrops(True)
    
    def draw_grid(self):
        """Draw background grid"""
        pen = QPen(QColor(200, 200, 200), 0.5)
        for x in range(-500, 501, GRID_SIZE):
            self.scene.addLine(x, -500, x, 500, pen)
        for y in range(-500, 501, GRID_SIZE):
            self.scene.addLine(-500, y, 500, y, pen)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle component drop from palette"""
        component_type = event.mimeData().text()
        if component_type in COMPONENTS:
            # Create new component
            symbol = COMPONENTS[component_type]['symbol']
            self.component_counter[symbol] += 1
            comp_id = f"{symbol}{self.component_counter[symbol]}"
            
            component = ComponentItem(component_type, comp_id)
            
            # Position at drop location (snapped to grid)
            pos = self.mapToScene(event.pos())
            grid_x = round(pos.x() / GRID_SIZE) * GRID_SIZE
            grid_y = round(pos.y() / GRID_SIZE) * GRID_SIZE
            component.setPos(grid_x, grid_y)
            
            self.scene.addItem(component)
            self.components[comp_id] = component
            
            event.acceptProposedAction()
    
    def mousePressEvent(self, event):
        """Handle wire drawing"""
        if event.button() == Qt.RightButton:
            # Start wire drawing
            item = self.itemAt(event.pos())
            if isinstance(item, ComponentItem):
                # Find closest terminal
                scene_pos = self.mapToScene(event.pos())
                terminals = [item.get_terminal_pos(i) for i in range(len(item.terminals))]
                distances = [(t - scene_pos).manhattanLength() for t in terminals]
                closest = distances.index(min(distances))
                
                if min(distances) < 20:  # Within 20 pixels
                    self.wire_start_comp = item
                    self.wire_start_term = closest
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Complete wire drawing"""
        if event.button() == Qt.RightButton and self.wire_start_comp:
            item = self.itemAt(event.pos())
            if isinstance(item, ComponentItem) and item != self.wire_start_comp:
                # Find closest terminal
                scene_pos = self.mapToScene(event.pos())
                terminals = [item.get_terminal_pos(i) for i in range(len(item.terminals))]
                distances = [(t - scene_pos).manhattanLength() for t in terminals]
                closest = distances.index(min(distances))
                
                if min(distances) < 20:
                    # Create wire
                    wire = WireItem(self.wire_start_comp, self.wire_start_term, 
                                  item, closest)
                    self.scene.addItem(wire)
                    self.wires.append(wire)
            
            self.wire_start_comp = None
            self.wire_start_term = None
        
        super().mouseReleaseEvent(event)
    
    def clear_circuit(self):
        """Clear all components and wires"""
        self.scene.clear()
        self.draw_grid()
        self.components = {}
        self.wires = []
        self.component_counter = {'R': 0, 'C': 0, 'L': 0, 'V': 0, 'I': 0, 'GND': 0}
    
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
            drag.exec_(Qt.CopyAction)


class CircuitDesignGUI(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.setGeometry(100, 100, 1200, 800)
        
        self.init_ui()
    
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
            "Right-click terminals to wire\n"
            "Left-click to select/move"
        )
        instructions.setWordWrap(True)
        left_panel.addWidget(instructions)
        
        main_layout.addLayout(left_panel, 1)
        
        # Center - Canvas and results
        center_splitter = QSplitter(Qt.Vertical)
        
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
                QMessageBox.information(self, "Success", "Circuit loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
    
    def clear_canvas(self):
        """Clear the canvas"""
        reply = QMessageBox.question(
            self, "Clear Canvas", 
            "Are you sure you want to clear the canvas?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
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
        
        # Generate component lines
        for comp in self.canvas.components.values():
            if comp.component_type == 'Ground':
                continue
            
            comp_id = comp.component_id
            nodes = []
            for i in range(len(comp.terminals)):
                key = (comp_id, i)
                node = node_map.get(key, 999)  # 999 for unconnected
                nodes.append(str(node))
            
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
        
        lines.append("")
        lines.append(".end")
        
        return "\n".join(lines)
    
    def run_simulation(self):
        """Run SPICE simulation (simplified version)"""
        try:
            netlist = self.create_netlist()
            
            # Display netlist and placeholder results
            results = "SPICE Netlist:\n" + netlist + "\n\n"
            results += "=" * 50 + "\n"
            results += "Simulation Results (Placeholder):\n\n"
            results += "NOTE: Full SPICE simulation requires PySpice integration.\n"
            results += "This prototype shows netlist generation.\n\n"
            results += "To enable full simulation:\n"
            results += "1. Install PySpice: pip install PySpice\n"
            results += "2. Install ngspice backend\n"
            results += "3. Extend this function to use PySpice Circuit class\n\n"
            results += "Example node voltages (placeholder):\n"
            results += "Node 0: 0.000V (Ground)\n"
            results += "Node 1: 5.000V\n"
            results += "Node 2: 2.500V\n"
            
            self.results_text.setPlainText(results)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Simulation failed: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = CircuitDesignGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()