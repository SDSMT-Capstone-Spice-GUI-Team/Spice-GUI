"""
Styles module - Centralized styling system for the Spice-GUI application.

Usage:
    from app.GUI.styles import GRID_SIZE, COMPONENTS, theme_manager

    # Get colors
    color = theme_manager.color('component_resistor')
    hex_color = theme_manager.color_hex('grid_minor')

    # Get pre-configured pens/brushes/fonts
    pen = theme_manager.pen('grid_minor')
    brush = theme_manager.brush('node_label_bg')
    font = theme_manager.font('node_label')

    # Get stylesheets
    style = theme_manager.stylesheet('instructions_panel')

    # Get component-specific styles
    comp_color = theme_manager.get_component_color('Resistor')
    comp_pen = theme_manager.create_component_pen('Resistor')

    # Future: switch themes at runtime
    # from app.GUI.styles import DarkTheme
    # theme_manager.set_theme(DarkTheme())
"""

from . import theme_store
# Core constants (always available, theme-independent)
from .constants import (COMPONENTS, DEFAULT_COMPONENT_COUNTER,
                        DEFAULT_SPLITTER_SIZES, DEFAULT_WINDOW_SIZE,
                        GRID_EXTENT, GRID_SIZE, INITIAL_LOAD_COUNT,
                        MAJOR_GRID_INTERVAL, SCROLL_LOAD_COUNT,
                        SIMULATION_TIMEOUT, TERMINAL_CLICK_RADIUS,
                        TERMINAL_HOVER_RADIUS, WIRE_CLICK_WIDTH,
                        WIRE_UPDATE_DELAY_MS, ZOOM_FACTOR, ZOOM_FIT_PADDING,
                        ZOOM_MAX, ZOOM_MIN)
from .custom_theme import CustomTheme
from .dark_theme import DarkTheme
from .light_theme import LightTheme
# Theme system
from .theme import BaseTheme, ThemeProtocol
from .theme_manager import (COLOR_MODES, SYMBOL_STYLES, ThemeManager,
                            theme_manager)

__all__ = [
    # Constants
    "GRID_SIZE",
    "GRID_EXTENT",
    "MAJOR_GRID_INTERVAL",
    "COMPONENTS",
    "DEFAULT_COMPONENT_COUNTER",
    "TERMINAL_CLICK_RADIUS",
    "TERMINAL_HOVER_RADIUS",
    "WIRE_CLICK_WIDTH",
    "DEFAULT_WINDOW_SIZE",
    "DEFAULT_SPLITTER_SIZES",
    "SIMULATION_TIMEOUT",
    "WIRE_UPDATE_DELAY_MS",
    "INITIAL_LOAD_COUNT",
    "SCROLL_LOAD_COUNT",
    "ZOOM_FACTOR",
    "ZOOM_MIN",
    "ZOOM_MAX",
    "ZOOM_FIT_PADDING",
    # Theme system
    "ThemeProtocol",
    "BaseTheme",
    "ThemeManager",
    "theme_manager",
    "LightTheme",
    "DarkTheme",
    "CustomTheme",
    "theme_store",
    "SYMBOL_STYLES",
    "COLOR_MODES",
]
