"""Tests for SVG export of circuit schematics (#239).

Verifies that the SVG export produces valid output and that the
menu infrastructure supports SVG as an export format.
"""

import inspect
import xml.etree.ElementTree as ET

import pytest
from GUI.component_item import ComponentGraphicsItem, Resistor, VoltageSource
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsScene


class TestSVGExportInfrastructure:
    """Verify SVG export infrastructure is in place."""

    def test_export_image_dialog_offers_svg(self):
        """Export image dialog should include SVG as a format option."""
        from GUI.main_window_view import ViewOperationsMixin

        source = inspect.getsource(ViewOperationsMixin.export_image)
        assert "*.svg" in source

    def test_canvas_has_export_svg_method(self):
        """CircuitCanvasView should have _export_svg method."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_export_svg")

    def test_export_svg_uses_qsvggenerator(self):
        """_export_svg should use QSvgGenerator."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._export_svg)
        assert "QSvgGenerator" in source

    def test_canvas_export_image_routes_svg(self):
        """canvas.export_image should detect .svg and call _export_svg."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView.export_image)
        assert '".svg"' in source or "'.svg'" in source
        assert "_export_svg" in source

    def test_export_svg_sets_title(self):
        """SVG export should set a document title."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._export_svg)
        assert "setTitle" in source


class TestSVGFileOutput:
    """Test actual SVG file generation."""

    def test_svg_file_created(self, qtbot, tmp_path):
        """Export should create a non-empty SVG file."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QPainter
        from PyQt6.QtSvg import QSvgGenerator

        scene = QGraphicsScene()
        comp = Resistor("R1")
        scene.addItem(comp)
        comp.setPos(100, 100)

        filepath = str(tmp_path / "test.svg")
        source_rect = comp.sceneBoundingRect()
        source_rect.adjust(-10, -10, 10, 10)

        width = int(source_rect.width())
        height = int(source_rect.height())

        svg = QSvgGenerator()
        svg.setFileName(filepath)
        svg.setSize(QSize(width, height))
        svg.setViewBox(source_rect)
        svg.setTitle("Test Circuit")

        painter = QPainter()
        painter.begin(svg)
        scene.render(painter, QRectF(0, 0, width, height), source_rect)
        painter.end()

        output = tmp_path / "test.svg"
        assert output.exists()
        content = output.read_text()
        assert len(content) > 0

    def test_svg_is_valid_xml(self, qtbot, tmp_path):
        """Exported SVG should be valid XML."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QPainter
        from PyQt6.QtSvg import QSvgGenerator

        scene = QGraphicsScene()
        comp = Resistor("R1")
        scene.addItem(comp)
        comp.setPos(50, 50)

        filepath = str(tmp_path / "valid.svg")
        rect = comp.sceneBoundingRect()
        rect.adjust(-10, -10, 10, 10)

        svg = QSvgGenerator()
        svg.setFileName(filepath)
        svg.setSize(QSize(int(rect.width()), int(rect.height())))
        svg.setViewBox(rect)

        painter = QPainter()
        painter.begin(svg)
        scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
        painter.end()

        content = (tmp_path / "valid.svg").read_text()
        # Should parse without error
        tree = ET.fromstring(content)
        assert tree.tag.endswith("svg")

    def test_svg_contains_drawing_elements(self, qtbot, tmp_path):
        """SVG should contain actual drawing elements (paths, lines, etc.)."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QPainter
        from PyQt6.QtSvg import QSvgGenerator

        scene = QGraphicsScene()
        comp = Resistor("R1")
        scene.addItem(comp)
        comp.setPos(50, 50)

        filepath = str(tmp_path / "elements.svg")
        rect = comp.sceneBoundingRect()
        rect.adjust(-10, -10, 10, 10)

        svg = QSvgGenerator()
        svg.setFileName(filepath)
        svg.setSize(QSize(int(rect.width()), int(rect.height())))
        svg.setViewBox(rect)

        painter = QPainter()
        painter.begin(svg)
        scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
        painter.end()

        content = (tmp_path / "elements.svg").read_text()
        # SVG should have drawing elements (lines, paths, etc.)
        has_drawing = any(tag in content for tag in ["<line", "<path", "<polyline", "<circle", "<rect", "<ellipse"])
        assert has_drawing, "SVG should contain drawing elements"

    def test_svg_multiple_components(self, qtbot, tmp_path):
        """SVG with multiple components should be larger than single component."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QPainter
        from PyQt6.QtSvg import QSvgGenerator

        # Single component
        scene1 = QGraphicsScene()
        r1 = Resistor("R1")
        scene1.addItem(r1)
        r1.setPos(50, 50)

        fp1 = str(tmp_path / "single.svg")
        rect1 = r1.sceneBoundingRect()
        rect1.adjust(-10, -10, 10, 10)

        svg1 = QSvgGenerator()
        svg1.setFileName(fp1)
        svg1.setSize(QSize(int(rect1.width()), int(rect1.height())))
        svg1.setViewBox(rect1)
        painter1 = QPainter()
        painter1.begin(svg1)
        scene1.render(painter1, QRectF(0, 0, rect1.width(), rect1.height()), rect1)
        painter1.end()

        # Two components
        scene2 = QGraphicsScene()
        r2 = Resistor("R1")
        v1 = VoltageSource("V1")
        scene2.addItem(r2)
        scene2.addItem(v1)
        r2.setPos(50, 50)
        v1.setPos(200, 50)

        fp2 = str(tmp_path / "multi.svg")
        rect2 = r2.sceneBoundingRect().united(v1.sceneBoundingRect())
        rect2.adjust(-10, -10, 10, 10)

        svg2 = QSvgGenerator()
        svg2.setFileName(fp2)
        svg2.setSize(QSize(int(rect2.width()), int(rect2.height())))
        svg2.setViewBox(rect2)
        painter2 = QPainter()
        painter2.begin(svg2)
        scene2.render(painter2, QRectF(0, 0, rect2.width(), rect2.height()), rect2)
        painter2.end()

        size1 = (tmp_path / "single.svg").stat().st_size
        size2 = (tmp_path / "multi.svg").stat().st_size
        assert size2 > size1, "Multi-component SVG should be larger"

    def test_svg_export_empty_scene(self, qtbot, tmp_path):
        """Exporting an empty scene should still produce valid SVG."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QPainter
        from PyQt6.QtSvg import QSvgGenerator

        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, 100, 100)

        filepath = str(tmp_path / "empty.svg")
        rect = scene.sceneRect()

        svg = QSvgGenerator()
        svg.setFileName(filepath)
        svg.setSize(QSize(int(rect.width()), int(rect.height())))
        svg.setViewBox(rect)

        painter = QPainter()
        painter.begin(svg)
        scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
        painter.end()

        content = (tmp_path / "empty.svg").read_text()
        assert len(content) > 0
        tree = ET.fromstring(content)
        assert tree.tag.endswith("svg")
