"""Tests for print/PDF/report resolution settings (#742, #743, #749).

QPrinter.PrinterMode.HighResolution causes text rendered via QPainter.drawText
inside QGraphicsItem.paint() to be double-scaled: once by the scene-to-device
transform and once by the high-DPI font resolution.  Using ScreenResolution
ensures text and shapes scale proportionally.

These tests verify that QPrinter is constructed with ScreenResolution by
reading the source files directly (not via inspect.getsource).
"""

import ast
from pathlib import Path


def _module_source(module):
    """Return the source text of a module by reading its __file__."""
    return Path(module.__file__).read_text()


def _function_source(module, func_name):
    """Return the source text of a function/method from a module."""
    tree = ast.parse(_module_source(module))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return ast.get_source_segment(_module_source(module), node)
    raise ValueError(f"{func_name} not found in {module.__file__}")


class TestPrintExportUsesScreenResolution:
    """Verify that print/PDF export uses ScreenResolution to avoid oversized text."""

    def test_print_preview_uses_screen_resolution(self):
        """_on_print_preview must use ScreenResolution, not HighResolution."""
        from GUI import main_window_print

        source = _function_source(main_window_print, "_on_print_preview")
        assert "ScreenResolution" in source
        assert "HighResolution" not in source

    def test_print_uses_screen_resolution(self):
        """_on_print must use ScreenResolution, not HighResolution."""
        from GUI import main_window_print

        source = _function_source(main_window_print, "_on_print")
        assert "ScreenResolution" in source
        assert "HighResolution" not in source

    def test_export_pdf_uses_screen_resolution(self):
        """_on_export_pdf must use ScreenResolution, not HighResolution."""
        from GUI import main_window_print

        source = _function_source(main_window_print, "_on_export_pdf")
        assert "ScreenResolution" in source
        assert "HighResolution" not in source

    def test_report_renderer_uses_screen_resolution(self):
        """PDFReportRenderer.render must use ScreenResolution, not HighResolution."""
        from GUI import report_renderer

        source = _function_source(report_renderer, "render")
        assert "ScreenResolution" in source
        assert "HighResolution" not in source
