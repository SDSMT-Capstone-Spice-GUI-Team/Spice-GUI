from PyQt6.QtWidgets import QGraphicsItem, QInputDialog, QLineEdit
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath
import math

GRID_SIZE = 10

class ComponentItem(QGraphicsItem):
    """Base class for graphical components on the canvas"""
    
    # Class attributes to be overridden by child classes
    SYMBOL = ''
    TERMINALS = 2
    COLOR = '#000000'
    DEFAULT_VALUE = '1u'
    
    def __init__(self, component_id, component_type = 'Unknown'):
        super().__init__()
        self.component_type = component_type
        self.component_id = component_id
        self.value = self.DEFAULT_VALUE
        self.rotation_angle = 0  # Rotation in degrees (0, 90, 180, 270)
        self.terminals = []
        self.connections = []  # Store wire connections
        self.is_being_dragged = False
        self.last_position = None
        self.update_timer = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # Create terminals
        self.update_terminals()
    
    def mousePressEvent(self, event):
        """Track when dragging starts"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_being_dragged = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle drag end"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_being_dragged = False
        super().mouseReleaseEvent(event)

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
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self.is_being_dragged:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

        super().hoverMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Open a dialog to edit component value on double-click"""
        if self.component_type == 'Ground':
            return  # Don't allow editing ground value

        current_value = self.value
        new_value, ok = QInputDialog.getText(
            None, 
            f"Edit Value for {self.component_id}", 
            "Enter new value:", 
            QLineEdit.EchoMode.Normal, 
            current_value
        )

        if ok and new_value:
            self.value = new_value
            self.update()  # Redraw the item to show the new value
            if self.scene():
                self.scene().update()  # Redraw the scene
    
    def boundingRect(self):
        return QRectF(-40, -30, 80, 60)
    
    def update_terminals(self):
        """Update terminal positions based on rotation"""
        # Base terminal positions (horizontal orientation)
        if self.TERMINALS == 2:
            base_terminals = [QPointF(-20, 0), QPointF(20, 0)]
        else:
            base_terminals = []
        
        # Rotate terminals based on rotation_angle
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
        self.update()
    
    def draw_component_body(self, painter):
        """Override this method in child classes to draw component-specific shape"""
        pass
    
    def paint(self, painter, option=None, widget=None):
        if painter is None:
            return
        
        color = QColor(self.COLOR)
        
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
        self.draw_component_body(painter)
        
        # Draw label
        painter.setPen(QPen(Qt.GlobalColor.black))
        label = f"{self.component_id}"
        painter.drawText(-20, -25, f"{label} ({self.value})")
        
        # Restore painter state
        painter.restore()
        
        # Draw terminals in scene coordinates (not rotated)
        painter.setPen(QPen(Qt.GlobalColor.red, 4))
        for terminal in self.terminals:
            painter.drawEllipse(terminal, 3, 3)
    
    def schedule_wire_update(self):
        """Schedule a wire update after a short delay"""
        # Cancel any existing timer
        if self.update_timer is not None:
            self.update_timer.stop()
            self.update_timer = None

        # Create a new timer to update wires after dragging stops
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_wires_after_drag)
        self.update_timer.start(50)  # 50ms delay

    def update_wires_after_drag(self):
        """Called after drag motion has stopped"""
        print(f"Timer fired for {self.component_id}, last_pos={self.last_position}, current_pos={self.pos()}")
        if self.last_position is not None and self.last_position != self.pos():
            print(f"Component {self.component_id} finished moving, updating wires...")
            # Get the CircuitCanvas (view) from the scene
            if self.scene():
                views = self.scene().views()
                if views:
                    canvas = views[0]  # Get the first (and typically only) view
                    if hasattr(canvas, 'reroute_connected_wires'):
                        canvas.reroute_connected_wires(self)
                    else:
                        print(f"  ERROR: View doesn't have reroute_connected_wires!")
                else:
                    print(f"  ERROR: Scene has no views!")
            else:
                print(f"  ERROR: Component has no scene!")
        else:
            print(f"  Component {self.component_id} did not move or last_position is None")
        self.last_position = None
        self.update_timer = None

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Snap to grid
            new_pos = value
            grid_x = round(new_pos.x() / GRID_SIZE) * GRID_SIZE
            grid_y = round(new_pos.y() / GRID_SIZE) * GRID_SIZE
            snapped_pos = QPointF(grid_x, grid_y)

            # Track that we're moving and schedule an update
            if self.last_position is None:
                self.last_position = self.pos()
            self.schedule_wire_update()

            return snapped_pos
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Force scene update to prevent dragging artifacts
            if self.scene():
                self.scene().update()

        return super().itemChange(change, value)
    
    def get_terminal_pos(self, index):
        """Get global position of terminal"""
        return self.pos() + self.terminals[index]
    
    def to_dict(self):
        """Serialize component to dictionary"""
        data = {
            'type': self.__class__.__name__,
            'id': self.component_id,
            'value': self.value,
            'pos': {'x': self.pos().x(), 'y': self.pos().y()},
            'rotation': self.rotation_angle
        }
        return data
    
    @staticmethod
    def from_dict(data):
        """Deserialize component from dictionary"""
        component_class = COMPONENT_CLASSES.get(data['type'])
        if component_class is None:
            raise ValueError(f"Unknown component type: {data['type']}")
        
        comp = component_class(data['id'])
        comp.value = data['value']
        comp.setPos(data['pos']['x'], data['pos']['y'])
        if 'rotation' in data:
            comp.rotation_angle = data['rotation']
            comp.update_terminals()
        return comp


