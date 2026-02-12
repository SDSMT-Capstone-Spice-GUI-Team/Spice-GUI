"""Unified Preferences dialog for application settings."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .styles import CustomTheme, theme_manager, theme_store

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
        self.setMinimumWidth(480)

        self._snapshot_settings()
        self._build_ui()
        self._load_current_values()
        self._connect_signals()

    # ---- snapshot / revert ------------------------------------------------

    def _snapshot_settings(self):
        """Capture current appearance and autosave settings for revert."""
        self._snap_theme_key = theme_manager.get_theme_key()
        self._snap_theme_obj = theme_manager.current_theme
        self._snap_symbol_style = theme_manager.symbol_style
        self._snap_color_mode = theme_manager.color_mode
        settings = QSettings("SDSMT", "SDM Spice")
        self._snap_autosave_enabled = settings.value("autosave/enabled", True)
        self._snap_autosave_interval = int(settings.value("autosave/interval", 60))

    def _revert_settings(self):
        """Restore appearance and autosave to snapshot values."""
        theme_manager.set_theme(self._snap_theme_obj)
        self.main_window._apply_theme()
        self.main_window._set_symbol_style(self._snap_symbol_style)
        self.main_window._set_color_mode(self._snap_color_mode)
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

        # Theme combo — dynamically populated
        self.theme_combo = QComboBox()
        self._populate_theme_combo()
        form.addRow("Theme:", self.theme_combo)

        # Theme management buttons
        theme_btn_layout = QHBoxLayout()
        self.new_theme_btn = QPushButton("New...")
        self.new_theme_btn.clicked.connect(self._on_new_theme)
        self.edit_theme_btn = QPushButton("Edit...")
        self.edit_theme_btn.clicked.connect(self._on_edit_theme)
        self.delete_theme_btn = QPushButton("Delete")
        self.delete_theme_btn.clicked.connect(self._on_delete_theme)
        theme_btn_layout.addWidget(self.new_theme_btn)
        theme_btn_layout.addWidget(self.edit_theme_btn)
        theme_btn_layout.addWidget(self.delete_theme_btn)
        form.addRow("", theme_btn_layout)

        # Import/Export
        ie_layout = QHBoxLayout()
        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self._on_import_theme)
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._on_export_theme)
        ie_layout.addWidget(import_btn)
        ie_layout.addWidget(export_btn)
        ie_layout.addStretch()
        form.addRow("", ie_layout)

        self.style_combo = QComboBox()
        for label, _val in _STYLE_ITEMS:
            self.style_combo.addItem(label)
        form.addRow("Symbol Style:", self.style_combo)

        self.color_combo = QComboBox()
        for label, _val in _COLOR_ITEMS:
            self.color_combo.addItem(label)
        form.addRow("Color Mode:", self.color_combo)

        self._update_theme_buttons()
        return widget

    def _populate_theme_combo(self):
        """Fill theme combo from theme_manager.get_available_themes()."""
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self._theme_keys = []
        for display_name, key in theme_manager.get_available_themes():
            self.theme_combo.addItem(display_name)
            self._theme_keys.append(key)
        self.theme_combo.blockSignals(False)

    def _update_theme_buttons(self):
        """Enable/disable Edit and Delete based on current selection."""
        idx = self.theme_combo.currentIndex()
        is_custom = idx >= 0 and idx < len(self._theme_keys) and self._theme_keys[idx].startswith("custom:")
        self.edit_theme_btn.setEnabled(is_custom)
        self.delete_theme_btn.setEnabled(is_custom)

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
        current_key = theme_manager.get_theme_key()
        if current_key in self._theme_keys:
            self.theme_combo.setCurrentIndex(self._theme_keys.index(current_key))
        else:
            self.theme_combo.setCurrentIndex(0)

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
        if 0 <= index < len(self._theme_keys):
            key = self._theme_keys[index]
            theme_manager.set_theme_by_key(key)
            self.main_window._apply_theme()
            self._update_theme_buttons()
            # Sync the View > Theme menu checkmarks
            if hasattr(self.main_window, "_refresh_theme_menu"):
                self.main_window._refresh_theme_menu()

    def _on_style_changed(self, index):
        self.main_window._set_symbol_style(_STYLE_ITEMS[index][1])

    def _on_color_changed(self, index):
        self.main_window._set_color_mode(_COLOR_ITEMS[index][1])

    # ---- Theme management -------------------------------------------------

    def _on_new_theme(self):
        from .theme_editor_dialog import ThemeEditorDialog

        dialog = ThemeEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            theme = dialog.get_theme()
            if theme is not None:
                theme_store.save_theme(theme)
                self._populate_theme_combo()
                key = f"custom:{theme_store._filename_safe(theme.name)}"
                if key in self._theme_keys:
                    self.theme_combo.setCurrentIndex(self._theme_keys.index(key))
                self._update_theme_buttons()
                if hasattr(self.main_window, "_refresh_theme_menu"):
                    self.main_window._refresh_theme_menu()

    def _on_edit_theme(self):
        idx = self.theme_combo.currentIndex()
        if idx < 0 or idx >= len(self._theme_keys):
            return
        key = self._theme_keys[idx]
        if not key.startswith("custom:"):
            return

        current_theme = theme_manager.current_theme
        if not isinstance(current_theme, CustomTheme):
            return

        from .theme_editor_dialog import ThemeEditorDialog

        dialog = ThemeEditorDialog(self, edit_theme=current_theme)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            theme = dialog.get_theme()
            if theme is not None:
                # Delete old file if name changed
                old_stem = key[len("custom:") :]
                new_stem = theme_store._filename_safe(theme.name)
                if old_stem != new_stem:
                    theme_store.delete_theme(old_stem)
                theme_store.save_theme(theme)
                self._populate_theme_combo()
                new_key = f"custom:{new_stem}"
                if new_key in self._theme_keys:
                    self.theme_combo.setCurrentIndex(self._theme_keys.index(new_key))
                self._update_theme_buttons()
                if hasattr(self.main_window, "_refresh_theme_menu"):
                    self.main_window._refresh_theme_menu()

    def _on_delete_theme(self):
        idx = self.theme_combo.currentIndex()
        if idx < 0 or idx >= len(self._theme_keys):
            return
        key = self._theme_keys[idx]
        if not key.startswith("custom:"):
            return

        name = self.theme_combo.currentText()
        reply = QMessageBox.question(
            self,
            "Delete Theme",
            f'Delete custom theme "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        stem = key[len("custom:") :]
        theme_store.delete_theme(stem)
        # Switch to Light theme
        theme_manager.set_theme_by_key("light")
        self.main_window._apply_theme()
        self._populate_theme_combo()
        self.theme_combo.setCurrentIndex(0)
        self._update_theme_buttons()
        if hasattr(self.main_window, "_refresh_theme_menu"):
            self.main_window._refresh_theme_menu()

    def _on_import_theme(self):
        from pathlib import Path

        path, _ = QFileDialog.getOpenFileName(self, "Import Theme", "", "Theme Files (*.json);;All Files (*)")
        if not path:
            return
        theme = theme_store.import_theme(Path(path))
        if theme is not None:
            self._populate_theme_combo()
            key = f"custom:{theme_store._filename_safe(theme.name)}"
            if key in self._theme_keys:
                self.theme_combo.setCurrentIndex(self._theme_keys.index(key))
            self._update_theme_buttons()
            if hasattr(self.main_window, "_refresh_theme_menu"):
                self.main_window._refresh_theme_menu()
        else:
            QMessageBox.warning(self, "Import Failed", "Could not import the theme file.")

    def _on_export_theme(self):
        from pathlib import Path

        current = theme_manager.current_theme
        if not isinstance(current, CustomTheme):
            QMessageBox.information(self, "Export Theme", "Only custom themes can be exported.")
            return

        default_name = theme_store._filename_safe(current.name) + ".json"
        path, _ = QFileDialog.getSaveFileName(self, "Export Theme", default_name, "Theme Files (*.json);;All Files (*)")
        if not path:
            return
        theme_store.export_theme(current, Path(path))

    # ---- Button handlers --------------------------------------------------

    def _on_ok(self):
        """Persist all settings and close."""
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("autosave/enabled", self.autosave_checkbox.isChecked())
        settings.setValue("autosave/interval", self.autosave_spin.value())
        self.main_window._start_autosave_timer()
        # Persist theme key
        settings.setValue("view/theme_key", theme_manager.get_theme_key())
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
