"""
Tests for simulation/spice_value_normalizer.py — SI suffix canonicalization.

Covers the bare-M bug (#948): the UI and ``parse_value`` read a bare ``M`` as
mega (1e6), but ngspice reads it as milli (1e-3).  Normalizing a bare ``M`` to
the canonical ``meg`` makes ngspice agree with the UI.
"""

import pytest
from simulation.spice_value_normalizer import normalize_spice_value


class TestNormalizeSpiceValueBareM:
    """A bare ``M`` suffix must be rewritten to ``meg`` (#948)."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1M", "1meg"),
            ("4.7M", "4.7meg"),
            ("100M", "100meg"),
            ("1e6M", "1e6meg"),
        ],
    )
    def test_bare_mega_is_normalized(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected

    def test_bare_mega_is_a_bug_fix(self):
        """Bare M -> meg makes ngspice agree with the UI's mega interpretation."""
        # ngspice reads "1M" as milli; "1meg" as mega.
        assert normalize_spice_value("1M", "1M") == "1meg"


class TestNormalizeSpiceValueMilliStays:
    """Lowercase ``m`` (milli) is already consistent and must stay milli."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1m", "1m"),
            ("4.7m", "4.7m"),
            ("5m", "5m"),
            ("10mH 10mH 0.99", "10mH 10mH 0.99"),
        ],
    )
    def test_milli_stays_milli(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected


class TestNormalizeSpiceValueMegVariants:
    """MEG variants are canonicalized to lowercase ``meg`` (already mega)."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("10MEG", "10meg"),
            ("10Meg", "10meg"),
            ("10meg", "10meg"),
            ("1.5MEG", "1.5meg"),
            ("4.7MEG", "4.7meg"),
        ],
    )
    def test_meg_variants(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected


class TestNormalizeSpiceValueOtherSuffixes:
    """Case-correct canonicalization of other SI suffixes."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("10K", "10k"),
            ("10k", "10k"),
            ("1G", "1g"),
            ("1T", "1t"),
            ("100n", "100n"),
            ("10u", "10u"),
            ("2.2p", "2.2p"),
            ("1f", "1f"),
        ],
    )
    def test_case_insensitive_suffix_canonicalization(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected

    def test_lower_case_g_stays_g(self):
        assert normalize_spice_value("1g", "1g") == "1g"


class TestNormalizeSpiceValueUnchanged:
    """Non-SI-suffix values must pass through untouched."""

    @pytest.mark.parametrize(
        "raw",
        [
            "100",
            "1e-3",
            "3.14",
            "1000",
            "-5",
            "2N3904",
            "2N3906",
            "SIN(0 5 1k)",
            "PULSE(0 5 0 1n 1n 5u 10u)",
            "AC 1",
            "BF=300 IS=1e-14 VAF=100",
            "VTO=0.7 KP=110u",
            "Ideal",
            "D_Ideal",
            "10kohm",  # multi-letter unit, not a bare SI letter
            "1Mh",  # multi-letter, not an SI letter
        ],
    )
    def test_non_numeric_values_unchanged(self, raw):
        assert normalize_spice_value(raw, raw) == raw

    def test_no_letters_keeps_number(self):
        assert normalize_spice_value("100", "100") == "100"


class TestNormalizeSpiceValueEdgeCases:
    """Behavior for malformed or non-string input."""

    def test_returns_validated_on_non_string(self):
        # A float raw value is not a "number<suffix>" string; return as-is.
        assert normalize_spice_value(1000, "1000") == "1000"

    def test_returns_validated_when_validated_missing(self):
        # If no sanitized form is provided, nothing is normalized.
        assert normalize_spice_value("1M", None) is None

    def test_leading_letter_not_matched(self):
        # Leading letters (model names, waveform specs) must not be treated
        # as a clean numeric suffix.
        assert normalize_spice_value("M1", "M1") == "M1"
        assert normalize_spice_value("2N3904", "2N3904") == "2N3904"

    def test_negative_number_with_suffix(self):
        assert normalize_spice_value("-5M", "-5M") == "-5meg"

    def test_decimal_number_with_suffix(self):
        assert normalize_spice_value("0.5M", "0.5M") == "0.5meg"

    def test_scientific_with_suffix(self):
        assert normalize_spice_value("1e6M", "1e6M") == "1e6meg"
