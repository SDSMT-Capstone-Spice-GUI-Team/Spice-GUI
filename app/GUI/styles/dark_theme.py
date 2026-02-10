"""
dark_theme.py - Dark theme implementation.

Provides a dark color scheme for reduced eye-strain during long lab sessions.
"""

from PyQt6.QtGui import QBrush, QColor, QPen

from .constants import COMPONENTS
from .theme import BaseTheme


class DarkTheme(BaseTheme):
    """Dark theme with high-contrast colors on a dark background."""

    def __init__(self):
        super().__init__()
        self._define_colors()
        self._define_pens()
        self._define_brushes()
        self._define_fonts()
        self._define_stylesheets()

    @property
    def name(self) -> str:
        return "Dark Theme"

    def _define_colors(self):
        """Define all color values for dark mode."""
        self._colors = {
            # ===== Component Colors (brightened for dark background) =====
            "component_resistor": "#64B5F6",  # Light blue
            "component_capacitor": "#81C784",  # Light green
            "component_inductor": "#FFB74D",  # Light orange
            "component_voltage_source": "#EF5350",  # Light red
            "component_current_source": "#CE93D8",  # Light purple
            "component_waveform_source": "#F48FB1",  # Light pink
            "component_ground": "#BDBDBD",  # Light gray (not black)
            "component_opamp": "#FFD54F",  # Light amber
            "component_vcvs": "#4DB6AC",  # Light teal
            "component_ccvs": "#4DD0E1",  # Light cyan
            "component_vccs": "#80CBC4",  # Light teal variant
            "component_cccs": "#4FC3F7",  # Light cyan variant
            "component_bjt_npn": "#FF8A80",  # Light coral
            "component_bjt_pnp": "#80CBC4",  # Light teal green
            "component_mosfet_nmos": "#B39DDB",  # Light deep purple
            "component_mosfet_pmos": "#9FA8DA",  # Light indigo
            "component_vc_switch": "#BCAAA4",  # Light brown
            "component_diode": "#90A4AE",  # Light blue-gray
            "component_led": "#FFF176",  # Light yellow
            "component_zener": "#A1887F",  # Light brown
            # ===== Algorithm Layer Colors =====
            "algorithm_astar": "#64B5F6",  # Light blue
            "algorithm_idastar": "#81C784",  # Light green
            "algorithm_dijkstra": "#FFB74D",  # Light orange
            # ===== Grid Colors =====
            "grid_minor": "#333333",  # Subtle dark gray
            "grid_major": "#4A4A4A",  # Medium dark gray
            "grid_label": "#888888",  # Lighter gray for readability
            # ===== Canvas/UI Colors =====
            "background_primary": "#1E1E1E",  # Dark background
            "background_secondary": "#2D2D2D",  # Slightly lighter
            "text_primary": "#D4D4D4",  # Light gray text
            "text_secondary": "#999999",  # Medium gray
            "text_muted": "#666666",  # Dimmed text
            # ===== Selection & Highlight =====
            "selection_highlight": "#FFFF00",  # Yellow (kept bright)
            "node_label": "#FF80FF",  # Bright magenta
            "node_label_bg": "#2D2D2D",  # Dark background
            # ===== OP Annotation Colors =====
            "op_voltage": "#66BBFF",  # Light blue for voltage annotations
            "op_current": "#66DD66",  # Light green for current annotations
            "op_annotation_bg": "#3D3D1E",  # Dark yellow-tinted background
            # ===== Wire Colors =====
            "wire_default": "#D4D4D4",  # Light gray
            "wire_preview": "#6699FF",  # Light blue
            "wire_selected": "#FFFF00",  # Yellow
            # ===== Terminal Colors =====
            "terminal_default": "#FF6666",  # Light red
            "terminal_highlight": "#66FF66",  # Light green
            "terminal_fill": "#00CC00",  # Medium green
            # ===== Obstacle Visualization =====
            "obstacle_full": "#FF6464",  # Light red
            "obstacle_inset": "#6496FF",  # Light blue
            # ===== Probe Colors =====
            "probe_voltage": "#FF66AA",  # Bright pink for probed voltages
            "probe_current": "#66DDAA",  # Light green for probed currents
            "probe_bg": "#3D1E2D",  # Dark pink-tinted background
            "probe_highlight": "#FF66CC",  # Bright pink for probe crosshair
        }

    def _define_pens(self):
        """Define all pen configurations."""
        self._pens = {
            # Grid pens
            "grid_minor": {"color": "grid_minor", "width": 0.5, "cosmetic": True},
            "grid_major": {"color": "grid_major", "width": 1.0, "cosmetic": True},
            # Component pens
            "component_outline": {"color": "text_primary", "width": 2.0},
            "component_selected": {"color": "selection_highlight", "width": 3.0},
            # Terminal pens
            "terminal": {"color": "terminal_default", "width": 4.0},
            "terminal_marker": {"color": "terminal_highlight", "width": 3.0},
            # Wire pens
            "wire_default": {"color": "wire_default", "width": 2.0},
            "wire_preview": {"color": "wire_preview", "width": 3.0, "style": "dash"},
            "wire_selected": {"color": "wire_selected", "width": 4.0},
            # Node label pens
            "node_label_outline": {"color": "node_label", "width": 1.0},
            # OP annotation pens
            "op_voltage": {"color": "op_voltage", "width": 1.0},
            "op_current": {"color": "op_current", "width": 1.0},
            # Obstacle visualization
            "obstacle_full": {"color": "obstacle_full", "width": 3.0},
            "obstacle_inset": {"color": "obstacle_inset", "width": 2.0, "style": "dot"},
            # Probe pens
            "probe_voltage": {"color": "probe_voltage", "width": 1.5},
            "probe_current": {"color": "probe_current", "width": 1.5},
            "probe_highlight": {"color": "probe_highlight", "width": 2.0, "style": "dash"},
        }

    def _define_brushes(self):
        """Define all brush configurations."""
        self._brushes = {
            "node_label_bg": {"color": "node_label_bg", "alpha": 200},
            "op_annotation_bg": {"color": "op_annotation_bg", "alpha": 220},
            "terminal_fill": {"color": "terminal_fill", "alpha": 100},
            "component_fill": {"color": "background_primary", "alpha": 255},
            "probe_bg": {"color": "probe_bg", "alpha": 230},
        }

    def _define_fonts(self):
        """Define all font configurations."""
        self._fonts = {
            "grid_label": {"size": 8, "bold": False},
            "node_label": {"size": 10, "bold": True},
            "op_annotation": {"size": 9, "bold": True},
            "panel_title": {"size": 10, "bold": True},
            "panel_subtitle": {"size": 12, "bold": True},
            "monospace": {"family": "monospace", "size": 9, "bold": False},
            "probe_label": {"size": 10, "bold": True},
        }

    def _define_stylesheets(self):
        """Define all stylesheet strings for dark mode."""
        self._stylesheets = {
            "instructions_panel": """
                QLabel {
                    background-color: #2D2D2D;
                    color: #D4D4D4;
                    padding: 10px;
                    border-radius: 5px;
                }
            """,
            "muted_label": "QLabel { color: #999; }",
            "title_bold": "font-weight: bold; font-size: 12pt; color: #D4D4D4;",
            "metrics_text": "font-family: monospace; font-size: 9pt; color: #D4D4D4;",
        }

    # ===== Helper methods (inherited from BaseTheme, same logic) =====

    def get_component_color(self, component_type: str) -> QColor:
        """Get the themed color for a component type."""
        comp_info = COMPONENTS.get(component_type, {})
        color_key = comp_info.get("color_key", "text_primary")
        return self.color(color_key)

    def get_component_color_hex(self, component_type: str) -> str:
        """Get the hex color string for a component type."""
        comp_info = COMPONENTS.get(component_type, {})
        color_key = comp_info.get("color_key", "text_primary")
        return self.color_hex(color_key)

    def get_algorithm_color(self, algorithm: str) -> QColor:
        """Get the themed color for an algorithm layer."""
        key = f"algorithm_{algorithm}"
        return self.color(key)

    def create_component_pen(self, component_type: str, width: float = 2.0) -> QPen:
        """Create a pen for drawing a specific component type."""
        color = self.get_component_color(component_type)
        return QPen(color, width)

    def create_component_brush(self, component_type: str) -> QBrush:
        """Create a brush for filling a specific component type."""
        color = self.get_component_color(component_type)
        return QBrush(color.lighter(150))
