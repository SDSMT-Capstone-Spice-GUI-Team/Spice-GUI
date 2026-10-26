"""
simulation/spice_value_normalizer.py

Canonicalization of component values before they are interpolated into a
SPICE netlist.  The single responsibility here is to make the SI suffix a
user writes match the SI suffix the UI interprets and ngspice simulates.

The problem this exists to solve is a bare ``M`` suffix: SPICE / the UI treat
``1M`` as 1 MOhms (1e6), but ngspice (and the legacy parse path that feeds
Monte Carlo) treat a bare ``M`` as milli (1e-3).  Writing ``1meg`` instead of
``1M`` to the netlist makes ngspice agree with the UI.

Only *clean* numeric values with a known SI suffix are touched.  Anything
that does not match a numeric prefix is returned unchanged, so model names
(``2N3904``), waveform specs (``SIN(...)``, ``PULSE(...)``) and compound
strings (``10mH 10mH 0.99``) pass straight through.

Component values may also contain UI-facing SI unicode characters (the micro
sign ``µ`` and omega ``Ω``) that ngspice rejects.  :func:`normalize_spice_value`
runs :func:`translate_spice_unicode` first so the netlist only ever carries
ASCII.
"""

import re

# UI-facing SI characters the user may type or paste but that ngspice does not
# speak: the micro sign ``µ`` (U+00B5, which the app also emits) and the
# Greek-mu variant (U+03BC, common from paste), plus the omega characters (U+03A9
# GREEK CAPITAL OMEGA and U+2126 OHM SIGN) used for ohms.
#
# SPICE passive values carry their unit implicitly (``10k`` *is* 10k ohms) and
# use ``u`` for micro, so we translate ``µ`` -> ``u`` and simply drop ``Ω``.
# For resistors a dropped omega still yields the correct ohm magnitude; for
# capacitors/inductors a trailing ``Ω`` is meaningless, so dropping it leaves
# the magnitude untouched.
_TRANSLATION_TABLE = str.maketrans(
    {
        "µ": "u",  # U+00B5 MICRO SIGN -> ngspice micro
        "μ": "u",  # U+03BC GREEK SMALL LETTER MU -> ngspice micro
        "Ω": "",  # U+03A9 GREEK CAPITAL OMEGA -> drop (ohms implicit)
        "Ω": "",  # U+2126 OHM SIGN -> drop (ohms implicit)
    }
)


def translate_spice_unicode(value: str) -> str:
    """Replace UI-facing SI unicode characters with their ngspice equivalents.

    ngspice reads micro as the ASCII ``u`` and expresses resistance as a bare
    SI-multiplied number (a trailing ``Ω`` carries no ngspice meaning), so any
    ``µ`` is lowered to ``u`` and every omega character is removed. Non-unicode
    values pass straight through.

    Args:
        value: The value string to translate.

    Returns:
        The value with ``µ``-family characters replaced by ``u`` and ``Ω``-family
        characters removed.
    """
    return value.translate(_TRANSLATION_TABLE)


# A leading/trailing unit letter (V, A, H, F, ...) may trail a bare number.
# Examples that must normalize: "1M" -> "1meg", "10K" -> "10k", "5m" stays "5m".
# Anything else (letters before the number, parentheses, etc.) is left alone.
_NUMERIC_SUFFIX_PATTERN = re.compile(r"^([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)([a-zA-Z]+)$")

# Suffix (as written by the user) -> canonical SPICE suffix.
#
# SPICE is case-insensitive for SI units, so "10MEG"/"10Meg"/"10meg" all mean
# mega; we canonicalize to the lowercase form ngspice uses everywhere else.
#
# The one case that matters is a bare "M": ngspice reads a bare "M" as milli
# (1e-3), while the UI and ``parse_value`` both read it as mega (1e6).  A bare
# "M" is not consistent, so we normalize it to "meg".  A lowercase "m" is
# already milli everywhere, so it is left untouched.  (A multi-letter unit
# such as "Ω" or "kohm" is not an SI SI-letter suffix, so it falls through to
# the unhandled branch and is returned unchanged.)
_SUFFIX_CANON = {
    "f": "f",
    "p": "p",
    "n": "n",
    "u": "u",  # micro — already the ngspice form after translate_spice_unicode()
    "m": "m",  # milli — ngspice and the UI already agree
    "M": "meg",  # bare M — the bug: ngspice read it as milli
    "k": "k",
    "K": "k",
    "g": "g",
    "G": "g",
    "t": "t",
    "T": "t",
    "meg": "meg",
    "MEG": "meg",
    "Meg": "meg",
}


def normalize_spice_value(raw: str, validated: str) -> str:
    """Normalize a component value's SI suffix for SPICE.

    Args:
        raw: The original value string (used only to detect the suffix; it has
            already been through :func:`sanitize_spice_value` so it is known
            safe).
        validated: The sanitized value to return on failure or when no
            normalization applies.  Passing this back through keeps callers
            from having to re-derive the sanitized form.

    Returns:
        A value whose SI suffix matches the UI's interpretation.  A bare number,
        a clean numeric value with a known SI suffix, or any non-numeric value
        is returned unchanged.
    """
    if not isinstance(validated, str) or not isinstance(raw, str):
        return validated

    # Translate UI-facing SI unicode (µ/Ω) to ngspice's ASCII equivalents before
    # matching. Translating ``validated`` -- the whitespace-stripped form
    # :func:`sanitize_spice_value` produces -- keeps the anchored regex working
    # even when ``raw`` carries leading/trailing spaces. The translation turns
    # ``100Ω`` into ``100`` (no suffix) and ``1µF`` into ``1uF`` (an unhandled
    # suffix that falls back to ``validated``), so the netlist never carries a
    # non-ASCII character.
    validated = translate_spice_unicode(validated)

    match = _NUMERIC_SUFFIX_PATTERN.match(validated)
    if match is None:
        return validated  # not a clean "number<suffix>" string

    num_part, suffix = match.group(1), match.group(2)

    # No letters at all -> leave the number exactly as-is (e.g. "1000",
    # "1e-3", "3.14").
    # Case-sensitive lookup: a bare "M" (mega) is distinct from a lowercase "m"
    # (milli), which is why the M-vs-m distinction above is what fixes the bug.
    # A bare "M" that is a pure SI-letter mega (not a spelled-out "meg", which
    # the lookup would have caught, and not a circuit unit like "mH"/"mF" whose
    # lowercase first letter means milli) may also carry a trailing unit that
    # the lookup missed -- e.g. "Mohm", "MOhm", "MV".  The UI and ``parse_value``
    # read such an input as mega, so rewrite the mega to its canonical "meg"
    # form and preserve the trailing unit: "Mohm" -> "megohm", "MV" -> "megv".
    # ngspice reads "1megohm" and "2megv" as 1e6 / 2e6, matching the UI.  The
    # recognized trailing units are limited to volt ("V") and ohm ("ohm"/
    # "ohms"); "Mh" (lowercase henry) is left untouched -- matching the existing
    # non-numeric-value behavior -- and spelled-out "meg" falls through below.
    if suffix.startswith("M") and not suffix.lower().startswith("meg"):
        tail = suffix[1:].lower()
        if tail in ("v", "ohm", "ohms"):
            return f"{num_part}meg{tail}"

    canonical = _SUFFIX_CANON.get(suffix)
    if canonical is None:
        return validated  # unknown / multi-letter unit (V, A, Hz, OHM...)

    return f"{num_part}{canonical}"
