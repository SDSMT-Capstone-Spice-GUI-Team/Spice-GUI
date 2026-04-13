"""
CircuitModel - Central data store for circuit state.

This module contains no Qt dependencies. It holds all circuit data
(components, wires, nodes) and provides node graph operations.
"""

import logging
from dataclasses import dataclass, field

from algorithms.graph_ops import (
    handle_ground_added,
    rebuild_all_nodes,
    rebuild_nodes_after_wire_removal,
    shift_wire_indices,
    update_nodes_for_wire,
)

from .annotation import AnnotationData
from .component import ComponentData
from .node import NodeData
from .wire import WireData

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


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

    annotations: list[AnnotationData] = field(default_factory=list)

    # File-level recommended components (advisory list for palette)
    recommended_components: list[str] = field(default_factory=list)

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
        """Remove a wire by index and incrementally update affected nodes."""
        if not (0 <= wire_index < len(self.wires)):
            return

        wire = self.wires[wire_index]
        start_terminal = (wire.start_component_id, wire.start_terminal)
        end_terminal = (wire.end_component_id, wire.end_terminal)

        # Find the affected node (both terminals should be in the same node)
        affected_node = self.terminal_to_node.get(start_terminal) or self.terminal_to_node.get(end_terminal)

        del self.wires[wire_index]

        shift_wire_indices(self.nodes, wire_index)

        if affected_node is not None:
            rebuild_nodes_after_wire_removal(
                self.nodes,
                self.terminal_to_node,
                self.components,
                self.wires,
                affected_node,
            )

    # --- Node graph operations (delegated to algorithms.graph_ops) ---

    def _handle_ground_added(self, ground_comp: ComponentData) -> None:
        """Handle adding a ground component to the node graph."""
        handle_ground_added(self.nodes, self.terminal_to_node, ground_comp)

    def _update_nodes_for_wire(self, wire: WireData, wire_index: int | None = None) -> None:
        """Update node connectivity when a wire is added."""
        if wire_index is None:
            wire_index = len(self.wires) - 1
        update_nodes_for_wire(self.nodes, self.terminal_to_node, self.components, wire, wire_index)

    def rebuild_nodes(self) -> None:
        """Rebuild all nodes from scratch based on current wires."""
        rebuild_all_nodes(self.nodes, self.terminal_to_node, self.components, self.wires)

    # --- Circuit operations ---

    def clear(self) -> None:
        """Clear all circuit data."""
        self.components.clear()
        self.wires.clear()
        self.nodes.clear()
        self.terminal_to_node.clear()
        self.component_counter.clear()
        self.annotations.clear()
        self.recommended_components.clear()
        self.analysis_type = "DC Operating Point"
        self.analysis_params = {}

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize circuit to dictionary (matches existing JSON format)."""
        data = {
            "schema_version": SCHEMA_VERSION,
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

        if self.annotations:
            data["annotations"] = [a.to_dict() for a in self.annotations]

        if self.recommended_components:
            data["recommended_components"] = list(self.recommended_components)

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitModel":
        """
        Deserialize circuit from dictionary.

        Rebuilds the node graph after loading components and wires.
        Corrupt individual components, wires, or annotations are
        skipped with a warning rather than crashing the entire load.
        """
        model = cls()
        model.component_counter = data.get("counters", {}).copy()
        model.analysis_type = data.get("analysis_type", "DC Operating Point")
        model.analysis_params = data.get("analysis_params", {}).copy()

        for i, comp_data in enumerate(data.get("components", [])):
            try:
                component = ComponentData.from_dict(comp_data)
                model.components[component.component_id] = component
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Skipping corrupt component #%d: %s", i + 1, exc)

        for i, wire_data in enumerate(data.get("wires", [])):
            try:
                wire = WireData.from_dict(wire_data)
                # Skip wires that reference components not in the model
                if wire.start_component_id not in model.components or wire.end_component_id not in model.components:
                    logger.warning(
                        "Skipping wire #%d: references missing component(s)",
                        i + 1,
                    )
                    continue
                model.wires.append(wire)
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Skipping corrupt wire #%d: %s", i + 1, exc)

        model.rebuild_nodes()

        # Restore custom net names
        for key, label in data.get("net_names", {}).items():
            try:
                comp_id, term_idx_str = key.split(":", 1)
                terminal_key = (comp_id, int(term_idx_str))
                node = model.terminal_to_node.get(terminal_key)
                if node:
                    node.set_custom_label(label)
            except (ValueError, TypeError) as exc:
                logger.warning("Skipping corrupt net name %r: %s", key, exc)

        for i, ann_data in enumerate(data.get("annotations", [])):
            try:
                model.annotations.append(AnnotationData.from_dict(ann_data))
            except (ValueError, TypeError, AttributeError) as exc:
                logger.warning("Skipping corrupt annotation #%d: %s", i + 1, exc)

        model.recommended_components = list(data.get("recommended_components", []))

        return model
