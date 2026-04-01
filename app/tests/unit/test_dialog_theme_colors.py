"""Tests that dialog widgets use theme colors instead of hardcoded values."""

import ast
import textwrap
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent.parent / "GUI"


def _read_source(filename):
    return (GUI_DIR / filename).read_text()


def test_results_plot_dialog_no_hardcoded_marker_colors():
    """Verify results_plot_dialog uses theme colors, not hardcoded hex strings."""
    source = _read_source("results_plot_dialog.py")
    # Should not contain the old hardcoded marker colors
    assert "#CC0066" not in source, "Cutoff marker color should come from theme, not hardcoded #CC0066"
    assert "#006633" not in source, "Unity-gain marker color should come from theme, not hardcoded #006633"


def test_results_plot_dialog_imports_theme_manager():
    """Verify results_plot_dialog imports theme_manager."""
    source = _read_source("results_plot_dialog.py")
    assert "theme_manager" in source, "results_plot_dialog should import theme_manager"
