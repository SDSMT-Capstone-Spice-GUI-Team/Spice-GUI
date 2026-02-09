"""
CircuitController - Orchestrates component and wire CRUD operations.

This module contains no Qt dependencies. It manages the CircuitModel
and notifies views of changes through an observer pattern.
"""

import logging
from typing import Callable, Any, Optional
from models.circuit import CircuitModel
from models.component import ComponentData, SPICE_SYMBOLS, DEFAULT_VALUES
from models.wire import WireData

logger = logging.getLogger(__name__)


class CircuitController:
    """
    Controller for circuit component and wire operations.

    Manages the CircuitModel and notifies registered observers when
    the model changes. Views register callbacks to stay in sync.

    Observer events:
        component_added (ComponentData) - A new component was added
        component_removed (str) - A component was removed (by ID)
        component_rotated (ComponentData) - A component was rotated
        component_moved (ComponentData) - A component was moved
        component_value_changed (ComponentData) - A component's value changed
        wire_added (WireData) - A new wire was added
        wire_removed (int) - A wire was removed (by index)
        wire_routed (tuple[int, WireData]) - A wire's waypoints were updated
        circuit_cleared (None) - The entire circuit was cleared
        nodes_rebuilt (None) - The node graph was rebuilt
        model_loaded (None) - Circuit loaded from file
        model_saved (None) - Circuit saved to file
        simulation_started (None) - Simulation began
        simulation_completed (SimulationResult) - Simulation finished
    """

    def __init__(self, model: Optional[CircuitModel] = None):
        self.model = model or CircuitModel()
        self._observers: list[Callable[[str, Any], None]] = []

    def add_observer(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback for model change events."""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[str, Any], None]) -> None:
        """Unregister a previously registered callback."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify(self, event: str, data: Any) -> None:
        """Notify all observers of a model change."""
        for observer in self._observers:
            try:
                observer(event, data)
            except (TypeError, AttributeError, RuntimeError) as e:
                logger.error("Error notifying observer: %s", e)

    # --- Component operations ---

    def add_component(self, component_type: str,
                      position: tuple[float, float]) -> ComponentData:
        """
        Create and add a new component to the circuit.

        Generates a unique ID using the component counter (R1, R2, V1, etc.).

        Returns:
            The newly created ComponentData.
        """
        symbol = SPICE_SYMBOLS.get(component_type, 'X')
        count = self.model.component_counter.get(symbol, 0) + 1
        self.model.component_counter[symbol] = count
        component_id = f"{symbol}{count}"

        component = ComponentData(
            component_id=component_id,
            component_type=component_type,
            value=DEFAULT_VALUES.get(component_type, "1"),
            position=position,
        )
        self.model.add_component(component)
        self._notify('component_added', component)
        return component

    def remove_component(self, component_id: str) -> None:
        """
        Remove a component and all connected wires.

        Wires are removed in reverse index order to preserve indices.
        """
        wire_indices = self.model.remove_component(component_id)
        for idx in sorted(wire_indices, reverse=True):
            self.model.remove_wire(idx)
            self._notify('wire_removed', idx)
        self._notify('component_removed', component_id)

    def rotate_component(self, component_id: str, clockwise: bool = True) -> None:
        """Rotate a component 90 degrees."""
        component = self.model.components.get(component_id)
        if component is None:
            return
        delta = 90 if clockwise else -90
        component.rotation = (component.rotation + delta) % 360
        self._notify('component_rotated', component)

    def update_component_value(self, component_id: str, value: str) -> None:
        """Update a component's value."""
        component = self.model.components.get(component_id)
        if component is None:
            return
        component.value = value
        self._notify('component_value_changed', component)

    def move_component(self, component_id: str,
                       position: tuple[float, float]) -> None:
        """Move a component to a new position."""
        component = self.model.components.get(component_id)
        if component is None:
            return
        component.position = position
        self._notify('component_moved', component)

    # --- Wire operations ---

    def add_wire(self, start_comp_id: str, start_term: int,
                 end_comp_id: str, end_term: int,
                 waypoints: Optional[list[tuple[float, float]]] = None) -> WireData:
        """
        Create and add a new wire connection.

        Returns:
            The newly created WireData.
        """
        wire = WireData(
            start_component_id=start_comp_id,
            start_terminal=start_term,
            end_component_id=end_comp_id,
            end_terminal=end_term,
            waypoints=waypoints or [],
        )
        self.model.add_wire(wire)
        self._notify('wire_added', wire)
        return wire

    def remove_wire(self, wire_index: int) -> None:
        """Remove a wire by index."""
        if 0 <= wire_index < len(self.model.wires):
            self.model.remove_wire(wire_index)
            self._notify('wire_removed', wire_index)

    def update_wire_waypoints(self, wire_index: int,
                              waypoints: list[tuple[float, float]]) -> None:
        """Update a wire's routing path."""
        if 0 <= wire_index < len(self.model.wires):
            wire = self.model.wires[wire_index]
            wire.waypoints = waypoints
            self._notify('wire_routed', (wire_index, wire))

    # --- Circuit operations ---

    def clear_circuit(self) -> None:
        """Clear the entire circuit."""
        self.model.clear()
        self._notify('circuit_cleared', None)

    def rebuild_nodes(self) -> None:
        """Rebuild the node graph from current wires."""
        self.model.rebuild_nodes()
        self._notify('nodes_rebuilt', None)
