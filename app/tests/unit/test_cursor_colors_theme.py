"""Tests for measurement cursor colors routed through theme system (#516).

Verifies that cursor colors are defined in both themes and that the
MeasurementCursors class uses theme_manager instead of hardcoded values.
"""

from unittest.mock import MagicMock, patch

from GUI.styles import theme_manager
from GUI.styles.dark_theme import DarkTheme
from GUI.styles.light_theme import LightTheme


class TestCursorColorsInThemes:
    """Both themes must define cursor_a and cursor_b color keys."""

    def test_light_theme_has_cursor_a(self):
        theme = LightTheme()
        assert "cursor_a" in theme._colors

    def test_light_theme_has_cursor_b(self):
        theme = LightTheme()
        assert "cursor_b" in theme._colors

    def test_dark_theme_has_cursor_a(self):
        theme = DarkTheme()
        assert "cursor_a" in theme._colors

    def test_dark_theme_has_cursor_b(self):
        theme = DarkTheme()
        assert "cursor_b" in theme._colors


def _make_cursors():
    """Return a MeasurementCursors instance backed by mock ax and canvas."""
    from GUI.measurement_cursors import MeasurementCursors

    ax = MagicMock()
    canvas = MagicMock()
    cursors = MeasurementCursors(ax, canvas)
    cursors._a_x = 1.0
    cursors._b_x = 2.0
    return cursors


class TestCursorDrawingUsesTheme:
    """MeasurementCursors._draw_cursor_* must query theme_manager for colors."""

    def test_draw_cursor_a_uses_theme(self):
        cursors = _make_cursors()
        with patch("GUI.measurement_cursors.theme_manager") as mock_tm:
            mock_tm.color_hex.return_value = "#ff0000"
            cursors._draw_cursor_a()
            mock_tm.color_hex.assert_called_once_with("cursor_a")

    def test_draw_cursor_b_uses_theme(self):
        cursors = _make_cursors()
        with patch("GUI.measurement_cursors.theme_manager") as mock_tm:
            mock_tm.color_hex.return_value = "#0000ff"
            cursors._draw_cursor_b()
            mock_tm.color_hex.assert_called_once_with("cursor_b")


class TestThemeManagerReturnsCursorColors:
    """theme_manager.color_hex must return valid hex for cursor keys."""

    def test_cursor_a_is_hex(self):
        color = theme_manager.color_hex("cursor_a")
        assert color.startswith("#")
        assert len(color) == 7

    def test_cursor_b_is_hex(self):
        color = theme_manager.color_hex("cursor_b")
        assert color.startswith("#")
        assert len(color) == 7
