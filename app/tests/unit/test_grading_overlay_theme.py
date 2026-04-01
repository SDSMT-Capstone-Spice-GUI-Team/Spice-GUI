"""Tests that grading overlay colors use the theme system and are colorblind-friendly."""

from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent.parent / "GUI"
STYLES_DIR = GUI_DIR / "styles"


def test_component_item_no_hardcoded_grading_colors():
    """Verify component_item.py grading overlay uses theme colors."""
    source = (GUI_DIR / "component_item.py").read_text()
    assert "QColor(0, 200, 0" not in source, "Grading passed color should come from theme"
    assert "QColor(220, 0, 0" not in source, "Grading failed color should come from theme"
    assert "grading_passed" in source
    assert "grading_failed" in source


def test_grading_panel_no_hardcoded_colors():
    """Verify grading_panel.py uses theme colors for pass/fail indicators."""
    source = (GUI_DIR / "grading_panel.py").read_text()
    assert 'QColor("green")' not in source, "Grading panel should use theme, not hardcoded green"
    assert 'QColor("red")' not in source, "Grading panel should use theme, not hardcoded red"
    assert "grading_passed" in source
    assert "grading_failed" in source


def test_grading_colors_in_both_themes():
    """Verify grading color keys exist in both themes."""
    keys = ["grading_passed", "grading_failed"]
    for theme_file in ("light_theme.py", "dark_theme.py"):
        source = (STYLES_DIR / theme_file).read_text()
        for key in keys:
            assert f'"{key}"' in source, f"{theme_file} is missing color key '{key}'"


def test_grading_colors_are_not_red_green():
    """Verify grading colors avoid pure red/green for colorblind accessibility."""
    for theme_file in ("light_theme.py", "dark_theme.py"):
        source = (STYLES_DIR / theme_file).read_text()
        # Find the grading color values - they should not be pure red or green
        for line in source.splitlines():
            if "grading_passed" in line and "#" in line:
                # Should not be a pure green (e.g., #00XX00 or #28A745)
                assert "#00FF00" not in line, "grading_passed should not use pure green"
            if "grading_failed" in line and "#" in line:
                # Should not be a pure red (e.g., #FF0000 or #DC3545)
                assert "#FF0000" not in line, "grading_failed should not use pure red"
