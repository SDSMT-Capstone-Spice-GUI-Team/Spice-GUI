"""Tests for centralized SettingsService (#598).

Verifies that:
- SettingsService provides typed accessors (get_bool, get_int, etc.)
- All production code uses the centralized service instead of QSettings directly
- JSON round-trip works correctly
"""

import json

import pytest
from controllers.settings_service import SettingsService, settings


class TestSettingsServiceTypedHelpers:
    """Test the typed helper methods handle QSettings string coercion."""

    @pytest.fixture(autouse=True)
    def _clean(self):
        """Clear test keys before and after each test."""
        for key in ("_test/bool", "_test/int", "_test/float", "_test/str", "_test/json", "_test/list"):
            settings.set(key, None)
        yield
        for key in ("_test/bool", "_test/int", "_test/float", "_test/str", "_test/json", "_test/list"):
            settings.set(key, None)

    def test_get_bool_true(self):
        settings.set("_test/bool", True)
        assert settings.get_bool("_test/bool") is True

    def test_get_bool_string_true(self):
        settings.set("_test/bool", "true")
        assert settings.get_bool("_test/bool") is True

    def test_get_bool_false(self):
        settings.set("_test/bool", False)
        assert settings.get_bool("_test/bool") is False

    def test_get_bool_string_false(self):
        settings.set("_test/bool", "false")
        assert settings.get_bool("_test/bool") is False

    def test_get_bool_default(self):
        assert settings.get_bool("_test/nonexistent", True) is True
        assert settings.get_bool("_test/nonexistent", False) is False

    def test_get_int(self):
        settings.set("_test/int", 42)
        assert settings.get_int("_test/int") == 42

    def test_get_int_default(self):
        assert settings.get_int("_test/nonexistent", 99) == 99

    def test_get_float(self):
        settings.set("_test/float", 3.14)
        assert abs(settings.get_float("_test/float") - 3.14) < 0.01

    def test_get_str(self):
        settings.set("_test/str", "hello")
        assert settings.get_str("_test/str") == "hello"

    def test_get_str_default(self):
        assert settings.get_str("_test/nonexistent", "default") == "default"

    def test_json_round_trip(self):
        data = [{"path": "/tmp/test.csv", "format": "CSV"}]
        settings.set_json("_test/json", data)
        result = settings.get_json("_test/json")
        assert result == data

    def test_get_json_default(self):
        result = settings.get_json("_test/nonexistent", [])
        assert result == []

    def test_get_json_invalid(self):
        settings.set("_test/json", "not-json{{{")
        result = settings.get_json("_test/json", [])
        assert result == []

    def test_singleton_is_settings_service(self):
        assert isinstance(settings, SettingsService)


class TestNoDirectQSettingsInProduction:
    """Verify production code no longer imports QSettings directly."""

    _GUI_FILES = [
        "GUI/main_window_settings.py",
        "GUI/main_window_file_ops.py",
        "GUI/preferences_dialog.py",
        "GUI/component_palette.py",
        "GUI/recent_exports.py",
        "GUI/circuitikz_options_dialog.py",
    ]

    _CONTROLLER_FILES = [
        "controllers/file_controller.py",
    ]

    @pytest.mark.parametrize("rel_path", _GUI_FILES + _CONTROLLER_FILES)
    def test_no_direct_qsettings_import(self, rel_path):
        """No production file should import QSettings directly."""
        import importlib
        import pathlib

        base = pathlib.Path(__file__).resolve().parent.parent.parent / "app" / rel_path
        if not base.exists():
            # Resolve relative to app/ in case cwd differs
            import os

            base = pathlib.Path(os.getcwd()) / rel_path
        source = base.read_text()
        assert 'QSettings("SDSMT"' not in source, f"{rel_path} still creates QSettings directly"

    @pytest.mark.parametrize("rel_path", _GUI_FILES + _CONTROLLER_FILES)
    def test_uses_settings_service(self, rel_path):
        """All production files should import from settings_service."""
        import pathlib

        base = pathlib.Path(__file__).resolve().parent.parent.parent / "app" / rel_path
        if not base.exists():
            import os

            base = pathlib.Path(os.getcwd()) / rel_path
        source = base.read_text()
        assert "settings_service" in source, f"{rel_path} does not use settings_service"
