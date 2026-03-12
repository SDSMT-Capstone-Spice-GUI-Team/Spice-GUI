"""
Pure-function graph operations for circuit node connectivity.

These functions implement the node-graph algorithms that track which
terminals are electrically connected.  They operate on plain data
structures (lists, dicts, NodeData) with **no Qt or GUI dependency**.

CircuitModel delegates to these functions so the algorithms can be
tested and reused independently of the data-model class.
"""

from __future__ import annotations

from models.component import ComponentData
from models.node import NodeData, reset_node_counter
from models.wire import WireData

# ------------------------------------------------------------------
# Primitive helpers
# ------------------------------------------------------------------


def handle_ground_added(
    nodes: list[NodeData],
    terminal_to_node: dict[tuple[str, int], NodeData],
    ground_comp: ComponentData,
) -> None:
    """Ensure a singleton ground node exists and register *ground_comp*'s terminal."""
    terminal_key = (ground_comp.component_id, 0)

    ground_node = None
    for node in nodes:
        if node.is_ground:
            ground_node = node
            break

    if ground_node is None:
        ground_node = NodeData(is_ground=True)
        nodes.append(ground_node)

    ground_node.add_terminal(ground_comp.component_id, 0)
    terminal_to_node[terminal_key] = ground_node


def update_nodes_for_wire(
    nodes: list[NodeData],
    terminal_to_node: dict[tuple[str, int], NodeData],
    components: dict[str, ComponentData],
    wire: WireData,
    wire_index: int | None = None,
) -> None:
    """Update node connectivity when a wire is added.

    Args:
        nodes: Mutable list of all circuit nodes.
        terminal_to_node: Mutable terminal→node lookup.
        components: Read-only component map (used for ground detection).
        wire: The wire being added.
        wire_index: Explicit index in the wire list.  When *None* the
                    caller must have already appended the wire so that
                    ``len(wires) - 1`` is correct; however, since the
                    wire list is **not** passed here, supply the index
                    explicitly whenever possible.
    """
    start_terminal = (wire.start_component_id, wire.start_terminal)
    end_terminal = (wire.end_component_id, wire.end_terminal)

    start_node = terminal_to_node.get(start_terminal)
    end_node = terminal_to_node.get(end_terminal)

    start_comp = components.get(wire.start_component_id)
    end_comp = components.get(wire.end_component_id)

    if start_node is None and end_node is None:
        new_node = NodeData()
        new_node.add_terminal(*start_terminal)
        new_node.add_terminal(*end_terminal)
        if wire_index is not None:
            new_node.add_wire(wire_index)

        nodes.append(new_node)
        terminal_to_node[start_terminal] = new_node
        terminal_to_node[end_terminal] = new_node

        if (start_comp and start_comp.component_type == "Ground") or (end_comp and end_comp.component_type == "Ground"):
            new_node.set_as_ground()

    elif start_node is None and end_node is not None:
        end_node.add_terminal(*start_terminal)
        if wire_index is not None:
            end_node.add_wire(wire_index)
        terminal_to_node[start_terminal] = end_node

        if start_comp and start_comp.component_type == "Ground":
            end_node.set_as_ground()

    elif end_node is None and start_node is not None:
        start_node.add_terminal(*end_terminal)
        if wire_index is not None:
            start_node.add_wire(wire_index)
        terminal_to_node[end_terminal] = start_node

        if end_comp and end_comp.component_type == "Ground":
            start_node.set_as_ground()

    elif start_node is not None and end_node is not None and start_node != end_node:
        start_node.merge_with(end_node)
        if wire_index is not None:
            start_node.add_wire(wire_index)

        for terminal in end_node.terminals:
            terminal_to_node[terminal] = start_node

        nodes.remove(end_node)


# ------------------------------------------------------------------
# Composite operations
# ------------------------------------------------------------------


def shift_wire_indices(nodes: list[NodeData], removed_index: int) -> None:
    """Adjust every node's wire_indices after a wire at *removed_index* is deleted."""
    for node in nodes:
        new_indices: set[int] = set()
        for idx in node.wire_indices:
            if idx == removed_index:
                continue
            elif idx > removed_index:
                new_indices.add(idx - 1)
            else:
                new_indices.add(idx)
        node.wire_indices = new_indices


def rebuild_nodes_after_wire_removal(
    nodes: list[NodeData],
    terminal_to_node: dict[tuple[str, int], NodeData],
    components: dict[str, ComponentData],
    wires: list[WireData],
    affected_node: NodeData,
) -> None:
    """Incrementally rebuild the subset of nodes affected by a wire removal.

    *affected_node* is the node that contained both terminals of the
    removed wire.  It is dissolved and the relevant wires are
    reprocessed so that connectivity may split into multiple nodes.
    """
    affected_terminals = set(affected_node.terminals)
    saved_label = affected_node.custom_label

    # Remove affected node and its terminal mappings
    if affected_node in nodes:
        nodes.remove(affected_node)
    for term in affected_terminals:
        terminal_to_node.pop(term, None)

    # Collect remaining wires that touch the affected terminal set
    relevant_wires: list[int] = []
    for i, w in enumerate(wires):
        st = (w.start_component_id, w.start_terminal)
        et = (w.end_component_id, w.end_terminal)
        if st in affected_terminals or et in affected_terminals:
            relevant_wires.append(i)

    # Re-add ground terminals for the affected set
    for term in affected_terminals:
        comp = components.get(term[0])
        if comp and comp.component_type == "Ground":
            handle_ground_added(nodes, terminal_to_node, comp)

    # Reprocess relevant wires to rebuild only affected nodes
    for wire_idx in relevant_wires:
        update_nodes_for_wire(nodes, terminal_to_node, components, wires[wire_idx], wire_idx)

    # Restore custom label on rebuilt nodes
    if saved_label:
        for term in affected_terminals:
            node = terminal_to_node.get(term)
            if node and not node.custom_label:
                node.set_custom_label(saved_label)
                break


def rebuild_all_nodes(
    nodes: list[NodeData],
    terminal_to_node: dict[tuple[str, int], NodeData],
    components: dict[str, ComponentData],
    wires: list[WireData],
) -> None:
    """Clear and rebuild the entire node graph from scratch.

    Custom labels are preserved by snapshotting them (keyed by terminal)
    before clearing, then restoring them on the rebuilt nodes.
    """
    # Snapshot custom labels keyed by terminal tuple
    saved_labels: dict[tuple[str, int], str] = {}
    for node in nodes:
        if node.custom_label:
            for terminal in node.terminals:
                saved_labels[terminal] = node.custom_label

    nodes.clear()
    terminal_to_node.clear()
    reset_node_counter()

    for comp in components.values():
        if comp.component_type == "Ground":
            handle_ground_added(nodes, terminal_to_node, comp)

    # AUDIT(quality): wire_index is not passed to update_nodes_for_wire during rebuild — node.wire_indices will remain empty after a full rebuild, which may cause stale data in incremental operations that rely on wire_indices
    for wire in wires:
        update_nodes_for_wire(nodes, terminal_to_node, components, wire)

    # Restore custom labels on rebuilt nodes
    for node in nodes:
        if not node.custom_label:
            for terminal in node.terminals:
                if terminal in saved_labels:
                    node.set_custom_label(saved_labels[terminal])
                    break
