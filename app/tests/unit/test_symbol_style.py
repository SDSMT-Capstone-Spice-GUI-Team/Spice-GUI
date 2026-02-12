"""Tests for symbol style system (#283), IEC symbols (#284), and color modes (#285)."""

import pytest
from GUI.component_item import (
    BJTNPN,
    BJTPNP,
    CCCS,
    CCVS,
    MOSFETNMOS,
    MOSFETPMOS,
    VCCS,
    VCVS,
    Capacitor,
    CurrentSource,
    Diode,
    Ground,
    Inductor,
    LEDComponent,
    OpAmp,
    Resistor,
    VCSwitch,
    VoltageSource,
    WaveformVoltageSource,
    ZenerDiode,
)
from GUI.styles import LightTheme, theme_manager
from GUI.styles.theme_manager import COLOR_MODES, SYMBOL_STYLES
from PyQt6.QtGui import QColor


@pytest.fixture(autouse=True)
def reset_theme_manager():
    """Reset theme manager to defaults after each test."""
    yield
    theme_manager.set_theme(LightTheme())
    theme_manager._symbol_style = "ieee"
    theme_manager._color_mode = "color"


# ── Symbol style constants ──────────────────────────────────────────


class TestSymbolStyleConstants:
    def test_ieee_in_valid_styles(self):
        assert "ieee" in SYMBOL_STYLES

    def test_iec_in_valid_styles(self):
        assert "iec" in SYMBOL_STYLES


# ── ThemeManager symbol_style property ──────────────────────────────


class TestSymbolStyleProperty:
    def test_default_is_ieee(self):
        assert theme_manager.symbol_style == "ieee"

    def test_set_to_iec(self):
        theme_manager.set_symbol_style("iec")
        assert theme_manager.symbol_style == "iec"

    def test_set_back_to_ieee(self):
        theme_manager.set_symbol_style("iec")
        theme_manager.set_symbol_style("ieee")
        assert theme_manager.symbol_style == "ieee"

    def test_invalid_style_ignored(self):
        theme_manager.set_symbol_style("bogus")
        assert theme_manager.symbol_style == "ieee"

    def test_listener_notified_on_style_change(self):
        received = []
        theme_manager.on_theme_changed(lambda t: received.append("changed"))
        theme_manager.set_symbol_style("iec")
        assert received == ["changed"]
        theme_manager.remove_listener(received.append)

    def test_no_notification_when_same_style(self):
        received = []
        theme_manager.on_theme_changed(lambda t: received.append("changed"))
        theme_manager.set_symbol_style("ieee")  # already ieee
        assert received == []
        theme_manager.remove_listener(received.append)


# ── Color mode property ─────────────────────────────────────────────


class TestColorModeProperty:
    def test_default_is_color(self):
        assert theme_manager.color_mode == "color"

    def test_valid_modes(self):
        assert "color" in COLOR_MODES
        assert "monochrome" in COLOR_MODES

    def test_set_monochrome(self):
        theme_manager.set_color_mode("monochrome")
        assert theme_manager.color_mode == "monochrome"

    def test_set_back_to_color(self):
        theme_manager.set_color_mode("monochrome")
        theme_manager.set_color_mode("color")
        assert theme_manager.color_mode == "color"

    def test_invalid_mode_ignored(self):
        theme_manager.set_color_mode("neon")
        assert theme_manager.color_mode == "color"

    def test_listener_notified_on_mode_change(self):
        received = []
        theme_manager.on_theme_changed(lambda t: received.append("changed"))
        theme_manager.set_color_mode("monochrome")
        assert received == ["changed"]
        theme_manager.remove_listener(received.append)

    def test_no_notification_when_same_mode(self):
        received = []
        theme_manager.on_theme_changed(lambda t: received.append("changed"))
        theme_manager.set_color_mode("color")  # already color
        assert received == []
        theme_manager.remove_listener(received.append)


# ── Monochrome color behavior ───────────────────────────────────────


class TestMonochromeColors:
    def test_color_mode_returns_per_type(self):
        """In color mode, different component types get different colors."""
        r = theme_manager.get_component_color("Resistor")
        c = theme_manager.get_component_color("Capacitor")
        assert r != c

    def test_monochrome_returns_foreground(self):
        """In monochrome mode, all components get the theme foreground."""
        theme_manager.set_color_mode("monochrome")
        fg = theme_manager.color("text_primary")
        for comp_type in ("Resistor", "Capacitor", "Inductor", "Voltage Source"):
            assert theme_manager.get_component_color(comp_type) == fg

    def test_monochrome_hex_returns_foreground(self):
        theme_manager.set_color_mode("monochrome")
        fg_hex = theme_manager.color_hex("text_primary")
        assert theme_manager.get_component_color_hex("Resistor") == fg_hex

    def test_color_mode_hex_returns_per_type(self):
        r_hex = theme_manager.get_component_color_hex("Resistor")
        c_hex = theme_manager.get_component_color_hex("Capacitor")
        assert r_hex != c_hex


# ── Component draw dispatch (IEEE default) ──────────────────────────


ALL_COMPONENT_CLASSES = [
    Resistor,
    Capacitor,
    Inductor,
    VoltageSource,
    CurrentSource,
    WaveformVoltageSource,
    Ground,
    OpAmp,
    VCVS,
    CCVS,
    VCCS,
    CCCS,
    BJTNPN,
    BJTPNP,
    MOSFETNMOS,
    MOSFETPMOS,
    VCSwitch,
    Diode,
    LEDComponent,
    ZenerDiode,
]


