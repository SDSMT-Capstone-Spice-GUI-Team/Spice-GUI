"""Protocol for the component selection palette."""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class ComponentPaletteProtocol(Protocol):
    """Contract for a component selection widget.

    Displays available component types organised by category.
    Supports add-to-canvas via double-click, drag-and-drop, or
    equivalent interaction.

    Callback signature::

        on_component_selected(component_type: str)
    """

    def set_component_selected_callback(self, callback: Callable[[str], None]) -> None:
        """Register the callback for adding a component to the canvas."""
        ...

    def set_recommended_components(self, component_types: list[str]) -> None:
        """Update the recommended / highlighted section."""
        ...

    def set_filter_text(self, text: str) -> None:
        """Filter the palette to show only matching components."""
        ...
