"""Theme editor dialog for creating and editing custom color themes."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .styles import CustomTheme, DarkTheme, LightTheme, theme_manager

# Color groups exposed in the editor (subset of all theme keys)
COLOR_GROUPS = [
    (
        "Canvas",
        [
            ("background_primary", "Background"),
            ("background_secondary", "Secondary Background"),
            ("text_primary", "Text"),
        ],
    ),
    (
        "Grid",
        [
            ("grid_minor", "Minor Grid"),
            ("grid_major", "Major Grid"),
        ],
    ),
    (
        "Wires & Selection",
        [
            ("wire_default", "Wire"),
            ("wire_selected", "Wire Selected"),
            ("selection_highlight", "Selection"),
        ],
    ),
    (
        "Terminals",
        [
            ("terminal_default", "Terminal"),
            ("terminal_highlight", "Terminal Highlight"),
        ],
    ),
    (
        "Components",
        [
            ("component_resistor", "Resistor"),
            ("component_capacitor", "Capacitor"),
            ("component_inductor", "Inductor"),
            ("component_voltage_source", "Voltage Source"),
            ("component_ground", "Ground"),
        ],
    ),
]


class ThemeEditorDialog(QDialog):
    """Dialog for creating/editing a custom color theme."""

    def __init__(self, parent=None, edit_theme=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.setMinimumSize(480, 600)

        self._result_theme = None
        self._color_buttons = {}  # key -> QPushButton
        self._hex_labels = {}  # key -> QLabel

        # Snapshot current theme for revert on cancel
        self._snap_theme = theme_manager.current_theme

        # Load base colors
        if edit_theme is not None and isinstance(edit_theme, CustomTheme):
            self._initial_name = edit_theme.name
            self._initial_base = edit_theme.base_name
            self._initial_is_dark = edit_theme.is_dark
            self._colors = dict((DarkTheme() if edit_theme.base_name == "dark" else LightTheme())._colors)
            self._colors.update(edit_theme.get_color_overrides())
        else:
            self._initial_name = ""
            self._initial_base = "light"
            self._initial_is_dark = False
            self._colors = dict(LightTheme()._colors)

        self._build_ui()

        if edit_theme is not None:
            self.name_edit.setText(self._initial_name)
            idx = self.base_combo.findData(self._initial_base)
            if idx >= 0:
                self.base_combo.setCurrentIndex(idx)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Name field
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Custom Theme")
        form.addRow("Theme Name:", self.name_edit)

        self.base_combo = QComboBox()
        self.base_combo.addItem("Light", "light")
        self.base_combo.addItem("Dark", "dark")
        self.base_combo.currentIndexChanged.connect(self._on_base_changed)
        form.addRow("Base Theme:", self.base_combo)
        layout.addLayout(form)

        # Scrollable color groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for group_name, keys in COLOR_GROUPS:
            group = QGroupBox(group_name)
            group_layout = QFormLayout(group)
            for color_key, label in keys:
                row = QHBoxLayout()
                btn = QPushButton()
                btn.setFixedSize(40, 24)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self._update_swatch(btn, self._colors.get(color_key, "#FF00FF"))
                btn.clicked.connect(lambda checked, k=color_key: self._pick_color(k))
                self._color_buttons[color_key] = btn

                hex_label = QLabel(self._colors.get(color_key, "#FF00FF"))
                hex_label.setMinimumWidth(70)
                self._hex_labels[color_key] = hex_label

                row.addWidget(btn)
                row.addWidget(hex_label)
                row.addStretch()
                group_layout.addRow(f"{label}:", row)
            scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _update_swatch(self, btn, hex_color):
        btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #888; border-radius: 3px;")

    def _pick_color(self, key):
        current = QColor(self._colors.get(key, "#FF00FF"))
        color = QColorDialog.getColor(current, self, f"Pick color for {key}")
        if color.isValid():
            hex_val = color.name()
            self._colors[key] = hex_val
            self._update_swatch(self._color_buttons[key], hex_val)
            self._hex_labels[key].setText(hex_val)
            self._apply_preview()

    def _on_base_changed(self, index):
        base = self.base_combo.currentData()
        base_theme = DarkTheme() if base == "dark" else LightTheme()
        self._colors = dict(base_theme._colors)
        # Refresh all swatches
        for key, btn in self._color_buttons.items():
            hex_val = self._colors.get(key, "#FF00FF")
            self._update_swatch(btn, hex_val)
            self._hex_labels[key].setText(hex_val)
        self._apply_preview()

    def _on_reset(self):
        """Reset colors to the current base theme defaults."""
        self._on_base_changed(self.base_combo.currentIndex())

    def _apply_preview(self):
        """Apply current editor colors as a live preview."""
        base = self.base_combo.currentData()
        is_dark = base == "dark"
        name = self.name_edit.text() or "Preview"

        # Compute overrides relative to base
        base_theme = DarkTheme() if is_dark else LightTheme()
        overrides = {k: v for k, v in self._colors.items() if v != base_theme._colors.get(k)}

        preview = CustomTheme(name=name, base=base, colors=overrides, theme_is_dark=is_dark)
        theme_manager.set_theme(preview)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a name for the theme.")
            return

        base = self.base_combo.currentData()
        is_dark = base == "dark"

        # Compute overrides relative to base
        base_theme = DarkTheme() if is_dark else LightTheme()
        overrides = {k: v for k, v in self._colors.items() if v != base_theme._colors.get(k)}

        self._result_theme = CustomTheme(name=name, base=base, colors=overrides, theme_is_dark=is_dark)
        theme_manager.set_theme(self._result_theme)
        self.accept()

    def _on_cancel(self):
        # Revert to snapshot
        theme_manager.set_theme(self._snap_theme)
        self.reject()

    def closeEvent(self, event):
        if self.result() != QDialog.DialogCode.Accepted:
            theme_manager.set_theme(self._snap_theme)
        super().closeEvent(event)

    def get_theme(self):
        """Return the created/edited CustomTheme, or None if cancelled."""
        return self._result_theme
