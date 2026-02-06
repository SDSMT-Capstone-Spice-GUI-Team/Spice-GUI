"""
Pure Python data models for Spice-GUI.

This package contains Qt-free data classes that represent circuit elements.
All models use only Python standard library types (no PyQt6 dependencies).
"""

from .component import (
    ComponentData,
    COMPONENT_TYPES,
    SPICE_SYMBOLS,
    TERMINAL_COUNTS,
    DEFAULT_VALUES,
    COMPONENT_COLORS,
    TERMINAL_GEOMETRY,
)
from .wire import WireData
from .node import NodeData

__all__ = [
    'ComponentData',
    'COMPONENT_TYPES',
    'SPICE_SYMBOLS',
    'TERMINAL_COUNTS',
    'DEFAULT_VALUES',
    'COMPONENT_COLORS',
    'TERMINAL_GEOMETRY',
    'WireData',
    'NodeData',
]
