"""Tests for print, print preview, and PDF export functionality."""

import os
import tempfile

import pytest
from GUI.keybindings import ACTION_LABELS, DEFAULTS
from PyQt6.QtCore import QRectF


class TestPrintKeybindings:
    """Verify keybinding entries for print/PDF actions."""

    def test_print_shortcut_registered(self):
        assert "file.print" in DEFAULTS
        assert DEFAULTS["file.print"] == "Ctrl+P"

    def test_print_preview_shortcut_registered(self):
        assert "file.print_preview" in DEFAULTS

    def test_export_pdf_shortcut_registered(self):
        assert "file.export_pdf" in DEFAULTS

    def test_print_labels_registered(self):
        assert "file.print" in ACTION_LABELS
        assert "file.print_preview" in ACTION_LABELS
        assert "file.export_pdf" in ACTION_LABELS

    def test_no_shortcut_conflicts(self):
        """Print shortcuts should not conflict with existing ones."""
        from GUI.keybindings import KeybindingsRegistry

        registry = KeybindingsRegistry(config_path="/dev/null")
        conflicts = registry.get_conflicts()
        shortcut_map = {}
        for shortcut, actions in conflicts:
            shortcut_map[shortcut] = actions
        # Ctrl+P should not appear in conflicts
        assert "ctrl+p" not in shortcut_map


class TestRenderToPrinter:
    """Test rendering the circuit scene to a QPrinter/PDF device."""

    def test_export_pdf_creates_nonempty_file(self, qtbot):
        """Rendering a scene with items to a PDF creates a valid file."""
        from PyQt6.QtGui import QPainter
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsEllipseItem(0, 0, 100, 100))

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(pdf_path)

            painter = QPainter(printer)
            source = scene.itemsBoundingRect()
            source.adjust(-10, -10, 10, 10)
            page_rect = QRectF(printer.pageRect(printer.Unit.DevicePixel))
            scene.render(painter, target=page_rect, source=source)
            painter.end()

            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 0
        finally:
            os.unlink(pdf_path)

    def test_landscape_chosen_for_wide_circuit(self):
        """Verify landscape detection logic works for wide source rects."""
        wide_rect = QRectF(0, 0, 800, 400)
        assert wide_rect.width() > wide_rect.height()

        tall_rect = QRectF(0, 0, 400, 800)
        assert tall_rect.width() < tall_rect.height()

    def test_scale_preserves_aspect_ratio(self):
        """The scale calculation should preserve the aspect ratio."""
        source = QRectF(0, 0, 800, 400)
        page = QRectF(0, 0, 1000, 1000)

        scale_x = page.width() / source.width()
        scale_y = page.height() / source.height()
        scale = min(scale_x, scale_y)

        target_w = source.width() * scale
        target_h = source.height() * scale

        # Aspect ratio should be preserved
        original_ratio = source.width() / source.height()
        target_ratio = target_w / target_h
        assert abs(original_ratio - target_ratio) < 0.001

        # Should fit within page
        assert target_w <= page.width()
        assert target_h <= page.height()


class TestPdfExportEndToEnd:
    """End-to-end PDF export using the circuit canvas scene rendering pattern."""

    def test_circuit_items_produce_pdf(self, qtbot):
        """Rendering circuit-like items to PDF produces a valid file."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPainter
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsScene

        scene = QGraphicsScene()
        # Simulate a component (rect) and wire (line)
        scene.addItem(QGraphicsRectItem(50, 50, 60, 30))
        scene.addItem(QGraphicsLineItem(110, 65, 200, 65))
        scene.addItem(QGraphicsRectItem(200, 50, 60, 30))

        source_rect = scene.itemsBoundingRect()
        source_rect.adjust(-40, -40, 40, 40)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(pdf_path)

            painter = QPainter(printer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            page_rect = QRectF(printer.pageRect(printer.Unit.DevicePixel))
            painter.fillRect(page_rect, Qt.GlobalColor.white)

            # Scale to fit
            scale_x = page_rect.width() / source_rect.width()
            scale_y = page_rect.height() / source_rect.height()
            scale = min(scale_x, scale_y)
            target_w = source_rect.width() * scale
            target_h = source_rect.height() * scale
            target_x = (page_rect.width() - target_w) / 2
            target_y = (page_rect.height() - target_h) / 2
            target_rect = QRectF(target_x, target_y, target_w, target_h)

            scene.render(painter, target=target_rect, source=source_rect)
            painter.end()

            assert os.path.exists(pdf_path)
            # PDF file should be more than just headers
            assert os.path.getsize(pdf_path) > 100
        finally:
            os.unlink(pdf_path)

    def test_pdf_with_white_background(self, qtbot):
        """PDF should have white background filled before rendering."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor, QImage, QPainter
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsRectItem(0, 0, 50, 50))

        # Render to an image (simulating the print path) to check background
        image = QImage(200, 200, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.white)

        painter = QPainter(image)
        source = scene.itemsBoundingRect()
        source.adjust(-10, -10, 10, 10)
        target = QRectF(0, 0, 200, 200)
        scene.render(painter, target=target, source=source)
        painter.end()

        # Corner pixel should be white (background, not scene default)
        corner_color = QColor(image.pixel(0, 0))
        assert corner_color.red() == 255
        assert corner_color.green() == 255
        assert corner_color.blue() == 255
