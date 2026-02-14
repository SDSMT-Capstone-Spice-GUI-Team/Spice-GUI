"""Tests for symbol style system (#283), IEC symbols (#284), color modes (#285),
and renderer strategy pattern (#327)."""

import pytest
from GUI.component_item import (BJTNPN, BJTPNP, CCCS, CCVS, MOSFETNMOS,
                                MOSFETPMOS, VCCS, VCVS, Capacitor,
                                CurrentSource, Diode, Ground, Inductor,
                                LEDComponent, OpAmp, Resistor, VCSwitch,
                                VoltageSource, WaveformVoltageSource,
                                ZenerDiode)
from GUI.renderers import get_renderer
from GUI.styles import LightTheme, theme_manager
from GUI.styles.theme_manager import COLOR_MODES, SYMBOL_STYLES


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


# ── Component class list ────────────────────────────────────────────


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


# ── Renderer registry coverage ──────────────────────────────────────


class TestRendererRegistry:
    """Verify every component type is registered for both IEEE and IEC."""

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_all_component_types_registered_for_ieee(self, cls):
        renderer = get_renderer(cls.type_name, "ieee")
        assert renderer is not None

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_all_component_types_registered_for_iec(self, cls):
        renderer = get_renderer(cls.type_name, "iec")
        assert renderer is not None

    def test_unregistered_type_raises_key_error(self):
        with pytest.raises(KeyError):
            get_renderer("Nonexistent", "ieee")

    def test_unregistered_style_raises_key_error(self):
        with pytest.raises(KeyError):
            get_renderer("Resistor", "bogus")


# ── Draw dispatch via renderers ─────────────────────────────────────


class TestDrawDispatch:
    """Verify draw_component_body delegates to the renderer."""

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_draw_component_body_dispatches_ieee(self, cls):
        """draw_component_body should invoke the IEEE renderer's draw."""
        comp = cls("T1")
        called = []
        renderer = get_renderer(cls.type_name, "ieee")
        orig_draw = renderer.draw
        renderer.draw = lambda painter, component: called.append(True)
        try:
            comp.draw_component_body(None)
            assert called, f"{cls.type_name} did not dispatch to IEEE renderer"
        finally:
            renderer.draw = orig_draw

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_draw_component_body_dispatches_iec(self, cls):
        """draw_component_body should invoke the IEC renderer's draw."""
        theme_manager.set_symbol_style("iec")
        comp = cls("T1")
        called = []
        renderer = get_renderer(cls.type_name, "iec")
        orig_draw = renderer.draw
        renderer.draw = lambda painter, component: called.append(True)
        try:
            comp.draw_component_body(None)
            assert called, f"{cls.type_name} did not dispatch to IEC renderer"
        finally:
            renderer.draw = orig_draw

    def test_renderer_receives_component(self):
        """The renderer's draw method receives the component instance."""
        comp = Resistor("R1")
        received = []
        renderer = get_renderer("Resistor", "ieee")
        orig_draw = renderer.draw
        renderer.draw = lambda painter, component: received.append(component)
        try:
            comp.draw_component_body(None)
            assert received[0] is comp
        finally:
            renderer.draw = orig_draw


# ── Obstacle shape dispatch ─────────────────────────────────────────


class TestObstacleShapeDispatch:
    """Verify obstacle shapes dispatch via renderers."""

    @pytest.mark.parametrize("cls", ALL_COMPONENT_CLASSES, ids=lambda c: c.type_name)
    def test_obstacle_shape_returns_polygon(self, cls):
        comp = cls("T1")
        shape = comp.get_obstacle_shape()
        assert isinstance(shape, list)
        assert len(shape) >= 3, "Obstacle polygon must have >=3 points"
        for pt in shape:
            assert len(pt) == 2, "Each point must be (x, y)"

    def test_ieee_obstacle_shape_matches_renderer(self):
        """Component obstacle shape matches the IEEE renderer directly."""
        r = Resistor("R1")
        renderer = get_renderer("Resistor", "ieee")
        assert r.get_obstacle_shape() == renderer.get_obstacle_shape(r)

    def test_iec_obstacle_shape_matches_renderer(self):
        """Component obstacle shape matches the IEC renderer directly."""
        theme_manager.set_symbol_style("iec")
        r = Resistor("R1")
        renderer = get_renderer("Resistor", "iec")
        assert r.get_obstacle_shape() == renderer.get_obstacle_shape(r)


# ── IEC-specific renderer behavior ──────────────────────────────────


class TestIECRenderers:
    """Verify IEC renderers differ from IEEE where expected."""

    def test_iec_resistor_differs_from_ieee(self):
        """Resistor IEC renderer is a different instance from IEEE."""
        ieee = get_renderer("Resistor", "ieee")
        iec = get_renderer("Resistor", "iec")
        assert ieee is not iec

    def test_iec_capacitor_differs_from_ieee(self):
        ieee = get_renderer("Capacitor", "ieee")
        iec = get_renderer("Capacitor", "iec")
        assert ieee is not iec

    def test_iec_inductor_differs_from_ieee(self):
        ieee = get_renderer("Inductor", "ieee")
        iec = get_renderer("Inductor", "iec")
        assert ieee is not iec

    def test_resistor_iec_and_ieee_obstacles_differ(self):
        r = Resistor("R1")
        ieee = get_renderer("Resistor", "ieee").get_obstacle_shape(r)
        iec = get_renderer("Resistor", "iec").get_obstacle_shape(r)
        assert ieee != iec

    def test_inductor_iec_and_ieee_obstacles_differ(self):
        ind = Inductor("L1")
        ieee = get_renderer("Inductor", "ieee").get_obstacle_shape(ind)
        iec = get_renderer("Inductor", "iec").get_obstacle_shape(ind)
        assert ieee != iec

    def test_resistor_iec_obstacle_shape(self):
        theme_manager.set_symbol_style("iec")
        r = Resistor("R1")
        shape = r.get_obstacle_shape()
        assert isinstance(shape, list)
        assert len(shape) == 4
        assert shape == get_renderer("Resistor", "iec").get_obstacle_shape(r)

    def test_inductor_iec_obstacle_shape(self):
        theme_manager.set_symbol_style("iec")
        ind = Inductor("L1")
        shape = ind.get_obstacle_shape()
        assert isinstance(shape, list)
        assert len(shape) == 4
        assert shape == get_renderer("Inductor", "iec").get_obstacle_shape(ind)

    def test_capacitor_iec_same_obstacle_as_ieee(self):
        """Capacitor IEC and IEEE have the same obstacle shape."""
        c = Capacitor("C1")
        ieee_shape = get_renderer("Capacitor", "ieee").get_obstacle_shape(c)
        iec_shape = get_renderer("Capacitor", "iec").get_obstacle_shape(c)
        assert ieee_shape == iec_shape
