"""Backward-compatible re-export — canonical location is services.theme_store."""

# AUDIT(quality): re-exporting private names (_SCHEMA_VERSION, _THEMES_DIR, _ensure_dir, _filename_safe) leaks implementation details; only re-export public API
from services.theme_store import (
    _SCHEMA_VERSION,
    _THEMES_DIR,
    _ensure_dir,
    _filename_safe,
    delete_theme,
    export_theme,
    import_theme,
    list_custom_themes,
    load_theme,
    save_theme,
)

__all__ = [
    "_THEMES_DIR",
    "_SCHEMA_VERSION",
    "_filename_safe",
    "_ensure_dir",
    "list_custom_themes",
    "load_theme",
    "save_theme",
    "delete_theme",
    "export_theme",
    "import_theme",
]
