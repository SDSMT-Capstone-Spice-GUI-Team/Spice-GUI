"""
Tests for GUI/format_utils.py — SI prefix parsing, formatting, and validation.
"""

import pytest
from GUI.format_utils import (format_value, parse_value,
                              validate_component_value)

# ── parse_value ──────────────────────────────────────────────────────


class TestParseValue:
    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("10k", 10_000.0),
            ("1M", 1_000_000.0),
            ("4.7M", 4_700_000.0),
            ("100n", 100e-9),
            ("1u", 1e-6),
            ("10m", 10e-3),
            ("2.2p", 2.2e-12),
            ("1f", 1e-15),
            ("1G", 1e9),
            ("1T", 1e12),
        ],
    )
    def test_si_suffixes(self, input_str, expected):
        assert parse_value(input_str) == pytest.approx(expected)

    def test_meg_suffix(self):
        assert parse_value("4.7MEG") == pytest.approx(4_700_000.0)

    def test_bare_number(self):
        assert parse_value("100") == 100.0

    def test_bare_float(self):
        assert parse_value("3.14") == pytest.approx(3.14)

    def test_negative_value(self):
        assert parse_value("-5") == -5.0

    def test_scientific_notation(self):
        assert parse_value("1e3") == pytest.approx(1000.0)

    def test_number_with_unit_suffix(self):
        # "10kOhm" — 'k' is the prefix, rest is unit
        assert parse_value("10kOhm") == pytest.approx(10_000.0)

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            parse_value("abc")

    def test_float_passthrough(self):
        assert parse_value(42.0) == 42.0

    def test_integer_passthrough(self):
        assert parse_value(100) == 100.0


# ── format_value ─────────────────────────────────────────────────────


class TestFormatValue:
    def test_zero(self):
        assert format_value(0) == "0.00 "

    def test_kilo(self):
        result = format_value(15000)
        assert "15" in result
        assert "k" in result

    def test_milli(self):
        result = format_value(0.015)
        assert "15" in result
        assert "m" in result

    def test_micro(self):
        result = format_value(1e-6)
        assert "µ" in result

    def test_with_unit(self):
        result = format_value(1000, "Ω")
        assert "k" in result
        assert "Ω" in result

    def test_very_small(self):
        result = format_value(1e-18)
        assert "e" in result  # scientific notation fallback


# ── validate_component_value ─────────────────────────────────────────


class TestValidateComponentValue:
    def test_valid_resistor(self):
        is_valid, msg = validate_component_value("10k", "Resistor")
        assert is_valid
        assert msg == ""

    def test_empty_value_rejected(self):
        is_valid, msg = validate_component_value("", "Resistor")
        assert not is_valid
        assert "empty" in msg.lower()

    def test_whitespace_only_rejected(self):
        is_valid, msg = validate_component_value("   ", "Resistor")
        assert not is_valid

    def test_invalid_format_rejected(self):
        is_valid, msg = validate_component_value("xyz", "Resistor")
        assert not is_valid
        assert "invalid" in msg.lower()

    def test_negative_resistor_rejected(self):
        is_valid, msg = validate_component_value("-10k", "Resistor")
        assert not is_valid
        assert "positive" in msg.lower()

    def test_negative_capacitor_rejected(self):
        is_valid, msg = validate_component_value("-1u", "Capacitor")
        assert not is_valid

    def test_negative_inductor_rejected(self):
        is_valid, msg = validate_component_value("-1m", "Inductor")
        assert not is_valid

    def test_negative_voltage_source_allowed(self):
        is_valid, msg = validate_component_value("-5", "Voltage Source")
        assert is_valid

    def test_skip_ground(self):
        is_valid, msg = validate_component_value("", "Ground")
        assert is_valid

    def test_skip_opamp(self):
        is_valid, msg = validate_component_value("", "Op-Amp")
        assert is_valid

    def test_skip_waveform_source(self):
        is_valid, msg = validate_component_value("", "Waveform Source")
        assert is_valid

    def test_dependent_source_accepts_value(self):
        is_valid, msg = validate_component_value("1k", "VCVS")
        assert is_valid

    def test_dependent_source_accepts_negative(self):
        is_valid, msg = validate_component_value("-2", "CCCS")
        assert is_valid
