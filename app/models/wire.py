"""
WireData - Pure Python data model for circuit wires.

This module contains no Qt dependencies. Waypoints are stored as
tuples (x, y) rather than QPointF.
"""

from dataclasses import dataclass, field


@dataclass
class WireData:
    """
    Pure Python data class representing a wire connection between two component terminals.

    This class stores connection information and routing data without any Qt dependencies.
    """

    start_component_id: str
    start_terminal: int
    end_component_id: str
    end_terminal: int

    # Routing data (populated after pathfinding)
    waypoints: list[tuple[float, float]] = field(default_factory=list)
    algorithm: str = "idastar"
    runtime: float = 0.0  # Time taken to route (seconds)
    iterations: int = 0  # Pathfinding iterations

    def get_terminals(self) -> list[tuple[str, int]]:
        """
        Get both terminal identifiers for this wire.

        Returns:
            List of two (component_id, terminal_index) tuples.
        """
        return [(self.start_component_id, self.start_terminal), (self.end_component_id, self.end_terminal)]

    def connects_component(self, component_id: str) -> bool:
        """Check if this wire connects to the given component."""
        return self.start_component_id == component_id or self.end_component_id == component_id

    def connects_terminal(self, component_id: str, terminal: int) -> bool:
        """Check if this wire connects to the given terminal."""
        return (self.start_component_id == component_id and self.start_terminal == terminal) or (
            self.end_component_id == component_id and self.end_terminal == terminal
        )

    def to_dict(self) -> dict:
        """
        Serialize wire to dictionary.

        Format matches the existing JSON circuit file format for compatibility.
        Note: waypoints are NOT serialized (they are recomputed on load).
        """
        return {
            "start_comp": self.start_component_id,
            "start_term": self.start_terminal,
            "end_comp": self.end_component_id,
            "end_term": self.end_terminal,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WireData":
        """
        Deserialize wire from dictionary.

        Handles the existing JSON circuit file format.
        """
        return cls(
            start_component_id=data["start_comp"],
            start_terminal=data["start_term"],
            end_component_id=data["end_comp"],
            end_terminal=data["end_term"],
        )

    def __repr__(self) -> str:
        return (
            f"WireData({self.start_component_id}[{self.start_terminal}] -> "
            f"{self.end_component_id}[{self.end_terminal}])"
        )
