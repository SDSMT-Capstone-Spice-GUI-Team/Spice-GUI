"""Tests for waveform SPICE utilities (#574, #599).

Verifies that format_waveform_spice_value produces correct SPICE strings
for each supported waveform type, and that default_waveform_params provides
correct defaults.
"""

from simulation.waveform_utils import DEFAULT_WAVEFORM_TYPE, default_waveform_params, format_waveform_spice_value


class TestFormatWaveformSpiceValue:
    """Test format_waveform_spice_value for each waveform type."""

    def test_sin_default_params(self):
        params = {
            "SIN": {
                "offset": "0",
                "amplitude": "5",
                "frequency": "1k",
                "delay": "0",
                "theta": "0",
                "phase": "0",
            }
        }
        result = format_waveform_spice_value("SIN", params, "fallback")
        assert result.startswith("SIN(")
        assert "5" in result
        assert "1k" in result

    def test_pulse_params(self):
        params = {
            "PULSE": {
                "v1": "0",
                "v2": "3.3",
                "td": "1u",
                "tr": "10n",
                "tf": "10n",
                "pw": "50u",
                "per": "100u",
            }
        }
        result = format_waveform_spice_value("PULSE", params, "fallback")
        assert result.startswith("PULSE(")
        assert "3.3" in result
        assert "50u" in result

    def test_exp_params(self):
        params = {
            "EXP": {
                "v1": "0",
                "v2": "5",
                "td1": "0",
                "tau1": "1u",
                "td2": "2u",
                "tau2": "2u",
            }
        }
        result = format_waveform_spice_value("EXP", params, "fallback")
        assert result.startswith("EXP(")
        assert "5" in result

    def test_none_params_returns_fallback(self):
        result = format_waveform_spice_value("SIN", None, "5V")
        assert result == "5V"

    def test_unknown_type_returns_fallback(self):
        result = format_waveform_spice_value("UNKNOWN", {"UNKNOWN": {}}, "5V")
        assert result == "5V"

    def test_none_waveform_type_defaults_to_sin(self):
        params = {"SIN": {"offset": "0", "amplitude": "10", "frequency": "2k"}}
        result = format_waveform_spice_value(None, params, "fallback")
        assert result.startswith("SIN(")
        assert "10" in result

    def test_missing_param_keys_use_defaults(self):
        """When param dict is empty, built-in defaults fill in."""
        params = {"SIN": {}}
        result = format_waveform_spice_value("SIN", params, "fallback")
        assert result.startswith("SIN(")
        assert "0" in result  # default offset
        assert "5" in result  # default amplitude


class TestDefaultWaveformParams:
    """Tests for default_waveform_params and DEFAULT_WAVEFORM_TYPE."""

    def test_default_type_is_sin(self):
        assert DEFAULT_WAVEFORM_TYPE == "SIN"

    def test_contains_all_waveform_types(self):
        params = default_waveform_params()
        assert set(params.keys()) == {"SIN", "PULSE", "EXP"}

    def test_sin_has_required_keys(self):
        params = default_waveform_params()
        assert set(params["SIN"].keys()) == {
            "offset",
            "amplitude",
            "frequency",
            "delay",
            "theta",
            "phase",
        }

    def test_pulse_has_required_keys(self):
        params = default_waveform_params()
        assert set(params["PULSE"].keys()) == {
            "v1",
            "v2",
            "td",
            "tr",
            "tf",
            "pw",
            "per",
        }

    def test_exp_has_required_keys(self):
        params = default_waveform_params()
        assert set(params["EXP"].keys()) == {"v1", "v2", "td1", "tau1", "td2", "tau2"}

    def test_returns_fresh_copy(self):
        p1 = default_waveform_params()
        p2 = default_waveform_params()
        assert p1 is not p2
        p1["SIN"]["offset"] = "999"
        assert p2["SIN"]["offset"] == "0"

    def test_component_data_uses_extracted_defaults(self):
        """ComponentData.__post_init__ should use defaults from waveform_utils."""
        from models.component import ComponentData

        comp = ComponentData(
            component_id="V1",
            component_type="Waveform Source",
            value="5V",
            position=(0.0, 0.0),
        )
        assert comp.waveform_type == DEFAULT_WAVEFORM_TYPE
        expected = default_waveform_params()
        assert comp.waveform_params == expected


class TestComponentDataDelegation:
    """Verify ComponentData.get_spice_value delegates to the utility."""

    def test_waveform_source_delegates(self):
        from models.component import ComponentData

        comp = ComponentData(
            component_id="V1",
            component_type="Waveform Source",
            value="5V",
            position=(0.0, 0.0),
        )
        result = comp.get_spice_value()
        assert result.startswith("SIN(")

    def test_non_waveform_returns_value(self):
        from models.component import ComponentData

        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0.0, 0.0),
        )
        assert comp.get_spice_value() == "1k"
