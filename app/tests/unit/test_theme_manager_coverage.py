"""Tests for services.theme_manager — pure-Python logic only.

Mocks the GUI.styles layer so these tests run without Qt.

The first import of services.theme_manager triggers:
  ThemeManager.__new__ -> _get_light_theme() -> from GUI.styles.light_theme ...
which recursively loads the whole GUI package and circles back.

We break the cycle by pre-seeding GUI, GUI.styles, and
GUI.styles.light_theme in sys.modules as stub packages before the
first import of services.theme_manager.
"""

import sys
import types
from unittest.mock import MagicMock, patch


def _make_mock_theme(name="Mock Theme"):
    t = MagicMock()
    t.name = name
    t.is_dark = False
    t.color.return_value = "#000"
    t.color_hex.return_value = "#000000"
    t.pen.return_value = MagicMock()
    t.brush.return_value = MagicMock()
    t.font.return_value = MagicMock()
    t.stylesheet.return_value = ""
    t.get_component_color.return_value = "#FF0000"
    t.get_component_color_hex.return_value = "#FF0000"
    t.get_algorithm_color.return_value = "#00FF00"
    t.create_component_pen.return_value = MagicMock()
    t.create_component_brush.return_value = MagicMock()
    return t


# ---------------------------------------------------------------------------
# Pre-seed GUI stub modules so the import chain doesn't recurse into Qt.
# This must run before `import services.theme_manager` for the first time.
# ---------------------------------------------------------------------------
_STUB_MODULES = [
    "GUI",
    "GUI.styles",
    "GUI.styles.light_theme",
    "GUI.styles.dark_theme",
    "GUI.styles.theme",
    "GUI.styles.constants",
    "GUI.styles.theme_manager",
    "GUI.styles.custom_theme",
]
_saved_modules = {}
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        if _mod_name in ("GUI", "GUI.styles"):
            _stub.__path__ = []  # make it a package
        sys.modules[_mod_name] = _stub
        _saved_modules[_mod_name] = _stub

# Provide a mock LightTheme class for _get_light_theme()
_MockLT = type(
    "LightTheme",
    (),
    {
        "__init__": lambda self: None,
        "name": property(lambda self: "Light Theme"),
        "is_dark": False,
        "color": lambda self, k: MagicMock(),
        "color_hex": lambda self, k: "#000000",
        "pen": lambda self, k: MagicMock(),
        "brush": lambda self, k: MagicMock(),
        "font": lambda self, k: MagicMock(),
        "stylesheet": lambda self, k: "",
        "get_component_color": lambda self, ct: MagicMock(),
        "get_component_color_hex": lambda self, ct: "#000000",
        "get_algorithm_color": lambda self, a: MagicMock(),
        "create_component_pen": lambda self, ct, w=2.0: MagicMock(),
        "create_component_brush": lambda self, ct: MagicMock(),
    },
)
sys.modules["GUI.styles.light_theme"].LightTheme = _MockLT

# Provide mock DarkTheme for set_theme_by_key
sys.modules["GUI.styles.dark_theme"].DarkTheme = type(
    "DarkTheme",
    (),
    {
        "__init__": lambda self: None,
        "name": property(lambda self: "Dark Theme"),
        "is_dark": True,
    },
)

# Provide mock CustomTheme for theme_store imports
sys.modules["GUI.styles.custom_theme"].CustomTheme = type(
    "CustomTheme",
    (),
    {
        "__init__": lambda self, *a, **kw: None,
    },
)

# Now it's safe to import
import services.theme_manager as _tm_mod  # noqa: E402


def _get_manager():
    """Get a fresh ThemeManager with mocked GUI dependencies."""
    _tm_mod.ThemeManager._instance = None
    mock_light_cls = MagicMock(return_value=_make_mock_theme("Light Theme"))
    with patch.object(_tm_mod, "_get_light_theme", return_value=mock_light_cls):
        mgr = _tm_mod.ThemeManager()
    return mgr, _tm_mod


