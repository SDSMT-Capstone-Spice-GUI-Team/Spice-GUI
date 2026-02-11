"""Print, print preview, and PDF export operations for MainWindow."""

from PyQt6.QtWidgets import QFileDialog, QMessageBox


class PrintExportMixin:
    """Mixin providing print, print preview, and PDF export capabilities."""

    def _get_circuit_source_rect(self):
        """Compute bounding rect of circuit items (excluding grid) with padding.

        Returns QRectF or None if canvas is empty.
        """
        from .annotation_item import AnnotationItem
        from .component_item import ComponentGraphicsItem
        from .wire_item import WireGraphicsItem

        scene = self.canvas.scene
        circuit_items = [
            item
            for item in scene.items()
            if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem, AnnotationItem))
        ]
        if not circuit_items:
            return None

        source_rect = circuit_items[0].sceneBoundingRect()
        for item in circuit_items[1:]:
            source_rect = source_rect.united(item.sceneBoundingRect())

        padding = 40
        source_rect.adjust(-padding, -padding, padding, padding)
        return source_rect

    def _render_to_printer(self, printer):
        """Render the circuit scene onto a QPrinter (or PDF device).

        Scales the scene to fit the printable page area while preserving
        aspect ratio. Forces a white background regardless of theme.
        """
        from PyQt6.QtCore import QRectF, Qt
        from PyQt6.QtGui import QPainter

        source_rect = self._get_circuit_source_rect()
        if source_rect is None:
            return

        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # White background
        page_rect = QRectF(printer.pageRect(printer.Unit.DevicePixel))
        painter.fillRect(page_rect, Qt.GlobalColor.white)

        # Scale source to fit page while preserving aspect ratio
        scale_x = page_rect.width() / source_rect.width()
        scale_y = page_rect.height() / source_rect.height()
        scale = min(scale_x, scale_y)

        target_w = source_rect.width() * scale
        target_h = source_rect.height() * scale
        target_x = (page_rect.width() - target_w) / 2
        target_y = (page_rect.height() - target_h) / 2
        target_rect = QRectF(target_x, target_y, target_w, target_h)

        self.canvas.scene.render(painter, target=target_rect, source=source_rect)
        painter.end()

    def _on_print(self):
        """Open a system print dialog and print the schematic."""
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

        source_rect = self._get_circuit_source_rect()
        if source_rect is None:
            QMessageBox.information(self, "Print", "Nothing to print — the canvas is empty.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Circuit")
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self._render_to_printer(printer)

    def _on_print_preview(self):
        """Open a print preview dialog."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog

        source_rect = self._get_circuit_source_rect()
        if source_rect is None:
            QMessageBox.information(self, "Print Preview", "Nothing to preview — the canvas is empty.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Print Preview — Circuit Schematic")
        preview.paintRequested.connect(self._render_to_printer)
        preview.exec()

    def _on_export_pdf(self):
        """Export the circuit schematic as a PDF file."""
        from PyQt6.QtPrintSupport import QPrinter

        source_rect = self._get_circuit_source_rect()
        if source_rect is None:
            QMessageBox.information(self, "Export PDF", "Nothing to export — the canvas is empty.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export as PDF", "", "PDF Files (*.pdf)")
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filename)

        # Landscape if circuit is wider than tall
        from PyQt6.QtGui import QPageLayout

        if source_rect.width() > source_rect.height():
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)

        self._render_to_printer(printer)
        QMessageBox.information(self, "Export PDF", f"Circuit exported to:\n{filename}")
