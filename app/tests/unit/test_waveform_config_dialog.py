"""
Unit tests for WaveformConfigDialog.

Tests dialog creation with waveform component data,
type switching, parameter population, and parameter retrieval.
"""

import pytest
from GUI.waveform_config_dialog import WaveformConfigDialog
from models.component import ComponentData


@pytest.fixture
def waveform_component():
    """Create a Waveform Source ComponentData with default params."""
    return ComponentData(
        component_id="VW1",
        component_type="Waveform Source",
        value="SIN(0 5 1k)",
        position=(0.0, 0.0),
    )


class TestWaveformConfigDialogInit:
    """Test dialog initialization."""

    def test_opens_with_correct_title(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        assert "VW1" in dialog.windowTitle()

    def test_type_combo_has_three_types(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        assert dialog.type_combo.count() == 3
        types = [dialog.type_combo.itemText(i) for i in range(3)]
        assert types == ["SIN", "PULSE", "EXP"]

    def test_default_type_matches_component(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        assert dialog.type_combo.currentText() == "SIN"


class TestWaveformConfigDialogParams:
    """Test parameter population and retrieval."""

    def test_sin_params_populated_from_component(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        sin_inputs = dialog.param_inputs["SIN"]
        assert sin_inputs["amplitude"].text() == "5"
        assert sin_inputs["frequency"].text() == "1k"

    def test_get_parameters_returns_current_type_and_values(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        wtype, params = dialog.get_parameters()
        assert wtype == "SIN"
        assert "amplitude" in params
        assert "frequency" in params

    def test_switching_type_changes_visible_fields(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentText("PULSE")
        wtype, params = dialog.get_parameters()
        assert wtype == "PULSE"
        assert "v1" in params
        assert "per" in params

    def test_editing_field_reflected_in_get_parameters(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.param_inputs["SIN"]["amplitude"].setText("10")
        _, params = dialog.get_parameters()
        assert params["amplitude"] == "10"

    def test_exp_type_has_correct_keys(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentText("EXP")
        wtype, params = dialog.get_parameters()
        assert wtype == "EXP"
        assert set(params.keys()) == {"v1", "v2", "td1", "tau1", "td2", "tau2"}

    def test_help_text_updates_on_type_change(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentText("PULSE")
        assert "Pulse" in dialog.help_label.text()
        dialog.type_combo.setCurrentText("EXP")
        assert "Exponential" in dialog.help_label.text()
