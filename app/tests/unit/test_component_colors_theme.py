"""Tests that component colors use the theme system, not the hardcoded COMPONENT_COLORS dict."""

import ast
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent.parent / "GUI"
STYLES_DIR = GUI_DIR / "styles"


def test_renderers_uses_theme_not_component_colors():
    """Verify renderers.py uses theme_manager instead of COMPONENT_COLORS."""
    source = (GUI_DIR / "renderers.py").read_text()
    assert (
        "COMPONENT_COLORS" not in source
    ), "renderers.py should use theme_manager.get_component_color() instead of COMPONENT_COLORS"
    assert "theme_manager" in source


def test_themes_have_all_color_keys():
    """Verify all component types in _COLOR_KEYS have matching theme color entries.

    Parses the source code directly to avoid PyQt6 import issues in CI.
    """
    # Extract _COLOR_KEYS values from constants.py
    constants_src = (STYLES_DIR / "constants.py").read_text()
    # Find the _COLOR_KEYS dict literal
    tree = ast.parse(constants_src)
    color_keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_COLOR_KEYS":
                    if isinstance(node.value, ast.Dict):
                        for val in node.value.values:
                            if isinstance(val, ast.Constant):
                                color_keys.add(val.value)

    assert color_keys, "Failed to parse _COLOR_KEYS from constants.py"

    # Check each theme file has these color keys in _colors dict
    for theme_file in ("light_theme.py", "dark_theme.py"):
        source = (STYLES_DIR / theme_file).read_text()
        for key in color_keys:
            assert f'"{key}"' in source, f"{theme_file} is missing color key '{key}'"
