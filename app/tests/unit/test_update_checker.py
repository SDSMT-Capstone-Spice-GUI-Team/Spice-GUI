"""Tests for the Qt-free update checker (services.update_checker).

Covers issue #905: startup version check against GitHub Releases, installer
download/open flow, and skip-this-version persistence. The core logic is Qt-free
and network access is injected, so these tests never touch the network.
"""

import json
import sys
from pathlib import Path

import pytest
from services.update_checker import (
    INSTALLER_SUFFIX,
    LatestRelease,
    _fetch_latest,
    _select_installer,
    check_for_update,
    download_and_open_installer,
    is_newer,
    parse_version,
)

CURRENT = "0.1.0"
OWNER = "SDSMT-Capstone-Spice-GUI-Team"
REPO = "Spice-GUI"


class FakeResponse:
    """Minimal stand-in for a urllib response (has .read())."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class TestParseVersion:
    """parse_version should normalize tags into comparable int tuples."""

    @pytest.mark.parametrize(
        "tag,expected",
        [
            ("0.1.0", (0, 1, 0)),
            ("v1.2.3", (1, 2, 3)),
            ("1.2", (1, 2)),
            ("1.2.3-rc1", (1, 2, 3)),
            ("0.1.0+build.5", (0, 1, 0)),
            ("  2.0.1  ", (2, 0, 1)),
        ],
    )
    def test_variants(self, tag, expected):
        assert parse_version(tag) == expected

    def test_non_numeric(self):
        """Non-numeric components are ignored."""
        assert parse_version("1.x.2") == (1, 2)

    def test_empty(self):
        assert parse_version("") == ()


class TestIsNewer:
    """Semantic comparison of version tuples."""

    def test_strictly_greater(self):
        assert is_newer("0.2.0", "0.1.0") is True

    def test_greater_second_component(self):
        assert is_newer("0.1.1", "0.1.0") is True

    def test_equal(self):
        assert is_newer("0.1.0", "0.1.0") is False

    def test_older(self):
        assert is_newer("0.0.9", "0.1.0") is False

    def test_prefix_tags(self):
        assert is_newer("v1.2.3", "1.2.0") is True


class TestSelectInstaller:
    """An installer is the first browser_download_url whose asset name ends .exe."""

    def test_picks_exe(self):
        assets = [
            {"name": "README", "browser_download_url": "https://example/README"},
            {
                "name": "SpiceGUI-0.1.0.exe",
                "browser_download_url": "https://example/SpiceGUI.exe",
            },
        ]
        assert _select_installer(assets) == "https://example/SpiceGUI.exe"

    def test_no_exe_returns_none(self):
        assets = [{"name": "Source.zip"}]
        assert _select_installer(assets) is None

    def test_empty_assets(self):
        assert _select_installer([]) is None

    def test_suffix_constant(self):
        assert INSTALLER_SUFFIX == ".exe"


def _json_response(tag_name: str, assets=None) -> FakeResponse:
    assets = assets or [{"name": "SpiceGUI.exe", "browser_download_url": "https://dl/SpiceGUI.exe"}]
    # ``/releases`` returns a *list* of release objects (not a single object,
    # which is what ``/releases/latest`` returns); each entry needs a tag and a
    # publication date to be selectable by ``_pick_latest_release``.
    payload = json.dumps([{"tag_name": tag_name, "published_at": "2024-01-01T00:00:00Z", "assets": assets}]).encode(
        "utf-8"
    )
    return FakeResponse(payload)


class TestFetchLatest:
    """_fetch_latest parses the GitHub ``/releases`` list payload."""

    def test_fetch_parses_release(self):
        resp = _json_response("0.2.0")
        release = _fetch_latest(OWNER, REPO, lambda req: resp)
        assert release == LatestRelease("0.2.0", "https://dl/SpiceGUI.exe")

    def test_fetch_no_installer(self):
        # A list entry with no ``.exe`` asset is skipped entirely, so nothing is
        # selected and ``_fetch_latest`` returns None (new list-based contract).
        resp = _json_response("0.2.0", assets=[{"name": "a.zip"}])
        assert _fetch_latest(OWNER, REPO, lambda req: resp) is None

    def test_fetch_network_error_returns_none(self):
        """A network failure is swallowed, not raised."""

        def boom(req):
            raise RuntimeError("no network")

        assert _fetch_latest(OWNER, REPO, boom) is None


class TestCheckForUpdate:
    def test_newer_release_when_frozen(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        resp = _json_response("0.2.0")
        release = check_for_update(CURRENT, OWNER, REPO, lambda req: resp)
        assert release is not None
        assert release.tag == "0.2.0"

    def test_no_release_when_same_version(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        resp = _json_response("0.1.0")
        assert check_for_update(CURRENT, OWNER, REPO, lambda req: resp) is None

    def test_no_release_when_older_version(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        resp = _json_response("0.0.1")
        assert check_for_update(CURRENT, OWNER, REPO, lambda req: resp) is None

    def test_no_check_in_dev_mode(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: False)
        called = []

        def tracer(req):
            called.append(req)
            return _json_response("9.9.9")

        assert check_for_update(CURRENT, OWNER, REPO, tracer) is None
        assert called == []  # never even attempted a request

    def test_network_error_swallowed(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)

        def boom(req):
            raise ConnectionError("offline")

        assert check_for_update(CURRENT, OWNER, REPO, boom) is None


class _FakeDownloader:
    """Captures the downloaded bytes and returns them."""

    def __init__(self, content: bytes = b"PEfakeexe") -> None:
        self.content = content
        self.saved_to = None

    def __call__(self, url, path):
        path.write_bytes(self.content)
        self.saved_to = path


class _FakeInstallerOpener:
    def __init__(self):
        self.opened = None

    def __call__(self, path):
        self.opened = path
        return True


class TestDownloadAndOpenInstaller:
    def test_downloads_and_opens(self, tmp_path):
        downloader = _FakeDownloader()
        opener = _FakeInstallerOpener()
        release = LatestRelease("0.2.0", "https://dl/SpiceGUI.exe")
        result = download_and_open_installer(release, downloader=downloader, opener_file=opener)
        assert result is True
        assert opener.opened is not None
        assert opener.opened.is_file()

    def test_no_installer_url_returns_false(self):
        release = LatestRelease("0.2.0", None)
        downloader = _FakeDownloader()
        opener = _FakeInstallerOpener()
        assert download_and_open_installer(release, downloader=downloader, opener_file=opener) is False

    def test_open_error_returns_false(self, tmp_path):
        def boom(path):
            raise OSError("can't launch")

        release = LatestRelease("0.2.0", "https://dl/SpiceGUI.exe")
        downloader = _FakeDownloader()
        assert download_and_open_installer(release, downloader=downloader, opener_file=boom) is False
