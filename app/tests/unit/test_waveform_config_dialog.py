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

class TestWaveformConfigDialogPartialParams:
    """Regression coverage for the KeyError 'SIN' crash on partial waveform_params.

    Circuits saved with a single-key ``waveform_params`` (the only current
    type present, as produced by ``netlist_parser._setup_waveform_params`` and
    round-tripped verbatim by ``models.component``) used to raise ``KeyError:
    'SIN'`` during dialog construction when switching to a type whose params
    were not stored.
    """

    def _partial_params_component(self, waveform_type, params):
        component = ComponentData(
            component_id="VW1",
            component_type="Waveform Source",
            value=f"{waveform_type}(test)",
            position=(0.0, 0.0),
        )
        component.waveform_type = waveform_type
        component.waveform_params = {waveform_type: params}  # only ONE type stored
        return component

    def test_loads_circuit_with_pulse_only_params(self, qtbot):
        """Loading a circuit whose stored params are PULSE-only must open."""
        component = self._partial_params_component(
            "PULSE",
            {"v1": "0", "v2": "5", "td": "0", "tr": "1n", "tf": "1n", "pw": "500u", "per": "1m"},
        )
        dialog = WaveformConfigDialog(component)
        qtbot.addWidget(dialog)
        assert dialog.type_combo.currentText() == "PULSE"

    def test_loads_circuit_with_exp_only_params(self, qtbot):
        """A circuit with EXP-only stored params must not raise KeyError."""
        component = self._partial_params_component(
            "EXP",
            {"v1": "0", "v2": "5", "td1": "0", "tau1": "1u", "td2": "2u", "tau2": "2u"},
        )
        dialog = WaveformConfigDialog(component)
        qtbot.addWidget(dialog)
        assert dialog.type_combo.currentText() == "EXP"

    def test_all_types_present_after_partial_load(self, qtbot):
        """Even with partial stored params, every type is editable afterwards."""
        component = self._partial_params_component("PULSE", {"v1": "1", "v2": "9"})
        dialog = WaveformConfigDialog(component)
        qtbot.addWidget(dialog)
        # Every type is fully populated even though only PULSE was stored.
        assert set(dialog.param_inputs) == {"SIN", "PULSE", "EXP"}
        assert dialog.param_inputs["SIN"]["amplitude"].text() == "5"
        assert dialog.param_inputs["PULSE"]["v1"].text() == "1"
        assert dialog.param_inputs["EXP"]["v1"].text() == "0"

    def test_stored_values_take_precedence_over_defaults(self, qtbot):
        """A partial param present in the file overrides the default."""
        component = self._partial_params_component(
            "SIN", {"offset": "2.5"}
        )
        dialog = WaveformConfigDialog(component)
        qtbot.addWidget(dialog)
        assert dialog.param_inputs["SIN"]["offset"].text() == "2.5"
        # Missing params fall back to the built-in default.
        assert dialog.param_inputs["SIN"]["amplitude"].text() == "5"

    def test_roundtrips_from_saved_dict_like_pulsetest(self, qtbot):
        """Exact reproduction: from_dict of a PulseTest-style circuit then dialog."""
        import json
        from pathlib import Path

        d = json.load(open(Path(__file__).resolve().parents[3] / "data" / "PulseTest.json"))
        wv = next(c for c in d["components"] if c.get("type") == "WaveformVoltageSource")
        component = ComponentData.from_dict(wv)
        assert set(component.waveform_params.keys()) == {"PULSE"}  # the crash condition
        dialog = WaveformConfigDialog(component)  # would raise KeyError: 'SIN' before fix
        qtbot.addWidget(dialog)

    def test_help_text_updates_on_type_change(self, qtbot, waveform_component):
        dialog = WaveformConfigDialog(waveform_component)
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentText("PULSE")
        assert "Pulse" in dialog.help_label.text()
        dialog.type_combo.setCurrentText("EXP")
        assert "Exponential" in dialog.help_label.text()