class TestThemeManagerProperties:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_default_symbol_style(self):
        assert self.mgr.symbol_style == "ieee"

    def test_default_color_mode(self):
        assert self.mgr.color_mode == "color"

    def test_default_wire_thickness(self):
        assert self.mgr.wire_thickness == "normal"

    def test_default_wire_thickness_px(self):
        assert self.mgr.wire_thickness_px == 2

    def test_default_show_junction_dots(self):
        assert self.mgr.show_junction_dots is True

    def test_default_routing_mode(self):
        assert self.mgr.routing_mode == "orthogonal"

    def test_current_theme_not_none(self):
        assert self.mgr.current_theme is not None


class TestSetTheme:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_theme_updates_current(self):
        new_theme = _make_mock_theme("Dark Theme")
        self.mgr.set_theme(new_theme)
        assert self.mgr.current_theme is new_theme

    def test_set_theme_notifies_listeners(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        new_theme = _make_mock_theme("Dark Theme")
        self.mgr.set_theme(new_theme)
        cb.assert_called_once_with(new_theme)


class TestSetSymbolStyle:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_valid_style(self):
        self.mgr.set_symbol_style("iec")
        assert self.mgr.symbol_style == "iec"

    def test_set_invalid_style_ignored(self):
        self.mgr.set_symbol_style("invalid")
        assert self.mgr.symbol_style == "ieee"

    def test_set_same_style_no_notify(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_symbol_style("ieee")
        cb.assert_not_called()

    def test_set_different_style_notifies(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_symbol_style("iec")
        cb.assert_called_once()


class TestSetColorMode:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_valid_mode(self):
        self.mgr.set_color_mode("monochrome")
        assert self.mgr.color_mode == "monochrome"

    def test_set_invalid_mode_ignored(self):
        self.mgr.set_color_mode("neon")
        assert self.mgr.color_mode == "color"

    def test_set_same_mode_no_notify(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_color_mode("color")
        cb.assert_not_called()


class TestSetWireThickness:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_thick(self):
        self.mgr.set_wire_thickness("thick")
        assert self.mgr.wire_thickness == "thick"
        assert self.mgr.wire_thickness_px == 3

    def test_set_thin(self):
        self.mgr.set_wire_thickness("thin")
        assert self.mgr.wire_thickness == "thin"
        assert self.mgr.wire_thickness_px == 1

    def test_invalid_thickness_ignored(self):
        self.mgr.set_wire_thickness("huge")
        assert self.mgr.wire_thickness == "normal"

    def test_same_thickness_no_notify(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_wire_thickness("normal")
        cb.assert_not_called()


class TestSetShowJunctionDots:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_false(self):
        self.mgr.set_show_junction_dots(False)
        assert self.mgr.show_junction_dots is False

    def test_same_value_no_notify(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_show_junction_dots(True)
        cb.assert_not_called()

    def test_different_value_notifies(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_show_junction_dots(False)
        cb.assert_called_once()


class TestSetRoutingMode:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_diagonal(self):
        self.mgr.set_routing_mode("diagonal")
        assert self.mgr.routing_mode == "diagonal"

    def test_invalid_mode_ignored(self):
        self.mgr.set_routing_mode("bezier")
        assert self.mgr.routing_mode == "orthogonal"

    def test_same_mode_no_notify(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_routing_mode("orthogonal")
        cb.assert_not_called()


class TestListenerManagement:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_add_listener(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.set_theme(_make_mock_theme())
        cb.assert_called_once()

    def test_remove_listener(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.remove_listener(cb)
        self.mgr.set_theme(_make_mock_theme())
        cb.assert_not_called()

    def test_remove_nonexistent_listener_no_error(self):
        self.mgr.remove_listener(lambda t: None)

    def test_duplicate_listener_not_added(self):
        cb = MagicMock()
        self.mgr.on_theme_changed(cb)
        self.mgr.on_theme_changed(cb)
        self.mgr.set_theme(_make_mock_theme())
        assert cb.call_count == 1

    def test_listener_error_does_not_break_others(self):
        bad_cb = MagicMock(side_effect=RuntimeError("boom"))
        good_cb = MagicMock()
        self.mgr.on_theme_changed(bad_cb)
        self.mgr.on_theme_changed(good_cb)
        self.mgr.set_theme(_make_mock_theme())
        good_cb.assert_called_once()


class TestConvenienceMethods:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_color(self):
        self.mgr.color("text_primary")
        self.mgr.current_theme.color.assert_called_with("text_primary")

    def test_color_hex(self):
        self.mgr.color_hex("text_primary")
        self.mgr.current_theme.color_hex.assert_called_with("text_primary")

    def test_pen(self):
        self.mgr.pen("wire")
        self.mgr.current_theme.pen.assert_called_with("wire")

    def test_brush(self):
        self.mgr.brush("background")
        self.mgr.current_theme.brush.assert_called_with("background")

    def test_font(self):
        self.mgr.font("label")
        self.mgr.current_theme.font.assert_called_with("label")

    def test_stylesheet(self):
        self.mgr.stylesheet("main")
        self.mgr.current_theme.stylesheet.assert_called_with("main")


class TestComponentColorHelpers:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_get_component_color_normal(self):
        self.mgr.get_component_color("Resistor")
        self.mgr.current_theme.get_component_color.assert_called_with("Resistor")

    def test_get_component_color_monochrome(self):
        self.mgr.set_color_mode("monochrome")
        self.mgr.get_component_color("Resistor")
        self.mgr.current_theme.color.assert_called_with("text_primary")

    def test_get_component_color_hex_normal(self):
        self.mgr.get_component_color_hex("Resistor")
        self.mgr.current_theme.get_component_color_hex.assert_called_with("Resistor")

    def test_get_component_color_hex_monochrome(self):
        self.mgr.set_color_mode("monochrome")
        self.mgr.get_component_color_hex("Resistor")
        self.mgr.current_theme.color_hex.assert_called_with("text_primary")

    def test_get_algorithm_color(self):
        self.mgr.get_algorithm_color("dijkstra")
        self.mgr.current_theme.get_algorithm_color.assert_called_with("dijkstra")

    def test_create_component_pen(self):
        self.mgr.create_component_pen("Resistor", 3.0)
        self.mgr.current_theme.create_component_pen.assert_called_with("Resistor", 3.0)

    def test_create_component_brush(self):
        self.mgr.create_component_brush("Resistor")
        self.mgr.current_theme.create_component_brush.assert_called_with("Resistor")


class TestThemeByKey:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_set_light_key(self):
        """set_theme_by_key("light") should apply the light theme."""
        self.mgr.set_theme_by_key("light")
        # After setting to light, it's a LightTheme (our mock stub)
        assert self.mgr.current_theme is not None

    def test_set_dark_key(self):
        """set_theme_by_key("dark") should apply DarkTheme."""
        self.mgr.set_theme_by_key("dark")
        assert self.mgr.current_theme is not None

    def test_set_custom_key_found(self):
        custom_theme = _make_mock_theme("My Custom")
        import services.theme_store as ts_mod

        with patch.object(ts_mod, "load_theme", return_value=custom_theme):
            self.mgr.set_theme_by_key("custom:my-custom")
        assert self.mgr.current_theme is custom_theme

    def test_set_custom_key_not_found_falls_back(self):
        import services.theme_store as ts_mod

        with patch.object(ts_mod, "load_theme", return_value=None):
            self.mgr.set_theme_by_key("custom:missing")
        # Falls back to light theme
        assert self.mgr.current_theme is not None


class TestGetAvailableThemes:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_includes_builtins(self):
        import services.theme_store as ts_mod

        with patch.object(ts_mod, "list_custom_themes", return_value=[]):
            themes = self.mgr.get_available_themes()
        assert ("Light", "light") in themes
        assert ("Dark", "dark") in themes

    def test_includes_custom(self):
        import services.theme_store as ts_mod

        with patch.object(ts_mod, "list_custom_themes", return_value=[("Ocean", "ocean")]):
            themes = self.mgr.get_available_themes()
        assert ("Ocean", "custom:ocean") in themes


class TestGetThemeKey:
    def setup_method(self):
        self.mgr, self.mod = _get_manager()

    def teardown_method(self):
        self.mod.ThemeManager._instance = None

    def test_light_theme_key(self):
        theme = _make_mock_theme("Light Theme")
        self.mgr.set_theme(theme)
        key = self.mgr.get_theme_key()
        assert key == "light"

    def test_dark_theme_key(self):
        theme = _make_mock_theme("Dark Theme")
        self.mgr.set_theme(theme)
        key = self.mgr.get_theme_key()
        assert key == "dark"
