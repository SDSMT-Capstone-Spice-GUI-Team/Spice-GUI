"""theme_store.py - Persistence layer for custom color themes.

Stores themes as JSON files in ~/.spice-gui/themes/.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from .custom_theme import CustomTheme

logger = logging.getLogger(__name__)

_THEMES_DIR = Path.home() / ".spice-gui" / "themes"
_SCHEMA_VERSION = 1


def _filename_safe(name: str) -> str:
    """Convert a theme name to a safe filename (lowercase, hyphens)."""
    safe = re.sub(r"[^\w\s-]", "", name.lower())
    safe = re.sub(r"[\s_]+", "-", safe).strip("-")
    return safe or "untitled"


def _ensure_dir():
    _THEMES_DIR.mkdir(parents=True, exist_ok=True)


def list_custom_themes(themes_dir: Optional[Path] = None) -> list:
    """Return list of (display_name, filename_stem) for all saved themes."""
    d = themes_dir if themes_dir is not None else _THEMES_DIR
    if not d.exists():
        return []
    result = []
    for path in sorted(d.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = data.get("name", path.stem)
            result.append((name, path.stem))
        except (json.JSONDecodeError, OSError):
            continue
    return result


def load_theme(
    name_or_stem: str, themes_dir: Optional[Path] = None
) -> Optional[CustomTheme]:
    """Load a custom theme by filename stem. Returns None on error."""
    d = themes_dir if themes_dir is not None else _THEMES_DIR
    path = d / f"{name_or_stem}.json"
    if not path.exists():
        logger.warning("Theme file not found: %s", path)
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CustomTheme(
            name=data["name"],
            base=data.get("base", "light"),
            colors=data.get("colors", {}),
            theme_is_dark=data.get("is_dark", False),
        )
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.error("Failed to load theme %s: %s", name_or_stem, e)
        return None


def save_theme(theme: CustomTheme, themes_dir: Optional[Path] = None) -> str:
    """Save a custom theme to disk. Returns the filename stem."""
    d = themes_dir if themes_dir is not None else _THEMES_DIR
    d.mkdir(parents=True, exist_ok=True)
    stem = _filename_safe(theme.name)
    data = {
        "name": theme.name,
        "base": theme.base_name,
        "is_dark": theme.is_dark,
        "version": _SCHEMA_VERSION,
        "colors": theme.get_color_overrides(),
    }
    path = d / f"{stem}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return stem


def delete_theme(name_or_stem: str, themes_dir: Optional[Path] = None) -> bool:
    """Delete a custom theme file. Returns True if deleted."""
    d = themes_dir if themes_dir is not None else _THEMES_DIR
    path = d / f"{name_or_stem}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def export_theme(theme: CustomTheme, path: Path) -> None:
    """Export a custom theme to an arbitrary file path."""
    data = {
        "name": theme.name,
        "base": theme.base_name,
        "is_dark": theme.is_dark,
        "version": _SCHEMA_VERSION,
        "colors": theme.get_color_overrides(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def import_theme(
    path: Path, themes_dir: Optional[Path] = None
) -> Optional[CustomTheme]:
    """Import a theme JSON file into the themes directory. Returns the theme or None."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        theme = CustomTheme(
            name=data["name"],
            base=data.get("base", "light"),
            colors=data.get("colors", {}),
            theme_is_dark=data.get("is_dark", False),
        )
        save_theme(theme, themes_dir=themes_dir)
        return theme
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.error("Failed to import theme from %s: %s", path, e)
        return None
