"""Tests for the framework-free update checker.

These cover the pure logic (version comparison) and the network/asset behaviour
behind ``update_checker`` without importing PyQt6, so they run fast and offline.
"""

import os
from pathlib import Path

from services import update_checker

# --- version comparison -------------------------------------------------------


def test_compare_versions_equal():
    assert update_checker.compare_versions("1.0.0", "1.0.0") == 0


def test_compare_versions_newer():
    assert update_checker.compare_versions("1.0.1", "1.0.0") == 1
    assert update_checker.compare_versions("1.1.0", "1.0.9") == 1
    assert update_checker.compare_versions("2.0.0", "1.9.9") == 1


def test_compare_versions_older():
    assert update_checker.compare_versions("1.0.0", "1.0.1") == -1
    assert update_checker.compare_versions("1.0.9", "1.1.0") == -1
    assert update_checker.compare_versions("1.9.9", "2.0.0") == -1


def test_compare_versions_strips_v_prefix():
    assert update_checker.compare_versions("v1.2.3", "1.2.3") == 0
    assert update_checker.compare_versions("V0.1.0", "1.0.0") == -1


def test_compare_versions_trailing_components():
    assert update_checker.compare_versions("1.0", "1.0.0") == 0
    assert update_checker.compare_versions("1.0.1", "1.0") == 1


def test_compare_versions_alpha_tag_treated_as_older():
    # A non-numeric "dev" tag should never compare as newer than a real release.
    assert update_checker.compare_versions("dev", "1.0.0") < 0
    assert update_checker.new_version_available("dev", "1.0.0") is True
    assert update_checker.new_version_available("1.0.0", "dev") is False


# --- check_for_update ---------------------------------------------------------


def test_check_for_update_network_error():
    result = update_checker.check_for_update("0.1.0", None)
    assert result["status"] == "network_error"
    assert result["version"] is None
    assert result["has_downloader"] is False


def test_check_for_update_prerelease():
    # A pre-release (e.g. "v0.1.0-alpha1") is treated as a development build, not
    # a full release to offer as an update.
    result = update_checker.check_for_update("0.1.0", "v0.1.0-alpha1")
    assert result["status"] == "prerelease"
    assert result["version"] == "v0.1.0-alpha1"
    assert result["has_downloader"] is False


def test_check_for_update_available():
    result = update_checker.check_for_update("0.1.0", "v1.0.0")
    assert result["status"] == "update_available"
    assert result["version"] == "v1.0.0"
    assert result["has_downloader"] is True


def test_check_for_update_up_to_date():
    result = update_checker.check_for_update("1.0.0", "v1.0.0")
    assert result["status"] == "up_to_date"
    assert result["has_downloader"] is False


def test_check_for_update_skipped():
    result = update_checker.check_for_update("1.0.0", "v2.0.0", skipped_version="2.0.0")
    assert result["status"] == "skipped"


def test_check_for_update_skipped_ignores_prefix_mismatch():
    # skipped_version stored as "2.0.0" matches remote "v2.0.0" by numeric form.
    result = update_checker.check_for_update("1.0.0", "v2.0.0", skipped_version="2.0.0")
    assert result["status"] == "skipped"


def test_check_for_update_not_skipped_when_version_differs():
    result = update_checker.check_for_update("1.0.0", "v2.0.0", skipped_version="2.1.0")
    assert result["status"] == "update_available"


def test_check_for_update_network_error_when_not_skipped():
    # No remote tag at all beats skip handling.
    result = update_checker.check_for_update("1.0.0", None, skipped_version="2.0.0")
    assert result["status"] == "network_error"


# --- new_version_available ----------------------------------------------------


def test_new_version_available_true():
    assert update_checker.new_version_available("0.9.0", "1.0.0") is True


def test_new_version_available_false():
    assert update_checker.new_version_available("1.0.0", "1.0.0") is False
    assert update_checker.new_version_available("2.0.0", "1.0.0") is False


