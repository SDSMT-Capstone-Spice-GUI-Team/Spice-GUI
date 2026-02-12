"""Unit tests for AnnotationItem and ParameterSweepPlotDialog.

Tests app/GUI/annotation_item.py (serialization, flags, styling) and
app/GUI/parameter_sweep_plot_dialog.py (plot routing per analysis type).
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from GUI.annotation_item import AnnotationItem
from GUI.parameter_sweep_plot_dialog import ParameterSweepPlotDialog
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsItem

# ---------------------------------------------------------------------------
# AnnotationItem
# ---------------------------------------------------------------------------


class TestAnnotationItemCreation:
    def test_default_creation(self, qtbot):
        item = AnnotationItem()
        assert item.toPlainText() == "Annotation"

    def test_custom_text(self, qtbot):
        item = AnnotationItem(text="Hello World")
        assert item.toPlainText() == "Hello World"

    def test_position(self, qtbot):
        item = AnnotationItem(x=100.0, y=200.0)
        assert item.pos().x() == pytest.approx(100.0)
        assert item.pos().y() == pytest.approx(200.0)

    def test_font_size(self, qtbot):
        item = AnnotationItem(font_size=14)
        assert item.font().pointSize() == 14

    def test_bold(self, qtbot):
        item = AnnotationItem(bold=True)
        assert item.font().bold() is True

    def test_not_bold_by_default(self, qtbot):
        item = AnnotationItem()
        assert item.font().bold() is False

    def test_color(self, qtbot):
        item = AnnotationItem(color="#FF0000")
        assert item.defaultTextColor() == QColor("#FF0000")

    def test_z_value(self, qtbot):
        item = AnnotationItem()
        assert item.zValue() == 90


class TestAnnotationItemFlags:
    def test_is_movable(self, qtbot):
        item = AnnotationItem()
        assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable

    def test_is_selectable(self, qtbot):
        item = AnnotationItem()
        assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable

    def test_sends_geometry_changes(self, qtbot):
        item = AnnotationItem()
        assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges


class TestAnnotationItemSerialization:
    def test_to_dict_keys(self, qtbot):
        item = AnnotationItem(text="Test", x=10, y=20, font_size=12, bold=True, color="#00FF00")
        d = item.to_dict()
        assert set(d.keys()) == {"text", "x", "y", "font_size", "bold", "color"}

    def test_to_dict_values(self, qtbot):
        item = AnnotationItem(text="Test", x=10.0, y=20.0, font_size=12, bold=True, color="#00FF00")
        d = item.to_dict()
        assert d["text"] == "Test"
        assert d["x"] == pytest.approx(10.0)
        assert d["y"] == pytest.approx(20.0)
        assert d["font_size"] == 12
        assert d["bold"] is True
        assert d["color"] == "#00FF00"

    def test_from_dict_roundtrip(self, qtbot):
        original = AnnotationItem(text="Round Trip", x=55.5, y=66.6, font_size=16, bold=True, color="#AABBCC")
        d = original.to_dict()
        restored = AnnotationItem.from_dict(d)

        assert restored.toPlainText() == "Round Trip"
        assert restored.pos().x() == pytest.approx(55.5)
        assert restored.pos().y() == pytest.approx(66.6)
        assert restored.font().pointSize() == 16
        assert restored.font().bold() is True
        assert restored._color_hex == "#AABBCC"

    def test_from_dict_defaults(self, qtbot):
        restored = AnnotationItem.from_dict({})
        assert restored.toPlainText() == "Annotation"
        assert restored.pos().x() == pytest.approx(0.0)
        assert restored.font().pointSize() == 10
        assert restored.font().bold() is False


# ---------------------------------------------------------------------------
# ParameterSweepPlotDialog — helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeResult:
    success: bool = True
    data: Any = None


def _sweep_data(base_type, results, **kwargs):
    return {
        "component_id": "R1",
        "base_analysis_type": base_type,
        "sweep_values": [1000, 2000, 3000],
        "sweep_labels": ["1k", "2k", "3k"],
        "results": results,
        **kwargs,
    }


# ---------------------------------------------------------------------------
# ParameterSweepPlotDialog
# ---------------------------------------------------------------------------


class TestParameterSweepPlotDialog:
    def test_dc_op_sweep(self, qtbot):
        results = [FakeResult(success=True, data={"out": 4.9 + i * 0.1}) for i in range(3)]
        dlg = ParameterSweepPlotDialog(_sweep_data("DC Operating Point", results))
        qtbot.addWidget(dlg)
        assert "R1" in dlg.windowTitle()
        assert "DC Operating Point" in dlg.windowTitle()

    def test_transient_sweep(self, qtbot):
        results = [
            FakeResult(
                success=True,
                data=[
                    {"time": 0.0, "out": 0.0},
                    {"time": 0.5e-3, "out": 2.5 + i * 0.1},
                    {"time": 1e-3, "out": 5.0},
                ],
            )
            for i in range(3)
        ]
        dlg = ParameterSweepPlotDialog(_sweep_data("Transient", results))
        qtbot.addWidget(dlg)
        assert "Transient" in dlg.windowTitle()

    def test_ac_sweep(self, qtbot):
        results = [
            FakeResult(
                success=True,
                data={
                    "frequencies": [100, 1000, 10000],
                    "magnitude": {"out": [1.0, 0.7, 0.3]},
                    "phase": {"out": [-10, -45, -80]},
                },
            )
            for _ in range(3)
        ]
        dlg = ParameterSweepPlotDialog(_sweep_data("AC Sweep", results))
        qtbot.addWidget(dlg)
        assert "AC Sweep" in dlg.windowTitle()

    def test_dc_sweep(self, qtbot):
        results = [
            FakeResult(
                success=True,
                data={
                    "headers": ["idx", "v-sweep", "V(out)"],
                    "data": [[0, 0.0, 0.0], [1, 5.0, 2.5], [2, 10.0, 5.0]],
                },
            )
            for _ in range(3)
        ]
        dlg = ParameterSweepPlotDialog(_sweep_data("DC Sweep", results))
        qtbot.addWidget(dlg)
        assert "DC Sweep" in dlg.windowTitle()

    def test_unknown_base_type_fallback(self, qtbot):
        results = [FakeResult(success=True, data={})]
        dlg = ParameterSweepPlotDialog(_sweep_data("Unknown Analysis", results))
        qtbot.addWidget(dlg)
        assert "Unknown Analysis" in dlg.windowTitle()

    def test_canvas_widget_exists(self, qtbot):
        results = [FakeResult(success=True, data={"out": 5.0})]
        dlg = ParameterSweepPlotDialog(_sweep_data("DC Operating Point", results))
        qtbot.addWidget(dlg)
        assert dlg._canvas is not None

    def test_close_event_cleans_up(self, qtbot):
        import matplotlib.pyplot as plt

        results = [FakeResult(success=True, data={"out": 5.0})]
        dlg = ParameterSweepPlotDialog(_sweep_data("DC Operating Point", results))
        qtbot.addWidget(dlg)

        with patch.object(plt, "close") as mock_close:
            dlg.close()
            mock_close.assert_called_once()
