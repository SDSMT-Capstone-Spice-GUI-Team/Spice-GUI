"""
Tests for simulation/spice_value_normalizer.py — SI suffix canonicalization.

Covers the bare-M bug (#948): the UI and ``parse_value`` read a bare ``M`` as
mega (1e6), but ngspice reads it as milli (1e-3).  Normalizing a bare ``M`` to
the canonical ``meg`` makes ngspice agree with the UI.

Also covers unicode SI characters (#949): the UI accepts the micro sign (µ) and
omega (Ω), but ngspice only speaks ``u`` and uses no omega suffix, so they are
translated (µ -> u, Ω dropped) on the way to the netlist.
"""

import pytest
from simulation.spice_value_normalizer import normalize_spice_value
from simulation.spice_value_normalizer import translate_spice_unicode


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
    """``MEG`` / ``Meg`` / ``meg`` are all canonicalized to ``meg``."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1MEG", "1meg"),
            ("1Meg", "1meg"),
            ("10MEG", "10meg"),
        ],
    )
    def test_mega_variants_normalized(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected


class TestTranslateSpiceUnicode:
    """µ/Omega characters translate to ngspice's ASCII equivalents (#949)."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("100µ", "100u"),  # U+00B5 MICRO SIGN
            ("100μ", "100u"),  # U+03BC GREEK SMALL LETTER MU
            ("100Ω", "100"),  # U+03A9 GREEK CAPITAL OMEGA (dropped)
            ("100Ω", "100"),  # U+2126 OHM SIGN (dropped)
            ("1kΩ", "1k"),
            ("1µF", "1uF"),
            ("4.7µ", "4.7u"),
            ("", ""),
            ("100", "100"),  # no unicode -> untouched
            ("1M", "1M"),  # plain ascii -> untouched by translate
        ],
    )
    def test_translation(self, raw, expected):
        assert translate_spice_unicode(raw) == expected


class TestNormalizeSpiceValueUnicode:
    """A full normalize call maps µ/Omega onto ngspice's ASCII values (#949).

    The UI accepts µ and Ω (``format_value`` emits µ for micro), but ngspice
    rejects them.  Normalizing ``100µ`` -> ``100u`` and ``100Ω`` -> ``100``
    lets ngspice agree with the UI while keeping the magnitude correct.
    """

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("100µ", "100u"),  # micro farads/picofarads -> ngspice u
            ("100μ", "100u"),  # greek-mu variant
            ("1µF", "1uF"),
            ("4.7µ", "4.7u"),
            ("100Ω", "100"),  # ohms implicit -> omega dropped, magnitude kept
            ("1kΩ", "1k"),
            ("100Ω", "100"),  # ohm sign dropped
            ("100µΩ", "100u"),  # micro + ohm: both handled -> 100u
        ],
    )
    def test_unicode_is_normalized(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected

    def test_unicode_maps_to_ascii_the_ui_emits(self):
        # format_value renders micro as U+00B5; ngspice wants 'u'.
        from utils.format_utils import format_value

        displayed = format_value(100e-6, "")  # -> "100.00 µ"
        assert normalize_spice_value(displayed, displayed) == displayed.replace("µ", "u")

    def test_normalized_value_is_ascii(self):
        # A translated value must contain no unicode — ngspice writes it to disk.
        for raw in ("100µ", "100Ω", "1µF", "1kΩ"):
            result = normalize_spice_value(raw, raw)
            assert all(ord(c) <= 127 for c in result), f"{result!r} still has unicode"

    @pytest.mark.parametrize("raw", ["2N3904", "100", "1e-3"])
    def test_ascii_value_unchanged_by_translation(self, raw):
        assert normalize_spice_value(raw, raw) == raw

    def test_mega_still_normalized_after_translation(self):
        # Translation is a no-op for 'M', which still goes through canonicalization.
        assert normalize_spice_value("1M", "1M") == "1meg"
