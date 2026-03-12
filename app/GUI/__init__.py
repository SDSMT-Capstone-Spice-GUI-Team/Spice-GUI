# AUDIT(architecture): re-exporting pathfinding internals from the GUI package creates coupling; consumers should import directly from algorithms
from algorithms.path_finding import IDAStarPathfinder, get_component_obstacles, get_wire_obstacles

from .analysis_dialog import AnalysisDialog
from .circuit_canvas import CircuitCanvas, CircuitCanvasView
from .component_item import ComponentGraphicsItem
from .component_palette import ComponentPalette
from .main_window import MainWindow

# Re-export from centralized styles module
from .styles import COMPONENTS, DEFAULT_COMPONENT_COUNTER, GRID_SIZE, theme_manager
from .wire_item import WireGraphicsItem, WireItem

__all__ = [
    "AnalysisDialog",
    "CircuitCanvasView",
    "CircuitCanvas",  # Backward compatibility
    "MainWindow",
    "ComponentGraphicsItem",
    "ComponentPalette",
    "IDAStarPathfinder",
    "get_component_obstacles",
    "get_wire_obstacles",
    "WireGraphicsItem",
    # AUDIT(cleanup): verify if WireItem backward-compat alias is still needed; remove from exports if all callsites use WireGraphicsItem
    "WireItem",  # Backward compatibility
    "GRID_SIZE",
    "COMPONENTS",
    "DEFAULT_COMPONENT_COUNTER",
    "theme_manager",
]
