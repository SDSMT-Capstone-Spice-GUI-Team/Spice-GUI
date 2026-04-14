"""Protocol for simulation results display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from controllers.simulation_controller import SimulationResult


@runtime_checkable
class ResultsDisplayProtocol(Protocol):
    """Contract for displaying simulation results.

    The shell calls these methods after running a simulation.  Different
    analysis types produce different result formats; the implementation
    should dispatch on ``result.analysis_type``.
    """

    def display_simulation_result(self, result: SimulationResult) -> None:
        """Display a complete simulation result.

        Dispatch based on ``result.analysis_type`` to show the
        appropriate visualisation (table, plot, etc.).
        """
        ...

    def display_text(self, text: str) -> None:
        """Display plain text (netlist, error messages, etc.)."""
        ...

    def set_netlist_preview(self, netlist: str) -> None:
        """Update the netlist preview tab."""
        ...

    def clear(self) -> None:
        """Clear all displayed results."""
        ...

    def set_export_enabled(self, enabled: bool) -> None:
        """Enable or disable export actions (CSV, Excel, Markdown)."""
        ...
