"""Tests for the unified Preferences dialog."""

from unittest.mock import MagicMock

import pytest
from GUI.preferences_dialog import PreferencesDialog
from GUI.styles import LightTheme, theme_manager
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QCheckBox, QComboBox, QPushButton, QSpinBox, QTabWidget


@pytest.fixture(autouse=True)
def restore_theme():
    """Ensure light theme, wire defaults, autosave, and default zoom are restored after each test."""
    yield
    theme_manager.set_theme(LightTheme())
    theme_manager.set_wire_thickness("normal")
    theme_manager.set_show_junction_dots(True)
    settings = QSettings("SDSMT", "SDM Spice")
    settings.setValue("view/default_zoom", 100)
    settings.setValue("autosave/enabled", True)
    settings.setValue("autosave/interval", 60)


@pytest.fixture
def mock_main_window():
    """Create a mock MainWindow with the methods PreferencesDialog calls."""
    mw = MagicMock()
    mw._set_theme = MagicMock()
    mw._apply_theme = MagicMock()
    mw._set_symbol_style = MagicMock()
    mw._set_color_mode = MagicMock()
    mw._set_wire_thickness = MagicMock()
    mw._set_show_junction_dots = MagicMock()
    mw._start_autosave_timer = MagicMock()
    mw._open_keybindings_dialog = MagicMock()
    mw._refresh_theme_menu = MagicMock()
    return mw


@pytest.fixture
def dialog(qtbot, mock_main_window):
    """Create a PreferencesDialog with default (light/ieee/color) settings."""
    dlg = PreferencesDialog(mock_main_window, parent=None)
    qtbot.addWidget(dlg)
    return dlg


class TestDialogStructure:
    """Tests verifying the dialog has the expected widgets."""

    def test_has_four_tabs(self, dialog):
        tabs = dialog.findChild(QTabWidget)
        assert tabs is not None
        assert tabs.count() == 4
        assert tabs.tabText(0) == "Appearance"
        assert tabs.tabText(1) == "Grid"
        assert tabs.tabText(2) == "Behavior"
        assert tabs.tabText(3) == "Keybindings"

    def test_appearance_tab_has_combos(self, dialog):
        tab = dialog.tabs.widget(0)
        combos = tab.findChildren(QComboBox)
        assert len(combos) == 4  # theme, style, color mode, wire thickness

    def test_appearance_tab_has_theme_buttons(self, dialog):
        tab = dialog.tabs.widget(0)
        buttons = tab.findChildren(QPushButton)
        texts = {b.text() for b in buttons}
        assert "New..." in texts
        assert "Edit..." in texts
        assert "Delete" in texts
        assert "Import..." in texts
        assert "Export..." in texts

    def test_grid_tab_is_placeholder(self, dialog):
        tab = dialog.tabs.widget(1)
        combos = tab.findChildren(QComboBox)
        assert len(combos) == 0

    def test_behavior_tab_has_autosave(self, dialog):
        tab = dialog.tabs.widget(2)
        checkboxes = tab.findChildren(QCheckBox)
        spinboxes = tab.findChildren(QSpinBox)
        assert len(checkboxes) == 1
        assert len(spinboxes) == 1
        assert spinboxes[0].minimum() == 10
        assert spinboxes[0].maximum() == 600

    def test_behavior_tab_has_default_zoom_combo(self, dialog):
        tab = dialog.tabs.widget(2)
        combos = tab.findChildren(QComboBox)
        assert len(combos) == 1
        zoom_combo = combos[0]
        assert zoom_combo.count() == 5
        assert zoom_combo.itemText(0) == "50%"
        assert zoom_combo.itemText(1) == "75%"
        assert zoom_combo.itemText(2) == "100%"
        assert zoom_combo.itemText(3) == "125%"
        assert zoom_combo.itemText(4) == "150%"

    def test_keybindings_tab_has_button(self, dialog):
        tab = dialog.tabs.widget(3)
        buttons = tab.findChildren(QPushButton)
        labels = [b.text() for b in buttons]
        assert "Open Keybindings Editor..." in labels


