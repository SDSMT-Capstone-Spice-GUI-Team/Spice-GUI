from models.component import COMPONENT_CATEGORIES
from PyQt6.QtCore import QMimeData, QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QDrag, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLineEdit, QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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
    """Component palette with collapsible category groups, search filter, drag support, and pinned favorites"""

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

        # Component tree with collapsible categories
        self.tree_widget = _PaletteTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.tree_widget.setIconSize(QSize(48, 48))
        self.tree_widget.setIndentation(16)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)

        # Track category items for persistence and search
        self._category_items: dict[str, QTreeWidgetItem] = {}

        # Load saved expanded state
        expanded_state = self._load_expanded_state()

        # Build the favorites section and category tree
        self._rebuild_favorites()

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
                child.setData(0, ITEM_ROLE, ITEM_TYPE_COMPONENT)
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

    def _rebuild_favorites(self):
        """Rebuild the favorites section at the top of the tree widget."""
        # Remove existing favorites category if present
        if FAVORITES_HEADER_TEXT in self._category_items:
            old_fav = self._category_items.pop(FAVORITES_HEADER_TEXT)
            index = self.tree_widget.indexOfTopLevelItem(old_fav)
            if index >= 0:
                self.tree_widget.takeTopLevelItem(index)

        if not self._favorites:
            return

        # Create favorites category at the top
        fav_category = QTreeWidgetItem([FAVORITES_HEADER_TEXT])
        fav_category.setData(0, ITEM_ROLE, ITEM_TYPE_HEADER)
        fav_category.setFlags(Qt.ItemFlag.ItemIsEnabled)
        bold_font = QFont()
        bold_font.setBold(True)
        fav_category.setFont(0, bold_font)

        for component_name in self._favorites:
            child = QTreeWidgetItem(fav_category, [component_name])
            child.setData(0, ITEM_ROLE, ITEM_TYPE_FAVORITE)
            child.setIcon(0, create_component_icon(component_name))
            child.setToolTip(0, COMPONENT_TOOLTIPS.get(component_name, component_name))
            child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

        # Insert at position 0 (top of tree)
        self.tree_widget.insertTopLevelItem(0, fav_category)
        fav_category.setExpanded(True)
        self._category_items[FAVORITES_HEADER_TEXT] = fav_category

    def _show_context_menu(self, position):
        """Show right-click context menu for pin/unpin actions."""
        item = self.tree_widget.itemAt(position)
        if item is None:
            return
        # Only show menu for component/favorite items (not category headers)
        if item.parent() is None:
            return

        component_name = item.text(0)
        menu = QMenu(self)

        if component_name in self._favorites:
            action = menu.addAction("Unpin from Favorites")
            action.triggered.connect(lambda: self._unpin_favorite(component_name))
        else:
            action = menu.addAction("Pin to Favorites")
            action.triggered.connect(lambda: self._pin_favorite(component_name))

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _pin_favorite(self, component_name):
        """Pin a component to favorites."""
        if component_name not in self._favorites:
            self._favorites.append(component_name)
            _save_favorites(self._favorites)
            self._rebuild_favorites()
            # Re-apply current filter if active
            if self.search_input.text():
                self._filter_components(self.search_input.text())

    def _unpin_favorite(self, component_name):
        """Unpin a component from favorites."""
        if component_name in self._favorites:
            self._favorites.remove(component_name)
            _save_favorites(self._favorites)
            self._rebuild_favorites()
            # Re-apply current filter if active
            if self.search_input.text():
                self._filter_components(self.search_input.text())

    def get_favorites(self):
        """Return the current list of pinned favorites."""
        return list(self._favorites)

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
                if category_name == FAVORITES_HEADER_TEXT:
                    # Favorites are always expanded
                    category_item.setExpanded(True)
                else:
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
            # Don't save favorites expanded state (always expanded)
            if category_name == FAVORITES_HEADER_TEXT:
                continue
            settings.setValue(f"palette/expanded/{category_name}", category_item.isExpanded())

    def get_all_component_items(self) -> list[QTreeWidgetItem]:
        """Return all component (leaf) items across all categories (excluding favorites)."""
        items = []
        for category_name, category_item in self._category_items.items():
            if category_name == FAVORITES_HEADER_TEXT:
                continue
            for i in range(category_item.childCount()):
                items.append(category_item.child(i))
        return items

    def get_favorite_items(self) -> list[QTreeWidgetItem]:
        """Return all favorite (leaf) items from the favorites category."""
        fav_category = self._category_items.get(FAVORITES_HEADER_TEXT)
        if fav_category is None:
            return []
        return [fav_category.child(i) for i in range(fav_category.childCount())]


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
