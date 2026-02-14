"""Tests for ThemeEditorDialog."""

from unittest.mock import MagicMock, patch

import pytest
from GUI.styles import LightTheme, theme_manager
from GUI.theme_editor_dialog import COLOR_GROUPS, ThemeEditorDialog
from PyQt6.QtWidgets import QGroupBox, QLineEdit, QPushButton


@pytest.fixture(autouse=True)
def restore_theme():
    """Ensure light theme is restored after each test."""
    yield
    theme_manager.set_theme(LightTheme())


@pytest.fixture
def editor(qtbot):
    dlg = ThemeEditorDialog()
    qtbot.addWidget(dlg)
    return dlg


class TestEditorStructure:
    """Verify the dialog has expected widgets."""

    def test_has_all_color_groups(self, editor):
        groups = editor.findChildren(QGroupBox)
        group_names = {g.title() for g in groups}
        for expected_name, _ in COLOR_GROUPS:
            assert expected_name in group_names

    def test_has_name_field(self, editor):
        name_edit = editor.findChild(QLineEdit)
        assert name_edit is not None

    def test_has_ok_cancel_reset_buttons(self, editor):
        buttons = editor.findChildren(QPushButton)
        texts = {b.text() for b in buttons}
        assert "OK" in texts
        assert "Cancel" in texts
        assert "Reset" in texts


class TestColorSwatches:
    """Verify color swatch interaction."""

    def test_all_15_keys_have_swatches(self, editor):
        total_keys = sum(len(keys) for _, keys in COLOR_GROUPS)
        assert total_keys == 15
        assert len(editor._color_buttons) == 15

    @patch("GUI.theme_editor_dialog.QColorDialog.getColor")
    def test_pick_color_updates_swatch(self, mock_get_color, editor):
        from PyQt6.QtGui import QColor

        mock_get_color.return_value = QColor("#ABCDEF")
        editor._pick_color("background_primary")
        assert editor._colors["background_primary"] == "#abcdef"


class TestNameRequired:
    """Verify name validation."""

    @patch("GUI.theme_editor_dialog.QMessageBox.warning")
    def test_empty_name_shows_warning(self, mock_warning, editor, qtbot):
        editor.name_edit.setText("")
        # _on_ok should not accept with empty name
        editor._on_ok()
        assert editor.get_theme() is None
        mock_warning.assert_called_once()


class TestResetButton:
    """Verify reset restores base colors."""

    def test_reset_restores_base(self, editor):
        editor._colors["background_primary"] = "#FF0000"
        editor._on_reset()
        light = LightTheme()
        assert editor._colors["background_primary"] == light.color_hex(
            "background_primary"
        )
