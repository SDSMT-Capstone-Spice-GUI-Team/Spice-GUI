"""
simulation/result_history.py

Stores timestamped simulation results for history browsing and comparison.
Pure Python — no Qt dependencies.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default maximum number of results to keep in history
DEFAULT_MAX_HISTORY = 50


@dataclass
class HistoryEntry:
    """A single entry in the simulation result history."""

    timestamp: datetime
    analysis_type: str
    success: bool
    data: Any = None
    netlist: str = ""
    label: str = ""
    measurements: Optional[dict] = None

    @property
    def summary(self) -> str:
        """One-line summary for display in history lists."""
        status = "OK" if self.success else "FAIL"
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        label_part = f" ({self.label})" if self.label else ""
        return f"[{ts}] {self.analysis_type} — {status}{label_part}"


class SimulationHistory:
    """
    Manages a bounded list of simulation result snapshots.

    Entries are stored newest-first.  When *max_entries* is exceeded the
    oldest entry is silently dropped.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY):
        self._entries: list[HistoryEntry] = []
        self._max_entries = max(1, max_entries)

    # -- mutators ---------------------------------------------------------

    def add(
        self,
        analysis_type: str,
        success: bool,
        data: Any = None,
        netlist: str = "",
        label: str = "",
        measurements: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> HistoryEntry:
        """Record a new simulation result and return the entry."""
        entry = HistoryEntry(
            timestamp=timestamp or datetime.now(),
            analysis_type=analysis_type,
            success=success,
            data=data,
            netlist=netlist,
            label=label,
            measurements=measurements,
        )
        self._entries.insert(0, entry)
        if len(self._entries) > self._max_entries:
            self._entries.pop()
        return entry

    def clear(self) -> None:
        """Remove all history entries."""
        self._entries.clear()

    def remove(self, index: int) -> HistoryEntry:
        """Remove and return the entry at *index* (0 = newest)."""
        return self._entries.pop(index)

    def set_label(self, index: int, label: str) -> None:
        """Attach or update a user-supplied label for the entry at *index*."""
        self._entries[index].label = label

    # -- queries ----------------------------------------------------------

    @property
    def entries(self) -> list[HistoryEntry]:
        """All entries, newest first (read-only snapshot)."""
        return list(self._entries)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> HistoryEntry:
        return self._entries[index]

    def __bool__(self) -> bool:
        return bool(self._entries)

    def latest(self) -> Optional[HistoryEntry]:
        """Return the most recent entry, or *None* if empty."""
        return self._entries[0] if self._entries else None

    def filter_by_type(self, analysis_type: str) -> list[HistoryEntry]:
        """Return entries matching *analysis_type*."""
        return [e for e in self._entries if e.analysis_type == analysis_type]

    def successful(self) -> list[HistoryEntry]:
        """Return only successful entries."""
        return [e for e in self._entries if e.success]

    # -- comparison -------------------------------------------------------

    @staticmethod
    def compare_op_results(entry_a: HistoryEntry, entry_b: HistoryEntry) -> dict:
        """
        Compare two DC Operating Point results.

        Returns a dict mapping each node/branch to
        ``{"a": val_a, "b": val_b, "delta": val_b - val_a}``.
        Only entries whose *analysis_type* is ``"DC Operating Point"`` and
        whose *data* dicts contain ``node_voltages`` are supported.

        Raises *ValueError* if either entry is not a compatible OP result.
        """
        for tag, entry in [("a", entry_a), ("b", entry_b)]:
            if not isinstance(entry.data, dict):
                raise ValueError(f"Entry {tag} does not contain dict data")

        merged: dict[str, dict] = {}

        # Helper to collect values from one entry
        def _collect(entry: HistoryEntry, key: str) -> None:
            if not isinstance(entry.data, dict):
                return
            for section in ("node_voltages", "branch_currents"):
                mapping = entry.data.get(section, {})
                for name, value in mapping.items():
                    full = f"{section}:{name}"
                    merged.setdefault(full, {"a": None, "b": None})[key] = value

        _collect(entry_a, "a")
        _collect(entry_b, "b")

        for info in merged.values():
            a_val = info["a"]
            b_val = info["b"]
            if a_val is not None and b_val is not None:
                try:
                    info["delta"] = float(b_val) - float(a_val)
                except (TypeError, ValueError):
                    info["delta"] = None
            else:
                info["delta"] = None

        return merged

    @staticmethod
    def compare_dc_sweep_results(entry_a: HistoryEntry, entry_b: HistoryEntry) -> dict:
        """
        Compare two DC Sweep results.

        Returns metadata about shared headers and data-length match.
        """
        for tag, entry in [("a", entry_a), ("b", entry_b)]:
            if not isinstance(entry.data, dict) or "headers" not in entry.data:
                raise ValueError(f"Entry {tag} does not contain DC sweep data")

        headers_a = set(entry_a.data["headers"])
        headers_b = set(entry_b.data["headers"])
        shared = sorted(headers_a & headers_b)
        only_a = sorted(headers_a - headers_b)
        only_b = sorted(headers_b - headers_a)

        len_a = len(entry_a.data.get("data", []))
        len_b = len(entry_b.data.get("data", []))

        return {
            "shared_headers": shared,
            "only_in_a": only_a,
            "only_in_b": only_b,
            "rows_a": len_a,
            "rows_b": len_b,
            "same_length": len_a == len_b,
        }
