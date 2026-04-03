"""Stub for font loading — replace with Jon's implementation when available."""

DEFAULT_FONT_FAMILY = ""
DYSLEXIA_FONT_FAMILY = "OpenDyslexic"


def load_bundled_fonts():
    """Load bundled font files. Stub — no-op until font files are added."""
    pass


def available_font_families():
    """Return list of available font families."""
    from PyQt6.QtGui import QFontDatabase

    return QFontDatabase.families()
