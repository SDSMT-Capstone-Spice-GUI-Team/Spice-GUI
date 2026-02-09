"""
NodeData - Pure Python data model for electrical nodes.

This module contains no Qt dependencies. An electrical node represents
a set of component terminals that are electrically connected (share the
same voltage).
"""

from dataclasses import dataclass, field
from typing import Optional


# Module-level counter for generating unique node labels
_node_counter = 0


def reset_node_counter():
    """Reset the node label counter. Call when starting a new circuit."""
    global _node_counter
    _node_counter = 0


def _generate_label(index: int) -> str:
    """
    Generate label like nodeA, nodeB, ..., nodeZ, nodeAA, nodeAB...

    Args:
        index: Zero-based index for the node.

    Returns:
        A string label like "nodeA", "nodeB", etc.
    """
    if index < 26:
        return "node" + chr(ord('A') + index)
    else:
        # For more than 26 nodes, use AA, AB, AC...
        first = (index // 26) - 1
        second = index % 26
        return "node" + chr(ord('A') + first) + chr(ord('A') + second)


@dataclass
class NodeData:
    """
    Pure Python data class representing an electrical node.

    A node is a set of component terminals that are electrically connected.
    This is the fundamental unit of circuit topology for netlist generation.
    """
    # Set of (component_id, terminal_index) tuples in this node
    terminals: set[tuple[str, int]] = field(default_factory=set)

    # Set of wire indices (into the circuit's wire list) connecting terminals in this node
    wire_indices: set[int] = field(default_factory=set)

    # Whether this is the ground node (SPICE node 0)
    is_ground: bool = False

    # User-assigned label (takes precedence over auto_label)
    custom_label: Optional[str] = None

    # Auto-generated label (nodeA, nodeB, etc., or "0" for ground)
    auto_label: str = ""

    def __post_init__(self):
        """Generate auto_label if not provided."""
        if not self.auto_label:
            if self.is_ground:
                self.auto_label = "0"
            else:
                global _node_counter
                self.auto_label = _generate_label(_node_counter)
                _node_counter += 1

    def get_label(self) -> str:
        """
        Get the display label for this node.

        Returns:
            The custom label if set, otherwise the auto-generated label.
            For ground nodes with a custom label, appends "(ground)".
        """
        if self.custom_label:
            if self.is_ground:
                return f"{self.custom_label} (ground)"
            return self.custom_label
        return self.auto_label

    def set_custom_label(self, label: str) -> None:
        """Set a custom label for this node."""
        self.custom_label = label

    def add_terminal(self, component_id: str, terminal_index: int) -> None:
        """Add a terminal to this node."""
        self.terminals.add((component_id, terminal_index))

    def remove_terminal(self, component_id: str, terminal_index: int) -> None:
        """Remove a terminal from this node."""
        self.terminals.discard((component_id, terminal_index))

    def add_wire(self, wire_index: int) -> None:
        """Add a wire index to this node."""
        self.wire_indices.add(wire_index)

    def remove_wire(self, wire_index: int) -> None:
        """Remove a wire index from this node."""
        self.wire_indices.discard(wire_index)

    def merge_with(self, other: 'NodeData') -> None:
        """
        Merge another node into this one.

        All terminals and wires from the other node are added to this node.
        If the other node is ground, this node becomes ground.
        """
        self.terminals.update(other.terminals)
        self.wire_indices.update(other.wire_indices)

        # Handle ground merging - ground status propagates
        if other.is_ground:
            self.is_ground = True
            if not self.custom_label:
                self.auto_label = "0"

    def set_as_ground(self) -> None:
        """Mark this node as ground (node 0)."""
        self.is_ground = True
        if not self.custom_label:
            self.auto_label = "0"

    def get_position(self, components: dict) -> Optional[tuple[float, float]]:
        """
        Get a representative position for label placement (average of all terminals).

        Args:
            components: Dict mapping component_id to ComponentData objects.

        Returns:
            Average (x, y) position of all terminals, or None if no terminals.
        """
        if not self.terminals:
            return None

        positions = []
        for comp_id, term_idx in self.terminals:
            if comp_id in components:
                comp = components[comp_id]
                # Get terminal positions from ComponentData
                term_positions = comp.get_terminal_positions()
                if term_idx < len(term_positions):
                    positions.append(term_positions[term_idx])

        if not positions:
            return None

        # Return average position
        avg_x = sum(p[0] for p in positions) / len(positions)
        avg_y = sum(p[1] for p in positions) / len(positions)
        return (avg_x, avg_y)

    def is_empty(self) -> bool:
        """Check if this node has no terminals."""
        return len(self.terminals) == 0

    def __repr__(self) -> str:
        label = self.get_label()
        return f"NodeData({label}, terminals={len(self.terminals)}, wires={len(self.wire_indices)})"
