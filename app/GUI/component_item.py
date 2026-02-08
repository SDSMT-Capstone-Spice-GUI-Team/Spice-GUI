from PyQt6.QtWidgets import QGraphicsItem, QInputDialog, QLineEdit, QMessageBox
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPen, QBrush, QColor  # QPainterPath imported locally where needed
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.component import ComponentData, DEFAULT_VALUES
from .format_utils import validate_component_value
from .styles import GRID_SIZE, TERMINAL_HOVER_RADIUS, WIRE_UPDATE_DELAY_MS, theme_manager

class ComponentItem(QGraphicsItem):
    """Base class for graphical components on the canvas.

    Each ComponentItem holds a reference to a ComponentData model object.
    Data properties (component_id, component_type, value, rotation) are
    delegated to the model. Drawing and Qt interaction stay in this class.
    """

    # Class attribute for subclass type identification
    type_name = 'Unknown'

    def __init__(self, component_id, component_type='Unknown', model=None):
        super().__init__()

        # Create or accept a ComponentData backing object
        if model is not None:
            self.model = model
        else:
            self.model = ComponentData(
                component_id=component_id,
                component_type=component_type,
                value=DEFAULT_VALUES.get(component_type, '1u'),
                position=(0.0, 0.0),
            )

        self.terminals = []  # List[QPointF] - Qt rendering positions
        self.connections = []  # Store wire connections
        self.is_being_dragged = False
        self.last_position = None
        self.update_timer = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # Create terminals
        self.update_terminals()

    # --- Data delegation properties ---

    @property
    def component_id(self):
        return self.model.component_id

    @component_id.setter
    def component_id(self, value):
        self.model.component_id = value

    @property
    def component_type(self):
        return self.model.component_type

    @property
    def value(self):
        return self.model.value

    @value.setter
    def value(self, v):
        self.model.value = v

    @property
    def rotation_angle(self):
        return self.model.rotation

    @rotation_angle.setter
    def rotation_angle(self, v):
        self.model.rotation = v

    # --- Event handlers ---

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
            if distance < TERMINAL_HOVER_RADIUS:
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
        if self.component_type in ('Ground', 'Op-Amp'):
            return

        if self.component_type == 'Waveform Source':
            QMessageBox.information(
                None, "Waveform Source",
                "Use the 'Configure Waveform...' button in the Properties panel."
            )
            return

        current_value = self.value
        new_value, ok = QInputDialog.getText(
            None,
            f"Edit Value for {self.component_id}",
            "Enter new value (e.g. 10k, 100n, 4.7M):",
            QLineEdit.EchoMode.Normal,
            current_value
        )

        if ok and new_value:
            is_valid, error_msg = validate_component_value(new_value, self.component_type)
            if not is_valid:
                QMessageBox.warning(None, "Invalid Value", error_msg)
                return

            self.value = new_value
            self.update()
            _scene = self.scene()
            if _scene is not None:
                _scene.update()

    # --- Geometry ---

    def boundingRect(self):
        return QRectF(-40, -30, 80, 60)

    def get_obstacle_shape(self):
        """
        Return the obstacle boundary shape for pathfinding.

        Returns a list of (x, y) points defining a polygon in LOCAL coordinates
        (relative to component center, before rotation).

        Returns:
            List of (x, y) tuples forming a closed polygon
        """
        rect = self.boundingRect()
        return [
            (rect.left(), rect.top()),
            (rect.right(), rect.top()),
            (rect.right(), rect.bottom()),
            (rect.left(), rect.bottom())
        ]

    def update_terminals(self):
        """Update terminal positions based on rotation, sourced from model geometry."""
        base = self.model.get_base_terminal_positions()

        rad = math.radians(self.rotation_angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        self.terminals = []
        for tx, ty in base:
            new_x = tx * cos_a - ty * sin_a
            new_y = tx * sin_a + ty * cos_a
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

        # Get component color from theme
        color = theme_manager.get_component_color(self.component_type)

        # Save painter state
        painter.save()

        # Apply rotation
        painter.rotate(self.rotation_angle)

        # Highlight if selected
        if self.isSelected():
            painter.setPen(theme_manager.pen('component_selected'))
            painter.drawRect(QRectF(-40, -20, 80, 40))

        # Draw component body
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        self.draw_component_body(painter)

        # Draw label (check canvas visibility settings)
        canvas = self.scene().views()[0] if self.scene() and self.scene().views() else None
        show_label = canvas.show_component_labels if canvas and hasattr(canvas, 'show_component_labels') else True
        show_value = canvas.show_component_values if canvas and hasattr(canvas, 'show_component_values') else True

        if show_label or show_value:
            painter.setPen(QPen(Qt.GlobalColor.black))
            if show_label and show_value:
                painter.drawText(-20, -25, f"{self.component_id} ({self.value})")
            elif show_label:
                painter.drawText(-20, -25, self.component_id)
            elif show_value:
                painter.drawText(-20, -25, f"({self.value})")

        # Restore painter state
        painter.restore()

        # Draw terminals in scene coordinates (not rotated)
        painter.setPen(theme_manager.pen('terminal'))
        for terminal in self.terminals:
            painter.drawEllipse(terminal, 3, 3)

    def schedule_wire_update(self):
        """Schedule a wire update after a short delay"""
        if self.update_timer is not None:
            self.update_timer.stop()
            self.update_timer = None

        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_wires_after_drag)
        self.update_timer.start(WIRE_UPDATE_DELAY_MS)

    def update_wires_after_drag(self):
        """Called after drag motion has stopped"""
        if self.last_position is not None and self.last_position != self.pos():
            if self.scene():
                views = self.scene().views()
                if views:
                    canvas = views[0]
                    if hasattr(canvas, 'reroute_connected_wires'):
                        canvas.reroute_connected_wires(self)
        self.last_position = None
        self.update_timer = None

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Snap to grid
            new_pos = value
            grid_x = round(new_pos.x() / GRID_SIZE) * GRID_SIZE
            grid_y = round(new_pos.y() / GRID_SIZE) * GRID_SIZE
            snapped_pos = QPointF(grid_x, grid_y)

            # Sync position to model
            self.model.position = (grid_x, grid_y)

            # Track that we're moving and schedule an update
            if self.last_position is None:
                self.last_position = self.pos()
            self.schedule_wire_update()

            return snapped_pos
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update this item and connected wires to prevent dragging artifacts
            self.update()
            if self.scene():
                views = self.scene().views()
                if views:
                    canvas = views[0]
                    if hasattr(canvas, 'wires'):
                        for wire in canvas.wires:
                            if wire.start_comp is self or wire.end_comp is self:
                                wire.update()

        return super().itemChange(change, value)

    def get_terminal_pos(self, index):
        """Get global position of terminal"""
        return self.pos() + self.terminals[index]

    def to_dict(self):
        """Serialize component to dictionary via the model"""
        # Sync Qt position to model before serializing
        self.model.position = (self.pos().x(), self.pos().y())
        return self.model.to_dict()

    @staticmethod
    def from_dict(data_dict):
        """Deserialize component from dictionary"""
        # Create model first
        comp_data = ComponentData.from_dict(data_dict)

        # Find the right GUI class
        component_class = COMPONENT_CLASSES.get(comp_data.component_type)
        if component_class is None:
            raise ValueError(f"Unknown component type: {comp_data.component_type}")

        # Create GUI component backed by the model
        comp = component_class(comp_data.component_id, model=comp_data)
        comp.setPos(comp_data.position[0], comp_data.position[1])
        comp.update_terminals()

        return comp


