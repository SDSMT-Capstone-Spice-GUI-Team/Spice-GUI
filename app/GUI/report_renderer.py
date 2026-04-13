"""PDF report renderer using QPrinter/QPainter.

This is the GUI-layer counterpart to services.report_generator.  It
takes a ReportData bundle (assembled by ReportDataBuilder) and renders
it to a multi-page PDF.  All Qt dependencies live here.
"""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetrics, QPainter
from PyQt6.QtPrintSupport import QPrinter
from services.report_generator import ReportData


class PDFReportRenderer:
    """Renders a ReportData bundle to a multi-page PDF via QPrinter/QPainter."""

    MARGIN_RATIO = 0.05
    TITLE_FONT_SIZE = 24
    HEADING_FONT_SIZE = 16
    BODY_FONT_SIZE = 10
    CODE_FONT_SIZE = 9

    def render(self, filepath: str, data: ReportData, scene=None) -> None:
        """Render report data to a PDF file.

        Args:
            filepath: Output PDF file path.
            data: Assembled report content from ReportDataBuilder.
            scene: Optional QGraphicsScene for schematic rendering.
        """
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filepath)

        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        page_rect = QRectF(printer.pageRect(printer.Unit.DevicePixel))
        margin = page_rect.width() * self.MARGIN_RATIO
        content_rect = page_rect.adjusted(margin, margin, -margin, -margin)

        first_page = True

        if data.config.include_title:
            self._render_title_page(painter, content_rect, data)
            first_page = False

        if data.config.include_schematic and scene is not None:
            if not first_page:
                printer.newPage()
            self._render_schematic_page(painter, printer, content_rect, scene)
            first_page = False

        if data.config.include_netlist and data.netlist:
            if not first_page:
                printer.newPage()
            self._render_text_section(
                painter,
                printer,
                content_rect,
                "SPICE Netlist",
                data.netlist,
                monospace=True,
            )
            first_page = False

        if data.config.include_analysis and data.analysis_text:
            if not first_page:
                printer.newPage()
            self._render_text_section(
                painter,
                printer,
                content_rect,
                "Analysis Configuration",
                data.analysis_text,
            )
            first_page = False

        if data.config.include_results and data.results_text:
            if not first_page:
                printer.newPage()
            self._render_text_section(
                painter,
                printer,
                content_rect,
                "Simulation Results",
                data.results_text,
                monospace=True,
            )

        painter.end()

    # ------------------------------------------------------------------
    # Private rendering helpers
    # ------------------------------------------------------------------

    def _render_title_page(self, painter: QPainter, rect: QRectF, data: ReportData) -> None:
        """Render the title page with circuit name, date, and student name."""
        painter.fillRect(rect, Qt.GlobalColor.white)

        title_font = QFont("Helvetica", self.TITLE_FONT_SIZE, QFont.Weight.Bold)
        subtitle_font = QFont("Helvetica", self.HEADING_FONT_SIZE)
        body_font = QFont("Helvetica", self.BODY_FONT_SIZE)

        center_y = rect.top() + rect.height() * 0.35
        center_x = rect.left() + rect.width() / 2

        # Circuit name
        painter.setFont(title_font)
        fm = QFontMetrics(title_font)
        title_width = fm.horizontalAdvance(data.title)
        painter.drawText(int(center_x - title_width / 2), int(center_y), data.title)

        # Subtitle
        painter.setFont(subtitle_font)
        fm = QFontMetrics(subtitle_font)
        sub_width = fm.horizontalAdvance(data.subtitle)
        painter.drawText(
            int(center_x - sub_width / 2),
            int(center_y + fm.height() * 2),
            data.subtitle,
        )

        # Analysis type if available
        if data.analysis_type:
            analysis_line = f"Analysis: {data.analysis_type}"
            fm_body = QFontMetrics(body_font)
            painter.setFont(body_font)
            al_width = fm_body.horizontalAdvance(analysis_line)
            painter.drawText(
                int(center_x - al_width / 2),
                int(center_y + fm.height() * 4),
                analysis_line,
            )

        # Component count
        if data.component_count:
            comp_line = f"Components: {data.component_count}"
            painter.setFont(body_font)
            fm_body = QFontMetrics(body_font)
            cl_width = fm_body.horizontalAdvance(comp_line)
            painter.drawText(
                int(center_x - cl_width / 2),
                int(center_y + fm.height() * 5),
                comp_line,
            )

        # Date and student name at bottom
        bottom_y = rect.top() + rect.height() * 0.7
        painter.setFont(body_font)
        fm = QFontMetrics(body_font)
        line_height = fm.height() * 1.5

        date_width = fm.horizontalAdvance(data.date_str)
        painter.drawText(int(center_x - date_width / 2), int(bottom_y), data.date_str)

        if data.config.student_name:
            name_width = fm.horizontalAdvance(data.config.student_name)
            painter.drawText(
                int(center_x - name_width / 2),
                int(bottom_y + line_height),
                data.config.student_name,
            )

    def _render_schematic_page(self, painter: QPainter, printer: QPrinter, rect: QRectF, scene) -> None:
        """Render the circuit schematic on a dedicated page."""
        heading_font = QFont("Helvetica", self.HEADING_FONT_SIZE, QFont.Weight.Bold)
        painter.setFont(heading_font)
        fm = QFontMetrics(heading_font)
        painter.drawText(int(rect.left()), int(rect.top() + fm.ascent()), "Schematic")

        heading_height = fm.height() * 2

        source_rect = self._get_scene_source_rect(scene)
        if source_rect is None:
            body_font = QFont("Helvetica", self.BODY_FONT_SIZE)
            painter.setFont(body_font)
            painter.drawText(
                int(rect.left()),
                int(rect.top() + heading_height + 50),
                "(Empty canvas)",
            )
            return

        avail = QRectF(
            rect.left(),
            rect.top() + heading_height,
            rect.width(),
            rect.height() - heading_height,
        )

        scale_x = avail.width() / source_rect.width()
        scale_y = avail.height() / source_rect.height()
        scale = min(scale_x, scale_y)

        target_w = source_rect.width() * scale
        target_h = source_rect.height() * scale
        target_x = avail.left() + (avail.width() - target_w) / 2
        target_y = avail.top() + (avail.height() - target_h) / 2
        target_rect = QRectF(target_x, target_y, target_w, target_h)

        # Override scene background to white so dark-mode theme doesn't leak
        from PyQt6.QtGui import QBrush

        original_brush = scene.backgroundBrush()
        scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        painter.fillRect(target_rect, Qt.GlobalColor.white)
        scene.render(painter, target=target_rect, source=source_rect)
        scene.setBackgroundBrush(original_brush)

    def _render_text_section(
        self,
        painter: QPainter,
        printer: QPrinter,
        rect: QRectF,
        heading: str,
        text: str,
        monospace: bool = False,
    ) -> None:
        """Render a text section with heading, handling page breaks."""
        heading_font = QFont("Helvetica", self.HEADING_FONT_SIZE, QFont.Weight.Bold)
        if monospace:
            body_font = QFont("Courier", self.CODE_FONT_SIZE)
        else:
            body_font = QFont("Helvetica", self.BODY_FONT_SIZE)

        painter.setFont(heading_font)
        hfm = QFontMetrics(heading_font)
        y = rect.top() + hfm.ascent()
        painter.drawText(int(rect.left()), int(y), heading)
        y += hfm.height() * 1.5

        painter.drawLine(int(rect.left()), int(y), int(rect.left() + rect.width()), int(y))
        y += hfm.height() * 0.5

        painter.setFont(body_font)
        bfm = QFontMetrics(body_font)
        line_height = bfm.height() * 1.2
        bottom = rect.top() + rect.height()

        lines = text.split("\n")
        for line in lines:
            if y + line_height > bottom:
                printer.newPage()
                y = rect.top() + hfm.height()
                painter.setFont(heading_font)
                painter.drawText(
                    int(rect.left()),
                    int(rect.top() + hfm.ascent()),
                    f"{heading} (continued)",
                )
                y += hfm.height() * 0.5
                painter.drawLine(
                    int(rect.left()),
                    int(y),
                    int(rect.left() + rect.width()),
                    int(y),
                )
                y += hfm.height() * 0.5
                painter.setFont(body_font)

            elided = bfm.elidedText(line, Qt.TextElideMode.ElideRight, int(rect.width()))
            painter.drawText(int(rect.left()), int(y), elided)
            y += line_height

    @staticmethod
    def _get_scene_source_rect(scene) -> QRectF | None:
        """Compute bounding rect of circuit items with padding.

        Filters out grid/background items by checking for circuit item types.
        Falls back to itemsBoundingRect if type checking is unavailable.
        """
        try:
            from GUI.annotation_item import AnnotationItem
            from GUI.component_item import ComponentGraphicsItem
            from GUI.wire_item import WireGraphicsItem

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
        except ImportError:
            source_rect = scene.itemsBoundingRect()
            if source_rect.isEmpty():
                return None

        padding = 40
        source_rect.adjust(-padding, -padding, padding, padding)
        return source_rect