class Resistor(ComponentItem):
    """Resistor component"""
    SYMBOL = 'R'
    TERMINALS = 2
    COLOR = '#2196F3'
    DEFAULT_VALUE = '1k'
    type_name = 'Resistor'
    
    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)
    
    def draw_component_body(self, painter):
        # Draw resistor zigzag
        painter.drawLine(-20, 0, -15, 0)
        painter.drawLine(-15, 0, -10, -8)
        painter.drawLine(-10, -8, -5, 8)
        painter.drawLine(-5, 8, 0, -8)
        painter.drawLine(0, -8, 5, 8)
        painter.drawLine(5, 8, 10, -8)
        painter.drawLine(10, -8, 15, 0)
        painter.drawLine(15, 0, 20, 0)


class Capacitor(ComponentItem):
    """Capacitor component"""
    SYMBOL = 'C'
    TERMINALS = 2
    COLOR = '#4CAF50'
    DEFAULT_VALUE = '1u'
    type_name = 'Capacitor'
    
    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)
    
    def draw_component_body(self, painter):
        # Draw capacitor plates
        painter.drawLine(-20, 0, -5, 0)
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(5, -12, 5, 12)
        painter.drawLine(5, 0, 20, 0)


class Inductor(ComponentItem):
    """Inductor component"""
    SYMBOL = 'L'
    TERMINALS = 2
    COLOR = '#FF9800'
    DEFAULT_VALUE = '1m'
    type_name = 'Inductor'
    
    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)

    
    def draw_component_body(self, painter):
        # Draw inductor coils
        painter.drawLine(-20, 0, -20, 0)
        for i in range(-20, 20, 8):
            painter.drawArc(i, -5, 8, 10, 0, 180*16)
        painter.drawLine(20, 0, 20, 0)


class VoltageSource(ComponentItem):
    """Voltage source component"""
    SYMBOL = 'V'
    TERMINALS = 2
    COLOR = '#F44336'
    DEFAULT_VALUE = '5V'
    type_name = 'Voltage Source'
    
    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)
    
    def draw_component_body(self, painter):
        # Draw circle for source
        painter.drawEllipse(-15, -15, 30, 30)
        painter.drawLine(-10, 2, -10, -2)
        painter.drawLine(-12, 0, -8, 0)
        painter.drawLine(12, 0, 8, 0)
        # painter.drawText(-5, 5, 'V')


class CurrentSource(ComponentItem):
    """Current source component"""
    SYMBOL = 'I'
    TERMINALS = 2
    COLOR = '#9C27B0'
    DEFAULT_VALUE = '1A'

    type_name = 'Current Source'
    
    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)

    def draw_component_body(self, painter):
        # Draw circle for source
        painter.drawEllipse(-15, -15, 30, 30)
        painter.drawLine(-20, 5, -20, -5)
        painter.drawLine(-25, 0, -15, 0)
        painter.drawLine(15, 0, 25, 0)
        painter.drawText(-5, 5, 'I')