class Resistor(ComponentItem):
    """Resistor component"""
    type_name = 'Resistor'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawLine(-15, 0, -10, -8)
        painter.drawLine(-10, -8, -5, 8)
        painter.drawLine(-5, 8, 0, -8)
        painter.drawLine(0, -8, 5, 8)
        painter.drawLine(5, 8, 10, -8)
        painter.drawLine(10, -8, 15, 0)

    def get_obstacle_shape(self):
        return [
            (-18.0, -11.0),
            (18.0, -11.0),
            (18.0, 11.0),
            (-18.0, 11.0)
        ]


class Capacitor(ComponentItem):
    """Capacitor component"""
    type_name = 'Capacitor'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, 0, -5, 0)
            painter.drawLine(5, 0, 30, 0)
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(5, -12, 5, 12)

    def get_obstacle_shape(self):
        return [
            (-18.0, -14.0),
            (18.0, -14.0),
            (18.0, 14.0),
            (-18.0, 14.0)
        ]


class Inductor(ComponentItem):
    """Inductor component"""
    type_name = 'Inductor'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, 0, -20, 0)
            painter.drawLine(20, 0, 30, 0)
        for i in range(-20, 20, 8):
            painter.drawArc(i, -5, 8, 10, 0, 180*16)

    def get_obstacle_shape(self):
        return [
            (-18.0, -11.0),
            (18.0, -11.0),
            (18.0, 11.0),
            (-18.0, 11.0)
        ]


