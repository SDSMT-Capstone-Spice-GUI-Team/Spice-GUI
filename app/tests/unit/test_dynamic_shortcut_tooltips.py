"""Tests for dynamic shortcut display in tooltips and context menus (#513).

Verifies that keyboard shortcuts shown in UI elements are read from
the keybindings registry rather than hardcoded.
"""

from controllers.keybindings import DEFAULTS, KeybindingsRegistry
from GUI.canvas_context_menu import _action_label_with_shortcut, _get_keybinding


class TestActionLabelWithShortcut:
    """Helper function formats labels with optional shortcut suffix."""

    def test_with_shortcut(self):
        assert _action_label_with_shortcut("Zoom In", "Ctrl+=") == "Zoom In (Ctrl+=)"

    def test_without_shortcut(self):
        assert _action_label_with_shortcut("Zoom In", "") == "Zoom In"

    def test_none_shortcut(self):
        assert _action_label_with_shortcut("Zoom In", None) == "Zoom In"


class TestGetKeybinding:
    """_get_keybinding reads from the main window's keybindings registry."""

    def test_returns_empty_when_no_window(self):
        class FakeCanvas:
            def window(self):
                return None

        assert _get_keybinding(FakeCanvas(), "edit.rotate_cw") == ""

    def test_returns_empty_when_no_keybindings_attr(self):
        class FakeWindow:
            pass

        class FakeCanvas:
            def window(self):
                return FakeWindow()

        assert _get_keybinding(FakeCanvas(), "edit.rotate_cw") == ""

    def test_returns_shortcut_from_registry(self):
        kb = KeybindingsRegistry(config_path="/dev/null")

        class FakeWindow:
            keybindings = kb

        class FakeCanvas:
            def window(self):
                return FakeWindow()

        result = _get_keybinding(FakeCanvas(), "edit.rotate_cw")
        assert result == DEFAULTS["edit.rotate_cw"]


class TestDefaultShortcutsMatchTooltips:
    """Default keybinding values should produce the same tooltip text as previously hardcoded."""

    def test_zoom_in_default(self):
        assert DEFAULTS["view.zoom_in"] == "Ctrl+="

    def test_zoom_out_default(self):
        assert DEFAULTS["view.zoom_out"] == "Ctrl+-"

    def test_zoom_fit_default(self):
        assert DEFAULTS["view.zoom_fit"] == "Ctrl+0"

    def test_rotate_cw_default(self):
        assert DEFAULTS["edit.rotate_cw"] == "R"

    def test_delete_default(self):
        assert DEFAULTS["edit.delete"] == "Del"
