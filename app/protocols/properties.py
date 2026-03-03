"""Protocol for the component property editor panel."""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

from models.component import ComponentData


@runtime_checkable
class PropertiesPanelProtocol(Protocol):
    """Contract for a panel that displays and edits component properties.

    The panel receives a ``ComponentData`` reference and lets the user
    modify values.  Changes are communicated back to the shell via a
    registered callback.

    Callback signature::

        on_property_changed(component_id: str, property_name: str, new_value: Any)

    Recognised *property_name* values:

    =========== ======================================
    Name        Value type
    =========== ======================================
    value       ``str``
    rotation    ``int`` (degrees: 0, 90, 180, 270)
    waveform    ``tuple[str, dict]`` (type, params)
    initial_condition  ``Optional[str]``
    =========== ======================================
    """

    def show_component(self, component: ComponentData) -> None:
        """Display properties for the given component."""
        ...

    def show_multi_selection(self, count: int) -> None:
        """Show a summary when multiple components are selected."""
        ...

    def show_no_selection(self) -> None:
        """Show the empty / no-selection state."""
        ...

    def set_property_change_callback(self, callback: Callable[[str, str, Any], None]) -> None:
        """Register the callback invoked when the user edits a property.

        Args:
            callback: ``(component_id, property_name, new_value)``
        """
        ...
