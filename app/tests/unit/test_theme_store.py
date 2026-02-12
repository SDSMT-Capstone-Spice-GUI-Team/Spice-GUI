"""Tests for ThemeStore persistence layer."""

import json

import pytest
from GUI.styles.custom_theme import CustomTheme
from GUI.styles.theme_store import (
    _filename_safe,
    delete_theme,
    export_theme,
    import_theme,
    list_custom_themes,
    load_theme,
    save_theme,
)


class TestFilenameSafe:
    """Verify filename sanitization."""

    def test_basic_name(self):
        assert _filename_safe("My Theme") == "my-theme"

    def test_special_chars(self):
        assert _filename_safe("Foo!@#$%Bar") == "foobar"

    def test_empty_string(self):
        assert _filename_safe("") == "untitled"

    def test_underscores_to_hyphens(self):
        assert _filename_safe("foo_bar") == "foo-bar"


class TestSaveLoadRoundTrip:
    """Verify save + load round-trip."""

    def test_round_trip(self, tmp_path):
        theme = CustomTheme("Ocean Blue", "dark", {"background_primary": "#0A1628"}, theme_is_dark=True)
        stem = save_theme(theme, themes_dir=tmp_path)
        assert stem == "ocean-blue"
        assert (tmp_path / "ocean-blue.json").exists()

        loaded = load_theme(stem, themes_dir=tmp_path)
        assert loaded is not None
        assert loaded.name == "Ocean Blue"
        assert loaded.base_name == "dark"
        assert loaded.is_dark is True
        assert loaded.color_hex("background_primary") == "#0A1628"


class TestListThemes:
    """Verify listing custom themes."""

    def test_empty_dir(self, tmp_path):
        assert list_custom_themes(themes_dir=tmp_path) == []

    def test_lists_saved_themes(self, tmp_path):
        t1 = CustomTheme("Alpha", "light", {}, theme_is_dark=False)
        t2 = CustomTheme("Beta", "dark", {}, theme_is_dark=True)
        save_theme(t1, themes_dir=tmp_path)
        save_theme(t2, themes_dir=tmp_path)
        result = list_custom_themes(themes_dir=tmp_path)
        names = [name for name, _ in result]
        assert "Alpha" in names
        assert "Beta" in names


class TestDeleteTheme:
    """Verify theme deletion."""

    def test_delete_existing(self, tmp_path):
        theme = CustomTheme("ToDelete", "light", {}, theme_is_dark=False)
        stem = save_theme(theme, themes_dir=tmp_path)
        assert delete_theme(stem, themes_dir=tmp_path) is True
        assert list_custom_themes(themes_dir=tmp_path) == []

    def test_delete_nonexistent(self, tmp_path):
        assert delete_theme("nope", themes_dir=tmp_path) is False


class TestExportImport:
    """Verify export + import round-trip."""

    def test_export_import(self, tmp_path):
        theme = CustomTheme("Portable", "light", {"grid_minor": "#AAAAAA"}, theme_is_dark=False)
        export_path = tmp_path / "exported.json"
        export_theme(theme, export_path)
        assert export_path.exists()

        import_dir = tmp_path / "imported"
        import_dir.mkdir()
        imported = import_theme(export_path, themes_dir=import_dir)
        assert imported is not None
        assert imported.name == "Portable"
        assert imported.color_hex("grid_minor").lower() == "#aaaaaa"


class TestInvalidJson:
    """Verify graceful handling of corrupt files."""

    def test_load_invalid_json(self, tmp_path):
        bad_file = tmp_path / "broken.json"
        bad_file.write_text("not valid json{{{", encoding="utf-8")
        result = load_theme("broken", themes_dir=tmp_path)
        assert result is None

    def test_load_missing_name_key(self, tmp_path):
        bad_file = tmp_path / "noname.json"
        bad_file.write_text('{"base": "light", "colors": {}}', encoding="utf-8")
        result = load_theme("noname", themes_dir=tmp_path)
        assert result is None
