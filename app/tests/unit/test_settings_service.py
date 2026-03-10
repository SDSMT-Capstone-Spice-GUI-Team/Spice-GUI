"""Tests for centralized SettingsService (#598, #633).

Verifies that:
- SettingsService provides typed accessors (get_bool, get_int, etc.)
- All production code uses the centralized service instead of QSettings directly
- JSON round-trip works correctly
- Controller layer is free of PyQt6 imports
"""

import json
import pathlib

import pytest
from controllers.settings_service import SettingsService, settings


class TestSettingsServiceTypedHelpers:
    """Test the typed helper methods."""

    @pytest.fixture(autouse=True)
    def _clean(self):
        """Clear test keys before and after each test."""
        for key in (
            "_test/bool",
            "_test/int",
            "_test/float",
            "_test/str",
            "_test/json",
            "_test/list",
        ):
            settings.set(key, None)
        yield
        for key in (
            "_test/bool",
            "_test/int",
            "_test/float",
            "_test/str",
            "_test/json",
            "_test/list",
        ):
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


class TestSettingsServiceJsonFile:
    """Test the JSON-file backend specifics."""

    def test_constructor_with_custom_path(self, tmp_path):
        path = tmp_path / "test_settings.json"
        svc = SettingsService(path=path)
        svc.set("key", "value")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["key"] == "value"

    def test_load_from_existing_file(self, tmp_path):
        path = tmp_path / "test_settings.json"
        path.write_text(json.dumps({"saved": 123}))
        svc = SettingsService(path=path)
        assert svc.get_int("saved") == 123

    def test_corrupt_file_ignored(self, tmp_path):
        path = tmp_path / "test_settings.json"
        path.write_text("NOT VALID JSON{{{")
        svc = SettingsService(path=path)
        assert svc.get("anything") is None

    def test_bytes_round_trip(self, tmp_path):
        path = tmp_path / "test_settings.json"
        svc = SettingsService(path=path)
        original = b"\x00\x01\x02hello"
        svc.set("binary", original)
        assert svc.get("binary") == original
        # Reload from disk
        svc2 = SettingsService(path=path)
        assert svc2.get("binary") == original

    def test_set_none_removes_key(self, tmp_path):
        path = tmp_path / "test_settings.json"
        svc = SettingsService(path=path)
        svc.set("key", "value")
        assert svc.get("key") == "value"
        svc.set("key", None)
        assert svc.get("key") is None


class TestNoDirectQSettingsInProduction:
    """Verify production code no longer imports QSettings directly."""

    _GUI_FILES = [
        "GUI/main_window_settings.py",
        "GUI/main_window_file_ops.py",
        "GUI/preferences_dialog.py",
        "GUI/component_palette.py",
        "controllers/recent_exports.py",
        "GUI/circuitikz_options_dialog.py",
    ]

    _CONTROLLER_FILES = [
        "controllers/file_controller.py",
    ]

    @pytest.mark.parametrize("rel_path", _GUI_FILES + _CONTROLLER_FILES)
    def test_no_direct_qsettings_import(self, rel_path):
        """No production file should import QSettings directly."""
        base = pathlib.Path(__file__).resolve().parent.parent.parent / rel_path
        if not base.exists():
            import os

            base = pathlib.Path(os.getcwd()) / "app" / rel_path
        source = base.read_text()
        assert 'QSettings("SDSMT"' not in source, f"{rel_path} still creates QSettings directly"

    @pytest.mark.parametrize("rel_path", _GUI_FILES + _CONTROLLER_FILES)
    def test_uses_settings_service(self, rel_path):
        """All production files should import from settings_service."""
        base = pathlib.Path(__file__).resolve().parent.parent.parent / rel_path
        if not base.exists():
            import os

            base = pathlib.Path(os.getcwd()) / "app" / rel_path
        source = base.read_text()
        assert "settings_service" in source, f"{rel_path} does not use settings_service"


class TestControllerLayerNoPyQt6:
    """Verify the controller layer does not import from PyQt6 (#633)."""

    _CONTROLLER_FILES = [
        "controllers/settings_service.py",
        "controllers/file_controller.py",
        "controllers/recent_exports.py",
    ]

    @pytest.mark.parametrize("rel_path", _CONTROLLER_FILES)
    def test_no_pyqt6_import(self, rel_path):
        """Controller files must not import from PyQt6."""
        base = pathlib.Path(__file__).resolve().parent.parent.parent / rel_path
        if not base.exists():
            import os

            base = pathlib.Path(os.getcwd()) / "app" / rel_path
        source = base.read_text()
        assert "from PyQt6" not in source, f"{rel_path} imports from PyQt6"
        assert "import PyQt6" not in source, f"{rel_path} imports PyQt6"