class TestLivePreview:
    """Tests verifying combo changes apply theme immediately."""

    def test_theme_combo_dark(self, dialog, mock_main_window):
        mock_main_window._apply_theme.reset_mock()
        dialog.theme_combo.setCurrentIndex(1)  # Dark
        mock_main_window._apply_theme.assert_called()
        assert theme_manager.current_theme.name == "Dark Theme"

    def test_symbol_style_combo_live_preview(self, dialog, mock_main_window):
        mock_main_window._set_symbol_style.reset_mock()
        dialog.style_combo.setCurrentIndex(1)  # IEC
        mock_main_window._set_symbol_style.assert_called_with("iec")

    def test_color_mode_combo_live_preview(self, dialog, mock_main_window):
        mock_main_window._set_color_mode.reset_mock()
        dialog.color_combo.setCurrentIndex(1)  # Monochrome
        mock_main_window._set_color_mode.assert_called_with("monochrome")


class TestCancelRevert:
    """Tests verifying Cancel reverts to snapshot values."""

    def test_cancel_reverts_theme(self, dialog, mock_main_window):
        dialog.theme_combo.setCurrentIndex(1)  # Dark
        assert theme_manager.current_theme.name == "Dark Theme"
        dialog._on_cancel()
        # Should revert to Light
        assert theme_manager.current_theme.name == "Light Theme"

    def test_cancel_reverts_symbol_style(self, dialog, mock_main_window):
        dialog.style_combo.setCurrentIndex(1)
        mock_main_window._set_symbol_style.reset_mock()
        dialog._on_cancel()
        mock_main_window._set_symbol_style.assert_called_with("ieee")

    def test_cancel_reverts_default_zoom(self, dialog, mock_main_window):
        dialog.default_zoom_combo.setCurrentIndex(0)  # 50%
        dialog._on_cancel()
        settings = QSettings("SDSMT", "SDM Spice")
        # Should revert to original snapshot (100%)
        assert int(settings.value("view/default_zoom", 100)) == 100


class TestOkPersist:
    """Tests verifying OK persists settings."""

    def test_ok_persists_autosave(self, dialog, mock_main_window):
        dialog.autosave_checkbox.setChecked(True)
        dialog.autosave_spin.setValue(120)

        dialog._on_ok()

        settings = QSettings("SDSMT", "SDM Spice")
        assert settings.value("autosave/interval") == 120
        enabled = settings.value("autosave/enabled")
        assert enabled is True or enabled == "true"
        mock_main_window._start_autosave_timer.assert_called()

    def test_ok_persists_theme_key(self, dialog, mock_main_window):
        dialog._on_ok()
        settings = QSettings("SDSMT", "SDM Spice")
        assert settings.value("view/theme_key") == "light"

    def test_ok_persists_default_zoom(self, dialog, mock_main_window):
        dialog.default_zoom_combo.setCurrentIndex(3)  # 125%
        dialog._on_ok()
        settings = QSettings("SDSMT", "SDM Spice")
        assert int(settings.value("view/default_zoom")) == 125


class TestInitialValues:
    """Tests verifying initial widget values match snapshot."""

    def test_initial_values_match_current(self, dialog):
        assert dialog.theme_combo.currentIndex() == 0  # Light
        assert dialog.style_combo.currentIndex() == 0  # IEEE
        assert dialog.color_combo.currentIndex() == 0  # Color
        assert dialog.autosave_spin.value() >= 10

    def test_default_zoom_initial_value(self, dialog):
        # Default is 100% which maps to index 2
        assert dialog.default_zoom_combo.currentIndex() == 2
        assert dialog.default_zoom_combo.currentText() == "100%"


