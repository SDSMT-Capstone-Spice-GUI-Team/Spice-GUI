"""Tests for GUI.analysis_field_helpers — shared build/parse functions."""

import pytest
from PyQt6.QtWidgets import QComboBox, QFormLayout, QLineEdit, QWidget

# ---------------------------------------------------------------------------
# build_analysis_fields
# ---------------------------------------------------------------------------


class TestBuildAnalysisFields:
    """Tests for build_analysis_fields()."""

    def test_populates_transient_fields(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        form = QFormLayout(parent)
        widgets = {}

        from GUI.analysis_field_helpers import build_analysis_fields

        build_analysis_fields(form, "Transient", widgets)

        assert "duration" in widgets
        assert "step" in widgets
        assert "startTime" in widgets
        # Each entry is (widget, field_type)
        assert widgets["duration"][1] == "float"
        assert isinstance(widgets["duration"][0], QLineEdit)

    def test_populates_ac_sweep_with_combo(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        form = QFormLayout(parent)
        widgets = {}

        from GUI.analysis_field_helpers import build_analysis_fields

        build_analysis_fields(form, "AC Sweep", widgets)

        assert "sweepType" in widgets
        w, ft = widgets["sweepType"]
        assert ft == "combo"
        assert isinstance(w, QComboBox)
        assert w.currentText() == "dec"

    def test_dc_op_has_no_fields(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        form = QFormLayout(parent)
        widgets = {}

        from GUI.analysis_field_helpers import build_analysis_fields

        build_analysis_fields(form, "DC Operating Point", widgets)

        assert widgets == {}

    def test_clears_previous_fields(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        form = QFormLayout(parent)
        widgets = {}

        from GUI.analysis_field_helpers import build_analysis_fields

        build_analysis_fields(form, "Transient", widgets)
        assert len(widgets) == 3

        build_analysis_fields(form, "DC Operating Point", widgets)
        assert widgets == {}

    def test_unknown_type_produces_empty(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        form = QFormLayout(parent)
        widgets = {}

        from GUI.analysis_field_helpers import build_analysis_fields

        build_analysis_fields(form, "NonexistentAnalysis", widgets)
        assert widgets == {}

    def test_tooltips_applied(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        form = QFormLayout(parent)
        widgets = {}

        from GUI.analysis_field_helpers import build_analysis_fields

        build_analysis_fields(form, "Transient", widgets)
        # duration should have a tooltip
        assert widgets["duration"][0].toolTip() != ""


# ---------------------------------------------------------------------------
# parse_field_widgets
# ---------------------------------------------------------------------------


class TestParseFieldWidgets:
    """Tests for parse_field_widgets()."""

    def test_parses_float_with_si_prefix(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)

        w = QLineEdit("10k")
        w.setParent(parent)
        widgets = {"resistance": (w, "float")}

        from GUI.analysis_field_helpers import parse_field_widgets

        result = parse_field_widgets(widgets)
        assert result["resistance"] == pytest.approx(10_000.0)

    def test_parses_int(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)

        w = QLineEdit("100")
        w.setParent(parent)
        widgets = {"points": (w, "int")}

        from GUI.analysis_field_helpers import parse_field_widgets

        result = parse_field_widgets(widgets)
        assert result["points"] == 100
        assert isinstance(result["points"], int)

    def test_parses_combo(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)

        w = QComboBox()
        w.addItems(["dec", "oct", "lin"])
        w.setCurrentText("oct")
        w.setParent(parent)
        widgets = {"sweepType": (w, "combo")}

        from GUI.analysis_field_helpers import parse_field_widgets

        result = parse_field_widgets(widgets)
        assert result["sweepType"] == "oct"

    def test_parses_text(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)

        w = QLineEdit("V1")
        w.setParent(parent)
        widgets = {"source": (w, "text")}

        from GUI.analysis_field_helpers import parse_field_widgets

        result = parse_field_widgets(widgets)
        assert result["source"] == "V1"

    def test_raises_on_invalid_float(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)

        w = QLineEdit("not_a_number")
        w.setParent(parent)
        widgets = {"bad": (w, "float")}

        from GUI.analysis_field_helpers import parse_field_widgets

        with pytest.raises(ValueError):
            parse_field_widgets(widgets)

    def test_parses_mixed_fields(self, qtbot):
        """parse_field_widgets handles a realistic mix of field types."""
        parent = QWidget()
        qtbot.addWidget(parent)

        duration = QLineEdit("10m")
        duration.setParent(parent)
        step = QLineEdit("1u")
        step.setParent(parent)
        points = QLineEdit("100")
        points.setParent(parent)
        sweep = QComboBox()
        sweep.addItems(["dec", "oct", "lin"])
        sweep.setParent(parent)
        source = QLineEdit("V1")
        source.setParent(parent)

        widgets = {
            "duration": (duration, "float"),
            "step": (step, "float"),
            "points": (points, "int"),
            "sweepType": (sweep, "combo"),
            "source": (source, "text"),
        }

        from GUI.analysis_field_helpers import parse_field_widgets

        result = parse_field_widgets(widgets)

        assert result["duration"] == pytest.approx(0.01)
        assert result["step"] == pytest.approx(1e-6)
        assert result["points"] == 100
        assert result["sweepType"] == "dec"
        assert result["source"] == "V1"

    def test_empty_widgets_dict(self):
        from GUI.analysis_field_helpers import parse_field_widgets

        result = parse_field_widgets({})
        assert result == {}
