"""
Unit tests for AnalysisDialog.

Tests dialog creation, form building per analysis type,
parameter extraction, validation, and ngspice command generation.
"""

import pytest
from GUI.analysis_dialog import AnalysisDialog
from PyQt6.QtWidgets import QComboBox, QLineEdit


class TestAnalysisDialogDefaults:
    """Test dialog initialization and default state."""

    def test_opens_with_type_selector_when_no_type_given(self, qtbot):
        dialog = AnalysisDialog()
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "type_combo")
        assert isinstance(dialog.type_combo, QComboBox)

    def test_opens_without_type_selector_when_type_given(self, qtbot):
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        assert not hasattr(dialog, "type_combo")
        assert dialog.analysis_type == "Transient"

    def test_default_type_is_first_config(self, qtbot):
        dialog = AnalysisDialog()
        qtbot.addWidget(dialog)
        first_type = list(AnalysisDialog.ANALYSIS_CONFIGS.keys())[0]
        assert dialog.analysis_type == first_type

    def test_description_label_populated(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        expected = AnalysisDialog.ANALYSIS_CONFIGS["DC Operating Point"]["description"]
        assert dialog.desc_label.text() == expected


class TestAnalysisDialogFieldBuilding:
    """Test that correct fields appear for each analysis type."""

    def test_dc_op_has_no_parameter_fields(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        assert len(dialog.field_widgets) == 0

    def test_dc_sweep_has_four_fields(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        assert set(dialog.field_widgets.keys()) == {"source", "min", "max", "step"}

    def test_ac_sweep_has_four_fields(self, qtbot):
        dialog = AnalysisDialog(analysis_type="AC Sweep")
        qtbot.addWidget(dialog)
        assert set(dialog.field_widgets.keys()) == {
            "fStart",
            "fStop",
            "points",
            "sweepType",
        }

    def test_transient_has_three_fields(self, qtbot):
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        assert set(dialog.field_widgets.keys()) == {"duration", "step", "startTime"}

    def test_type_change_rebuilds_form(self, qtbot):
        dialog = AnalysisDialog()
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentText("DC Operating Point")
        assert len(dialog.field_widgets) == 0
        dialog.type_combo.setCurrentText("Transient")
        assert len(dialog.field_widgets) == 3


class TestAnalysisDialogParameters:
    """Test parameter extraction and validation."""

    def test_dc_op_parameters(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        params = dialog.get_parameters()
        assert params == {"analysis_type": "DC Operating Point"}

    def test_dc_sweep_default_parameters(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        params = dialog.get_parameters()
        assert params is not None
        assert params["analysis_type"] == "DC Sweep"
        assert params["source"] == "V1"
        assert params["min"] == 0.0
        assert params["max"] == 10.0
        assert params["step"] == 0.1

    def test_ac_sweep_combo_field(self, qtbot):
        dialog = AnalysisDialog(analysis_type="AC Sweep")
        qtbot.addWidget(dialog)
        # Change the sweep type combo
        widget, _ = dialog.field_widgets["sweepType"]
        widget.setCurrentText("lin")
        params = dialog.get_parameters()
        assert params["sweepType"] == "lin"

    def test_invalid_float_returns_none(self, qtbot):
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        # Set an invalid value
        widget, _ = dialog.field_widgets["duration"]
        widget.setText("not_a_number")
        params = dialog.get_parameters()
        assert params is None


class TestAnalysisDialogNgspiceCommand:
    """Test ngspice command generation."""

    def test_dc_op_command(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        assert dialog.get_ngspice_command() == ".op"

    def test_dc_sweep_command(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert cmd.startswith(".dc V1")

    def test_ac_sweep_command(self, qtbot):
        dialog = AnalysisDialog(analysis_type="AC Sweep")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert cmd.startswith(".ac dec")

    def test_transient_command(self, qtbot):
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert cmd.startswith(".tran")

    def test_invalid_params_return_none_command(self, qtbot):
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        widget, _ = dialog.field_widgets["duration"]
        widget.setText("bad")
        assert dialog.get_ngspice_command() is None
