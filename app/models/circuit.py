"""
CircuitModel - Central data store for circuit state.

This module contains no Qt dependencies. It holds all circuit data
(components, wires, nodes) and provides node graph operations.
"""

from dataclasses import dataclass, field

from .component import ComponentData
from .node import NodeData, reset_node_counter
from .wire import WireData


@dataclass
class CircuitModel:
    """
    Central data store holding all circuit state.

    Manages components, wires, and the node graph that tracks
    electrical connectivity between terminals.
    """

    components: dict[str, ComponentData] = field(default_factory=dict)
    wires: list[WireData] = field(default_factory=list)
    nodes: list[NodeData] = field(default_factory=list)
    terminal_to_node: dict[tuple[str, int], NodeData] = field(default_factory=dict)
    component_counter: dict[str, int] = field(default_factory=dict)

    # Analysis configuration
    analysis_type: str = "DC Operating Point"
    analysis_params: dict = field(default_factory=dict)

    # --- Component operations ---

    def add_component(self, component: ComponentData) -> None:
        """Add a component to the circuit."""
        self.components[component.component_id] = component
        if component.component_type == "Ground":
            self._handle_ground_added(component)

    def remove_component(self, component_id: str) -> list[int]:
        """
        Remove a component and return indices of connected wires to remove.

        The caller is responsible for calling remove_wire() for each returned
        index (in reverse order to avoid index shifts).
        """
        if component_id not in self.components:
            return []

        # Find wires connected to this component
        wire_indices = [i for i, wire in enumerate(self.wires) if wire.connects_component(component_id)]

        del self.components[component_id]
        return wire_indices

    # --- Wire operations ---

    def add_wire(self, wire: WireData) -> None:
        """Add a wire and update the node graph."""
        self.wires.append(wire)
        self._update_nodes_for_wire(wire)

    def remove_wire(self, wire_index: int) -> None:
        """Remove a wire by index and rebuild the node graph."""
        if 0 <= wire_index < len(self.wires):
            del self.wires[wire_index]
            self.rebuild_nodes()

    # --- Node graph operations ---

    def _handle_ground_added(self, ground_comp: ComponentData) -> None:
        """Handle adding a ground component to the node graph."""
        terminal_key = (ground_comp.component_id, 0)

        ground_node = None
        for node in self.nodes:
            if node.is_ground:
                ground_node = node
                break

        if ground_node is None:
            ground_node = NodeData(is_ground=True)
            self.nodes.append(ground_node)

        ground_node.add_terminal(ground_comp.component_id, 0)
        self.terminal_to_node[terminal_key] = ground_node

    def _update_nodes_for_wire(self, wire: WireData) -> None:
        """Update node connectivity when a wire is added."""
        start_terminal = (wire.start_component_id, wire.start_terminal)
        end_terminal = (wire.end_component_id, wire.end_terminal)

        start_node = self.terminal_to_node.get(start_terminal)
        end_node = self.terminal_to_node.get(end_terminal)

        start_comp = self.components.get(wire.start_component_id)
        end_comp = self.components.get(wire.end_component_id)

        if start_node is None and end_node is None:
            new_node = NodeData()
            new_node.add_terminal(*start_terminal)
            new_node.add_terminal(*end_terminal)
            new_node.add_wire(len(self.wires) - 1)

            self.nodes.append(new_node)
            self.terminal_to_node[start_terminal] = new_node
            self.terminal_to_node[end_terminal] = new_node

            if (start_comp and start_comp.component_type == "Ground") or (
                end_comp and end_comp.component_type == "Ground"
            ):
                new_node.set_as_ground()

        elif start_node is None and end_node is not None:
            end_node.add_terminal(*start_terminal)
            end_node.add_wire(len(self.wires) - 1)
            self.terminal_to_node[start_terminal] = end_node

            if start_comp and start_comp.component_type == "Ground":
                end_node.set_as_ground()

        elif end_node is None and start_node is not None:
            start_node.add_terminal(*end_terminal)
            start_node.add_wire(len(self.wires) - 1)
            self.terminal_to_node[end_terminal] = start_node

            if end_comp and end_comp.component_type == "Ground":
                start_node.set_as_ground()

        elif start_node is not None and end_node is not None and start_node != end_node:
            start_node.merge_with(end_node)
            start_node.add_wire(len(self.wires) - 1)

            for terminal in end_node.terminals:
                self.terminal_to_node[terminal] = start_node

            self.nodes.remove(end_node)

    def rebuild_nodes(self) -> None:
        """Rebuild all nodes from scratch based on current wires."""
        self.nodes.clear()
        self.terminal_to_node.clear()
        reset_node_counter()

        for comp in self.components.values():
            if comp.component_type == "Ground":
                self._handle_ground_added(comp)

        for wire in self.wires:
            self._update_nodes_for_wire(wire)

    # --- Circuit operations ---

    def clear(self) -> None:
        """Clear all circuit data."""
        self.components.clear()
        self.wires.clear()
        self.nodes.clear()
        self.terminal_to_node.clear()
        self.component_counter.clear()
        self.analysis_type = "DC Operating Point"
        self.analysis_params = {}

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize circuit to dictionary (matches existing JSON format)."""
        data = {
            "components": [c.to_dict() for c in self.components.values()],
            "wires": [w.to_dict() for w in self.wires],
            "counters": self.component_counter.copy(),
        }
        if self.analysis_type != "DC Operating Point" or self.analysis_params:
            data["analysis_type"] = self.analysis_type
            data["analysis_params"] = self.analysis_params.copy()

        # Persist custom net names (keyed by a representative terminal)
        net_names = {}
        for node in self.nodes:
            if node.custom_label and node.terminals:
                # Use the first terminal as the key (sorted for determinism)
                rep = sorted(node.terminals)[0]
                net_names[f"{rep[0]}:{rep[1]}"] = node.custom_label
        if net_names:
            data["net_names"] = net_names

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitModel":
        """
        Deserialize circuit from dictionary.

        Rebuilds the node graph after loading components and wires.
        """
        model = cls()
        model.component_counter = data.get("counters", {}).copy()
        model.analysis_type = data.get("analysis_type", "DC Operating Point")
        model.analysis_params = data.get("analysis_params", {}).copy()

        for comp_data in data.get("components", []):
            component = ComponentData.from_dict(comp_data)
            model.components[component.component_id] = component

        for wire_data in data.get("wires", []):
            wire = WireData.from_dict(wire_data)
            model.wires.append(wire)

        model.rebuild_nodes()

        # Restore custom net names
        for key, label in data.get("net_names", {}).items():
            comp_id, term_idx_str = key.split(":", 1)
            terminal_key = (comp_id, int(term_idx_str))
            node = model.terminal_to_node.get(terminal_key)
            if node:
                node.set_custom_label(label)

        return model
