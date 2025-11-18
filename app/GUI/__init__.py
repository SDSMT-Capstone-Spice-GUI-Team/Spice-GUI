from .analysis_dialog import AnalysisDialog
from .circuit_canvas import CircuitCanvas
from .circuit_design_gui import CircuitDesignGUI
from .circuit_node import Node
from .component_item import ComponentItem
from .component_palette import ComponentPalette
from .path_finding import GridPathfinder, get_component_obstacles
from .wire_item import WireItem

# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
}

GRID_SIZE = 10

__all__ = [
    'AnalysisDialog',
    'CircuitCanvas',
    'CircuitDesignGUI',
    'Node',
    'ComponentItem',
    'ComponentPalette',
    'GridPathfinder',
    'get_component_obstacles',
    'WireItem',
    'GRID_SIZE',
    'COMPONENTS',
]