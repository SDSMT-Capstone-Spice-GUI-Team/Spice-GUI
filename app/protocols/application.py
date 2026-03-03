"""Protocol for the top-level application shell."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from controllers.circuit_controller import CircuitController
    from controllers.file_controller import FileController
    from controllers.simulation_controller import SimulationController


@runtime_checkable
class ApplicationShellProtocol(Protocol):
    """Contract for the top-level application window.

    The shell owns the three controllers and wires together the view
    protocols.  It is the single integration point — the one place
    that knows about all the pieces.

    Required attributes (set during ``__init__``):

    ============== ==========================================
    Attribute      Type
    ============== ==========================================
    circuit_ctrl   ``CircuitController``
    file_ctrl      ``FileController``
    simulation_ctrl ``SimulationController``
    ============== ==========================================

    Bootstrap pattern::

        model = CircuitModel()
        circuit_ctrl = CircuitController(model)
        file_ctrl = FileController(model, circuit_ctrl)
        simulation_ctrl = SimulationController(model, circuit_ctrl)

        canvas = MyCanvas()
        circuit_ctrl.add_observer(canvas.handle_observer_event)
    """

    @property
    def circuit_ctrl(self) -> CircuitController: ...

    @property
    def file_ctrl(self) -> FileController: ...

    @property
    def simulation_ctrl(self) -> SimulationController: ...

    def set_window_title(self, title: str) -> None:
        """Update the window title bar."""
        ...

    def show_status_message(self, message: str, timeout_ms: int = 3000) -> None:
        """Show a transient message in the status bar."""
        ...

    def set_dirty(self, dirty: bool) -> None:
        """Mark the document as having unsaved changes."""
        ...