class VoltageSource(ComponentItem):
    """Voltage source component"""
    type_name = 'Voltage Source'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(-15, -15, 30, 30)
        painter.drawLine(-10, 2, -10, -2)
        painter.drawLine(-12, 0, -8, 0)
        painter.drawLine(12, 0, 8, 0)

    def get_obstacle_shape(self):
        return [
            (-18.0, -18.0),
            (18.0, -18.0),
            (18.0, 18.0),
            (-18.0, 18.0)
        ]


class CurrentSource(ComponentItem):
    """Current source component"""
    type_name = 'Current Source'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(-15, -15, 30, 30)
        painter.drawText(-5, 5, 'I')

    def get_obstacle_shape(self):
        return [
            (-18.0, -18.0),
            (18.0, -18.0),
            (18.0, 18.0),
            (-18.0, 18.0)
        ]

class WaveformVoltageSource(ComponentItem):
    """Waveform voltage source component (sine, pulse, PWL, etc.)"""
    type_name = 'Waveform Source'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    # Waveform properties delegated to model
    @property
    def waveform_type(self):
        return self.model.waveform_type

    @waveform_type.setter
    def waveform_type(self, v):
        self.model.waveform_type = v

    @property
    def waveform_params(self):
        return self.model.waveform_params

    @waveform_params.setter
    def waveform_params(self, v):
        self.model.waveform_params = v

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(-15, -15, 30, 30)
        # Draw sine wave symbol
        from models.component import COMPONENT_COLORS
        painter.setPen(QPen(QColor(COMPONENT_COLORS.get(self.component_type, '#E91E63')), 2))
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(-10, 0)
        for x in range(-10, 11, 2):
            y = 8 * math.sin(x * math.pi / 10)
            path.lineTo(x, y)
        painter.drawPath(path)

    def get_spice_value(self):
        """Generate SPICE waveform specification (delegates to model)"""
        return self.model.get_spice_value()

    def get_obstacle_shape(self):
        return super().get_obstacle_shape()

class Ground(ComponentItem):
    """Ground component"""
    type_name = 'Ground'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def paint(self, painter, option=None, widget=None):
        if painter is None:
            return

        color = theme_manager.get_component_color(self.component_type)

        painter.save()
        painter.rotate(self.rotation_angle)

        if self.isSelected():
            painter.setPen(theme_manager.pen('component_selected'))
            painter.drawRect(QRectF(-40, -20, 80, 40))

        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        self.draw_component_body(painter)

        canvas = self.scene().views()[0] if self.scene() and self.scene().views() else None
        show_label = canvas.show_component_labels if canvas and hasattr(canvas, 'show_component_labels') else True
        show_value = canvas.show_component_values if canvas and hasattr(canvas, 'show_component_values') else True

        if show_label or show_value:
            painter.setPen(QPen(Qt.GlobalColor.black))
            if show_label and show_value:
                painter.drawText(-20, -25, "GND (0V)")
            elif show_label:
                painter.drawText(-20, -25, "GND")
            elif show_value:
                painter.drawText(-20, -25, "(0V)")

        painter.restore()

        painter.setPen(theme_manager.pen('terminal'))
        for terminal in self.terminals:
            painter.drawEllipse(terminal, 3, 3)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(0, -10, 0, 0)
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(-15, 10, 15, 10)
        painter.drawLine(-10, 15, 10, 15)
        painter.drawLine(-5, 20, 5, 20)

    def get_obstacle_shape(self):
        return [
            (-17.0, 1.0),
            (17.0, 1.0),
            (17.0, 22.0),
            (-17.0, 22.0)
        ]

class OpAmp(ComponentItem):
    """Operational Amplifier component"""
    type_name = 'Op-Amp'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, -10, -20, -10)
            painter.drawLine(-30, 10, -20, 10)
            painter.drawLine(20, 0, 30, 0)
        painter.drawLine(-20, -15, 20, 0)
        painter.drawLine(20, 0, -20, 15)
        painter.drawLine(-20, 15, -20, -15)

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(-17, -8, -13, -8)
        painter.drawLine(-17, 8, -13, 8)
        painter.drawLine(-15, 6, -15, 10)

    def boundingRect(self):
        return QRectF(-30, -25, 60, 50)