class TestIEEEDrawDispatch:
    """Verify every component has a _draw_ieee method reachable via dispatch."""

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_has_draw_ieee(self, cls):
        assert hasattr(cls, "_draw_ieee"), f"{cls.type_name} missing _draw_ieee"

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_draw_component_body_dispatches_ieee(self, cls):
        """draw_component_body should call _draw_ieee when style is 'ieee'."""
        comp = cls("T1")
        called = []
        comp._draw_ieee = lambda painter: called.append(True)
        comp.draw_component_body(None)
        assert (
            called
        ), f"{cls.type_name} draw_component_body did not dispatch to _draw_ieee"


class TestObstacleShapeDispatch:
    """Verify obstacle shapes dispatch correctly."""

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_obstacle_shape_returns_polygon(self, cls):
        comp = cls("T1")
        shape = comp.get_obstacle_shape()
        assert isinstance(shape, list)
        assert len(shape) >= 3, "Obstacle polygon must have ≥3 points"
        for pt in shape:
            assert len(pt) == 2, "Each point must be (x, y)"

    def test_ieee_obstacle_shape_fallback(self):
        """Unknown style falls back to _get_obstacle_shape_ieee."""
        r = Resistor("R1")
        ieee_shape = r._get_obstacle_shape_ieee()
        theme_manager._symbol_style = "ieee"
        assert r.get_obstacle_shape() == ieee_shape

    def test_obstacle_dispatch_tries_style_specific(self):
        """If a style-specific method exists, it's used."""
        r = Resistor("R1")
        custom = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        r._get_obstacle_shape_iec = lambda: custom
        theme_manager.set_symbol_style("iec")
        assert r.get_obstacle_shape() == custom

    def test_obstacle_fallback_when_no_style_method(self):
        """When no style-specific method exists, IEEE is used."""
        d = Diode("D1")
        theme_manager.set_symbol_style("iec")
        # Diode has no _get_obstacle_shape_iec, so should fall back to ieee
        assert d.get_obstacle_shape() == d._get_obstacle_shape_ieee()


class TestDrawDispatchIEC:
    """Verify draw dispatch falls back to IEEE when IEC is not implemented."""

    def test_fallback_to_ieee_when_no_iec_method(self):
        """Components without _draw_iec should use _draw_ieee."""
        theme_manager.set_symbol_style("iec")
        comp = Diode("D1")
        called = []
        comp._draw_ieee = lambda painter: called.append(True)
        comp.draw_component_body(None)
        assert called

    def test_iec_method_used_when_available(self):
        """If _draw_iec exists, it should be called."""
        theme_manager.set_symbol_style("iec")
        comp = Resistor("R1")
        iec_called = []
        comp._draw_iec = lambda painter: iec_called.append(True)
        comp.draw_component_body(None)
        assert iec_called


# ── IEC symbol implementations (#284) ──────────────────────────────

IEC_COMPONENTS = [Resistor, Capacitor, Inductor]


class TestIECDrawMethods:
    """Verify IEC draw methods exist and dispatch correctly."""

    @pytest.mark.parametrize("cls", IEC_COMPONENTS, ids=lambda c: c.type_name)
    def test_has_draw_iec(self, cls):
        assert hasattr(cls, "_draw_iec"), f"{cls.type_name} missing _draw_iec"

    @pytest.mark.parametrize("cls", IEC_COMPONENTS, ids=lambda c: c.type_name)
    def test_iec_dispatches_to_draw_iec(self, cls):
        """Setting style to IEC should call _draw_iec on these components."""
        theme_manager.set_symbol_style("iec")
        comp = cls("T1")
        called = []
        comp._draw_iec = lambda painter: called.append(True)
        comp.draw_component_body(None)
        assert called

    def test_resistor_iec_different_from_ieee(self):
        """Resistor IEC (rectangle) should differ from IEEE (zigzag)."""
        r = Resistor("R1")
        assert hasattr(r, "_draw_iec")
        assert r._draw_iec is not r._draw_ieee

    def test_inductor_iec_different_from_ieee(self):
        """Inductor IEC (rectangular humps) should differ from IEEE (arcs)."""
        l = Inductor("L1")
        assert hasattr(l, "_draw_iec")
        assert l._draw_iec is not l._draw_ieee


class TestIECObstacleShapes:
    """Verify IEC obstacle shapes for components that differ from IEEE."""

    def test_resistor_iec_obstacle_shape(self):
        theme_manager.set_symbol_style("iec")
        r = Resistor("R1")
        shape = r.get_obstacle_shape()
        assert isinstance(shape, list)
        assert len(shape) == 4
        # IEC resistor is a rectangle — should return the IEC-specific shape
        assert shape == r._get_obstacle_shape_iec()

    def test_inductor_iec_obstacle_shape(self):
        theme_manager.set_symbol_style("iec")
        l = Inductor("L1")
        shape = l.get_obstacle_shape()
        assert isinstance(shape, list)
        assert len(shape) == 4
        assert shape == l._get_obstacle_shape_iec()

    def test_capacitor_falls_back_to_ieee_obstacle(self):
        """Capacitor is the same in both standards — should fall back."""
        theme_manager.set_symbol_style("iec")
        c = Capacitor("C1")
        assert c.get_obstacle_shape() == c._get_obstacle_shape_ieee()

    def test_resistor_iec_and_ieee_obstacles_differ(self):
        r = Resistor("R1")
        ieee = r._get_obstacle_shape_ieee()
        iec = r._get_obstacle_shape_iec()
        assert ieee != iec

    def test_inductor_iec_and_ieee_obstacles_differ(self):
        l = Inductor("L1")
        ieee = l._get_obstacle_shape_ieee()
        iec = l._get_obstacle_shape_iec()
        assert ieee != iec