class TestThemeButtons:
    """Tests for New/Edit/Delete button state."""

    def test_edit_delete_disabled_for_builtin(self, dialog):
        dialog.theme_combo.setCurrentIndex(0)  # Light
        assert not dialog.edit_theme_btn.isEnabled()
        assert not dialog.delete_theme_btn.isEnabled()


class TestWireRenderingPreferences:
    """Tests for wire thickness and junction dot controls."""

    def test_appearance_tab_has_wire_thickness_combo(self, dialog):
        assert hasattr(dialog, "wire_thickness_combo")
        assert dialog.wire_thickness_combo.count() == 3

    def test_appearance_tab_has_junction_dots_checkbox(self, dialog):
        tab = dialog.tabs.widget(0)
        checkboxes = tab.findChildren(QCheckBox)
        labels = [cb.text() for cb in checkboxes]
        assert "Show junction dots at wire intersections" in labels

    def test_wire_thickness_initial_value(self, dialog):
        # Default is "normal" -> index 1
        assert dialog.wire_thickness_combo.currentIndex() == 1

    def test_junction_dots_initial_value(self, dialog):
        # Default is True (checked)
        assert dialog.junction_dots_checkbox.isChecked()

    def test_wire_thickness_live_preview(self, dialog, mock_main_window):
        mock_main_window._set_wire_thickness.reset_mock()
        dialog.wire_thickness_combo.setCurrentIndex(0)  # Thin
        mock_main_window._set_wire_thickness.assert_called_with("thin")

    def test_wire_thickness_thick_live_preview(self, dialog, mock_main_window):
        mock_main_window._set_wire_thickness.reset_mock()
        dialog.wire_thickness_combo.setCurrentIndex(2)  # Thick
        mock_main_window._set_wire_thickness.assert_called_with("thick")

    def test_junction_dots_toggle_live_preview(self, dialog, mock_main_window):
        mock_main_window._set_show_junction_dots.reset_mock()
        dialog.junction_dots_checkbox.setChecked(False)
        mock_main_window._set_show_junction_dots.assert_called_with(False)

    def test_cancel_reverts_wire_thickness(self, dialog, mock_main_window):
        dialog.wire_thickness_combo.setCurrentIndex(0)  # Change to thin
        mock_main_window._set_wire_thickness.reset_mock()
        dialog._on_cancel()
        mock_main_window._set_wire_thickness.assert_called_with("normal")

    def test_cancel_reverts_junction_dots(self, dialog, mock_main_window):
        dialog.junction_dots_checkbox.setChecked(False)
        mock_main_window._set_show_junction_dots.reset_mock()
        dialog._on_cancel()
        mock_main_window._set_show_junction_dots.assert_called_with(True)

    def test_ok_persists_wire_thickness(self, dialog, mock_main_window):
        dialog.wire_thickness_combo.setCurrentIndex(2)  # Thick
        # The mock main_window doesn't actually call theme_manager, so set it directly
        theme_manager.set_wire_thickness("thick")
        dialog._on_ok()
        settings = QSettings("SDSMT", "SDM Spice")
        assert settings.value("view/wire_thickness") == "thick"

    def test_ok_persists_junction_dots(self, dialog, mock_main_window):
        dialog.junction_dots_checkbox.setChecked(False)
        # The mock main_window doesn't actually call theme_manager, so set it directly
        theme_manager.set_show_junction_dots(False)
        dialog._on_ok()
        settings = QSettings("SDSMT", "SDM Spice")
        val = settings.value("view/show_junction_dots")
        assert val is False or val == "false"


