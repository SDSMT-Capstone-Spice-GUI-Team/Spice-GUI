"""
theme_manager.py - Singleton theme manager.

Provides global access to the current theme and enables runtime theme switching.
"""
from typing import Optional, Callable, List
from .theme import ThemeProtocol
from .light_theme import LightTheme


class ThemeManager:
    """
    Singleton manager for application themes.

    Usage:
        from app.GUI.styles import theme_manager

        # Get current theme
        theme = theme_manager.current_theme
        color = theme.color('component_resistor')

        # Switch themes
        theme_manager.set_theme(DarkTheme())

        # Subscribe to theme changes
        theme_manager.on_theme_changed(my_callback)
    """

    _instance: Optional['ThemeManager'] = None
    _theme: ThemeProtocol
    _listeners: List[Callable[[ThemeProtocol], None]]

    def __new__(cls) -> 'ThemeManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._theme = LightTheme()
            cls._instance._listeners = []
        return cls._instance

    @property
    def current_theme(self) -> ThemeProtocol:
        """Get the current theme."""
        return self._theme

    def set_theme(self, theme: ThemeProtocol) -> None:
        """
        Set a new theme and notify all listeners.

        Args:
            theme: The new theme to use
        """
        self._theme = theme
        self._notify_listeners()

    def on_theme_changed(self, callback: Callable[[ThemeProtocol], None]) -> None:
        """
        Register a callback to be notified when theme changes.

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
            except Exception as e:
                print(f"Error notifying theme listener: {e}")

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
        """Get the themed color for a component type."""
        return self._theme.get_component_color(component_type)

    def get_component_color_hex(self, component_type: str) -> str:
        """Get the hex color string for a component type."""
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