class Ground(ComponentItem):
    """Ground component"""
    SYMBOL = 'GND'
    TERMINALS = 1
    COLOR = '#000000'
    DEFAULT_VALUE = '0V'
    type_name = 'Ground'
    
    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)

    def paint(self, painter, option=None, widget=None):
        if painter is None:
            return
        
        color = QColor(self.COLOR)
        
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
        self.draw_component_body(painter)
        
        # Draw label
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(-20, -25, "GND (0V)")
        
        # Restore painter state
        painter.restore()
        
        # Draw terminals in scene coordinates (not rotated)
        painter.setPen(QPen(Qt.GlobalColor.red, 4))
        for terminal in self.terminals:
            painter.drawEllipse(terminal, 3, 3)

    def draw_component_body(self, painter):
        # Draw ground symbol
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(-15, 10, 15, 10)
        painter.drawLine(-10, 15, 10, 15)
        painter.drawLine(-5, 20, 5, 20)
        
    def update_terminals(self):
        """Update terminal positions based on rotation"""
        # Base terminal positions (horizontal orientation)
        if self.TERMINALS == 2:
            base_terminals = [QPointF(-20, 0), QPointF(20, 0)]
        elif self.TERMINALS == 1:
            base_terminals = [QPointF(0, 0)]
        else:
            base_terminals = []
        
        # Rotate terminals based on rotation_angle
        rad = math.radians(self.rotation_angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        self.terminals = []
        for term in base_terminals:
            # Rotate point around origin
            new_x = term.x() * cos_a - term.y() * sin_a
            new_y = term.x() * sin_a + term.y() * cos_a
            self.terminals.append(QPointF(new_x, new_y))

class OpAmp(ComponentItem):
    """Operational Amplifier component"""
    SYMBOL = 'OA'
    TERMINALS = 3
    COLOR = '#FFC107'
    DEFAULT_VALUE = 'Ideal'
    type_name = 'Op-Amp'

    def __init__(self, component_id):
        super().__init__(component_id, self.type_name)

    def draw_component_body(self, painter):
        # Draw the triangular body of the op-amp
        painter.drawLine(-20, -15, 20, 0)
        painter.drawLine(20, 0, -20, 15)
        painter.drawLine(-20, 15, -20, -15)

        # Draw '+' and '-' signs for inputs
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(-17, -8, -13, -8) # Inverting (-)
        painter.drawLine(-17, 8, -13, 8)  # Non-inverting (+)
        painter.drawLine(-15, 6, -15, 10) # Non-inverting (+)

    def update_terminals(self):
        """Update terminal positions for the op-amp based on rotation"""
        # Base terminal positions (inverting, non-inverting, output)
        base_terminals = [
            QPointF(-20, -10),  # Inverting input
            QPointF(-20, 10),   # Non-inverting input
            QPointF(20, 0),     # Output
        ]

        # Rotate terminals based on rotation_angle
        rad = math.radians(self.rotation_angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        self.terminals = []
        for term in base_terminals:
            new_x = term.x() * cos_a - term.y() * sin_a
            new_y = term.x() * sin_a + term.y() * cos_a
            self.terminals.append(QPointF(new_x, new_y))

    def boundingRect(self):
        return QRectF(-30, -25, 60, 50)

# Component registry for factory pattern
COMPONENT_CLASSES = {
    'Resistor': Resistor,
    'Capacitor': Capacitor,
    'Inductor': Inductor,
    'VoltageSource': VoltageSource,
    'CurrentSource': CurrentSource,
    'Voltage Source': VoltageSource,
    'Current Source': CurrentSource,
    'Ground': Ground,
    'OpAmp': OpAmp,
    'Op-Amp': OpAmp
}

# # Legacy component definitions for compatibility
# COMPONENTS = {
#     'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
#     'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
#     'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
#     'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
#     'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
#     'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
# }


def create_component(component_type, component_id):
    """Factory function to create components"""
    component_class = COMPONENT_CLASSES.get(component_type)
    if component_class is None:
        raise ValueError(f"Unknown component type: {component_type}")
    return component_class(component_id)