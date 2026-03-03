"""Backward-compatible re-export — canonical location is services.theme_manager."""

from services.theme_manager import (
    COLOR_MODES,
    ROUTING_MODES,
    SYMBOL_STYLES,
    WIRE_THICKNESS_PX,
    WIRE_THICKNESSES,
    ThemeManager,
    theme_manager,
)

__all__ = [
    "SYMBOL_STYLES",
    "COLOR_MODES",
    "WIRE_THICKNESSES",
    "WIRE_THICKNESS_PX",
    "ROUTING_MODES",
    "ThemeManager",
    "theme_manager",
]
