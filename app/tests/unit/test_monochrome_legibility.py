"""Tests for monochrome mode component legibility (#911).

Verifies that component rendering uses the theme's background-based fill
(component_fill brush) instead of a derivative of the component color,
ensuring internal details remain visible in monochrome mode on both
light and dark themes.
"""

from pathlib import Path

import pytest
from GUI.styles import LightTheme, theme_manager
from GUI.styles.dark_theme import DarkTheme


def _module_source(module):
    return Path(module.__file__).read_text(encoding="utf-8")


class TestComponentFillUsesThemeBrush:
    """Verify component rendering uses theme_manager.brush('component_fill')."""

    def test_component_item_uses_component_fill_brush(self):
        from GUI import component_item

        src = _module_source(component_item)
        assert 'theme_manager.brush("component_fill")' in src
        assert "color.lighter(150)" not in src

    def test_palette_uses_component_fill_brush(self):
        from GUI import component_palette

        src = _module_source(component_palette)
        assert 'theme_manager.brush("component_fill")' in src
        assert "color.lighter(150)" not in src


class TestComponentFillContrastMonochrome:
    """Verify component_fill provides contrast with foreground in monochrome mode."""

    @pytest.fixture(autouse=True)
    def _setup_teardown(self):
        theme_manager.set_theme(LightTheme())
        theme_manager.set_color_mode("color")
        yield
        theme_manager.set_theme(LightTheme())
        theme_manager.set_color_mode("color")

    def test_light_monochrome_fill_differs_from_foreground(self):
        theme_manager.set_theme(LightTheme())
        theme_manager.set_color_mode("monochrome")
        fg = theme_manager.get_component_color("Voltage Source")
        fill = theme_manager.brush("component_fill").color()
        assert fg.name() != fill.name(), (
            f"In light+monochrome, fill ({fill.name()}) must differ from "
            f"foreground ({fg.name()}) for internal details to be visible"
        )

    def test_dark_monochrome_fill_differs_from_foreground(self):
        theme_manager.set_theme(DarkTheme())
        theme_manager.set_color_mode("monochrome")
        fg = theme_manager.get_component_color("Voltage Source")
        fill = theme_manager.brush("component_fill").color()
        assert fg.name() != fill.name(), (
            f"In dark+monochrome, fill ({fill.name()}) must differ from "
            f"foreground ({fg.name()}) for internal details to be visible"
        )

    def test_light_monochrome_fill_is_background(self):
        """Fill should be the theme background so details drawn with foreground are visible."""
        theme_manager.set_theme(LightTheme())
        theme_manager.set_color_mode("monochrome")
        bg = theme_manager.color("background_primary")
        fill = theme_manager.brush("component_fill").color()
        assert fill.name() == bg.name()

    def test_dark_monochrome_fill_is_background(self):
        theme_manager.set_theme(DarkTheme())
        theme_manager.set_color_mode("monochrome")
        bg = theme_manager.color("background_primary")
        fill = theme_manager.brush("component_fill").color()
        assert fill.name() == bg.name()
