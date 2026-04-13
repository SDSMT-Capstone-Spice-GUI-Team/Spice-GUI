"""Tests for services.theme_store — pure-Python persistence logic.

Mocks GUI.styles.custom_theme.CustomTheme so tests run without Qt.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.theme_store import _filename_safe, delete_theme, export_theme, list_custom_themes, save_theme

# ---------------------------------------------------------------------------
# Mock CustomTheme -- the real one inherits from BaseTheme which needs Qt
# ---------------------------------------------------------------------------


def _make_custom_theme(name="Test Theme", base="light", colors=None, is_dark=False):
    """Return a mock object that quacks like CustomTheme."""
    t = MagicMock()
    t.name = name
    t.base_name = base
    t.is_dark = is_dark
    t.get_color_overrides.return_value = colors or {}
    return t


# ---- _filename_safe ----


class TestFilenameSafe:
    def test_basic(self):
        assert _filename_safe("My Theme") == "my-theme"

    def test_special_chars(self):
        assert _filename_safe("Foo!@#$%Bar") == "foobar"

    def test_empty(self):
        assert _filename_safe("") == "untitled"

    def test_underscores(self):
        assert _filename_safe("foo_bar") == "foo-bar"

    def test_only_special_chars(self):
        assert _filename_safe("!@#$%") == "untitled"

    def test_whitespace_variants(self):
        assert _filename_safe("a   b") == "a-b"


# ---- list_custom_themes ----


class TestListCustomThemes:
    def test_empty_dir(self, tmp_path):
        assert list_custom_themes(themes_dir=tmp_path) == []

    def test_nonexistent_dir(self, tmp_path):
        assert list_custom_themes(themes_dir=tmp_path / "nonexistent") == []

    def test_lists_themes(self, tmp_path):
        (tmp_path / "alpha.json").write_text(json.dumps({"name": "Alpha"}), encoding="utf-8")
        (tmp_path / "beta.json").write_text(json.dumps({"name": "Beta"}), encoding="utf-8")
        result = list_custom_themes(themes_dir=tmp_path)
        names = [n for n, _ in result]
        assert "Alpha" in names
        assert "Beta" in names

    def test_fallback_to_stem_if_no_name(self, tmp_path):
        (tmp_path / "noname.json").write_text(json.dumps({"colors": {}}), encoding="utf-8")
        result = list_custom_themes(themes_dir=tmp_path)
        assert result[0][0] == "noname"

    def test_invalid_json_skipped(self, tmp_path):
        (tmp_path / "good.json").write_text(json.dumps({"name": "Good"}), encoding="utf-8")
        (tmp_path / "bad.json").write_text("not json{{{", encoding="utf-8")
        result = list_custom_themes(themes_dir=tmp_path)
        assert len(result) == 1
        assert result[0][0] == "Good"


# ---- save_theme ----


class TestSaveTheme:
    def test_save_creates_file(self, tmp_path):
        theme = _make_custom_theme("Ocean", "dark", {"bg": "#001"}, True)
        stem = save_theme(theme, themes_dir=tmp_path)
        assert stem == "ocean"
        assert (tmp_path / "ocean.json").exists()

    def test_save_content(self, tmp_path):
        theme = _make_custom_theme("My Theme", "light", {"fg": "#fff"}, False)
        save_theme(theme, themes_dir=tmp_path)
        data = json.loads((tmp_path / "my-theme.json").read_text(encoding="utf-8"))
        assert data["name"] == "My Theme"
        assert data["base"] == "light"
        assert data["is_dark"] is False
        assert data["colors"] == {"fg": "#fff"}
        assert data["version"] == 1

    def test_save_creates_dir(self, tmp_path):
        subdir = tmp_path / "deep" / "nested"
        theme = _make_custom_theme("T")
        save_theme(theme, themes_dir=subdir)
        assert subdir.is_dir()


# ---- load_theme ----


class TestLoadTheme:
    def test_load_nonexistent(self, tmp_path):
        from services.theme_store import load_theme

        result = load_theme("nope", themes_dir=tmp_path)
        assert result is None

    def test_load_valid(self, tmp_path):
        data = {
            "name": "Ocean",
            "base": "dark",
            "is_dark": True,
            "colors": {"bg": "#123"},
        }
        (tmp_path / "ocean.json").write_text(json.dumps(data), encoding="utf-8")

        mock_ct = MagicMock()
        with patch.dict("sys.modules", {"GUI.styles.custom_theme": MagicMock(CustomTheme=mock_ct)}):
            from importlib import reload

            import services.theme_store as ts_mod

            ts_mod.load_theme("ocean", themes_dir=tmp_path)
        mock_ct.assert_called_once_with(
            name="Ocean",
            base="dark",
            colors={"bg": "#123"},
            theme_is_dark=True,
        )

    def test_load_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
        from services.theme_store import load_theme

        result = load_theme("bad", themes_dir=tmp_path)
        assert result is None

    def test_load_missing_name_key(self, tmp_path):
        (tmp_path / "noname.json").write_text('{"base": "light"}', encoding="utf-8")
        from services.theme_store import load_theme

        result = load_theme("noname", themes_dir=tmp_path)
        assert result is None


# ---- delete_theme ----


class TestDeleteTheme:
    def test_delete_existing(self, tmp_path):
        (tmp_path / "old.json").write_text("{}", encoding="utf-8")
        assert delete_theme("old", themes_dir=tmp_path) is True
        assert not (tmp_path / "old.json").exists()

    def test_delete_nonexistent(self, tmp_path):
        assert delete_theme("missing", themes_dir=tmp_path) is False


# ---- export_theme ----


class TestExportTheme:
    def test_export_writes_file(self, tmp_path):
        theme = _make_custom_theme("Portable", "light", {"grid": "#aaa"}, False)
        path = tmp_path / "exported.json"
        export_theme(theme, path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["name"] == "Portable"
        assert data["colors"] == {"grid": "#aaa"}


# ---- import_theme ----


class TestImportTheme:
    def test_import_valid(self, tmp_path):
        data = {
            "name": "Imported",
            "base": "dark",
            "is_dark": True,
            "colors": {"bg": "#000"},
        }
        src_path = tmp_path / "source.json"
        src_path.write_text(json.dumps(data), encoding="utf-8")

        import_dir = tmp_path / "dest"
        import_dir.mkdir()

        mock_ct = MagicMock(return_value=_make_custom_theme("Imported"))
        with patch.dict("sys.modules", {"GUI.styles.custom_theme": MagicMock(CustomTheme=mock_ct)}):
            from services.theme_store import import_theme

            result = import_theme(src_path, themes_dir=import_dir)
        assert result is not None

    def test_import_invalid_json(self, tmp_path):
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("not json", encoding="utf-8")
        from services.theme_store import import_theme

        result = import_theme(bad_path, themes_dir=tmp_path)
        assert result is None
