"""Tests that the SPICE netlist syntax highlighter uses theme colors."""

from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent.parent / "GUI"
STYLES_DIR = GUI_DIR / "styles"


def test_highlighter_no_hardcoded_colors():
    """Verify SpiceHighlighter does not contain hardcoded color values."""
    source = (GUI_DIR / "netlist_preview.py").read_text()
    assert "#4CAF50" not in source, "Comment color should come from theme, not hardcoded"
    assert "#2196F3" not in source, "Directive color should come from theme, not hardcoded"
    assert "#9C27B0" not in source, "Keyword color should come from theme, not hardcoded"


def test_highlighter_uses_theme_manager():
    """Verify SpiceHighlighter uses theme_manager for colors."""
    source = (GUI_DIR / "netlist_preview.py").read_text()
    assert "theme_manager.color" in source, "Highlighter should use theme_manager.color()"
    assert "on_theme_changed" in source, "Highlighter should listen for theme changes"


def test_syntax_colors_in_both_themes():
    """Verify syntax highlighting color keys exist in both themes."""
    keys = ["syntax_comment", "syntax_directive", "syntax_keyword"]
    for theme_file in ("light_theme.py", "dark_theme.py"):
        source = (STYLES_DIR / theme_file).read_text()
        for key in keys:
            assert f'"{key}"' in source, f"{theme_file} is missing color key '{key}'"
