from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor

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
        self.rotation_angle = 0  # Rotation in degrees (0, 90, 180, 270)
        self.terminals = []
        self.connections = []  # Store wire connections
        self.is_being_dragged = False
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Create terminals based on component type
        self.update_terminals()

    # unsuccessful attempt to get rid of red squiggles
    # def scene(self):
    #     return super().scene()
    
    def hoverMoveEvent(self, event):
        """Update cursor based on whether hovering over terminal"""
        if event is None:
            return
        
        hover_pos = event.pos()
        near_terminal = False
        
        # Check if hovering near a terminal
        for terminal in self.terminals:
            distance = (terminal - hover_pos).manhattanLength()
            if distance < 15:
                near_terminal = True
                break
        
        # Change cursor based on position
        if near_terminal:
            self.setCursor(Qt.CursorShape.ArrowCursor)  # Normal cursor for wire drawing
        elif self.is_being_dragged:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)  # Hand cursor for dragging
        
        super().hoverMoveEvent(event)
    
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
        
        # Draw label
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
            snapped_pos = QPointF(grid_x, grid_y)
            return snapped_pos
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Position has changed, update wires
            print(f"Component {self.component_id} moved, updating wires...")
            if hasattr(self.scene(), 'reroute_connected_wires'):
                self.scene().reroute_connected_wires(self)
            else:
                print("  Scene doesn't have reroute_connected_wires!")
        
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
