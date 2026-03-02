"""
GUI/format_utils.py

Re-exports from utils.format_utils for backward compatibility.

The canonical definitions now live in ``utils.format_utils`` so that
non-GUI layers (simulation, controllers) can use them without depending
on the GUI package.
"""

from utils.format_utils import (
    FORMATTING_PREFIXES,
    SI_PREFIX_MULTIPLIERS,
    format_value,
    parse_value,
    validate_component_value,
)

__all__ = [
    "SI_PREFIX_MULTIPLIERS",
    "FORMATTING_PREFIXES",
    "parse_value",
    "format_value",
    "validate_component_value",
]