class VCVS(ComponentItem):
    """Voltage-Controlled Voltage Source (E element)"""
    type_name = 'VCVS'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-40, -25, 80, 50)

    def draw_component_body(self, painter):
        # Control and output lines
        if self.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape (dependent source symbol)
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # +/- polarity markers on output side
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(5, -6, 9, -6)
        painter.drawLine(7, -8, 7, -4)
        painter.drawLine(5, 6, 9, 6)

    def get_obstacle_shape(self):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class CCVS(ComponentItem):
    """Current-Controlled Voltage Source (H element)"""
    type_name = 'CCVS'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-40, -25, 80, 50)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # +/- polarity markers on output side
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(5, -6, 9, -6)
        painter.drawLine(7, -8, 7, -4)
        painter.drawLine(5, 6, 9, 6)
        # Arrow on control side to indicate current sensing
        painter.drawLine(-12, -2, -8, -2)
        painter.drawLine(-9, -4, -8, -2)
        painter.drawLine(-9, 0, -8, -2)

    def get_obstacle_shape(self):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class VCCS(ComponentItem):
    """Voltage-Controlled Current Source (G element)"""
    type_name = 'VCCS'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-40, -25, 80, 50)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # Arrow inside diamond (current source indicator)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(4, 6, 4, -6)
        painter.drawLine(2, -4, 4, -6)
        painter.drawLine(6, -4, 4, -6)

    def get_obstacle_shape(self):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class CCCS(ComponentItem):
    """Current-Controlled Current Source (F element)"""
    type_name = 'CCCS'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-40, -25, 80, 50)

    def draw_component_body(self, painter):
        if self.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # Arrow inside diamond (current source indicator)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(4, 6, 4, -6)
        painter.drawLine(2, -4, 4, -6)
        painter.drawLine(6, -4, 4, -6)
        # Arrow on control side to indicate current sensing
        painter.drawLine(-12, -2, -8, -2)
        painter.drawLine(-9, -4, -8, -2)
        painter.drawLine(-9, 0, -8, -2)

    def get_obstacle_shape(self):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class BJTNPN(ComponentItem):
    """NPN Bipolar Junction Transistor"""
    type_name = 'BJT NPN'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-30, -30, 60, 60)

    def draw_component_body(self, painter):
        # Terminal leads
        if self.scene() is not None:
            painter.drawLine(-20, 0, -8, 0)       # Base lead
            painter.drawLine(8, -12, 20, -20)      # Collector lead
            painter.drawLine(8, 12, 20, 20)        # Emitter lead

        # Vertical base bar
        painter.drawLine(-8, -12, -8, 12)

        # Collector line (from bar to upper-right)
        painter.drawLine(-8, -6, 8, -12)

        # Emitter line (from bar to lower-right)
        painter.drawLine(-8, 6, 8, 12)

        # Arrow on emitter (pointing outward for NPN)
        painter.drawLine(8, 12, 4, 7)
        painter.drawLine(8, 12, 3, 12)

    def get_obstacle_shape(self):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class BJTPNP(ComponentItem):
    """PNP Bipolar Junction Transistor"""
    type_name = 'BJT PNP'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-30, -30, 60, 60)

    def draw_component_body(self, painter):
        # Terminal leads
        if self.scene() is not None:
            painter.drawLine(-20, 0, -8, 0)       # Base lead
            painter.drawLine(8, -12, 20, -20)      # Collector lead
            painter.drawLine(8, 12, 20, 20)        # Emitter lead

        # Vertical base bar
        painter.drawLine(-8, -12, -8, 12)

        # Collector line (from bar to upper-right)
        painter.drawLine(-8, -6, 8, -12)

        # Emitter line (from bar to lower-right)
        painter.drawLine(-8, 6, 8, 12)

        # Arrow on emitter (pointing inward for PNP)
        painter.drawLine(-8, 6, -3, 2)
        painter.drawLine(-8, 6, -3, 7)

    def get_obstacle_shape(self):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class MOSFETNMOS(ComponentItem):
    """N-Channel MOSFET (M element)"""
    type_name = 'MOSFET NMOS'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        # Terminal lines: Drain (top-right), Gate (left), Source (bottom-right)
        if self.scene() is not None:
            painter.drawLine(20, -20, 20, -10)   # Drain terminal line
            painter.drawLine(-20, 0, -10, 0)     # Gate terminal line
            painter.drawLine(20, 20, 20, 10)     # Source terminal line

        # Gate vertical line
        painter.drawLine(-10, -12, -10, 12)

        # Channel line (vertical bar separated from gate)
        painter.drawLine(-5, -12, -5, 12)

        # Drain connection: horizontal from channel to drain terminal
        painter.drawLine(-5, -10, 20, -10)

        # Source connection: horizontal from channel to source terminal
        painter.drawLine(-5, 10, 20, 10)

        # Body connection (center of channel)
        painter.drawLine(-5, 0, 5, 0)

        # Arrow on source line pointing inward (NMOS indicator)
        painter.drawLine(-5, 10, -1, 7)
        painter.drawLine(-5, 10, -1, 13)

    def get_obstacle_shape(self):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class MOSFETPMOS(ComponentItem):
    """P-Channel MOSFET (M element)"""
    type_name = 'MOSFET PMOS'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def draw_component_body(self, painter):
        # Terminal lines: Drain (top-right), Gate (left), Source (bottom-right)
        if self.scene() is not None:
            painter.drawLine(20, -20, 20, -10)   # Drain terminal line
            painter.drawLine(-20, 0, -10, 0)     # Gate terminal line
            painter.drawLine(20, 20, 20, 10)     # Source terminal line

        # Gate vertical line
        painter.drawLine(-10, -12, -10, 12)

        # Channel line (vertical bar separated from gate) — gap for PMOS
        painter.drawLine(-5, -12, -5, 12)

        # Drain connection
        painter.drawLine(-5, -10, 20, -10)

        # Source connection
        painter.drawLine(-5, 10, 20, 10)

        # Body connection
        painter.drawLine(-5, 0, 5, 0)

        # Arrow on source line pointing outward (PMOS indicator)
        painter.drawLine(0, 10, -4, 7)
        painter.drawLine(0, 10, -4, 13)

        # Circle on gate to indicate PMOS (inversion bubble)
        painter.drawEllipse(-8, -2, 4, 4)

    def get_obstacle_shape(self):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class VCSwitch(ComponentItem):
    """Voltage-Controlled Switch (S element)"""
    type_name = 'VC Switch'

    def __init__(self, component_id, model=None):
        super().__init__(component_id, self.type_name, model=model)

    def boundingRect(self):
        return QRectF(-40, -25, 80, 50)

    def draw_component_body(self, painter):
        # Control and switch path terminal lines
        if self.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)   # ctrl+ terminal
            painter.drawLine(-30, 10, -15, 10)     # ctrl- terminal
            painter.drawLine(15, -10, 30, -10)     # switch+ terminal
            painter.drawLine(15, 10, 30, 10)       # switch- terminal

        # Box outline for the switch body
        painter.drawRect(-15, -15, 30, 30)

        # Switch symbol inside: open switch (angled line)
        painter.drawLine(-8, 8, 8, -4)
        # Contact dots
        painter.drawEllipse(-10, 6, 4, 4)
        painter.drawEllipse(6, -4, 4, 4)

        # Control arrow from left side
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawLine(-12, 0, -5, 0)
        painter.drawLine(-7, -2, -5, 0)
        painter.drawLine(-7, 2, -5, 0)

    def get_obstacle_shape(self):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


