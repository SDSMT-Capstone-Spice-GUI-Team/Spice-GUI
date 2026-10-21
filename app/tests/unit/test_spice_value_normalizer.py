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
from simulation.spice_value_normalizer import normalize_spice_value, translate_spice_unicode


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

    # Restored in full from #956: the renamed test above kept the class name and
    # the canonicalization guarantee, but this original method pins every MEG /
    # Meg / meg spelling explicitly, including the 1.5 and 4.7 cases.
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
    """Case-correct canonicalization of other SI suffixes (restored from #948)."""

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
    """Non-SI-suffix values must pass through untouched (restored from #948).

    This is the critical pass-through guarantee: model names (``2N3904``),
    waveform specs (``SIN(...)``/``PULSE(...)``), and model parameter strings
    must never be mangled by the normalizer.  The new unicode tests sit
    alongside these rather than replacing them.
    """

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


class TestNormalizeSpiceValueMegWithTrailingUnit:
    """A unit letter after ``M`` must still normalize to mega (#948 follow-up).

    The original lookup only rewrote a suffix that is exactly ``M``.  For
    ``1Mohm`` the regex captures ``Mohm`` as the suffix, the lookup misses, and
    the value passes through to ngspice as milli (1e-3) even though the UI and
    ``parse_value`` read it as mega (1e6).  We rewrite ``Mohm`` -> ``megohm``
    (preserving the trailing unit) so ngspice matches the UI.
    """

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1Mohm", "1megohm"),
            ("2MV", "2megv"),
            ("4.7MOhm", "4.7megohm"),
            ("1MOhm", "1megohm"),
        ],
    )
    def test_mega_with_trailing_unit_is_normalized(self, raw, expected):
        assert normalize_spice_value(raw, raw) == expected


class TestNormalizeSpiceValueMegaWhitespace:
    """Leading/trailing whitespace around a bare M must still normalize.

    ``sanitize_spice_value`` strips whitespace, so the sanitized (``validated``)
    form is clean but ``raw`` retains the spaces.  Matching against the
    sanitized form avoids the anchored regex missing on whitespace.
    """

    def test_trailing_space(self):
        assert normalize_spice_value("1M ", "1M") == "1meg"

    def test_leading_space(self):
        assert normalize_spice_value(" 1M", "1M") == "1meg"

    def test_both_spaces(self):
        assert normalize_spice_value(" 1M ", "1M") == "1meg"
