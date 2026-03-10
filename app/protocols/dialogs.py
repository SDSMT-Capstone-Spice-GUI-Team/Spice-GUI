"""Protocols for modal dialog interactions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass


@runtime_checkable
class ProgressHandle(Protocol):
    """Handle returned by ``DialogProvider.create_progress``."""

    def update(self, value: int, message: str = "") -> bool:
        """Advance the progress bar.

        Returns ``False`` if the user cancelled.
        """
        ...

    def close(self) -> None:
        """Close the progress dialog."""
        ...


@runtime_checkable
class DialogProvider(Protocol):
    """Contract for modal dialogs that collect user input.

    Each method shows a dialog and returns the result, or ``None``
    if the user cancelled.  This decouples dialog presentation from
    business logic.
    """

    # --- File dialogs ---

    def ask_save_file(self, title: str, filters: str, default_name: str = "") -> Optional[Path]:
        """Show a save-file dialog.  Returns chosen path or ``None``."""
        ...

    def ask_open_file(self, title: str, filters: str) -> Optional[Path]:
        """Show an open-file dialog.  Returns chosen path or ``None``."""
        ...

    # --- Confirmation / message dialogs ---

    def confirm(self, title: str, message: str) -> bool:
        """Show a yes/no confirmation.  Returns ``True`` for yes."""
        ...

    def show_error(self, title: str, message: str) -> None: ...
    def show_warning(self, title: str, message: str) -> None: ...
    def show_info(self, title: str, message: str) -> None: ...

    # --- Analysis configuration ---

    def ask_analysis_params(self, analysis_type: str, current_params: dict) -> Optional[dict]:
        """Show analysis-parameter dialog.  Returns params or ``None``."""
        ...

    def ask_parameter_sweep_config(self, components: dict[str, Any]) -> Optional[dict]:
        """Show parameter-sweep configuration.  Returns config or ``None``."""
        ...

    def ask_monte_carlo_config(self, components: dict[str, Any]) -> Optional[dict]:
        """Show Monte Carlo configuration.  Returns config or ``None``."""
        ...

    # --- Progress ---

    def create_progress(self, title: str, message: str, maximum: int) -> ProgressHandle:
        """Create a progress dialog.  Returns a handle for updates."""
        ...
