"""Unified Preferences dialog for application settings."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .styles import theme_manager

# Mapping between combo display text and internal values
_THEME_ITEMS = [("Light", "light"), ("Dark", "dark")]
_THEME_NAMES = {"Light Theme": 0, "Dark Theme": 1}

_STYLE_ITEMS = [("IEEE / ANSI", "ieee"), ("IEC (European)", "iec")]
_STYLE_VALUES = {"ieee": 0, "iec": 1}

_COLOR_ITEMS = [("Color", "color"), ("Monochrome", "monochrome")]
_COLOR_VALUES = {"color": 0, "monochrome": 1}

_SENTINEL = object()


class PreferencesDialog(QDialog):
    """Tabbed preferences dialog with live preview and snapshot-revert on cancel."""

    def __init__(self, main_window, parent=_SENTINEL):
        super().__init__(main_window if parent is _SENTINEL else parent)
        self.main_window = main_window
        self._accepted = False
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(400)

        self._snapshot_settings()
        self._build_ui()
        self._load_current_values()
        self._connect_signals()

    # ---- snapshot / revert ------------------------------------------------

    def _snapshot_settings(self):
        """Capture current appearance and autosave settings for revert."""
        self._snap_theme = theme_manager.current_theme.name  # "Light Theme" / "Dark Theme"
        self._snap_symbol_style = theme_manager.symbol_style  # "ieee" / "iec"
        self._snap_color_mode = theme_manager.color_mode  # "color" / "monochrome"
        settings = QSettings("SDSMT", "SDM Spice")
        self._snap_autosave_enabled = settings.value("autosave/enabled", True)
        self._snap_autosave_interval = int(settings.value("autosave/interval", 60))

    def _revert_settings(self):
        """Restore appearance and autosave to snapshot values."""
        # Revert appearance
        theme_val = "dark" if self._snap_theme == "Dark Theme" else "light"
        self.main_window._set_theme(theme_val)
        self.main_window._set_symbol_style(self._snap_symbol_style)
        self.main_window._set_color_mode(self._snap_color_mode)
        # Revert autosave
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("autosave/enabled", self._snap_autosave_enabled)
        settings.setValue("autosave/interval", self._snap_autosave_interval)
        self.main_window._start_autosave_timer()

    # ---- UI construction --------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_appearance_tab(), "Appearance")
        self.tabs.addTab(self._build_grid_tab(), "Grid")
        self.tabs.addTab(self._build_behavior_tab(), "Behavior")
        self.tabs.addTab(self._build_keybindings_tab(), "Keybindings")

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _build_appearance_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.theme_combo = QComboBox()
        for label, _val in _THEME_ITEMS:
            self.theme_combo.addItem(label)
        form.addRow("Theme:", self.theme_combo)

        self.style_combo = QComboBox()
        for label, _val in _STYLE_ITEMS:
            self.style_combo.addItem(label)
        form.addRow("Symbol Style:", self.style_combo)

        self.color_combo = QComboBox()
        for label, _val in _COLOR_ITEMS:
            self.color_combo.addItem(label)
        form.addRow("Color Mode:", self.color_combo)

        return widget

    def _build_grid_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Grid settings will be available in a future update."))
        layout.addStretch()
        return widget

    def _build_behavior_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.autosave_checkbox = QCheckBox("Enable auto-save")
        form.addRow(self.autosave_checkbox)

        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(10, 600)
        self.autosave_spin.setSingleStep(10)
        self.autosave_spin.setSuffix(" seconds")
        form.addRow("Auto-save interval:", self.autosave_spin)

        return widget

    def _build_keybindings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Keyboard shortcuts can be customized in the keybindings editor."))
        self.keybindings_btn = QPushButton("Open Keybindings Editor...")
        self.keybindings_btn.clicked.connect(self._open_keybindings)
        layout.addWidget(self.keybindings_btn)
        layout.addStretch()
        return widget

    # ---- Load current values into widgets ---------------------------------

    def _load_current_values(self):
        self.theme_combo.setCurrentIndex(_THEME_NAMES.get(self._snap_theme, 0))
        self.style_combo.setCurrentIndex(_STYLE_VALUES.get(self._snap_symbol_style, 0))
        self.color_combo.setCurrentIndex(_COLOR_VALUES.get(self._snap_color_mode, 0))

        enabled = self._snap_autosave_enabled
        self.autosave_checkbox.setChecked(enabled != "false" and enabled is not False)
        self.autosave_spin.setValue(self._snap_autosave_interval)

    # ---- Signal wiring (live preview) -------------------------------------

    def _connect_signals(self):
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        self.color_combo.currentIndexChanged.connect(self._on_color_changed)

    def _on_theme_changed(self, index):
        self.main_window._set_theme(_THEME_ITEMS[index][1])

    def _on_style_changed(self, index):
        self.main_window._set_symbol_style(_STYLE_ITEMS[index][1])

    def _on_color_changed(self, index):
        self.main_window._set_color_mode(_COLOR_ITEMS[index][1])

    # ---- Button handlers --------------------------------------------------

    def _on_ok(self):
        """Persist all settings and close."""
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("autosave/enabled", self.autosave_checkbox.isChecked())
        settings.setValue("autosave/interval", self.autosave_spin.value())
        self.main_window._start_autosave_timer()
        # Appearance is already applied via live preview — settings are saved
        # in MainWindow._save_settings() on close, but persist theme now too
        settings.setValue("view/theme", theme_manager.current_theme.name)
        settings.setValue("view/symbol_style", theme_manager.symbol_style)
        settings.setValue("view/color_mode", theme_manager.color_mode)
        self._accepted = True
        self.close()

    def _on_cancel(self):
        """Revert to snapshot and close."""
        self._revert_settings()
        self.close()

    def closeEvent(self, event):
        """Treat window close (X button) as Cancel if not accepted."""
        if not self._accepted:
            self._revert_settings()
        super().closeEvent(event)

    # ---- Helpers ----------------------------------------------------------

    def _open_keybindings(self):
        """Open the keybindings editor dialog."""
        self.main_window._open_keybindings_dialog()
