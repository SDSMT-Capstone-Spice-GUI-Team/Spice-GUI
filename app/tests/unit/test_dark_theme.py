"""Tests for dark theme and theme switching."""

import pytest
from PyQt6.QtGui import QColor

from GUI.styles import DarkTheme, LightTheme, ThemeManager, theme_manager
from GUI.styles.constants import COMPONENTS


class TestDarkThemeColors:
    """Verify DarkTheme defines all required color keys."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.theme = DarkTheme()

    def test_name(self):
        assert self.theme.name == "Dark Theme"

    def test_has_background_primary(self):
        color = self.theme.color("background_primary")
        assert isinstance(color, QColor)
        # Dark background should be dark
        assert color.lightness() < 100

    def test_has_text_primary(self):
        color = self.theme.color("text_primary")
        assert isinstance(color, QColor)
        # Text on dark bg should be light
        assert color.lightness() > 150

    def test_has_grid_colors(self):
        for key in ("grid_minor", "grid_major", "grid_label"):
            color = self.theme.color(key)
            assert isinstance(color, QColor), f"Missing color: {key}"

    def test_has_wire_colors(self):
        for key in ("wire_default", "wire_preview", "wire_selected"):
            color = self.theme.color(key)
            assert isinstance(color, QColor), f"Missing color: {key}"

    def test_has_terminal_colors(self):
        for key in ("terminal_default", "terminal_highlight", "terminal_fill"):
            color = self.theme.color(key)
            assert isinstance(color, QColor), f"Missing color: {key}"

    def test_has_selection_colors(self):
        for key in ("selection_highlight", "node_label", "node_label_bg"):
            color = self.theme.color(key)
            assert isinstance(color, QColor), f"Missing color: {key}"

    def test_all_component_types_have_colors(self):
        """Every component type from COMPONENTS should have a valid color."""
        for comp_type in COMPONENTS:
            color = self.theme.get_component_color(comp_type)
            assert isinstance(color, QColor), f"Missing color for {comp_type}"

    def test_ground_not_black(self):
        """Ground should not be pure black in dark theme (invisible)."""
        color = self.theme.color("component_ground")
        assert color != QColor("#000000")


class TestLightThemeColors:
    """Verify LightTheme still works as expected."""

    def test_name(self):
        assert LightTheme().name == "Light Theme"

    def test_background_is_white(self):
        color = LightTheme().color("background_primary")
        assert color == QColor("#FFFFFF")


class TestDarkThemePens:
    """Verify pens are correctly defined."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.theme = DarkTheme()

    def test_grid_pens_exist(self):
        pen = self.theme.pen("grid_minor")
        assert pen is not None
        assert pen.widthF() == 0.5

    def test_wire_pen(self):
        pen = self.theme.pen("wire_default")
        assert pen is not None

    def test_component_pen(self):
        pen = self.theme.create_component_pen("Resistor")
        assert pen is not None


class TestDarkThemeBrushes:
    """Verify brushes are correctly defined."""

    def test_node_label_bg(self):
        theme = DarkTheme()
        brush = theme.brush("node_label_bg")
        assert brush is not None
        # Should have alpha < 255 for semi-transparency
        assert brush.color().alpha() == 200


class TestDarkThemeStylesheets:
    """Verify stylesheets are correctly defined."""

    def test_instructions_panel(self):
        theme = DarkTheme()
        ss = theme.stylesheet("instructions_panel")
        assert "background-color" in ss
        assert "#2D2D2D" in ss

    def test_muted_label(self):
        theme = DarkTheme()
        ss = theme.stylesheet("muted_label")
        assert "color" in ss


class TestThemeManagerSwitch:
    """Test switching between themes via ThemeManager."""

    @pytest.fixture(autouse=True)
    def restore_theme(self):
        """Ensure we restore the light theme after each test."""
        yield
        theme_manager.set_theme(LightTheme())

    def test_switch_to_dark(self):
        theme_manager.set_theme(DarkTheme())
        assert theme_manager.current_theme.name == "Dark Theme"

    def test_switch_back_to_light(self):
        theme_manager.set_theme(DarkTheme())
        theme_manager.set_theme(LightTheme())
        assert theme_manager.current_theme.name == "Light Theme"

    def test_listener_notified(self):
        received = []
        theme_manager.on_theme_changed(lambda t: received.append(t.name))
        theme_manager.set_theme(DarkTheme())
        assert received == ["Dark Theme"]
        theme_manager.remove_listener(received.append)  # cleanup

    def test_color_changes_with_theme(self):
        light_bg = theme_manager.color_hex("background_primary")
        theme_manager.set_theme(DarkTheme())
        dark_bg = theme_manager.color_hex("background_primary")
        assert light_bg != dark_bg

    def test_component_color_accessible_after_switch(self):
        theme_manager.set_theme(DarkTheme())
        color = theme_manager.get_component_color("Resistor")
        assert isinstance(color, QColor)


class TestContrastRequirements:
    """Ensure dark theme has sufficient contrast between key elements."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.theme = DarkTheme()

    def _luminance_diff(self, key1, key2):
        c1 = self.theme.color(key1)
        c2 = self.theme.color(key2)
        return abs(c1.lightness() - c2.lightness())

    def test_text_vs_background_contrast(self):
        diff = self._luminance_diff("text_primary", "background_primary")
        assert diff > 100, "Text must be clearly visible on background"

    def test_grid_minor_vs_background(self):
        diff = self._luminance_diff("grid_minor", "background_primary")
        assert diff > 10, "Grid lines must be visible but subtle"

    def test_wire_vs_background(self):
        diff = self._luminance_diff("wire_default", "background_primary")
        assert diff > 100, "Wires must be clearly visible"
