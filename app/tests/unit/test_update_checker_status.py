"""Tests for the manual startup update-check status API (issue #905).

Covers ``services.update_checker.check_for_update_status`` and its ``UpdateOutcome``
classification, which lets the GUI distinguish "up to date" from a network error.
"""

import json

import pytest
from services.update_checker import (
    UpdateOutcome,
    UpdateResult,
    check_for_update_status,
)

CURRENT = "0.1.0"
OWNER = "SDSMT-Capstone-Spice-GUI-Team"
REPO = "Spice-GUI"


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


def _json_response(tag_name: str, assets=None) -> FakeResponse:
    if assets is None:
        assets = [{"name": "SpiceGUI-0.1.0.exe", "browser_download_url": "https://dl/SpiceGUI.exe"}]
    payload = json.dumps({"tag_name": tag_name, "assets": assets}).encode("utf-8")
    return FakeResponse(payload)


class TestStatusUpToDate:
    def test_equal_version_is_up_to_date(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        result = check_for_update_status(CURRENT, OWNER, REPO, lambda req: _json_response("0.1.0"))
        assert result.outcome is UpdateOutcome.UP_TO_DATE
        assert result.latest is None
        assert result.error is None

    def test_older_version_is_up_to_date(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        result = check_for_update_status(CURRENT, OWNER, REPO, lambda req: _json_response("0.0.9"))
        assert result.outcome is UpdateOutcome.UP_TO_DATE


class TestStatusAvailable:
    def test_newer_version_is_available(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        result = check_for_update_status(CURRENT, OWNER, REPO, lambda req: _json_response("0.2.0"))
        assert result.outcome is UpdateOutcome.AVAILABLE
        assert result.latest is not None
        assert result.latest.tag == "0.2.0"
        assert result.latest.installer_url == "https://dl/SpiceGUI.exe"


class TestStatusError:
    def test_network_error_returns_error(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)

        def boom(req):
            raise ConnectionError("offline")

        result = check_for_update_status(CURRENT, OWNER, REPO, boom)
        assert result.outcome is UpdateOutcome.ERROR
        assert result.latest is None
        assert result.error

    def test_no_installer_returns_error(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)
        result = check_for_update_status(CURRENT, OWNER, REPO, lambda req: _json_response("0.2.0", assets=[]))
        assert result.outcome is UpdateOutcome.ERROR
        assert result.error

    def test_dev_mode_returns_error(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: False)
        result = check_for_update_status(CURRENT, OWNER, REPO)
        assert result.outcome is UpdateOutcome.ERROR
        assert "source" in result.error

    def test_none_payload_returns_error(self, monkeypatch):
        monkeypatch.setattr("services.update_checker._is_frozen", lambda: True)

        def boom(req):
            return FakeResponse(b"null")

        result = check_for_update_status(CURRENT, OWNER, REPO, boom)
        assert result.outcome is UpdateOutcome.ERROR
