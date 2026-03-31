"""custom_theme.py - User-created theme that overlays colors on a built-in base."""

from .dark_theme import DarkTheme
from .light_theme import LightTheme
from .theme import BaseTheme


class CustomTheme(BaseTheme):
    """Theme with user-chosen color overrides on top of a Light or Dark base."""

    def __init__(self, name: str, base: str, colors: dict, theme_is_dark: bool):
        super().__init__()
        self._custom_name = name
        self._base_name = base
        self._theme_is_dark = theme_is_dark

        # Initialize from the base theme
        base_theme = DarkTheme() if base == "dark" else LightTheme()
        self._colors = dict(base_theme._colors)
        self._pens = dict(base_theme._pens)
        self._brushes = dict(base_theme._brushes)
        self._fonts = dict(base_theme._fonts)

        # Use the base theme's QSS file
        self._qss_filename = base_theme._qss_filename

        # Apply user color overrides
        self._color_overrides = dict(colors)
        self._colors.update(colors)

    @property
    def name(self) -> str:
        return self._custom_name

    @property
    def is_dark(self) -> bool:
        return self._theme_is_dark

    @property
    def base_name(self) -> str:
        return self._base_name

    def get_color_overrides(self) -> dict:
        """Return only the colors that differ from the base theme."""
        return dict(self._color_overrides)