# --- latest_release_tag (network) --------------------------------------------


def test_latest_release_tag_returns_tag(monkeypatch):
    fake = {"tag_name": "v2.3.4", "assets": []}
    monkeypatch.setattr(
        update_checker.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(200, fake),
    )
    assert update_checker.latest_release_tag() == "v2.3.4"


def test_latest_release_tag_none_on_non_200(monkeypatch):
    monkeypatch.setattr(
        update_checker.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(404, {}),
    )
    assert update_checker.latest_release_tag() is None


def test_latest_release_tag_none_on_network_error(monkeypatch):
    def boom(*args, **kwargs):
        raise update_checker.requests.RequestException("offline")

    monkeypatch.setattr(update_checker.requests, "get", boom)
    assert update_checker.latest_release_tag() is None


def test_latest_release_tag_none_on_bad_json(monkeypatch):
    monkeypatch.setattr(
        update_checker.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(200, object()),
    )
    # ``.json()`` raising ValueError must be swallowed.
    monkeypatch.setattr(
        _FakeResponse,
        "json",
        lambda self: (_ for _ in ()).throw(ValueError("nope")),
    )
    assert update_checker.latest_release_tag() is None


def test_latest_release_tag_none_when_no_tag(monkeypatch):
    monkeypatch.setattr(
        update_checker.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(200, {"foo": "bar"}),
    )
    assert update_checker.latest_release_tag() is None


# --- download_installer -------------------------------------------------------


def test_download_installer_streams_to_file(monkeypatch, tmp_path):
    payload = b"INSTALLER-BYTES"
    download_url = "https://example.com/SpiceGUI-1.0.0.exe"
    release = {
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "SpiceGUI-1.0.0.exe", "browser_download_url": download_url}
        ],
    }

    captured = {}

    def fake_get(url, timeout=None, stream=False):
        if url == update_checker.LATEST_RELEASE_URL:
            captured["stream"] = stream
            return _FakeResponse(200, release)
        return _FakeResponse(200, payload, is_binary=True)

    monkeypatch.setattr(update_checker.requests, "get", fake_get)

    result = update_checker.download_installer(remote_tag="v1.0.0", tmp_dir=tmp_path)
    assert result is not None
    assert result.name.endswith(".exe")
    assert result.read_bytes() == payload
    # The metadata request must not have used streaming (needed for .json()).
    assert captured.get("stream") is False


def test_download_installer_none_when_no_exe_asset(monkeypatch, tmp_path):
    release = {
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "notes.txt", "browser_download_url": "https://x/notes.txt"}
        ],
    }
    monkeypatch.setattr(
        update_checker.requests,
        "get",
        lambda url, **kw: _FakeResponse(200, release),
    )
    assert (
        update_checker.download_installer(remote_tag="v1.0.0", tmp_dir=tmp_path) is None
    )


def test_download_installer_none_on_network_error(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise update_checker.requests.RequestException("offline")

    monkeypatch.setattr(update_checker.requests, "get", boom)
    assert (
        update_checker.download_installer(remote_tag="v1.0.0", tmp_dir=tmp_path) is None
    )


def test_download_installer_none_on_bad_json(monkeypatch, tmp_path):
    def bad_json():
        raise ValueError("bad")

    resp = _FakeResponse(200, object())
    monkeypatch.setattr(resp, "json", bad_json)
    monkeypatch.setattr(update_checker.requests, "get", lambda *a, **k: resp)
    assert (
        update_checker.download_installer(remote_tag="v1.0.0", tmp_dir=tmp_path) is None
    )


# --- helper -------------------------------------------------------------------


class _FakeResponse:
    """Minimal ``requests.Response`` stand-in for tests."""

    def __init__(self, status_code, data, is_binary=False):
        self.status_code = status_code
        self._data = data
        self._is_binary = is_binary

    def json(self):
        return self._data

    def iter_content(self, chunk_size=8192):
        if self._is_binary:
            yield self._data
