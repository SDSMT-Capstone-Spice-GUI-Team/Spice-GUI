"""Tests for recent exports tracking and recall logic."""

import json
import os
import tempfile

import pytest
from GUI.recent_exports import (
    MAX_RECENT_EXPORTS,
    SETTINGS_KEY,
    add_recent_export,
    clear_recent_exports,
    get_recent_exports,
)
from PyQt6.QtCore import QSettings


@pytest.fixture(autouse=True)
def _clean_settings():
    """Clear recent exports before and after each test."""
    settings = QSettings("SDSMT", "SDM Spice")
    settings.setValue(SETTINGS_KEY, "[]")
    yield
    settings.setValue(SETTINGS_KEY, "[]")


class TestGetRecentExports:
    def test_empty_by_default(self):
        assert get_recent_exports() == []

    def test_returns_list(self):
        result = get_recent_exports()
        assert isinstance(result, list)


class TestAddRecentExport:
    def test_add_one_export(self, tmp_path):
        path = tmp_path / "test.csv"
        path.touch()
        add_recent_export(str(path), "CSV", "export_results_csv")
        exports = get_recent_exports()
        assert len(exports) == 1
        assert exports[0]["path"] == str(path)
        assert exports[0]["format"] == "CSV"
        assert exports[0]["export_function"] == "export_results_csv"

    def test_most_recent_first(self, tmp_path):
        p1 = tmp_path / "first.csv"
        p2 = tmp_path / "second.csv"
        p1.touch()
        p2.touch()
        add_recent_export(str(p1), "CSV", "export_results_csv")
        add_recent_export(str(p2), "Excel", "export_results_excel")
        exports = get_recent_exports()
        assert exports[0]["path"] == str(p2)
        assert exports[1]["path"] == str(p1)

    def test_duplicate_path_moves_to_front(self, tmp_path):
        p1 = tmp_path / "file.csv"
        p2 = tmp_path / "other.xlsx"
        p1.touch()
        p2.touch()
        add_recent_export(str(p1), "CSV", "export_results_csv")
        add_recent_export(str(p2), "Excel", "export_results_excel")
        add_recent_export(str(p1), "CSV", "export_results_csv")
        exports = get_recent_exports()
        assert len(exports) == 2
        assert exports[0]["path"] == str(p1)

    def test_max_limit_enforced(self, tmp_path):
        for i in range(MAX_RECENT_EXPORTS + 3):
            p = tmp_path / f"file{i}.csv"
            p.touch()
            add_recent_export(str(p), "CSV", "export_results_csv")
        exports = get_recent_exports()
        assert len(exports) == MAX_RECENT_EXPORTS

    def test_has_timestamp(self, tmp_path):
        p = tmp_path / "test.csv"
        p.touch()
        add_recent_export(str(p), "CSV", "export_results_csv")
        exports = get_recent_exports()
        assert "timestamp" in exports[0]


class TestClearRecentExports:
    def test_clear(self, tmp_path):
        p = tmp_path / "test.csv"
        p.touch()
        add_recent_export(str(p), "CSV", "export_results_csv")
        assert len(get_recent_exports()) == 1
        clear_recent_exports()
        assert len(get_recent_exports()) == 0


class TestFiltersMissing:
    def test_filters_nonexistent_paths(self, tmp_path):
        p = tmp_path / "exists.csv"
        p.touch()
        add_recent_export(str(p), "CSV", "export_results_csv")
        add_recent_export("/nonexistent/path.csv", "CSV", "export_results_csv")
        exports = get_recent_exports()
        # Only the existing file should remain
        assert all(os.path.exists(e["path"]) for e in exports)
