"""
theme_manager.py - Singleton theme manager.

Provides global access to the current theme, symbol style, and color mode.
Enables runtime theme/style switching with observer notification.
"""

import logging
from typing import Callable, List, Optional, Tuple

from .light_theme import LightTheme
from .theme import ThemeProtocol

logger = logging.getLogger(__name__)

# Valid symbol styles
SYMBOL_STYLES = ("ieee", "iec")

# Valid color modes
COLOR_MODES = ("color", "monochrome")


class ThemeManager:
    """
    Singleton manager for application themes, symbol styles, and color modes.

    Usage:
        from app.GUI.styles import theme_manager

        # Get current theme
        theme = theme_manager.current_theme
        color = theme.color('component_resistor')

        # Switch themes
        theme_manager.set_theme(DarkTheme())

        # Symbol style
        theme_manager.symbol_style  # "ieee" (default)
        theme_manager.set_symbol_style("iec")

        # Color mode
        theme_manager.color_mode  # "color" (default)
        theme_manager.set_color_mode("monochrome")

        # Subscribe to theme changes
        theme_manager.on_theme_changed(my_callback)
    """

    _instance: Optional["ThemeManager"] = None
    _theme: ThemeProtocol
    _listeners: List[Callable[[ThemeProtocol], None]]
    _symbol_style: str
    _color_mode: str

    def __new__(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._theme = LightTheme()
            cls._instance._listeners = []
            cls._instance._symbol_style = "ieee"
            cls._instance._color_mode = "color"
        return cls._instance

    @property
    def current_theme(self) -> ThemeProtocol:
        """Get the current theme."""
        return self._theme

    @property
    def symbol_style(self) -> str:
        """Get the current symbol style ('ieee' or 'iec')."""
        return self._symbol_style

    @property
    def color_mode(self) -> str:
        """Get the current color mode ('color' or 'monochrome')."""
        return self._color_mode

    def set_theme(self, theme: ThemeProtocol) -> None:
        """
        Set a new theme and notify all listeners.

        Args:
            theme: The new theme to use
        """
        self._theme = theme
        self._notify_listeners()

    def set_symbol_style(self, style: str) -> None:
        """Set the symbol drawing style and notify listeners.

        Args:
            style: 'ieee' for IEEE/ANSI or 'iec' for IEC 60617
        """
        if style not in SYMBOL_STYLES:
            logger.warning("Unknown symbol style %r, ignoring", style)
            return
        if style != self._symbol_style:
            self._symbol_style = style
            self._notify_listeners()

    def set_color_mode(self, mode: str) -> None:
        """Set the component color mode and notify listeners.

        Args:
            mode: 'color' for per-type colors or 'monochrome' for single color
        """
        if mode not in COLOR_MODES:
            logger.warning("Unknown color mode %r, ignoring", mode)
            return
        if mode != self._color_mode:
            self._color_mode = mode
            self._notify_listeners()

    def on_theme_changed(self, callback: Callable[[ThemeProtocol], None]) -> None:
        """
        Register a callback to be notified when theme, style, or color mode changes.

        Args:
            callback: Function that takes the new theme as argument
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[ThemeProtocol], None]) -> None:
        """Remove a previously registered callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all registered listeners of theme change."""
        for callback in self._listeners:
            try:
                callback(self._theme)
            except (TypeError, AttributeError, RuntimeError) as e:
                logger.error("Error notifying theme listener: %s", e)

    # ===== Custom theme support =====

    def get_available_themes(self) -> List[Tuple[str, str]]:
        """Return list of (display_name, key) for all available themes.

        Built-in themes use keys "light" and "dark".
        Custom themes use keys "custom:<filename_stem>".
        """
        from . import theme_store

        themes: List[Tuple[str, str]] = [("Light", "light"), ("Dark", "dark")]
        for display_name, stem in theme_store.list_custom_themes():
            themes.append((display_name, f"custom:{stem}"))
        return themes

    def set_theme_by_key(self, key: str) -> None:
        """Set theme by key string ("light", "dark", or "custom:<stem>")."""
        from . import theme_store
        from .dark_theme import DarkTheme

        if key == "dark":
            self.set_theme(DarkTheme())
        elif key.startswith("custom:"):
            stem = key[len("custom:") :]
            theme = theme_store.load_theme(stem)
            if theme is not None:
                self.set_theme(theme)
            else:
                logger.warning("Custom theme %r not found, falling back to light", stem)
                self.set_theme(LightTheme())
        else:
            self.set_theme(LightTheme())

    def get_theme_key(self) -> str:
        """Return the key for the current theme."""
        from .custom_theme import CustomTheme

        theme = self._theme
        if isinstance(theme, CustomTheme):
            from . import theme_store

            stem = theme_store._filename_safe(theme.name)
            return f"custom:{stem}"
        elif theme.name == "Dark Theme":
            return "dark"
        return "light"

    # ===== Convenience methods for common operations =====

    def color(self, key: str):
        """Shortcut to get a color from current theme."""
        return self._theme.color(key)

    def color_hex(self, key: str) -> str:
        """Shortcut to get a hex color from current theme."""
        return self._theme.color_hex(key)

    def pen(self, key: str):
        """Shortcut to get a pen from current theme."""
        return self._theme.pen(key)

    def brush(self, key: str):
        """Shortcut to get a brush from current theme."""
        return self._theme.brush(key)

    def font(self, key: str):
        """Shortcut to get a font from current theme."""
        return self._theme.font(key)

    def stylesheet(self, key: str) -> str:
        """Shortcut to get a stylesheet from current theme."""
        return self._theme.stylesheet(key)

    # ===== Helper methods delegated to current theme =====

    def get_component_color(self, component_type: str):
        """Get the themed color for a component type.

        In monochrome mode, returns the theme's foreground color instead of
        the per-type color.
        """
        if self._color_mode == "monochrome":
            return self._theme.color("text_primary")
        return self._theme.get_component_color(component_type)

    def get_component_color_hex(self, component_type: str) -> str:
        """Get the hex color string for a component type."""
        if self._color_mode == "monochrome":
            return self._theme.color_hex("text_primary")
        return self._theme.get_component_color_hex(component_type)

    def get_algorithm_color(self, algorithm: str):
        """Get the themed color for an algorithm layer."""
        return self._theme.get_algorithm_color(algorithm)

    def create_component_pen(self, component_type: str, width: float = 2.0):
        """Create a pen for drawing a specific component type."""
        return self._theme.create_component_pen(component_type, width)

    def create_component_brush(self, component_type: str):
        """Create a brush for filling a specific component type."""
        return self._theme.create_component_brush(component_type)


# Module-level singleton instance for easy import
theme_manager = ThemeManager()
