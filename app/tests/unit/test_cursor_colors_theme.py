"""Tests for measurement cursor colors routed through theme system (#516).

Verifies that cursor colors are defined in both themes and that the
MeasurementCursors class uses theme_manager instead of hardcoded values.
"""

import inspect

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


class TestCursorDrawingUsesTheme:
    """MeasurementCursors._draw_cursor_* must use theme_manager, not class constants."""

    def test_draw_cursor_a_uses_theme(self):
        from GUI.measurement_cursors import MeasurementCursors

        source = inspect.getsource(MeasurementCursors._draw_cursor_a)
        assert "theme_manager" in source
        assert "CURSOR_A_COLOR" not in source

    def test_draw_cursor_b_uses_theme(self):
        from GUI.measurement_cursors import MeasurementCursors

        source = inspect.getsource(MeasurementCursors._draw_cursor_b)
        assert "theme_manager" in source
        assert "CURSOR_B_COLOR" not in source


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
