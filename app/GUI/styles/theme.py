"""
theme.py - Theme protocol and base class.

Defines the contract that all themes must fulfill.
"""

from typing import Dict, Protocol

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPen

from .constants import COMPONENTS


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

    def stylesheet(self, key: str) -> str:
        """Get stylesheet string by key."""
        return self._stylesheets.get(key, "")

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

    def generate_dark_stylesheet(self) -> str:
        """Generate a global dark stylesheet from theme colors.

        Returns an empty string for light themes.
        """
        if not self.is_dark:
            return ""

        bg1 = self.color_hex("background_primary")
        bg2 = self.color_hex("background_secondary")
        fg = self.color_hex("text_primary")
        # Derive mid-tone colors from the background
        bg_mid = QColor(bg2).lighter(120).name()
        border = QColor(bg2).lighter(150).name()

        return (
            f"QMainWindow, QWidget {{ background-color: {bg1}; color: {fg}; }}"
            f" QMenuBar {{ background-color: {bg2}; color: {fg}; }}"
            f" QMenuBar::item:selected {{ background-color: {bg_mid}; }}"
            f" QMenu {{ background-color: {bg2}; color: {fg}; }}"
            f" QMenu::item:selected {{ background-color: {bg_mid}; }}"
            f" QLabel {{ color: {fg}; }}"
            f" QPushButton {{"
            f"   background-color: {bg_mid}; color: {fg};"
            f"   border: 1px solid {border}; padding: 4px 12px; border-radius: 3px;"
            f" }}"
            f" QPushButton:hover {{ background-color: {QColor(bg_mid).lighter(110).name()}; }}"
            f" QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{"
            f"   background-color: {bg2}; color: {fg};"
            f"   border: 1px solid {border};"
            f" }}"
            f" QSplitter::handle {{ background-color: {bg_mid}; }}"
            f" QScrollBar {{ background-color: {bg2}; }}"
            f" QScrollBar::handle {{ background-color: {border}; }}"
            f" QGroupBox {{ color: {fg}; border: 1px solid {border}; }}"
            f" QTableWidget {{ background-color: {bg2}; color: {fg};"
            f"   gridline-color: {border}; }}"
            f" QHeaderView::section {{ background-color: {bg_mid}; color: {fg}; }}"
        )
