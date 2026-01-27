"""
constants.py - Centralized constants for the application.

This file is the SINGLE SOURCE OF TRUTH for:
- GRID_SIZE: Used for snapping components and pathfinding
- COMPONENTS: Component definitions with symbols, terminals, and color keys
- DEFAULT_COMPONENT_COUNTER: Initial counters for component IDs
"""

# Grid settings
GRID_SIZE = 10
GRID_EXTENT = 500  # Half the grid size (-500 to 500)

# Click/selection radius settings (in pixels)
TERMINAL_CLICK_RADIUS = 10  # Radius for clicking terminals to route wires
TERMINAL_HOVER_RADIUS = 15  # Radius for hover detection on terminals
WIRE_CLICK_WIDTH = 10       # Width of clickable area around wires

# Component definitions - SINGLE SOURCE OF TRUTH
# color_key references semantic color names in the theme
COMPONENTS = {
    'Resistor': {
        'symbol': 'R',
        'terminals': 2,
        'color_key': 'component_resistor',
    },
    'Capacitor': {
        'symbol': 'C',
        'terminals': 2,
        'color_key': 'component_capacitor',
    },
    'Inductor': {
        'symbol': 'L',
        'terminals': 2,
        'color_key': 'component_inductor',
    },
    'Voltage Source': {
        'symbol': 'V',
        'terminals': 2,
        'color_key': 'component_voltage_source',
    },
    'Current Source': {
        'symbol': 'I',
        'terminals': 2,
        'color_key': 'component_current_source',
    },
    'Waveform Source': {
        'symbol': 'VW',
        'terminals': 2,
        'color_key': 'component_waveform_source',
    },
    'Ground': {
        'symbol': 'GND',
        'terminals': 1,
        'color_key': 'component_ground',
    },
    'Op-Amp': {
        'symbol': 'OA',
        'terminals': 5,
        'color_key': 'component_opamp',
    },
}

# Default component counter for ID generation
DEFAULT_COMPONENT_COUNTER = {
    comp['symbol']: 0 for comp in COMPONENTS.values()
}