# Component registry for factory pattern
COMPONENT_CLASSES = {
    'Resistor': Resistor,
    'Capacitor': Capacitor,
    'Inductor': Inductor,
    'VoltageSource': VoltageSource,
    'CurrentSource': CurrentSource,
    'Voltage Source': VoltageSource,
    'Current Source': CurrentSource,
    'WaveformVoltageSource': WaveformVoltageSource,
    'Waveform Source': WaveformVoltageSource,
    'Ground': Ground,
    'OpAmp': OpAmp,
    'Op-Amp': OpAmp,
    'VCVS': VCVS,
    'VoltageControlledVoltageSource': VCVS,
    'CCVS': CCVS,
    'CurrentControlledVoltageSource': CCVS,
    'VCCS': VCCS,
    'VoltageControlledCurrentSource': VCCS,
    'CCCS': CCCS,
    'CurrentControlledCurrentSource': CCCS,
    'BJT NPN': BJTNPN,
    'BJT PNP': BJTPNP,
    'MOSFET NMOS': MOSFETNMOS,
    'MOSFETNMOS': MOSFETNMOS,
    'MOSFET PMOS': MOSFETPMOS,
    'MOSFETPMOS': MOSFETPMOS,
    'VC Switch': VCSwitch,
    'VCSwitch': VCSwitch,
}


def create_component(component_type, component_id):
    """Factory function to create components with a backing ComponentData model"""
    component_class = COMPONENT_CLASSES.get(component_type)
    if component_class is None:
        raise ValueError(f"Unknown component type: {component_type}")

    comp_model = ComponentData(
        component_id=component_id,
        component_type=component_type,
        value=DEFAULT_VALUES.get(component_type, '1u'),
        position=(0.0, 0.0),
    )
    return component_class(component_id, model=comp_model)
