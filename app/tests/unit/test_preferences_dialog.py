"""Tests for the unified Preferences dialog."""

from unittest.mock import MagicMock

import pytest
from GUI.preferences_dialog import PreferencesDialog
from GUI.styles import LightTheme, theme_manager
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QPushButton, QSpinBox,
                             QTabWidget)


@pytest.fixture(autouse=True)
def restore_theme():
    """Ensure light theme is restored after each test."""
    yield
    theme_manager.set_theme(LightTheme())


@pytest.fixture
def mock_main_window():
    """Create a mock MainWindow with the methods PreferencesDialog calls."""
    mw = MagicMock()
    mw._set_theme = MagicMock()
    mw._apply_theme = MagicMock()
    mw._set_symbol_style = MagicMock()
    mw._set_color_mode = MagicMock()
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
        assert len(combos) == 3

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


class TestInitialValues:
    """Tests verifying initial widget values match snapshot."""

    def test_initial_values_match_current(self, dialog):
        assert dialog.theme_combo.currentIndex() == 0  # Light
        assert dialog.style_combo.currentIndex() == 0  # IEEE
        assert dialog.color_combo.currentIndex() == 0  # Color
        assert dialog.autosave_spin.value() >= 10


class TestThemeButtons:
    """Tests for New/Edit/Delete button state."""

    def test_edit_delete_disabled_for_builtin(self, dialog):
        dialog.theme_combo.setCurrentIndex(0)  # Light
        assert not dialog.edit_theme_btn.isEnabled()
        assert not dialog.delete_theme_btn.isEnabled()
