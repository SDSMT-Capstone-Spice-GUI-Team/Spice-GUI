from PyQt6.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QDrag, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QMenu, QVBoxLayout, QWidget

from .component_item import COMPONENT_CLASSES
from .styles import COMPONENTS, theme_manager

# Custom data role to distinguish item types
ITEM_ROLE = Qt.ItemDataRole.UserRole
ITEM_TYPE_HEADER = "header"
ITEM_TYPE_FAVORITE = "favorite"
ITEM_TYPE_COMPONENT = "component"

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

FAVORITES_HEADER_TEXT = "\u2605 Favorites"


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


def _load_favorites():
    """Load pinned favorites from QSettings."""
    from PyQt6.QtCore import QSettings

    settings = QSettings("SDSMT", "SDM Spice")
    raw = settings.value("palette/favorites", [])
    if isinstance(raw, str):
        # QSettings may return a single string instead of a list
        return [raw] if raw else []
    if raw is None:
        return []
    return [f for f in raw if f in COMPONENTS]


def _save_favorites(favorites):
    """Save pinned favorites to QSettings."""
    from PyQt6.QtCore import QSettings

    settings = QSettings("SDSMT", "SDM Spice")
    settings.setValue("palette/favorites", list(favorites))


class ComponentPalette(QWidget):
    """Component palette with search filter, drag support, and pinned favorites"""

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

        # Load persisted favorites
        self._favorites = _load_favorites()

        # Component list
        self.list_widget = _PaletteListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setSpacing(4)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)

        self._rebuild_list()

        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

    def _rebuild_list(self):
        """Rebuild the list widget with favorites section and all components."""
        self.list_widget.clear()

        # Add favorites section if there are pinned items
        if self._favorites:
            header = QListWidgetItem(FAVORITES_HEADER_TEXT)
            header.setData(ITEM_ROLE, ITEM_TYPE_HEADER)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            bold_font = QFont()
            bold_font.setBold(True)
            header.setFont(bold_font)
            self.list_widget.addItem(header)

            for component_name in self._favorites:
                item = QListWidgetItem(component_name)
                item.setData(ITEM_ROLE, ITEM_TYPE_FAVORITE)
                item.setIcon(create_component_icon(component_name))
                tooltip = COMPONENT_TOOLTIPS.get(component_name, component_name)
                item.setToolTip(tooltip)
                self.list_widget.addItem(item)

        # Add all components
        for component_name in COMPONENTS.keys():
            item = QListWidgetItem(component_name)
            item.setData(ITEM_ROLE, ITEM_TYPE_COMPONENT)
            item.setIcon(create_component_icon(component_name))
            item.setToolTip(COMPONENT_TOOLTIPS.get(component_name, component_name))
            self.list_widget.addItem(item)

        # Re-apply current filter if active
        if self.search_input.text():
            self._filter_components(self.search_input.text())

    def _show_context_menu(self, position):
        """Show right-click context menu for pin/unpin actions."""
        item = self.list_widget.itemAt(position)
        if item is None:
            return
        item_type = item.data(ITEM_ROLE)
        if item_type == ITEM_TYPE_HEADER:
            return

        component_name = item.text()
        menu = QMenu(self)

        if component_name in self._favorites:
            action = menu.addAction("Unpin from Favorites")
            action.triggered.connect(lambda: self._unpin_favorite(component_name))
        else:
            action = menu.addAction("Pin to Favorites")
            action.triggered.connect(lambda: self._pin_favorite(component_name))

        menu.exec(self.list_widget.viewport().mapToGlobal(position))

    def _pin_favorite(self, component_name):
        """Pin a component to favorites."""
        if component_name not in self._favorites:
            self._favorites.append(component_name)
            _save_favorites(self._favorites)
            self._rebuild_list()

    def _unpin_favorite(self, component_name):
        """Unpin a component from favorites."""
        if component_name in self._favorites:
            self._favorites.remove(component_name)
            _save_favorites(self._favorites)
            self._rebuild_list()

    def get_favorites(self):
        """Return the current list of pinned favorites."""
        return list(self._favorites)

    def _on_item_double_clicked(self, item):
        """Handle double-click on palette item"""
        item_type = item.data(ITEM_ROLE)
        if item_type == ITEM_TYPE_HEADER:
            return
        self.componentDoubleClicked.emit(item.text())

    def _filter_components(self, text):
        """Show/hide components based on search text."""
        text = text.lower()
        has_visible_favorite = False

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item is None:
                continue
            item_type = item.data(ITEM_ROLE)

            if item_type == ITEM_TYPE_HEADER:
                # Header visibility is set after scanning favorites
                continue

            name = item.text().lower()
            tooltip = (item.toolTip() or "").lower()
            matches = not text or text in name or text in tooltip
            item.setHidden(not matches)

            if item_type == ITEM_TYPE_FAVORITE and matches:
                has_visible_favorite = True

        # Show/hide the favorites header based on whether any favorites match
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item is not None and item.data(ITEM_ROLE) == ITEM_TYPE_HEADER:
                item.setHidden(not has_visible_favorite)
                break


class _PaletteListWidget(QListWidget):
    """Internal list widget with drag support for the component palette."""

    def startDrag(self, supportedActions):
        """Start drag operation"""
        item = self.currentItem()
        if item and item.data(ITEM_ROLE) != ITEM_TYPE_HEADER:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)
