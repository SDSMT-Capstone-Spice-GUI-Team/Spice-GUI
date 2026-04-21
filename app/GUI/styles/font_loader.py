"""Font loader for bundled and system fonts.

Loads bundled font files (e.g. OpenDyslexic) into the Qt font database
so they are available by family name without system-level installation.
"""

import logging
from pathlib import Path

from PyQt6.QtGui import QFontDatabase

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).parent / "fonts"

DYSLEXIA_FONT_FAMILY = "OpenDyslexic"
DEFAULT_FONT_FAMILY = "JetBrains Mono"


def load_bundled_fonts() -> list[str]:
    """Register all .otf/.ttf files in the fonts/ directory with Qt.

    Returns a list of font family names that were successfully loaded.
    """
    loaded: list[str] = []
    if not _FONTS_DIR.is_dir():
        return loaded

    for font_file in sorted(_FONTS_DIR.iterdir()):
        if font_file.suffix.lower() not in (".otf", ".ttf"):
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id < 0:
            logger.warning("Failed to load font: %s", font_file.name)
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        for family in families:
            if family not in loaded:
                loaded.append(family)
        logger.debug("Loaded font %s (families: %s)", font_file.name, families)

    return loaded


def available_font_families() -> list[str]:
    """Return all font families available to the application."""
    return QFontDatabase.families()
