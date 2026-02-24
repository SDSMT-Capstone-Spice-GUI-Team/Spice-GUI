"""
Unit tests for dialog validation feedback (issue #514).

Verifies that dialogs show user-visible error messages when
submitted with invalid input, rather than failing silently.
"""

import pytest
from GUI.analysis_dialog import AnalysisDialog
from GUI.meas_dialog import MeasurementEntryDialog
from GUI.parameter_sweep_dialog import ParameterSweepDialog
from GUI.validation_helpers import clear_field_error, set_field_error
from GUI.waveform_config_dialog import WaveformConfigDialog
from models.component import ComponentData

# ===================================================================
# Validation Helpers
# ===================================================================


class TestValidationHelpers:
    """Test the shared set_field_error / clear_field_error utilities."""

    def test_set_field_error_adds_red_border(self, qtbot):
        from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

        parent = QWidget()
        layout = QVBoxLayout(parent)
        field = QLineEdit()
        layout.addWidget(field)
        qtbot.addWidget(parent)

        set_field_error(field, "bad value")
        assert "red" in field.styleSheet()

    def test_clear_field_error_removes_border(self, qtbot):
        from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

        parent = QWidget()
        layout = QVBoxLayout(parent)
        field = QLineEdit()
        layout.addWidget(field)
        qtbot.addWidget(parent)

        set_field_error(field, "bad value")
        clear_field_error(field)
        assert "red" not in field.styleSheet()


# ===================================================================
# AnalysisDialog Validation
# ===================================================================


class TestAnalysisDialogValidation:
    """Test AnalysisDialog validates fields and shows error label."""

    def test_valid_dc_op_has_no_errors(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        errors = dialog._validate()
        assert errors == []

    def test_invalid_float_shows_error(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        # Set an invalid value in the min field
        widget, _ = dialog.field_widgets["min"]
        widget.setText("abc")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("number" in e.lower() for e in errors)

    def test_empty_text_field_shows_error(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        # Clear the source field
        widget, _ = dialog.field_widgets["source"]
        widget.setText("")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)

    def test_error_label_hidden_on_valid_input(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        assert dialog._error_label.isHidden()

    def test_on_accept_shows_error_label_on_invalid(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        widget, _ = dialog.field_widgets["min"]
        widget.setText("not-a-number")
        dialog._on_accept()
        assert dialog._error_label.text() != ""
        assert "number" in dialog._error_label.text().lower()

    def test_on_accept_hides_error_and_accepts_valid(self, qtbot):
        dialog = AnalysisDialog(analysis_type="DC Operating Point")
        qtbot.addWidget(dialog)
        # Should accept without errors (DC Op has no fields)
        # We can't easily test accept() was called, but error label should be hidden
        dialog._on_accept()
        assert dialog._error_label.isHidden()


# ===================================================================
# WaveformConfigDialog Validation
# ===================================================================


@pytest.fixture
def waveform_component():
    """Create a Waveform Source ComponentData."""
    return ComponentData(
        component_id="VW1",
        component_type="Waveform Source",
        value="SIN(0 5 1k)",
        position=(0.0, 0.0),
    )


class TestWaveformConfigDialogValidation:
    """Test WaveformConfigDialog validates numeric fields."""

    def test_valid_defaults_have_no_errors(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        errors = dialog._validate()
        assert errors == []

    def test_invalid_frequency_shows_error(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.param_inputs["SIN"]["frequency"].setText("not-a-number")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("frequency" in e for e in errors)

    def test_empty_field_shows_required_error(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.param_inputs["SIN"]["amplitude"].setText("")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("required" in e.lower() for e in errors)

    def test_on_accept_shows_error_label(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.param_inputs["SIN"]["frequency"].setText("xyz")
        dialog._on_accept()
        assert dialog._error_label.text() != ""

    def test_error_label_exists(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "_error_label")
        assert dialog._error_label.isHidden()


# ===================================================================
# ParameterSweepDialog Validation
# ===================================================================


class TestParameterSweepDialogValidation:
    """Test ParameterSweepDialog validates sweep parameters."""

    @pytest.fixture
    def components(self):
        return {
            "R1": ComponentData(
                component_id="R1",
                component_type="Resistor",
                value="1k",
                position=(0.0, 0.0),
            ),
        }

    def test_valid_defaults_have_no_errors(self, qtbot, components):
        dialog = ParameterSweepDialog(components)
        qtbot.addWidget(dialog)
        errors = dialog._validate()
        assert errors == []

    def test_invalid_start_value_shows_error(self, qtbot, components):
        dialog = ParameterSweepDialog(components)
        qtbot.addWidget(dialog)
        dialog.start_edit.setText("abc")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("start" in e.lower() for e in errors)

    def test_start_equals_stop_shows_error(self, qtbot, components):
        dialog = ParameterSweepDialog(components)
        qtbot.addWidget(dialog)
        dialog.start_edit.setText("1k")
        dialog.stop_edit.setText("1k")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("different" in e.lower() for e in errors)

    def test_error_label_shown_on_invalid_accept(self, qtbot, components):
        dialog = ParameterSweepDialog(components)
        qtbot.addWidget(dialog)
        dialog.start_edit.setText("not-valid")
        dialog._on_accept()
        assert dialog._error_label.text() != ""

    def test_no_component_shows_error(self, qtbot):
        dialog = ParameterSweepDialog({})  # no sweepable components
        qtbot.addWidget(dialog)
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("component" in e.lower() for e in errors)


# ===================================================================
# MeasurementEntryDialog Validation
# ===================================================================


class TestMeasurementEntryDialogValidation:
    """Test MeasurementEntryDialog validates name/variable fields."""

    def test_valid_defaults_have_no_errors(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        errors = dialog._validate()
        assert errors == []

    def test_empty_name_shows_error(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("name" in e.lower() for e in errors)

    def test_empty_variable_shows_error(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        dialog.var_edit.setText("")
        errors = dialog._validate()
        assert len(errors) > 0
        assert any("variable" in e.lower() for e in errors)

    def test_on_accept_shows_error_label_for_empty_name(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("")
        dialog._on_accept()
        assert dialog._error_label.text() != ""

    def test_error_label_exists(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "_error_label")
