"""Waveform SPICE command generation utilities.

Extracted from ComponentData (#574, #599) to keep domain-specific
SPICE formatting logic in the simulation layer rather than the data model.

The canonical implementations now live in models.waveform_defaults (issue #767)
so that the model layer can use them without a models → simulation import.
This module re-exports them for backwards compatibility.
"""

from models.waveform_defaults import (  # noqa: F401  (re-export)
    DEFAULT_WAVEFORM_TYPE,
    default_waveform_params,
    format_waveform_spice_value,
)
