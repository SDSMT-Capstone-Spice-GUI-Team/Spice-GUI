"""
light_theme.py - Default light theme implementation.

All color values from the original codebase are centralized here.
Teammates can update these values from design documents.
"""
from PyQt6.QtGui import QColor, QPen, QBrush
from .theme import BaseTheme
from .constants import COMPONENTS


class LightTheme(BaseTheme):
    """Light theme - the default application theme."""

    def __init__(self):
        super().__init__()
        self._define_colors()
        self._define_pens()
        self._define_brushes()
        self._define_fonts()
        self._define_stylesheets()

    @property
    def name(self) -> str:
        return "Light Theme"

    def _define_colors(self):
        """Define all color values."""
        self._colors = {
            # ===== Component Colors =====
            'component_resistor': '#2196F3',       # Blue
            'component_capacitor': '#4CAF50',      # Green
            'component_inductor': '#FF9800',       # Orange
            'component_voltage_source': '#F44336', # Red
            'component_current_source': '#9C27B0', # Purple
            'component_waveform_source': '#E91E63', # Pink
            'component_ground': '#000000',         # Black
            'component_opamp': '#FFC107',          # Amber
            'component_vcvs': '#00897B',           # Teal
            'component_ccvs': '#00ACC1',           # Cyan
            'component_vccs': '#26A69A',           # Teal variant
            'component_cccs': '#0097A7',           # Dark cyan
            'component_bjt_npn': '#FF6B6B',        # Coral red
            'component_bjt_pnp': '#4ECDC4',        # Teal green
            'component_mosfet_nmos': '#7B1FA2',    # Deep purple
            'component_mosfet_pmos': '#512DA8',    # Indigo

            # ===== Algorithm Layer Colors =====
            'algorithm_astar': '#2196F3',          # Blue (33, 150, 243)
            'algorithm_idastar': '#4CAF50',        # Green (76, 175, 80)
            'algorithm_dijkstra': '#FF9800',       # Orange (255, 152, 0)

            # ===== Grid Colors =====
            'grid_minor': '#C8C8C8',               # Light gray (200, 200, 200)
            'grid_major': '#969696',               # Medium gray (150, 150, 150)
            'grid_label': '#646464',               # Dark gray (100, 100, 100)

            # ===== Canvas/UI Colors =====
            'background_primary': '#FFFFFF',       # White
            'background_secondary': '#F0F0F0',     # Light gray
            'text_primary': '#000000',             # Black
            'text_secondary': '#666666',           # Medium gray
            'text_muted': '#999999',               # Light gray text

            # ===== Selection & Highlight =====
            'selection_highlight': '#FFFF00',      # Yellow
            'node_label': '#FF00FF',               # Magenta (255, 0, 255)
            'node_label_bg': '#FFFFFF',            # White (with alpha applied)

            # ===== Wire Colors =====
            'wire_default': '#000000',             # Black
            'wire_preview': '#0000FF',             # Blue (temp wire)
            'wire_selected': '#FFFF00',            # Yellow

            # ===== Terminal Colors =====
            'terminal_default': '#FF0000',         # Red
            'terminal_highlight': '#00C800',       # Green (0, 200, 0)
            'terminal_fill': '#00FF00',            # Bright green

            # ===== Obstacle Visualization =====
            'obstacle_full': '#FF6464',            # Light red (255, 100, 100)
            'obstacle_inset': '#6496FF',           # Light blue (100, 150, 255)
        }

    def _define_pens(self):
        """Define all pen configurations."""
        self._pens = {
            # Grid pens
            'grid_minor': {
                'color': 'grid_minor',
                'width': 0.5,
                'cosmetic': True
            },
            'grid_major': {
                'color': 'grid_major',
                'width': 1.0,
                'cosmetic': True
            },

            # Component pens
            'component_outline': {
                'color': 'text_primary',
                'width': 2.0
            },
            'component_selected': {
                'color': 'selection_highlight',
                'width': 3.0
            },

            # Terminal pens
            'terminal': {
                'color': 'terminal_default',
                'width': 4.0
            },
            'terminal_marker': {
                'color': 'terminal_highlight',
                'width': 3.0
            },

            # Wire pens
            'wire_default': {
                'color': 'wire_default',
                'width': 2.0
            },
            'wire_preview': {
                'color': 'wire_preview',
                'width': 3.0,
                'style': 'dash'
            },
            'wire_selected': {
                'color': 'wire_selected',
                'width': 4.0
            },

            # Node label pens
            'node_label_outline': {
                'color': 'node_label',
                'width': 1.0
            },

            # Obstacle visualization
            'obstacle_full': {
                'color': 'obstacle_full',
                'width': 3.0
            },
            'obstacle_inset': {
                'color': 'obstacle_inset',
                'width': 2.0,
                'style': 'dot'
            },
        }

    def _define_brushes(self):
        """Define all brush configurations."""
        self._brushes = {
            'node_label_bg': {
                'color': 'node_label_bg',
                'alpha': 200
            },
            'terminal_fill': {
                'color': 'terminal_fill',
                'alpha': 100
            },
            'component_fill': {
                'color': 'background_primary',
                'alpha': 255
            },
        }

    def _define_fonts(self):
        """Define all font configurations."""
        self._fonts = {
            'grid_label': {
                'size': 8,
                'bold': False
            },
            'node_label': {
                'size': 10,
                'bold': True
            },
            'panel_title': {
                'size': 10,
                'bold': True
            },
            'panel_subtitle': {
                'size': 12,
                'bold': True
            },
            'monospace': {
                'family': 'monospace',
                'size': 9,
                'bold': False
            },
        }

    def _define_stylesheets(self):
        """Define all stylesheet strings."""
        self._stylesheets = {
            'instructions_panel': """
                QLabel {
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 5px;
                }
            """,
            'muted_label': "QLabel { color: #666; }",
            'title_bold': "font-weight: bold; font-size: 12pt;",
            'metrics_text': "font-family: monospace; font-size: 9pt;",
        }

    # ===== Helper methods for common patterns =====

    def get_component_color(self, component_type: str) -> QColor:
        """Get the themed color for a component type."""
        comp_info = COMPONENTS.get(component_type, {})
        color_key = comp_info.get('color_key', 'text_primary')
        return self.color(color_key)

    def get_component_color_hex(self, component_type: str) -> str:
        """Get the hex color string for a component type."""
        comp_info = COMPONENTS.get(component_type, {})
        color_key = comp_info.get('color_key', 'text_primary')
        return self.color_hex(color_key)

    def get_algorithm_color(self, algorithm: str) -> QColor:
        """Get the themed color for an algorithm layer."""
        key = f'algorithm_{algorithm}'
        return self.color(key)

    def create_component_pen(self, component_type: str, width: float = 2.0) -> QPen:
        """Create a pen for drawing a specific component type."""
        color = self.get_component_color(component_type)
        return QPen(color, width)

    def create_component_brush(self, component_type: str) -> QBrush:
        """Create a brush for filling a specific component type."""
        color = self.get_component_color(component_type)
        return QBrush(color.lighter(150))