class TestAutosaveSpinboxState:
    """Tests for auto-save interval spinbox enabled/disabled state."""

    def test_spinbox_enabled_when_autosave_checked(self, dialog):
        """Spinbox should be enabled when auto-save checkbox is checked."""
        dialog.autosave_checkbox.setChecked(True)
        assert dialog.autosave_spin.isEnabled()

    def test_spinbox_disabled_when_autosave_unchecked(self, dialog):
        """Spinbox should be disabled when auto-save checkbox is unchecked."""
        dialog.autosave_checkbox.setChecked(False)
        assert not dialog.autosave_spin.isEnabled()

    def test_toggling_checkbox_updates_spinbox_enabled(self, dialog):
        """Toggling the checkbox should update the spinbox enabled state."""
        dialog.autosave_checkbox.setChecked(True)
        assert dialog.autosave_spin.isEnabled()
        dialog.autosave_checkbox.setChecked(False)
        assert not dialog.autosave_spin.isEnabled()
        dialog.autosave_checkbox.setChecked(True)
        assert dialog.autosave_spin.isEnabled()

    def test_spinbox_initial_state_matches_checkbox(self, qtbot, mock_main_window):
        """Spinbox enabled state should match the checkbox on dialog open."""
        # Set autosave disabled before opening dialog
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("autosave/enabled", False)
        dlg = PreferencesDialog(mock_main_window, parent=None)
        qtbot.addWidget(dlg)
        assert not dlg.autosave_checkbox.isChecked()
        assert not dlg.autosave_spin.isEnabled()

    def test_cancel_reverts_autosave_enabled(self, qtbot, mock_main_window):
        """Cancel should revert auto-save enabled to the snapshot value."""
        # Ensure autosave is enabled before opening dialog so snapshot captures True
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("autosave/enabled", True)
        dlg = PreferencesDialog(mock_main_window, parent=None)
        qtbot.addWidget(dlg)
        dlg.autosave_checkbox.setChecked(False)
        dlg._on_cancel()
        enabled = settings.value("autosave/enabled")
        assert enabled is True or enabled == "true"
        mock_main_window._start_autosave_timer.assert_called()

    def test_cancel_reverts_autosave_interval(self, dialog, mock_main_window):
        """Cancel should revert auto-save interval to the snapshot value."""
        original = dialog.autosave_spin.value()
        dialog.autosave_spin.setValue(300)
        dialog._on_cancel()
        settings = QSettings("SDSMT", "SDM Spice")
        assert int(settings.value("autosave/interval", 60)) == original


class TestThemeManagerWireProperties:
    """Tests for ThemeManager wire_thickness and show_junction_dots properties."""

    def test_default_wire_thickness(self):
        assert theme_manager.wire_thickness == "normal"

    def test_default_wire_thickness_px(self):
        assert theme_manager.wire_thickness_px == 2

    def test_default_show_junction_dots(self):
        assert theme_manager.show_junction_dots is True

    def test_set_wire_thickness_thin(self):
        theme_manager.set_wire_thickness("thin")
        assert theme_manager.wire_thickness == "thin"
        assert theme_manager.wire_thickness_px == 1

    def test_set_wire_thickness_thick(self):
        theme_manager.set_wire_thickness("thick")
        assert theme_manager.wire_thickness == "thick"
        assert theme_manager.wire_thickness_px == 3

    def test_set_wire_thickness_invalid(self):
        theme_manager.set_wire_thickness("invalid")
        assert theme_manager.wire_thickness == "normal"  # unchanged

    def test_set_show_junction_dots_false(self):
        theme_manager.set_show_junction_dots(False)
        assert theme_manager.show_junction_dots is False

    def test_set_show_junction_dots_true(self):
        theme_manager.set_show_junction_dots(False)
        theme_manager.set_show_junction_dots(True)
        assert theme_manager.show_junction_dots is True

    def test_wire_thickness_notifies_listeners(self):
        notified = []
        theme_manager.on_theme_changed(lambda t: notified.append(True))
        theme_manager.set_wire_thickness("thin")
        assert len(notified) >= 1
        theme_manager.remove_listener(notified.append if notified else lambda t: None)

    def test_junction_dots_notifies_listeners(self):
        notified = []

        def callback(t):
            notified.append(True)

        theme_manager.on_theme_changed(callback)
        theme_manager.set_show_junction_dots(False)
        assert len(notified) >= 1
        theme_manager.remove_listener(callback)
