"""Waveform source defaults and SPICE formatting for ComponentData.

Pure Python — no Qt, no simulation layer imports.

Moved here from simulation.waveform_utils (issue #767) so that
models.component can initialise Waveform Source defaults without
creating a models → simulation import dependency.
"""

from typing import Optional

DEFAULT_WAVEFORM_TYPE = "SIN"


def default_waveform_params() -> dict:
    """Return default waveform parameters for all waveform types.

    Each key is a waveform type (``"SIN"``, ``"PULSE"``, ``"EXP"``),
    and the value is a dict of parameter names to their default string
    values.
    """
    return {
        "SIN": {
            "offset": "0",
            "amplitude": "5",
            "frequency": "1k",
            "delay": "0",
            "theta": "0",
            "phase": "0",
        },
        "PULSE": {
            "v1": "0",
            "v2": "5",
            "td": "0",
            "tr": "1n",
            "tf": "1n",
            "pw": "500u",
            "per": "1m",
        },
        "EXP": {
            "v1": "0",
            "v2": "5",
            "td1": "0",
            "tau1": "1u",
            "td2": "2u",
            "tau2": "2u",
        },
    }


def format_waveform_spice_value(
    waveform_type: Optional[str],
    waveform_params: Optional[dict],
    fallback_value: str,
) -> str:
    """Generate a SPICE waveform source specification string.

    Args:
        waveform_type: Waveform type key (``"SIN"``, ``"PULSE"``, ``"EXP"``).
        waveform_params: Dict mapping waveform type keys to parameter dicts.
        fallback_value: Value to return when *waveform_params* is ``None``
            or the *waveform_type* is unrecognised.

    Returns:
        A SPICE-compatible waveform specification string.
    """
    if waveform_params is None:
        return fallback_value

    wtype = waveform_type or "SIN"
    params = waveform_params.get(wtype, {})

    if wtype == "SIN":
        return (
            f"SIN({params.get('offset', '0')} {params.get('amplitude', '5')} "
            f"{params.get('frequency', '1k')} {params.get('delay', '0')} "
            f"{params.get('theta', '0')} {params.get('phase', '0')})"
        )
    elif wtype == "PULSE":
        return (
            f"PULSE({params.get('v1', '0')} {params.get('v2', '5')} "
            f"{params.get('td', '0')} {params.get('tr', '1n')} "
            f"{params.get('tf', '1n')} {params.get('pw', '500u')} "
            f"{params.get('per', '1m')})"
        )
    elif wtype == "EXP":
        return (
            f"EXP({params.get('v1', '0')} {params.get('v2', '5')} "
            f"{params.get('td1', '0')} {params.get('tau1', '1u')} "
            f"{params.get('td2', '2u')} {params.get('tau2', '2u')})"
        )
    else:
        return fallback_value
