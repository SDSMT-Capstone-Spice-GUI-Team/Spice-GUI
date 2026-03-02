"""Controller for theme mutations.

Routes all runtime theme changes through a single point of control
so that view-layer dialogs never mutate global theme_manager state
directly.
"""

from GUI.styles import theme_manager
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


# Module-level singleton
theme_ctrl = ThemeController()
