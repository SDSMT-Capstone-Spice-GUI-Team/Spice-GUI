"""Tests for CustomTheme class."""

import pytest
from GUI.styles import DarkTheme, LightTheme
from GUI.styles.custom_theme import CustomTheme
from PyQt6.QtGui import QColor


class TestCustomThemeConstruction:
    """Verify CustomTheme can be constructed from either base."""

    def test_from_light_base(self):
        theme = CustomTheme("My Light", "light", {}, theme_is_dark=False)
        assert theme.name == "My Light"
        assert theme.base_name == "light"
        assert not theme.is_dark

    def test_from_dark_base(self):
        theme = CustomTheme("My Dark", "dark", {}, theme_is_dark=True)
        assert theme.name == "My Dark"
        assert theme.base_name == "dark"
        assert theme.is_dark


class TestColorOverrides:
    """Verify color overrides are applied correctly."""

    def test_override_applied(self):
        theme = CustomTheme(
            "Test", "light", {"background_primary": "#123456"}, theme_is_dark=False
        )
        assert theme.color_hex("background_primary") == "#123456"

    def test_fallback_to_base(self):
        """Keys not in overrides should come from the base theme."""
        theme = CustomTheme("Test", "light", {}, theme_is_dark=False)
        light = LightTheme()
        assert theme.color_hex("background_primary") == light.color_hex(
            "background_primary"
        )

    def test_get_color_overrides_returns_only_changes(self):
        overrides = {"wire_default": "#AABBCC"}
        theme = CustomTheme("Test", "light", overrides, theme_is_dark=False)
        result = theme.get_color_overrides()
        assert result == overrides


class TestIsDark:
    """Verify is_dark property is correct."""

    def test_light_custom_not_dark(self):
        theme = CustomTheme("L", "light", {}, theme_is_dark=False)
        assert not theme.is_dark

    def test_dark_custom_is_dark(self):
        theme = CustomTheme("D", "dark", {}, theme_is_dark=True)
        assert theme.is_dark


class TestInheritedHelpers:
    """Verify helper methods inherited from BaseTheme work."""

    def test_get_component_color(self):
        theme = CustomTheme("Test", "dark", {}, theme_is_dark=True)
        color = theme.get_component_color("Resistor")
        assert isinstance(color, QColor)

    def test_create_component_pen(self):
        theme = CustomTheme("Test", "light", {}, theme_is_dark=False)
        pen = theme.create_component_pen("Capacitor")
        assert pen is not None


class TestDarkStylesheet:
    """Verify generate_dark_stylesheet() behavior."""

    def test_dark_custom_has_stylesheet(self):
        theme = CustomTheme("D", "dark", {}, theme_is_dark=True)
        ss = theme.generate_dark_stylesheet()
        assert len(ss) > 0
        assert "background-color" in ss

    def test_light_custom_empty_stylesheet(self):
        theme = CustomTheme("L", "light", {}, theme_is_dark=False)
        ss = theme.generate_dark_stylesheet()
        assert ss == ""

    def test_dark_stylesheet_uses_theme_colors(self):
        theme = CustomTheme(
            "D", "dark", {"background_primary": "#1A1A2E"}, theme_is_dark=True
        )
        ss = theme.generate_dark_stylesheet()
        assert "#1a1a2e" in ss.lower()
