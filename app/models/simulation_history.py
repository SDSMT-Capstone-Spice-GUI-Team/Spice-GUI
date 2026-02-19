"""
SimulationHistoryManager - Stores recent simulation results for comparison.

This module contains no Qt dependencies. It manages a bounded list of
simulation snapshots that can be overlaid in the waveform viewer.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class SimulationSnapshot:
    """A single stored simulation result.

    Attributes:
        timestamp: When the simulation was run.
        label: User-provided or auto-generated description.
        analysis_type: The type of analysis (e.g. "Transient", "DC Sweep").
        data: Parsed result data (same format as SimulationResult.data).
        netlist: The netlist used for this simulation.
        pinned: If True, this snapshot is protected from eviction.
        component_hash: Hash of circuit structure for detecting structural changes.
    """

    timestamp: datetime
    label: str
    analysis_type: str
    data: Any
    netlist: str = ""
    pinned: bool = False
    component_hash: str = ""

    def to_summary(self) -> dict:
        """Return a summary dict suitable for display in the UI."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "label": self.label,
            "analysis_type": self.analysis_type,
            "pinned": self.pinned,
        }


class SimulationHistoryManager:
    """Manages a bounded collection of simulation result snapshots.

    Stores the last N results so users can compare before/after changes.
    History clears on structural circuit changes (add/remove components)
    but persists across value-only changes. Pinned results survive clearing.

    Args:
        max_size: Maximum number of snapshots to retain (default 5).
    """

    def __init__(self, max_size: int = 5):
        self._max_size = max_size
        self._snapshots: deque[SimulationSnapshot] = deque()

    @property
    def max_size(self) -> int:
        return self._max_size

    @max_size.setter
    def max_size(self, value: int) -> None:
        if value < 1:
            raise ValueError("max_size must be at least 1")
        self._max_size = value
        self._evict()

    def add(
        self,
        analysis_type: str,
        data: Any,
        netlist: str = "",
        label: Optional[str] = None,
        component_hash: str = "",
    ) -> SimulationSnapshot:
        """Add a simulation result to history.

        If the history is full, the oldest unpinned snapshot is evicted.

        Args:
            analysis_type: Analysis type string.
            data: Parsed result data.
            netlist: The netlist used.
            label: Optional description. Auto-generated from timestamp if None.
            component_hash: Hash of circuit structure.

        Returns:
            The created SimulationSnapshot.
        """
        now = datetime.now()
        if label is None:
            label = now.strftime("Run %H:%M:%S")

        snapshot = SimulationSnapshot(
            timestamp=now,
            label=label,
            analysis_type=analysis_type,
            data=data,
            netlist=netlist,
            component_hash=component_hash,
        )
        self._snapshots.append(snapshot)
        self._evict()
        return snapshot

    def get_all(self) -> list[SimulationSnapshot]:
        """Return all snapshots in chronological order (oldest first)."""
        return list(self._snapshots)

    def get_latest(self) -> Optional[SimulationSnapshot]:
        """Return the most recent snapshot, or None if empty."""
        return self._snapshots[-1] if self._snapshots else None

    def get_by_index(self, index: int) -> SimulationSnapshot:
        """Return a snapshot by index (0 = oldest).

        Raises:
            IndexError: If index is out of range.
        """
        return self._snapshots[index]

    def count(self) -> int:
        """Return the number of stored snapshots."""
        return len(self._snapshots)

    def pin(self, index: int) -> None:
        """Pin a snapshot to prevent eviction.

        Raises:
            IndexError: If index is out of range.
        """
        self._snapshots[index].pinned = True

    def unpin(self, index: int) -> None:
        """Unpin a snapshot, allowing eviction.

        Raises:
            IndexError: If index is out of range.
        """
        self._snapshots[index].pinned = False

    def remove(self, index: int) -> SimulationSnapshot:
        """Remove a snapshot by index.

        Raises:
            IndexError: If index is out of range.
        """
        snapshot = self._snapshots[index]
        del self._snapshots[index]
        return snapshot

    def clear(self, keep_pinned: bool = True) -> None:
        """Remove all snapshots.

        Args:
            keep_pinned: If True (default), pinned snapshots are preserved.
        """
        if keep_pinned:
            pinned = [s for s in self._snapshots if s.pinned]
            self._snapshots.clear()
            self._snapshots.extend(pinned)
        else:
            self._snapshots.clear()

    def clear_on_structural_change(self, new_component_hash: str) -> bool:
        """Clear non-pinned history if circuit structure has changed.

        Compares the new component hash to the most recent snapshot's hash.
        If they differ, non-pinned snapshots are removed.

        Args:
            new_component_hash: Hash of the current circuit structure.

        Returns:
            True if history was cleared, False if unchanged.
        """
        latest = self.get_latest()
        if latest is None:
            return False
        if latest.component_hash and latest.component_hash != new_component_hash:
            self.clear(keep_pinned=True)
            return True
        return False

    def get_summaries(self) -> list[dict]:
        """Return summary dicts for all snapshots (for UI display)."""
        return [s.to_summary() for s in self._snapshots]

    def _evict(self) -> None:
        """Remove oldest unpinned snapshots until within max_size."""
        while len(self._snapshots) > self._max_size:
            # Find oldest unpinned snapshot
            evicted = False
            for i, s in enumerate(self._snapshots):
                if not s.pinned:
                    del self._snapshots[i]
                    evicted = True
                    break
            if not evicted:
                # All remaining snapshots are pinned; allow over-limit
                break
