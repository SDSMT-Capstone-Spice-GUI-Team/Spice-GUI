from collections import OrderedDict

from PyQt6.QtCore import QMimeData, QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QDrag, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLineEdit, QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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

# Component categories (ordered)
COMPONENT_CATEGORIES: OrderedDict[str, list[str]] = OrderedDict(
    [
        ("Passive", ["Resistor", "Capacitor", "Inductor"]),
        ("Sources", ["Voltage Source", "Current Source", "Waveform Source"]),
        (
            "Semiconductors",
            [
                "Diode",
                "LED",
                "Zener Diode",
                "BJT NPN",
                "BJT PNP",
                "MOSFET NMOS",
                "MOSFET PMOS",
            ],
        ),
        ("Controlled Sources", ["VCVS", "CCVS", "VCCS", "CCCS"]),
        ("Other", ["Op-Amp", "VC Switch", "Transformer", "Ground"]),
    ]
)

_FAVORITES_CATEGORY = "Favorites"


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
    """Component palette with collapsible categories, pinned favorites, search filter, and drag support."""

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

        # Category tree
        self.tree_widget = _PaletteTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIconSize(QSize(48, 48))
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.tree_widget.setIndentation(16)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setRootIsDecorated(True)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)

        self._category_items: dict[str, QTreeWidgetItem] = {}
        self._favorites: list[str] = self._load_favorites()
        self._populate_tree()
        self._restore_collapse_state()

        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.itemExpanded.connect(self._save_collapse_state)
        self.tree_widget.itemCollapsed.connect(self._save_collapse_state)
        layout.addWidget(self.tree_widget)

    def _populate_tree(self):
        """Build category tree with favorites section and component categories."""
        # Favorites section (only visible when non-empty)
        self._favorites_item = QTreeWidgetItem(self.tree_widget, [_FAVORITES_CATEGORY])
        self._favorites_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = self._favorites_item.font(0)
        font.setBold(True)
        self._favorites_item.setFont(0, font)
        self._category_items[_FAVORITES_CATEGORY] = self._favorites_item
        self._rebuild_favorites_children()

        # Regular categories
        for category_name, component_names in COMPONENT_CATEGORIES.items():
            category_item = QTreeWidgetItem(self.tree_widget, [category_name])
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            cat_font = category_item.font(0)
            cat_font.setBold(True)
            category_item.setFont(0, cat_font)
            self._category_items[category_name] = category_item

            for component_name in component_names:
                if component_name not in COMPONENTS:
                    continue
                child = QTreeWidgetItem(category_item, [component_name])
                child.setIcon(0, create_component_icon(component_name))
                child.setToolTip(0, COMPONENT_TOOLTIPS.get(component_name, component_name))
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

    def _rebuild_favorites_children(self):
        """Rebuild the children of the Favorites category from the favorites list."""
        # Remove existing children
        while self._favorites_item.childCount() > 0:
            self._favorites_item.removeChild(self._favorites_item.child(0))

        # Add current favorites
        for component_name in self._favorites:
            if component_name not in COMPONENTS:
                continue
            child = QTreeWidgetItem(self._favorites_item, [component_name])
            child.setIcon(0, create_component_icon(component_name))
            child.setToolTip(0, COMPONENT_TOOLTIPS.get(component_name, component_name))
            child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

        # Hide Favorites when empty
        self._favorites_item.setHidden(len(self._favorites) == 0)
        if self._favorites:
            self._favorites_item.setExpanded(True)

    def _load_favorites(self) -> list[str]:
        """Load pinned favorites from QSettings."""
        settings = QSettings("SDSMT", "SDM Spice")
        raw = settings.value("palette/favorites", [])
        if isinstance(raw, str):
            return [raw] if raw else []
        if isinstance(raw, list):
            return [f for f in raw if f in COMPONENTS]
        return []

    def _save_favorites(self):
        """Persist pinned favorites to QSettings."""
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("palette/favorites", self._favorites)

    def _show_context_menu(self, position):
        """Show right-click context menu for pin/unpin."""
        item = self.tree_widget.itemAt(position)
        if item is None or item.parent() is None:
            return

        component_name = item.text(0)
        if component_name not in COMPONENTS:
            return

        menu = QMenu(self.tree_widget)
        if component_name in self._favorites:
            action = QAction("Unpin from Favorites", menu)
            action.triggered.connect(lambda: self._unpin_favorite(component_name))
        else:
            action = QAction("Pin to Favorites", menu)
            action.triggered.connect(lambda: self._pin_favorite(component_name))
        menu.addAction(action)
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _pin_favorite(self, component_name):
        """Add a component to the favorites list."""
        if component_name not in self._favorites:
            self._favorites.append(component_name)
            self._save_favorites()
            self._rebuild_favorites_children()

    def _unpin_favorite(self, component_name):
        """Remove a component from the favorites list."""
        if component_name in self._favorites:
            self._favorites.remove(component_name)
            self._save_favorites()
            self._rebuild_favorites_children()

    def get_favorites(self) -> list[str]:
        """Return the current list of pinned favorites."""
        return list(self._favorites)

    def _restore_collapse_state(self):
        """Restore expanded/collapsed state from QSettings."""
        settings = QSettings("SDSMT", "SDM Spice")
        for category_name, item in self._category_items.items():
            if category_name == _FAVORITES_CATEGORY:
                continue  # Favorites always expanded when visible
            key = f"palette/collapsed/{category_name}"
            collapsed = settings.value(key, False)
            is_collapsed = collapsed == "true" or collapsed is True
            item.setExpanded(not is_collapsed)

    def _save_collapse_state(self, _item=None):
        """Persist expanded/collapsed state to QSettings."""
        settings = QSettings("SDSMT", "SDM Spice")
        for category_name, item in self._category_items.items():
            if category_name == _FAVORITES_CATEGORY:
                continue
            key = f"palette/collapsed/{category_name}"
            settings.setValue(key, not item.isExpanded())

    def _on_item_double_clicked(self, item, _column):
        """Handle double-click: emit signal only for component items (not categories)."""
        if item.parent() is not None:
            self.componentDoubleClicked.emit(item.text(0))

    def _filter_components(self, text):
        """Show/hide components based on search text; auto-expand matching categories."""
        text = text.lower()
        for category_name, category_item in self._category_items.items():
            any_visible = False
            for i in range(category_item.childCount()):
                child = category_item.child(i)
                name = child.text(0).lower()
                tooltip = (child.toolTip(0) or "").lower()
                matches = not text or text in name or text in tooltip
                child.setHidden(not matches)
                if matches:
                    any_visible = True

            if category_name == _FAVORITES_CATEGORY:
                # Favorites hidden when empty OR no search matches
                category_item.setHidden(not any_visible or not self._favorites)
            else:
                category_item.setHidden(not any_visible)

            if text and any_visible:
                category_item.setExpanded(True)
            elif not text:
                if category_name == _FAVORITES_CATEGORY:
                    if self._favorites:
                        category_item.setExpanded(True)
                else:
                    self._restore_collapse_state()

    def get_component_names(self):
        """Return list of all component names across all categories (excluding favorites duplicates)."""
        names = []
        for cat_name, category_item in self._category_items.items():
            if cat_name == _FAVORITES_CATEGORY:
                continue
            for i in range(category_item.childCount()):
                names.append(category_item.child(i).text(0))
        return names

    def get_visible_component_names(self):
        """Return list of currently visible (not hidden) component names (excluding favorites duplicates)."""
        names = []
        for cat_name, category_item in self._category_items.items():
            if cat_name == _FAVORITES_CATEGORY:
                continue
            if category_item.isHidden():
                continue
            for i in range(category_item.childCount()):
                child = category_item.child(i)
                if not child.isHidden():
                    names.append(child.text(0))
        return names

    def get_category_names(self):
        """Return ordered list of category names (excluding hidden Favorites)."""
        names = []
        for name in self._category_items:
            if name == _FAVORITES_CATEGORY and not self._favorites:
                continue
            names.append(name)
        return names

    def is_category_expanded(self, category_name):
        """Return whether a category is currently expanded."""
        item = self._category_items.get(category_name)
        if item is None:
            return False
        return item.isExpanded()


class _PaletteTreeWidget(QTreeWidget):
    """Internal tree widget with drag support for the component palette."""

    def startDrag(self, supportedActions):
        """Start drag operation with component name as text mime data."""
        item = self.currentItem()
        if item and item.parent() is not None:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text(0))
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)
