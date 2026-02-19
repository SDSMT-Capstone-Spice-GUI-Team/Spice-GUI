from models.component import COMPONENT_CATEGORIES
from PyQt6.QtCore import QMimeData, QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QDrag, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .component_item import COMPONENT_CLASSES
from .styles import COMPONENTS, theme_manager

# Brief descriptions for each component type
COMPONENT_TOOLTIPS = {
    "Resistor": "Resistor (R) — Resists current flow",
    "Capacitor": "Capacitor (C) — Stores energy in an electric field",
    "Inductor": "Inductor (L) — Stores energy in a magnetic field",
    "Voltage Source": "Voltage Source (V) — Provides a constant voltage",
    "Current Source": "Current Source (I) — Provides a constant current",
    "Waveform Source": "Waveform Source (VW) — Time-varying voltage source",
    "Ground": "Ground (GND) — Zero-volt reference node",
    "Op-Amp": "Op-Amp (OA) — Operational amplifier",
    "VCVS": "VCVS (E) — Voltage-controlled voltage source",
    "CCVS": "CCVS (H) — Current-controlled voltage source",
    "VCCS": "VCCS (G) — Voltage-controlled current source",
    "CCCS": "CCCS (F) — Current-controlled current source",
    "BJT NPN": "BJT NPN (Q) — NPN bipolar junction transistor",
    "BJT PNP": "BJT PNP (Q) — PNP bipolar junction transistor",
    "MOSFET NMOS": "MOSFET NMOS (M) — N-channel MOSFET",
    "MOSFET PMOS": "MOSFET PMOS (M) — P-channel MOSFET",
    "VC Switch": "VC Switch (S) — Voltage-controlled switch",
    "Diode": "Diode (D) — Allows current in one direction",
    "LED": "LED (D) — Light-emitting diode",
    "Zener Diode": "Zener Diode (D) — Voltage-regulating diode",
    "Transformer": "Transformer (K) — Coupled inductors / ideal transformer",
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

    temp_comp = component_class("temp")

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


class ComponentPalette(QWidget):
    """Component palette with collapsible category groups, search filter, and drag support"""

    # Signal emitted when component is double-clicked
    componentDoubleClicked = pyqtSignal(str)  # component_type

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Search filter
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter components...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_components)
        layout.addWidget(self.search_input)

        # Component tree with collapsible categories
        self.tree_widget = _PaletteTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.tree_widget.setIconSize(QSize(48, 48))
        self.tree_widget.setIndentation(16)
        self.tree_widget.setAnimated(True)

        # Track category items for persistence and search
        self._category_items: dict[str, QTreeWidgetItem] = {}

        # Load saved expanded state
        expanded_state = self._load_expanded_state()

        for category_name, component_names in COMPONENT_CATEGORIES.items():
            category_item = QTreeWidgetItem(self.tree_widget, [category_name])
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # clickable but not selectable/draggable
            bold_font = QFont()
            bold_font.setBold(True)
            category_item.setFont(0, bold_font)
            self._category_items[category_name] = category_item

            for component_name in component_names:
                if component_name not in COMPONENTS:
                    continue
                child = QTreeWidgetItem(category_item, [component_name])
                child.setIcon(0, create_component_icon(component_name))
                child.setToolTip(0, COMPONENT_TOOLTIPS.get(component_name, component_name))
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

            # Restore expanded state (default: expanded)
            is_expanded = expanded_state.get(category_name, True)
            category_item.setExpanded(is_expanded)

        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.itemExpanded.connect(self._save_expanded_state)
        self.tree_widget.itemCollapsed.connect(self._save_expanded_state)
        layout.addWidget(self.tree_widget)

    def _on_item_double_clicked(self, item, column):
        """Handle double-click on palette item (ignore category headers)."""
        if item.parent() is not None:
            self.componentDoubleClicked.emit(item.text(0))

    def _filter_components(self, text):
        """Show/hide components based on search text. Auto-expand matching categories."""
        text = text.lower()
        is_searching = bool(text)

        for category_name, category_item in self._category_items.items():
            any_child_visible = False
            for i in range(category_item.childCount()):
                child = category_item.child(i)
                name = child.text(0).lower()
                tooltip = (child.toolTip(0) or "").lower()
                matches = text in name or text in tooltip
                child.setHidden(not matches)
                if matches:
                    any_child_visible = True

            # Hide entire category if no children match
            category_item.setHidden(not any_child_visible)

            # Auto-expand categories with matches during search
            if is_searching and any_child_visible:
                category_item.setExpanded(True)

        # Restore saved expanded state when search is cleared
        if not is_searching:
            saved_state = self._load_expanded_state()
            for category_name, category_item in self._category_items.items():
                category_item.setExpanded(saved_state.get(category_name, True))

    def _load_expanded_state(self) -> dict[str, bool]:
        """Load category expanded/collapsed state from QSettings."""
        settings = QSettings("SDSMT", "SDM Spice")
        state = {}
        for category_name in COMPONENT_CATEGORIES:
            val = settings.value(f"palette/expanded/{category_name}")
            if val is not None:
                state[category_name] = val == "true" or val is True
            else:
                state[category_name] = True  # default expanded
        return state

    def _save_expanded_state(self, _item=None):
        """Save category expanded/collapsed state to QSettings."""
        # Don't save while searching (search auto-expands categories)
        if self.search_input.text():
            return
        settings = QSettings("SDSMT", "SDM Spice")
        for category_name, category_item in self._category_items.items():
            settings.setValue(f"palette/expanded/{category_name}", category_item.isExpanded())

    def get_all_component_items(self) -> list[QTreeWidgetItem]:
        """Return all component (leaf) items across all categories."""
        items = []
        for category_item in self._category_items.values():
            for i in range(category_item.childCount()):
                items.append(category_item.child(i))
        return items


class _PaletteTreeWidget(QTreeWidget):
    """Internal tree widget with drag support for the component palette."""

    def startDrag(self, supportedActions):
        """Start drag operation for component items only."""
        item = self.currentItem()
        if item and item.parent() is not None:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text(0))
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)
