"""
CircuitController - Orchestrates component and wire CRUD operations.

This module contains no Qt dependencies. It manages the CircuitModel
and notifies views of changes through an observer pattern.
"""

import logging
from typing import Callable, Any, Optional
from models.circuit import CircuitModel
from models.clipboard import ClipboardData
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
        self._clipboard = ClipboardData()

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

    # --- Clipboard operations ---

    def copy_components(self, component_ids: list[str]) -> bool:
        """
        Copy selected components and their internal wires to the clipboard.

        Only wires where BOTH endpoints are in the selection are copied.
        Returns True if anything was copied.
        """
        if not component_ids:
            return False

        selected_set = set(component_ids)

        comp_dicts = []
        for comp_id in component_ids:
            comp = self.model.components.get(comp_id)
            if comp is not None:
                comp_dicts.append(comp.to_dict())

        if not comp_dicts:
            return False

        wire_dicts = []
        for wire in self.model.wires:
            if (wire.start_component_id in selected_set
                    and wire.end_component_id in selected_set):
                wire_dicts.append(wire.to_dict())

        self._clipboard = ClipboardData(
            components=comp_dicts,
            wires=wire_dicts,
            paste_count=0,
        )
        return True

    def paste_components(
        self,
        offset: tuple[float, float] = (40.0, 40.0),
    ) -> tuple[list[ComponentData], list[WireData]]:
        """
        Paste clipboard contents into the circuit with new unique IDs.

        Each paste increments the paste_count so successive pastes
        are offset further from the original position.

        Returns:
            Tuple of (new_components, new_wires) that were added.
        """
        if self._clipboard.is_empty():
            return ([], [])

        self._clipboard.paste_count += 1
        multiplier = self._clipboard.paste_count
        dx = offset[0] * multiplier
        dy = offset[1] * multiplier

        id_map: dict[str, str] = {}
        new_components: list[ComponentData] = []

        for comp_dict in self._clipboard.components:
            comp_data = ComponentData.from_dict(comp_dict)

            symbol = SPICE_SYMBOLS.get(comp_data.component_type, 'X')
            count = self.model.component_counter.get(symbol, 0) + 1
            self.model.component_counter[symbol] = count
            new_id = f"{symbol}{count}"

            old_id = comp_data.component_id
            id_map[old_id] = new_id

            new_comp = ComponentData(
                component_id=new_id,
                component_type=comp_data.component_type,
                value=comp_data.value,
                position=(comp_data.position[0] + dx,
                          comp_data.position[1] + dy),
                rotation=comp_data.rotation,
                waveform_type=comp_data.waveform_type,
                waveform_params=(comp_data.waveform_params.copy()
                                 if comp_data.waveform_params else None),
            )
            self.model.add_component(new_comp)
            self._notify('component_added', new_comp)
            new_components.append(new_comp)

        new_wires: list[WireData] = []
        for wire_dict in self._clipboard.wires:
            new_start = id_map.get(wire_dict['start_comp'])
            new_end = id_map.get(wire_dict['end_comp'])

            if new_start is None or new_end is None:
                continue

            wire = WireData(
                start_component_id=new_start,
                start_terminal=wire_dict['start_term'],
                end_component_id=new_end,
                end_terminal=wire_dict['end_term'],
            )
            self.model.add_wire(wire)
            self._notify('wire_added', wire)
            new_wires.append(wire)

        return (new_components, new_wires)

    def cut_components(self, component_ids: list[str]) -> bool:
        """Cut selected components: copy to clipboard, then delete."""
        copied = self.copy_components(component_ids)
        if copied:
            for comp_id in list(component_ids):
                if comp_id in self.model.components:
                    self.remove_component(comp_id)
        return copied

    def has_clipboard_content(self) -> bool:
        """Return whether the clipboard has content to paste."""
        return not self._clipboard.is_empty()
