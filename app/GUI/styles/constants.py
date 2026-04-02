"""
constants.py - Centralized constants for the application.

This file is the SINGLE SOURCE OF TRUTH for:
- GRID_SIZE: Used for snapping components and pathfinding
- COMPONENTS: Component definitions (sourced from models, plus GUI color keys)
- DEFAULT_COMPONENT_COUNTER: Initial counters for component IDs
"""

from models.component import COMPONENT_TYPES, SPICE_SYMBOLS, TERMINAL_COUNTS

# Grid settings
GRID_SIZE = 10
GRID_EXTENT = 500  # Half the grid size (-500 to 500)
MAJOR_GRID_INTERVAL = 100  # Pixels between major grid lines

# Click/selection radius settings (in pixels)
TERMINAL_CLICK_RADIUS = 10  # Radius for clicking terminals to route wires
TERMINAL_HOVER_RADIUS = 15  # Radius for hover detection on terminals
WIRE_CLICK_WIDTH = 10  # Width of clickable area around wires

# Terminal configuration defaults
DEFAULT_TERMINAL_PADDING = 15  # Gap between body edge and terminal (grid-aligned)

# Window layout
DEFAULT_WINDOW_SIZE = (1200, 800)
DEFAULT_SPLITTER_SIZES = [500, 300]  # Canvas height : results height

# Component drag settings
WIRE_UPDATE_DELAY_MS = 50  # Delay before rerouting wires after drag

# Zoom settings
ZOOM_FACTOR = 1.15  # Multiplier per zoom step
ZOOM_MIN = 0.1  # Minimum zoom level (10%)
ZOOM_MAX = 5.0  # Maximum zoom level (500%)
ZOOM_FIT_PADDING = 50  # Pixels of padding when fitting to circuit

# Z-value layering (higher values are drawn on top)
Z_GRID = -1  # Grid lines and labels (background)
Z_COMPONENT = 0  # Components (default QGraphicsItem z)
Z_WIRE = 1  # Wires (above components)
Z_ANNOTATION = 90  # Text annotations
Z_WIRE_PREVIEW = 100  # Temporary wire preview during drawing
Z_WAYPOINT_MARKER = 101  # Waypoint placement markers
Z_SEGMENT_HANDLE = 199  # Wire segment drag handles
Z_WAYPOINT_HANDLE = 200  # Waypoint drag handles (topmost)

# Waveform viewer
INITIAL_LOAD_COUNT = 50  # Rows loaded on first display
SCROLL_LOAD_COUNT = 25  # Additional rows loaded on scroll

# GUI-specific theme color keys per component type
_COLOR_KEYS = {
    "Resistor": "component_resistor",
    "Capacitor": "component_capacitor",
    "Inductor": "component_inductor",
    "Voltage Source": "component_voltage_source",
    "Current Source": "component_current_source",
    "Waveform Source": "component_waveform_source",
    "AC Voltage Source": "component_ac_voltage_source",
    "AC Current Source": "component_ac_current_source",
    "Ground": "component_ground",
    "Op-Amp": "component_opamp",
    "VCVS": "component_vcvs",
    "CCVS": "component_ccvs",
    "VCCS": "component_vccs",
    "CCCS": "component_cccs",
    "BJT NPN": "component_bjt_npn",
    "BJT PNP": "component_bjt_pnp",
    "MOSFET NMOS": "component_mosfet_nmos",
    "MOSFET PMOS": "component_mosfet_pmos",
    "VC Switch": "component_vc_switch",
    "Diode": "component_diode",
    "LED": "component_led",
    "Zener Diode": "component_zener",
    "Transformer": "component_transformer",
    "Current Probe": "component_current_probe",
}

# Component definitions - symbol and terminals sourced from models
COMPONENTS = {
    comp_type: {
        "symbol": SPICE_SYMBOLS[comp_type],
        "terminals": TERMINAL_COUNTS.get(comp_type, 2),
        "color_key": _COLOR_KEYS.get(comp_type, "text_primary"),
    }
    for comp_type in COMPONENT_TYPES
}

# Default component counter for ID generation
DEFAULT_COMPONENT_COUNTER = {comp["symbol"]: 0 for comp in COMPONENTS.values()}
