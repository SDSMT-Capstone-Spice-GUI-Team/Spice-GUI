from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QMimeData, QSize, pyqtSignal
from PyQt6.QtGui import QDrag, QIcon, QPixmap, QPainter, QPen, QBrush
from .styles import COMPONENTS, theme_manager
from .component_item import COMPONENT_CLASSES

# Brief descriptions for each component type
COMPONENT_TOOLTIPS = {
    'Resistor': 'Resistor (R) — Resists current flow',
    'Capacitor': 'Capacitor (C) — Stores energy in an electric field',
    'Inductor': 'Inductor (L) — Stores energy in a magnetic field',
    'Voltage Source': 'Voltage Source (V) — Provides a constant voltage',
    'Current Source': 'Current Source (I) — Provides a constant current',
    'Waveform Source': 'Waveform Source (VW) — Time-varying voltage source',
    'Ground': 'Ground (GND) — Zero-volt reference node',
    'Op-Amp': 'Op-Amp (OA) — Operational amplifier',
    'VCVS': 'VCVS (E) — Voltage-controlled voltage source',
    'CCVS': 'CCVS (H) — Current-controlled voltage source',
    'VCCS': 'VCCS (G) — Voltage-controlled current source',
    'CCCS': 'CCCS (F) — Current-controlled current source',
    'BJT NPN': 'BJT NPN (Q) — NPN bipolar junction transistor',
    'BJT PNP': 'BJT PNP (Q) — PNP bipolar junction transistor',
    'MOSFET NMOS': 'MOSFET NMOS (M) — N-channel MOSFET',
    'MOSFET PMOS': 'MOSFET PMOS (M) — P-channel MOSFET',
    'VC Switch': 'VC Switch (S) — Voltage-controlled switch',
    'Diode': 'Diode (D) — Allows current in one direction',
    'LED': 'LED (D) — Light-emitting diode',
    'Zener Diode': 'Zener Diode (D) — Voltage-regulating diode',
}


def create_component_icon(component_type, size=48):
    """Create a QIcon by rendering component symbol to QPixmap"""
    # Create transparent pixmap
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    # Get component class and create temp instance
    component_class = COMPONENT_CLASSES.get(component_type)
    if not component_class:
        return QIcon()

    temp_comp = component_class('temp')

    # Paint component symbol
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Set up painter with theme color
    color = theme_manager.get_component_color(temp_comp.component_type)
    painter.setPen(QPen(color, 2))
    painter.setBrush(QBrush(color.lighter(150)))

    # Center and scale to fit icon
    painter.translate(size / 2, size / 2)
    painter.scale(0.8, 0.8)

    # Draw the component body
    temp_comp.draw_component_body(painter)
    painter.end()

    return QIcon(pixmap)

class ComponentPalette(QListWidget):
    """Component palette with drag support"""

    # Signal emitted when component is double-clicked
    componentDoubleClicked = pyqtSignal(str)  # component_type

    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setIconSize(QSize(48, 48))
        self.setSpacing(4)

        for component_name in COMPONENTS.keys():
            item = QListWidgetItem(component_name)
            item.setIcon(create_component_icon(component_name))
            item.setToolTip(COMPONENT_TOOLTIPS.get(component_name, component_name))
            self.addItem(item)

        # Connect double-click to emit signal
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _on_item_double_clicked(self, item):
        """Handle double-click on palette item"""
        self.componentDoubleClicked.emit(item.text())
    
    def startDrag(self, supportedActions):
        """Start drag operation"""
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)
