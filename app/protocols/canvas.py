"""Protocol for the circuit drawing surface."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CircuitCanvasProtocol(Protocol):
    """Contract for a circuit drawing surface.

    The canvas registers as a ``CircuitController`` observer and reacts
    to model-change events.  It also exposes methods that the application
    shell delegates to for zoom, selection, and display toggles.

    Minimal implementation checklist:
        1. Call ``circuit_ctrl.add_observer(self.handle_observer_event)``
           during initialisation.
        2. Implement ``handle_observer_event`` to dispatch each event
           string to an internal handler (see ``protocols.events`` for
           the full event list and payload types).
        3. Expose selection, zoom, and display-toggle methods so the
           shell can wire them to menu/toolbar actions.
    """

    # --- Observer dispatch ---

    def handle_observer_event(self, event: str, data: Any) -> None:
        """Handle a ``CircuitController`` observer notification.

        Dispatch based on *event* (see :pymod:`protocols.events`).
        """
        ...

    # --- Selection ---

    def get_selected_component_ids(self) -> list[str]:
        """Return IDs of currently selected components."""
        ...

    def clear_selection(self) -> None:
        """Deselect all items."""
        ...

    def select_components(self, component_ids: list[str]) -> None:
        """Programmatically select the given components."""
        ...

    # --- Zoom ---

    def zoom_in(self) -> None: ...
    def zoom_out(self) -> None: ...

    def zoom_fit(self) -> None:
        """Fit all circuit content in the viewport."""
        ...

    def get_zoom_level(self) -> float:
        """Return current zoom as a multiplier (1.0 = 100 %)."""
        ...

    # --- Display toggles ---

    def set_show_component_labels(self, show: bool) -> None:
        """Toggle component ID labels (R1, V1, etc.)."""
        ...

    def set_show_component_values(self, show: bool) -> None:
        """Toggle component value labels (1k, 5V, etc.)."""
        ...

    def set_show_node_labels(self, show: bool) -> None:
        """Toggle node labels (nodeA, nodeB, etc.)."""
        ...

    # --- Operating-point annotations ---

    def set_node_voltages(self, voltages: dict[str, float]) -> None:
        """Display operating-point voltage annotations on nodes."""
        ...

    def clear_op_annotations(self) -> None:
        """Remove all operating-point annotations."""
        ...

    # --- Image export ---

    def export_image(self, filepath: str, include_grid: bool = False) -> None:
        """Render the canvas to an image file (PNG, SVG, etc.)."""
        ...

    # --- Theme ---

    def refresh_theme(self) -> None:
        """Re-apply the current theme to all visual elements."""
        ...
