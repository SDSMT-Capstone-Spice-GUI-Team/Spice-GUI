"""
theme.py - Theme protocol and base class.

Defines the contract that all themes must fulfill.
"""

from typing import Dict, Protocol

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPen


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

    def stylesheet(self, key: str) -> str:
        """Get a stylesheet string by semantic key."""
        ...


class BaseTheme:
    """Base class for themes with shared functionality."""

    def __init__(self):
        self._colors: Dict[str, str] = {}  # key -> hex string
        self._pens: Dict[str, Dict] = {}  # key -> pen config dict
        self._brushes: Dict[str, Dict] = {}  # key -> brush config dict
        self._fonts: Dict[str, Dict] = {}  # key -> font config dict
        self._stylesheets: Dict[str, str] = {}  # key -> stylesheet string

    @property
    def name(self) -> str:
        return "Base Theme"

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

    def stylesheet(self, key: str) -> str:
        """Get stylesheet string by key."""
        return self._stylesheets.get(key, "")
