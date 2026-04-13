"""
NodeData - Pure Python data model for electrical nodes.

This module contains no Qt dependencies. An electrical node represents
a set of component terminals that are electrically connected (share the
same voltage).
"""

from dataclasses import dataclass, field
from typing import Optional


class NodeLabelGenerator:
    """Encapsulates the counter used to generate unique node labels.

    Each call to :meth:`next_label` returns labels in sequence:
    ``nodeA``, ``nodeB``, ... ``nodeZ``, ``nodeAA``, ``nodeAB``, ...

    Call :meth:`reset` when starting a new circuit.
    """

    def __init__(self) -> None:
        self._counter: int = 0

    def reset(self) -> None:
        """Reset the counter to zero."""
        self._counter = 0

    def next_label(self) -> str:
        """Return the next label and advance the counter."""
        label = _generate_label(self._counter)
        self._counter += 1
        return label


def _generate_label(index: int) -> str:
    """
    Generate label like nodeA, nodeB, ..., nodeZ, nodeAA, nodeAB, ..., nodeZZ, nodeAAA, ...

    Uses a bijective base-26 encoding so every non-negative index maps to a
    unique sequence of uppercase letters (A=0 .. Z=25, AA=26 .. AZ=51, ...).

    Args:
        index: Zero-based index for the node.

    Returns:
        A string label like "nodeA", "nodeB", etc.
    """
    chars: list[str] = []
    n = index
    while True:
        chars.append(chr(ord("A") + n % 26))
        n = n // 26 - 1
        if n < 0:
            break
    return "node" + "".join(reversed(chars))


# Default module-level generator used by NodeData.__post_init__
# Lazily initialized on first use to avoid module-level mutable state.
_default_generator: "NodeLabelGenerator | None" = None


def _get_default_generator() -> NodeLabelGenerator:
    """Return the shared NodeLabelGenerator, creating it on first call."""
    global _default_generator
    if _default_generator is None:
        _default_generator = NodeLabelGenerator()
    return _default_generator


def reset_node_counter() -> None:
    """Reset the node label counter. Call when starting a new circuit."""
    _get_default_generator().reset()


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
                self.auto_label = _get_default_generator().next_label()

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

    def set_custom_label(self, label: Optional[str]) -> None:
        """Set a custom label for this node, or None to clear it."""
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

    def merge_with(self, other: "NodeData") -> None:
        """
        Merge another node into this one.

        All terminals and wires from the other node are added to this node.
        If the other node is ground, this node becomes ground.
        Custom labels are preserved: keep self's label, or adopt other's if self has none.
        """
        self.terminals.update(other.terminals)
        self.wire_indices.update(other.wire_indices)

        # Preserve custom label from other node if self has none
        if other.custom_label and not self.custom_label:
            self.custom_label = other.custom_label

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

    def get_position(
        self,
        terminal_positions: dict[tuple[str, int], tuple[float, float]],
    ) -> Optional[tuple[float, float]]:
        """
        Get a representative position for label placement (average of all terminals).

        Args:
            terminal_positions: Mapping of ``(component_id, terminal_index)``
                to ``(x, y)`` world-coordinate positions.  Callers are
                responsible for computing these from their own layer
                (e.g. from ComponentData or from the GUI scene).

        Returns:
            Average (x, y) position of all terminals, or None if no terminals
            have a known position.
        """
        if not self.terminals:
            return None

        positions = [terminal_positions[t] for t in self.terminals if t in terminal_positions]

        if not positions:
            return None

        avg_x = sum(p[0] for p in positions) / len(positions)
        avg_y = sum(p[1] for p in positions) / len(positions)
        return (avg_x, avg_y)

    def is_empty(self) -> bool:
        """Check if this node has no terminals."""
        return len(self.terminals) == 0

    def __repr__(self) -> str:
        label = self.get_label()
        return f"NodeData({label}, terminals={len(self.terminals)}, wires={len(self.wire_indices)})"
