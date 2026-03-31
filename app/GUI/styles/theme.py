"""
theme.py - Theme protocol and base class.

Defines the contract that all themes must fulfill.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Protocol

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPen

from .constants import COMPONENTS

logger = logging.getLogger(__name__)

_STYLES_DIR = Path(__file__).parent


class ThemeProtocol(Protocol):
    """Protocol defining the theme interface."""

    @property
    def name(self) -> str:
        """Theme name for display."""
        ...

    def color(self, key: str) -> QColor:
        """Get a QColor by semantic key."""
        ...

    def color_hex(self, key: str) -> str:
        """Get a hex color string by semantic key."""
        ...

    def pen(self, key: str) -> QPen:
        """Get a pre-configured QPen by semantic key."""
        ...

    def brush(self, key: str) -> QBrush:
        """Get a pre-configured QBrush by semantic key."""
        ...

    def font(self, key: str) -> QFont:
        """Get a pre-configured QFont by semantic key."""
        ...

    def load_qss(self) -> str:
        """Load and return the resolved QSS stylesheet string."""
        ...


class BaseTheme:
    """Base class for themes with shared functionality."""

    _qss_filename: str = ""

    def __init__(self):
        self._colors: Dict[str, str] = {}  # key -> hex string
        self._pens: Dict[str, Dict] = {}  # key -> pen config dict
        self._brushes: Dict[str, Dict] = {}  # key -> brush config dict
        self._fonts: Dict[str, Dict] = {}  # key -> font config dict

    @property
    def name(self) -> str:
        return "Base Theme"

    @property
    def is_dark(self) -> bool:
        return False

    def color(self, key: str) -> QColor:
        """Get QColor by key. Falls back to magenta if not found (debug)."""
        hex_color = self._colors.get(key, "#FF00FF")
        return QColor(hex_color)

    def color_hex(self, key: str) -> str:
        """Get hex color string by key."""
        return self._colors.get(key, "#FF00FF")

    def color_rgb(self, key: str) -> tuple:
        """Get (r, g, b) tuple by key."""
        qc = self.color(key)
        return (qc.red(), qc.green(), qc.blue())

    def color_rgba(self, key: str, alpha: int = 255) -> QColor:
        """Get QColor with specified alpha."""
        qc = self.color(key)
        qc.setAlpha(alpha)
        return qc

    def pen(self, key: str) -> QPen:
        """Get QPen by key."""
        config = self._pens.get(key, {})
        color_key = config.get("color", "text_primary")
        width = config.get("width", 1.0)
        cosmetic = config.get("cosmetic", False)
        style = config.get("style", "solid")

        pen = QPen(self.color(color_key), width)
        pen.setCosmetic(cosmetic)

        # Map style string to Qt enum
        style_map = {
            "solid": Qt.PenStyle.SolidLine,
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
            "dashdot": Qt.PenStyle.DashDotLine,
        }
        pen.setStyle(style_map.get(style, Qt.PenStyle.SolidLine))

        return pen

    def brush(self, key: str) -> QBrush:
        """Get QBrush by key."""
        config = self._brushes.get(key, {})
        color_key = config.get("color", "background_primary")
        alpha = config.get("alpha", 255)

        color = self.color_rgba(color_key, alpha)
        return QBrush(color)

    def font(self, key: str) -> QFont:
        """Get QFont by key."""
        config = self._fonts.get(key, {})
        font = QFont()

        if "family" in config:
            font.setFamily(config["family"])
        if "size" in config:
            font.setPointSize(config["size"])
        if config.get("bold", False):
            font.setBold(True)
        if config.get("italic", False):
            font.setItalic(True)

        return font

    def load_qss(self) -> str:
        """Load the QSS file for this theme and substitute @variable@ placeholders.

        Derived colors (background_mid, border, background_mid_hover) are
        computed automatically from the theme's color definitions.
        """
        if not self._qss_filename:
            return ""

        qss_path = _STYLES_DIR / self._qss_filename
        if not qss_path.exists():
            logger.warning("QSS file not found: %s", qss_path)
            return ""

        template = qss_path.read_text(encoding="utf-8")
        return self._substitute_variables(template)

    def _substitute_variables(self, template: str) -> str:
        """Replace @key@ placeholders with color values from self._colors.

        Also computes derived colors that aren't stored directly:
        - background_mid: lighter shade of background_secondary
        - border: even lighter shade of background_secondary
        - background_mid_hover: lighter shade of background_mid

        Placeholders inside CSS comments are ignored.
        """
        # Build the substitution map from theme colors + derived colors
        variables = dict(self._colors)

        # Compute derived colors
        bg2 = QColor(self._colors.get("background_secondary", "#F0F0F0"))
        bg_mid = bg2.lighter(120)
        border = bg2.lighter(150)
        bg_mid_hover = bg_mid.lighter(110)

        variables["background_mid"] = bg_mid.name()
        variables["border"] = border.name()
        variables["background_mid_hover"] = bg_mid_hover.name()

        # Strip CSS comments before substitution, then substitute on the
        # original template by only replacing @var@ outside of comments.
        comment_ranges = [(m.start(), m.end()) for m in re.finditer(r"/\*.*?\*/", template, re.DOTALL)]

        def in_comment(pos: int) -> bool:
            return any(start <= pos < end for start, end in comment_ranges)

        def replace_var(match):
            if in_comment(match.start()):
                return match.group(0)
            key = match.group(1)
            if key in variables:
                return variables[key]
            logger.warning("Unknown QSS variable: @%s@", key)
            return match.group(0)

        return re.sub(r"@(\w+)@", replace_var, template)

    # ===== Helper methods for common patterns =====

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
