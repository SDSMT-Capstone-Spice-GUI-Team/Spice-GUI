"""Tests for simulation.ngspice_config (#832)."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from simulation.ngspice_config import (
    SETTINGS_KEY_NGSPICE_PATH,
    SETTINGS_KEY_NGSPICE_SOURCE,
    bundled_ngspice_path,
    detect_ngspice_sources,
    needs_user_choice,
    resolve_ngspice_path,
    save_ngspice_preference,
    system_ngspice_path,
)


class _FakeSettings:
    """Minimal settings stub for testing."""

    def __init__(self, data=None):
        self._data = data or {}

    def get_str(self, key, default=""):
        val = self._data.get(key)
        return str(val) if val is not None else default

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


# ── bundled_ngspice_path ─────────────────────────────────────────────


class TestBundledNgspicePath:
    def test_returns_path_when_bundled_exists(self, tmp_path):
        ngspice_bin = tmp_path / "ngspice" / "bin"
        ngspice_bin.mkdir(parents=True)
        exe = ngspice_bin / "ngspice"
        exe.write_text("fake")

        with patch("simulation.ngspice_config._bundle_root", return_value=tmp_path):
            with patch("simulation.ngspice_config.platform.system", return_value="Linux"):
                result = bundled_ngspice_path()
        assert result == str(exe)

    def test_returns_none_when_not_bundled(self, tmp_path):
        with patch("simulation.ngspice_config._bundle_root", return_value=tmp_path):
            result = bundled_ngspice_path()
        assert result is None

    def test_windows_exe_suffix(self, tmp_path):
        ngspice_bin = tmp_path / "ngspice" / "bin"
        ngspice_bin.mkdir(parents=True)
        exe = ngspice_bin / "ngspice.exe"
        exe.write_text("fake")

        with patch("simulation.ngspice_config._bundle_root", return_value=tmp_path):
            with patch("simulation.ngspice_config.platform.system", return_value="Windows"):
                result = bundled_ngspice_path()
        assert result == str(exe)


# ── system_ngspice_path ──────────────────────────────────────────────


class TestSystemNgspicePath:
    def test_found_on_path(self):
        with patch("simulation.ngspice_config.shutil.which", return_value="/usr/bin/ngspice"):
            result = system_ngspice_path()
        assert result == "/usr/bin/ngspice"

    def test_not_found_returns_none(self):
        with (
            patch("simulation.ngspice_config.shutil.which", return_value=None),
            patch("simulation.ngspice_config.os.path.isfile", return_value=False),
        ):
            result = system_ngspice_path()
        assert result is None

    def test_fallback_linux(self):
        def fake_isfile(path):
            return path == "/usr/local/bin/ngspice"

        with (
            patch("simulation.ngspice_config.shutil.which", return_value=None),
            patch("simulation.ngspice_config.platform.system", return_value="Linux"),
            patch("simulation.ngspice_config.os.path.isfile", side_effect=fake_isfile),
        ):
            result = system_ngspice_path()
        assert result == "/usr/local/bin/ngspice"


# ── resolve_ngspice_path ─────────────────────────────────────────────


class TestResolveNgspicePath:
    def test_uses_stored_preference(self, tmp_path):
        exe = tmp_path / "ngspice"
        exe.write_text("fake")
        sett = _FakeSettings({SETTINGS_KEY_NGSPICE_PATH: str(exe)})

        result = resolve_ngspice_path(sett)
        assert result == str(exe)

    def test_ignores_stale_stored_path(self, tmp_path):
        """If the stored path no longer exists, fall through to bundled/system."""
        sett = _FakeSettings({SETTINGS_KEY_NGSPICE_PATH: "/nonexistent/ngspice"})

        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value=None),
            patch("simulation.ngspice_config.system_ngspice_path", return_value="/usr/bin/ngspice"),
        ):
            result = resolve_ngspice_path(sett)
        assert result == "/usr/bin/ngspice"

    def test_prefers_bundled_over_system(self, tmp_path):
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value="/bundle/ngspice"),
            patch("simulation.ngspice_config.system_ngspice_path", return_value="/usr/bin/ngspice"),
        ):
            result = resolve_ngspice_path()
        assert result == "/bundle/ngspice"

    def test_falls_back_to_system(self):
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value=None),
            patch("simulation.ngspice_config.system_ngspice_path", return_value="/usr/bin/ngspice"),
        ):
            result = resolve_ngspice_path()
        assert result == "/usr/bin/ngspice"

    def test_returns_none_when_nothing_found(self):
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value=None),
            patch("simulation.ngspice_config.system_ngspice_path", return_value=None),
        ):
            result = resolve_ngspice_path()
        assert result is None

    def test_no_settings_skips_preference(self):
        with patch("simulation.ngspice_config.bundled_ngspice_path", return_value="/bundle/ngspice"):
            result = resolve_ngspice_path(settings=None)
        assert result == "/bundle/ngspice"


# ── detect_ngspice_sources ───────────────────────────────────────────


class TestDetectNgspiceSources:
    def test_returns_both(self):
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value="/b/ngspice"),
            patch("simulation.ngspice_config.system_ngspice_path", return_value="/s/ngspice"),
        ):
            result = detect_ngspice_sources()
        assert result == {"bundled": "/b/ngspice", "system": "/s/ngspice"}


# ── save_ngspice_preference ──────────────────────────────────────────


class TestSaveNgspicePreference:
    def test_stores_path_and_source(self):
        sett = _FakeSettings()
        save_ngspice_preference(sett, "/usr/bin/ngspice", "system")
        assert sett._data[SETTINGS_KEY_NGSPICE_PATH] == "/usr/bin/ngspice"
        assert sett._data[SETTINGS_KEY_NGSPICE_SOURCE] == "system"


# ── needs_user_choice ────────────────────────────────────────────────


class TestNeedsUserChoice:
    def test_true_when_both_exist_and_no_pref(self):
        sett = _FakeSettings()
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value="/b/ngspice"),
            patch("simulation.ngspice_config.system_ngspice_path", return_value="/s/ngspice"),
        ):
            assert needs_user_choice(sett) is True

    def test_false_when_preference_stored(self):
        sett = _FakeSettings({SETTINGS_KEY_NGSPICE_PATH: "/usr/bin/ngspice"})
        assert needs_user_choice(sett) is False

    def test_false_when_only_bundled(self):
        sett = _FakeSettings()
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value="/b/ngspice"),
            patch("simulation.ngspice_config.system_ngspice_path", return_value=None),
        ):
            assert needs_user_choice(sett) is False

    def test_false_when_only_system(self):
        sett = _FakeSettings()
        with (
            patch("simulation.ngspice_config.bundled_ngspice_path", return_value=None),
            patch("simulation.ngspice_config.system_ngspice_path", return_value="/s/ngspice"),
        ):
            assert needs_user_choice(sett) is False
