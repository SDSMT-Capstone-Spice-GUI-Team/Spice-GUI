"""
Pure Python data models for Spice-GUI.

This package contains Qt-free data classes that represent circuit elements.
All models use only Python standard library types (no PyQt6 dependencies).
"""

from .circuit import CircuitModel
from .component import (
    COMPONENT_COLORS,
    COMPONENT_TYPES,
    DEFAULT_VALUES,
    SPICE_SYMBOLS,
    TERMINAL_COUNTS,
    TERMINAL_GEOMETRY,
    ComponentData,
)
from .node import NodeData
from .wire import WireData

__all__ = [
    "CircuitModel",
    "ComponentData",
    "COMPONENT_TYPES",
    "SPICE_SYMBOLS",
    "TERMINAL_COUNTS",
    "DEFAULT_VALUES",
    "COMPONENT_COLORS",
    "TERMINAL_GEOMETRY",
    "WireData",
    "NodeData",
]
