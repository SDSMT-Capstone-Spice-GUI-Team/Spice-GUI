"""Tests to increase settings_service.py coverage to 98%+.

Covers:
- _default_settings_path win32 branch (line 25)
- _default_settings_path darwin branch (line 27)
- _save OSError branch (lines 61-62)
- _encode duck-type byte-array objects (lines 74-78)
- get_list when value is not a list (line 156)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controllers.settings_service import SettingsService, _default_settings_path


class TestDefaultSettingsPathPlatforms:
    """Cover lines 25, 27: platform-specific path branches."""

    @patch("controllers.settings_service.sys")
    @patch("controllers.settings_service.os")
    def test_win32_path_with_appdata(self, mock_os, mock_sys):
        """On win32, should use APPDATA environment variable."""
        mock_sys.platform = "win32"
        mock_os.environ = {"APPDATA": "/fake/appdata"}
        result = _default_settings_path()
        assert "SDSMT" in str(result)
        assert "SDM Spice" in str(result)
        assert "fake" in str(result) or "appdata" in str(result)

    @patch("controllers.settings_service.sys")
    @patch("controllers.settings_service.os")
    def test_win32_path_without_appdata(self, mock_os, mock_sys):
        """On win32 without APPDATA, should fall back to home dir."""
        mock_sys.platform = "win32"
        mock_os.environ = {}
        result = _default_settings_path()
        assert "SDSMT" in str(result)

    @patch("controllers.settings_service.sys")
    def test_darwin_path(self, mock_sys):
        """On darwin, should use ~/Library/Preferences."""
        mock_sys.platform = "darwin"
        result = _default_settings_path()
        assert "Library" in str(result)
        assert "Preferences" in str(result)
        assert "SDSMT" in str(result)

    @patch("controllers.settings_service.sys")
    def test_linux_path(self, mock_sys):
        """On linux, should use XDG_CONFIG_HOME or ~/.config."""
        mock_sys.platform = "linux"
        result = _default_settings_path()
        assert "SDSMT" in str(result)


class TestSaveOSError:
    """Cover lines 61-62: _save OSError branch."""

    def test_save_oserror_is_logged(self, tmp_path):
        """_save should log a warning on OSError, not raise."""
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        # Make _save fail by patching open to raise OSError
        with patch("builtins.open", side_effect=OSError("disk full")):
            # Should not raise
            svc._save()

    def test_set_survives_save_oserror(self, tmp_path):
        """set() should update in-memory data even if _save fails."""
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        with patch("pathlib.Path.mkdir", side_effect=OSError("denied")):
            svc.set("key", "value")
        # In-memory value should still be set
        assert svc.get("key") == "value"


class TestEncodeDuckTypedByteArray:
    """Cover lines 74-78: _encode with duck-typed byte-array objects."""

    def test_encode_object_with_data_method(self):
        """_encode should base64-encode objects with a .data() method returning bytes."""
        mock_ba = MagicMock()
        mock_ba.data.return_value = b"hello"
        result = SettingsService._encode(mock_ba)
        assert isinstance(result, dict)
        assert "__bytes__" in result

    def test_encode_object_with_data_method_roundtrip(self, tmp_path):
        """Setting a QByteArray-like object should round-trip correctly."""
        mock_ba = MagicMock()
        mock_ba.data.return_value = b"\x00\x01\x02"
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        svc.set("blob", mock_ba)
        assert svc.get("blob") == b"\x00\x01\x02"

    def test_encode_object_with_data_raising_typeerror(self):
        """_encode should fall through if .data() raises TypeError."""
        mock_obj = MagicMock()
        mock_obj.data.side_effect = TypeError("not bytes")
        result = SettingsService._encode(mock_obj)
        # Should return the original object since data() failed
        assert result is mock_obj

    def test_encode_object_with_data_raising_attributeerror(self):
        """_encode should fall through if bytes() on .data() raises AttributeError."""
        mock_obj = MagicMock()
        mock_obj.data.side_effect = AttributeError("no data")
        result = SettingsService._encode(mock_obj)
        assert result is mock_obj


class TestGetListNonList:
    """Cover line 156: get_list when value is not a list."""

    def test_get_list_returns_empty_for_non_list(self, tmp_path):
        """get_list should return [] when stored value is not a list."""
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        svc._data["test_key"] = "not a list"
        assert svc.get_list("test_key") == []

    def test_get_list_returns_empty_for_int(self, tmp_path):
        """get_list should return [] when stored value is an int."""
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        svc._data["test_key"] = 42
        assert svc.get_list("test_key") == []

    def test_get_list_returns_empty_for_dict(self, tmp_path):
        """get_list should return [] when stored value is a dict."""
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        svc._data["test_key"] = {"a": 1}
        assert svc.get_list("test_key") == []

    def test_get_list_returns_list_when_valid(self, tmp_path):
        """get_list should return the list when value is a list."""
        path = tmp_path / "settings.json"
        svc = SettingsService(path=path)
        svc._data["test_key"] = ["a", "b"]
        assert svc.get_list("test_key") == ["a", "b"]
