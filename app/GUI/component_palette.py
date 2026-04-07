from controllers.settings_service import settings as app_settings
from models.builtin_subcircuits import register_builtin_subcircuits
from models.component import COMPONENT_CATEGORIES
from PyQt6.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QDrag, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .component_item import COMPONENT_CLASSES
from .styles import COMPONENTS, theme_manager

# Register built-in subcircuit components (voltage regulators etc.) so they
# appear in COMPONENT_CATEGORIES["Subcircuits"] before the palette is built.
register_builtin_subcircuits()

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

# Name for the recommended section in the palette
_RECOMMENDED_CATEGORY = "Recommended"

# Name for the used-in-file section in the palette
_USED_IN_FILE_CATEGORY = "Used in File"


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
        self.tree_widget.setRootIsDecorated(False)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.tree_widget.setIconSize(QSize(48, 48))
        self.tree_widget.setIndentation(16)
        self.tree_widget.setAnimated(True)

        # Track category items for persistence and search
        self._category_items: dict[str, QTreeWidgetItem] = {}

        # Track the recommended section separately
        self._recommended_item: QTreeWidgetItem | None = None
        self._recommended_components: list[str] = []

        # Track the "Used in File" section
        self._used_in_file_item: QTreeWidgetItem | None = None

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

        self.tree_widget.itemClicked.connect(self._on_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.itemExpanded.connect(self._save_expanded_state)
        self.tree_widget.itemCollapsed.connect(self._save_expanded_state)
        layout.addWidget(self.tree_widget)

        # Refresh cached icons whenever the theme, symbol style, or color
        # mode changes so the palette stays in sync with the canvas.
        theme_manager.on_theme_changed(self._on_theme_changed)

    def _on_theme_changed(self, _theme=None) -> None:
        """Regenerate all cached palette icons using current theme settings."""
        def walk(parent: QTreeWidgetItem) -> None:
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.childCount() > 0:
                    walk(child)
                else:
                    name = child.text(0)
                    if name in COMPONENTS:
                        try:
                            child.setIcon(0, create_component_icon(name))
                        except Exception:
                            pass

        walk(self.tree_widget.invisibleRootItem())

    def _on_item_clicked(self, item, column):
        """Toggle expand/collapse when a category header is clicked."""
        if item.parent() is None:
            item.setExpanded(not item.isExpanded())

    def _on_item_double_clicked(self, item, column):
        """Handle double-click on palette item (ignore category headers)."""
        if item.parent() is not None:
            self.componentDoubleClicked.emit(item.text(0))

    def set_recommended_components(self, component_names: list[str]) -> None:
        """Set file-level recommended components.

        When recommendations are active a "Recommended" section appears at the
        top of the palette and all other categories are auto-collapsed.  When
        the list is empty the section is removed and categories are restored.
        """
        # Validate names against known component types
        valid_names = [n for n in component_names if n in COMPONENTS]
        self._recommended_components = valid_names

        # Remove previous recommended section if it exists
        self._remove_recommended_section()

        if not valid_names:
            # Restore user-preferred expanded state
            saved_state = self._load_expanded_state()
            for category_name, category_item in self._category_items.items():
                category_item.setExpanded(saved_state.get(category_name, True))
            return

        # Create the Recommended category at the top of the tree
        rec_item = QTreeWidgetItem()
        rec_item.setText(0, _RECOMMENDED_CATEGORY)
        rec_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setItalic(True)
        rec_item.setFont(0, bold_font)

        for component_name in valid_names:
            child = QTreeWidgetItem(rec_item, [component_name])
            child.setIcon(0, create_component_icon(component_name))
            child.setToolTip(0, COMPONENT_TOOLTIPS.get(component_name, component_name))
            child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

        # Insert at position 0 (top of tree)
        self.tree_widget.insertTopLevelItem(0, rec_item)
        rec_item.setExpanded(True)
        self._recommended_item = rec_item

        # Auto-collapse all other categories when recommendations are active
        for category_item in self._category_items.values():
            category_item.setExpanded(False)

    def get_recommended_components(self) -> list[str]:
        """Return the current list of recommended component names."""
        return list(self._recommended_components)

    def has_recommendations(self) -> bool:
        """Return True when file-level recommendations are active."""
        return self._recommended_item is not None

    def _remove_recommended_section(self) -> None:
        """Remove the Recommended top-level item if present."""
        if self._recommended_item is not None:
            index = self.tree_widget.indexOfTopLevelItem(self._recommended_item)
            if index >= 0:
                self.tree_widget.takeTopLevelItem(index)
            self._recommended_item = None

    def _filter_components(self, text):
        """Show/hide components based on search text. Auto-expand matching categories."""
        text = text.lower()
        is_searching = bool(text)

        # Filter the recommended section
        if self._recommended_item is not None:
            any_rec_visible = False
            for i in range(self._recommended_item.childCount()):
                child = self._recommended_item.child(i)
                name = child.text(0).lower()
                tooltip = (child.toolTip(0) or "").lower()
                matches = text in name or text in tooltip
                child.setHidden(not matches)
                if matches:
                    any_rec_visible = True
            self._recommended_item.setHidden(not any_rec_visible)
            if is_searching and any_rec_visible:
                self._recommended_item.setExpanded(True)

        # Filter the "Used in File" section
        if self._used_in_file_item is not None:
            any_uif_visible = False
            for i in range(self._used_in_file_item.childCount()):
                child = self._used_in_file_item.child(i)
                name = child.text(0).lower()
                tooltip = (child.toolTip(0) or "").lower()
                matches = text in name or text in tooltip
                child.setHidden(not matches)
                if matches:
                    any_uif_visible = True
            self._used_in_file_item.setHidden(not any_uif_visible)
            if is_searching and any_uif_visible:
                self._used_in_file_item.setExpanded(True)

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
            if self._recommended_item is not None:
                # Recommendations active: keep others collapsed
                for category_item in self._category_items.values():
                    category_item.setExpanded(False)
                self._recommended_item.setExpanded(True)
            else:
                saved_state = self._load_expanded_state()
                for category_name, category_item in self._category_items.items():
                    category_item.setExpanded(saved_state.get(category_name, True))
            # Keep "Used in File" expanded when not searching
            if self._used_in_file_item is not None:
                self._used_in_file_item.setExpanded(True)

    def _load_expanded_state(self) -> dict[str, bool]:
        """Load category expanded/collapsed state from settings."""
        state = {}
        for category_name in COMPONENT_CATEGORIES:
            val = app_settings.get(f"palette/expanded/{category_name}")
            if val is not None:
                state[category_name] = app_settings.get_bool(f"palette/expanded/{category_name}")
            else:
                state[category_name] = True  # default expanded
        return state

    def _save_expanded_state(self, _item=None):
        """Save category expanded/collapsed state to settings."""
        # Don't save while searching (search auto-expands categories)
        if self.search_input.text():
            return
        # Don't persist the recommended section's state or override user
        # prefs when recommendations auto-collapse categories
        if self._recommended_item is not None:
            return
        for category_name, category_item in self._category_items.items():
            app_settings.set(f"palette/expanded/{category_name}", category_item.isExpanded())

    def update_used_in_file(self, component_types: list[str]) -> None:
        """Show a 'Used in File' section at the top of the palette.

        Derives a unique, sorted list of component types currently placed on
        the canvas and displays them in a special category above all others.
        When the list is empty the section is removed.
        """
        # Deduplicate and preserve only known types
        seen: set[str] = set()
        unique: list[str] = []
        for ct in component_types:
            if ct not in seen and ct in COMPONENTS:
                seen.add(ct)
                unique.append(ct)
        unique.sort()

        self._remove_used_in_file_section()

        if not unique:
            return

        uif_item = QTreeWidgetItem()
        uif_item.setText(0, _USED_IN_FILE_CATEGORY)
        uif_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setItalic(True)
        uif_item.setFont(0, bold_font)

        for component_name in unique:
            child = QTreeWidgetItem(uif_item, [component_name])
            child.setIcon(0, create_component_icon(component_name))
            child.setToolTip(0, COMPONENT_TOOLTIPS.get(component_name, component_name))
            child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

        # Insert after recommended section if present, otherwise at position 0
        insert_pos = 0
        if self._recommended_item is not None:
            idx = self.tree_widget.indexOfTopLevelItem(self._recommended_item)
            if idx >= 0:
                insert_pos = idx + 1

        self.tree_widget.insertTopLevelItem(insert_pos, uif_item)
        uif_item.setExpanded(True)
        self._used_in_file_item = uif_item

    def _remove_used_in_file_section(self) -> None:
        """Remove the 'Used in File' top-level item if present."""
        if self._used_in_file_item is not None:
            index = self.tree_widget.indexOfTopLevelItem(self._used_in_file_item)
            if index >= 0:
                self.tree_widget.takeTopLevelItem(index)
            self._used_in_file_item = None

    def refresh_subcircuits(self) -> None:
        """Rebuild the 'Subcircuits' category from COMPONENT_CATEGORIES.

        Call this after importing new subcircuit definitions to update the
        palette without recreating the entire widget.
        """
        category_name = "Subcircuits"
        component_names = COMPONENT_CATEGORIES.get(category_name, [])

        # Remove existing Subcircuits category if present
        if category_name in self._category_items:
            old_item = self._category_items.pop(category_name)
            idx = self.tree_widget.indexOfTopLevelItem(old_item)
            if idx >= 0:
                self.tree_widget.takeTopLevelItem(idx)

        if not component_names:
            return

        # Create category item
        category_item = QTreeWidgetItem(self.tree_widget, [category_name])
        category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        bold_font = QFont()
        bold_font.setBold(True)
        category_item.setFont(0, bold_font)
        self._category_items[category_name] = category_item

        for component_name in component_names:
            child = QTreeWidgetItem(category_item, [component_name])
            try:
                child.setIcon(0, create_component_icon(component_name))
            except Exception:
                pass
            child.setToolTip(
                0,
                COMPONENT_TOOLTIPS.get(component_name, f"Subcircuit: {component_name}"),
            )
            child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

        category_item.setExpanded(True)

    def get_all_component_items(self) -> list[QTreeWidgetItem]:
        """Return all component (leaf) items across all categories."""
        items = []
        for category_item in self._category_items.values():
            for i in range(category_item.childCount()):
                items.append(category_item.child(i))
        return items

    def set_component_selected_callback(self, callback) -> None:
        """Register a callback for component double-click (ComponentPaletteProtocol)."""
        self.componentDoubleClicked.connect(callback)

    def set_filter_text(self, text: str) -> None:
        """Set the search filter text (ComponentPaletteProtocol)."""
        self.search_input.setText(text)


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
