"""Tests for controllers.theme_controller — pure-Python logic only.

Mocks services.theme_manager so these tests run without Qt.
controllers.theme_controller imports services.theme_manager which
triggers a GUI import chain. We pre-seed GUI stubs to break the cycle.
"""

import sys
import types
from unittest.mock import MagicMock, patch

# Pre-seed GUI modules to prevent circular import when loading
# services.theme_manager for the first time.
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
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        if _mod_name in ("GUI", "GUI.styles"):
            _stub.__path__ = []
        sys.modules[_mod_name] = _stub

if not hasattr(sys.modules["GUI.styles.light_theme"], "LightTheme"):
    sys.modules["GUI.styles.light_theme"].LightTheme = type(
        "LightTheme",
        (),
        {
            "__init__": lambda self: None,
            "name": property(lambda self: "Light Theme"),
        },
    )

import controllers.theme_controller as _tc_mod  # noqa: E402


class TestThemeControllerDelegation:
    """Verify every ThemeController method delegates to theme_manager."""

    def setup_method(self):
        self._patcher = patch.object(_tc_mod, "theme_manager")
        self.mock_tm = self._patcher.start()
        self.ctrl = _tc_mod.ThemeController()

    def teardown_method(self):
        self._patcher.stop()

    def test_set_theme(self):
        theme = MagicMock()
        self.ctrl.set_theme(theme)
        self.mock_tm.set_theme.assert_called_once_with(theme)

    def test_current_theme(self):
        self.mock_tm.current_theme = MagicMock(name="Mock Theme")
        assert self.ctrl.current_theme is self.mock_tm.current_theme

    def test_set_theme_by_key(self):
        self.ctrl.set_theme_by_key("dark")
        self.mock_tm.set_theme_by_key.assert_called_once_with("dark")

    def test_set_symbol_style(self):
        self.ctrl.set_symbol_style("iec")
        self.mock_tm.set_symbol_style.assert_called_once_with("iec")

    def test_set_color_mode(self):
        self.ctrl.set_color_mode("monochrome")
        self.mock_tm.set_color_mode.assert_called_once_with("monochrome")

    def test_set_wire_thickness(self):
        self.ctrl.set_wire_thickness("thick")
        self.mock_tm.set_wire_thickness.assert_called_once_with("thick")

    def test_set_show_junction_dots(self):
        self.ctrl.set_show_junction_dots(False)
        self.mock_tm.set_show_junction_dots.assert_called_once_with(False)

    def test_set_routing_mode(self):
        self.ctrl.set_routing_mode("diagonal")
        self.mock_tm.set_routing_mode.assert_called_once_with("diagonal")


class TestModuleSingleton:
    """Verify the module-level singleton."""

    def test_singleton_type(self):
        assert isinstance(_tc_mod.theme_ctrl, _tc_mod.ThemeController)
