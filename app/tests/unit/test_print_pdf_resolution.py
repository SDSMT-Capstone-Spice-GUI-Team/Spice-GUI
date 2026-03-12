"""Tests for print/PDF/report resolution settings (#742, #743, #749).

QPrinter.PrinterMode.HighResolution causes text rendered via QPainter.drawText
inside QGraphicsItem.paint() to be double-scaled: once by the scene-to-device
transform and once by the high-DPI font resolution.  Using ScreenResolution
ensures text and shapes scale proportionally.

These tests verify the source code uses ScreenResolution, not HighResolution.
"""

import inspect


class TestPrintExportUsesScreenResolution:
    """Verify that print/PDF export uses ScreenResolution to avoid oversized text."""

    def test_print_preview_uses_screen_resolution(self):
        from GUI.main_window_print import PrintExportMixin

        source = inspect.getsource(PrintExportMixin._on_print_preview)
        assert "ScreenResolution" in source
        assert "HighResolution" not in source

    def test_print_uses_screen_resolution(self):
        from GUI.main_window_print import PrintExportMixin

        source = inspect.getsource(PrintExportMixin._on_print)
        assert "ScreenResolution" in source
        assert "HighResolution" not in source

    def test_export_pdf_uses_screen_resolution(self):
        from GUI.main_window_print import PrintExportMixin

        source = inspect.getsource(PrintExportMixin._on_export_pdf)
        assert "ScreenResolution" in source
        assert "HighResolution" not in source

    def test_report_renderer_uses_screen_resolution(self):
        from GUI.report_renderer import PDFReportRenderer

        source = inspect.getsource(PDFReportRenderer.render)
        assert "ScreenResolution" in source
        assert "HighResolution" not in source
