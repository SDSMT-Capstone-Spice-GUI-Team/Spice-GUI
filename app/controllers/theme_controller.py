"""Controller for theme mutations.

Routes all runtime theme changes through a single point of control
so that view-layer dialogs never mutate global theme_manager state
directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.theme_manager import theme_manager

if TYPE_CHECKING:
    from GUI.styles.theme import ThemeProtocol


class ThemeController:
    """Thin controller that wraps theme_manager mutation methods."""

    def set_theme(self, theme: ThemeProtocol) -> None:
        """Apply *theme* as the active application theme."""
        theme_manager.set_theme(theme)

    @property
    def current_theme(self) -> ThemeProtocol:
        """Return the currently active theme."""
        return theme_manager.current_theme

    def set_theme_by_key(self, key: str) -> None:
        """Set theme by key string ('light', 'dark', or 'custom:<stem>')."""
        theme_manager.set_theme_by_key(key)

    def set_symbol_style(self, style: str) -> None:
        """Set the symbol drawing style ('ieee' or 'iec')."""
        theme_manager.set_symbol_style(style)

    def set_color_mode(self, mode: str) -> None:
        """Set the component color mode ('color' or 'monochrome')."""
        theme_manager.set_color_mode(mode)

    def set_wire_thickness(self, thickness: str) -> None:
        """Set the wire rendering thickness ('thin', 'normal', or 'thick')."""
        theme_manager.set_wire_thickness(thickness)

    def set_show_junction_dots(self, show: bool) -> None:
        """Set whether junction dots are shown at wire intersections."""
        theme_manager.set_show_junction_dots(show)

    def set_routing_mode(self, mode: str) -> None:
        """Set the wire routing mode ('orthogonal' or 'diagonal')."""
        theme_manager.set_routing_mode(mode)


# Module-level singleton
theme_ctrl = ThemeController()
