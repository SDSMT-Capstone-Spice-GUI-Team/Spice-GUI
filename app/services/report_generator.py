"""PDF circuit report generator.

Renders multi-page PDF reports containing schematic image, SPICE netlist,
analysis configuration, and simulation results using QPrinter/QPainter.
"""

from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetrics, QPainter
from PyQt6.QtPrintSupport import QPrinter


@dataclass
class ReportConfig:
    """Configuration for which sections to include in a circuit report."""

    include_title: bool = True
    include_schematic: bool = True
    include_netlist: bool = True
    include_analysis: bool = True
    include_results: bool = True
    student_name: str = ""
    circuit_name: str = ""


class ReportGenerator:
    """Generates multi-page PDF circuit reports.

    Uses QPrinter/QPainter to render a structured report with optional
    sections: title page, schematic image, SPICE netlist, analysis
    configuration, and simulation results.
    """

    # Page layout constants (in device pixels at high-res)
    MARGIN_RATIO = 0.05  # 5% margin on each side
    TITLE_FONT_SIZE = 24
    HEADING_FONT_SIZE = 16
    BODY_FONT_SIZE = 10
    CODE_FONT_SIZE = 9

    def __init__(self, config: ReportConfig):
        self.config = config

    def generate(
        self,
        filepath: str,
        scene=None,
        model=None,
        netlist: str = "",
        results_text: str = "",
    ) -> None:
        """Generate a PDF report to the given file path.

        Args:
            filepath: Output PDF file path.
            scene: QGraphicsScene containing the circuit schematic.
            model: CircuitModel with analysis type/params and component data.
            netlist: SPICE netlist string.
            results_text: Formatted simulation results text.
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filepath)

        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        page_rect = QRectF(printer.pageRect(printer.Unit.DevicePixel))
        margin = page_rect.width() * self.MARGIN_RATIO
        content_rect = page_rect.adjusted(margin, margin, -margin, -margin)

        first_page = True

        if self.config.include_title:
            self._render_title_page(painter, content_rect, model)
            first_page = False

        if self.config.include_schematic and scene is not None:
            if not first_page:
                printer.newPage()
            self._render_schematic_page(painter, printer, content_rect, scene)
            first_page = False

        if self.config.include_netlist and netlist:
            if not first_page:
                printer.newPage()
            self._render_text_section(painter, printer, content_rect, "SPICE Netlist", netlist, monospace=True)
            first_page = False

        if self.config.include_analysis and model is not None:
            if not first_page:
                printer.newPage()
            analysis_text = self._format_analysis_config(model)
            self._render_text_section(painter, printer, content_rect, "Analysis Configuration", analysis_text)
            first_page = False

        if self.config.include_results and results_text:
            if not first_page:
                printer.newPage()
            self._render_text_section(
                painter,
                printer,
                content_rect,
                "Simulation Results",
                results_text,
                monospace=True,
            )

        painter.end()

    def _render_title_page(self, painter: QPainter, rect: QRectF, model=None) -> None:
        """Render the title page with circuit name, date, and student name."""
        painter.fillRect(rect, Qt.GlobalColor.white)

        title_font = QFont("Helvetica", self.TITLE_FONT_SIZE, QFont.Weight.Bold)
        subtitle_font = QFont("Helvetica", self.HEADING_FONT_SIZE)
        body_font = QFont("Helvetica", self.BODY_FONT_SIZE)

        center_y = rect.top() + rect.height() * 0.35
        center_x = rect.left() + rect.width() / 2

        # Circuit name
        title = self.config.circuit_name or "Circuit Report"
        painter.setFont(title_font)
        fm = QFontMetrics(title_font)
        title_width = fm.horizontalAdvance(title)
        painter.drawText(int(center_x - title_width / 2), int(center_y), title)

        # Subtitle
        painter.setFont(subtitle_font)
        subtitle = "Circuit Analysis Report"
        fm = QFontMetrics(subtitle_font)
        sub_width = fm.horizontalAdvance(subtitle)
        painter.drawText(int(center_x - sub_width / 2), int(center_y + fm.height() * 2), subtitle)

        # Analysis type if available
        if model and model.analysis_type:
            analysis_line = f"Analysis: {model.analysis_type}"
            fm_body = QFontMetrics(body_font)
            painter.setFont(body_font)
            al_width = fm_body.horizontalAdvance(analysis_line)
            painter.drawText(
                int(center_x - al_width / 2),
                int(center_y + fm.height() * 4),
                analysis_line,
            )

        # Component count
        if model and model.components:
            comp_line = f"Components: {len(model.components)}"
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

        date_str = datetime.now().strftime("%B %d, %Y")
        date_width = fm.horizontalAdvance(date_str)
        painter.drawText(int(center_x - date_width / 2), int(bottom_y), date_str)

        if self.config.student_name:
            name_width = fm.horizontalAdvance(self.config.student_name)
            painter.drawText(
                int(center_x - name_width / 2),
                int(bottom_y + line_height),
                self.config.student_name,
            )

    def _render_schematic_page(self, painter: QPainter, printer: QPrinter, rect: QRectF, scene) -> None:
        """Render the circuit schematic on a dedicated page."""
        # Heading
        heading_font = QFont("Helvetica", self.HEADING_FONT_SIZE, QFont.Weight.Bold)
        painter.setFont(heading_font)
        fm = QFontMetrics(heading_font)
        painter.drawText(int(rect.left()), int(rect.top() + fm.ascent()), "Schematic")

        heading_height = fm.height() * 2

        # Compute source rect from circuit items (excluding grid)
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

        # Available area below heading
        avail = QRectF(
            rect.left(),
            rect.top() + heading_height,
            rect.width(),
            rect.height() - heading_height,
        )

        # Scale to fit while preserving aspect ratio
        scale_x = avail.width() / source_rect.width()
        scale_y = avail.height() / source_rect.height()
        scale = min(scale_x, scale_y)

        target_w = source_rect.width() * scale
        target_h = source_rect.height() * scale
        target_x = avail.left() + (avail.width() - target_w) / 2
        target_y = avail.top() + (avail.height() - target_h) / 2
        target_rect = QRectF(target_x, target_y, target_w, target_h)

        # White background for schematic area
        painter.fillRect(target_rect, Qt.GlobalColor.white)
        scene.render(painter, target=target_rect, source=source_rect)

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

        # Draw heading
        painter.setFont(heading_font)
        hfm = QFontMetrics(heading_font)
        y = rect.top() + hfm.ascent()
        painter.drawText(int(rect.left()), int(y), heading)
        y += hfm.height() * 1.5

        # Draw separator line
        painter.drawLine(int(rect.left()), int(y), int(rect.left() + rect.width()), int(y))
        y += hfm.height() * 0.5

        # Draw body text
        painter.setFont(body_font)
        bfm = QFontMetrics(body_font)
        line_height = bfm.height() * 1.2
        bottom = rect.top() + rect.height()

        lines = text.split("\n")
        for line in lines:
            if y + line_height > bottom:
                # New page
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

            # Truncate line if it's too wide
            elided = bfm.elidedText(line, Qt.TextElideMode.ElideRight, int(rect.width()))
            painter.drawText(int(rect.left()), int(y), elided)
            y += line_height

    def _format_analysis_config(self, model) -> str:
        """Format analysis type and parameters as readable text."""
        lines = []
        lines.append(f"Analysis Type: {model.analysis_type}")
        lines.append("")

        if model.analysis_params:
            lines.append("Parameters:")
            for key, value in model.analysis_params.items():
                # Format parameter name nicely
                display_key = key.replace("_", " ").title()
                lines.append(f"  {display_key}: {value}")
        else:
            lines.append("Parameters: (default)")

        lines.append("")
        lines.append(f"Total Components: {len(model.components)}")
        lines.append(f"Total Wires: {len(model.wires)}")

        # Component breakdown by type
        if model.components:
            lines.append("")
            lines.append("Component Summary:")
            type_counts: dict[str, int] = {}
            for comp in model.components.values():
                ctype = comp.component_type
                type_counts[ctype] = type_counts.get(ctype, 0) + 1
            for ctype, count in sorted(type_counts.items()):
                lines.append(f"  {ctype}: {count}")

        return "\n".join(lines)

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
            # Fallback for testing without full GUI imports
            source_rect = scene.itemsBoundingRect()
            if source_rect.isEmpty():
                return None

        padding = 40
        source_rect.adjust(-padding, -padding, padding, padding)
        return source_rect
