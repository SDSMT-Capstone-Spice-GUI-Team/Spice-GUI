"""
View-layer protocols for Spice-GUI.

These ``typing.Protocol`` classes define the contracts between the
controller/model layer and any GUI implementation.  The existing
PyQt6 GUI satisfies these protocols implicitly.  A new GUI must
implement them explicitly.

Usage::

    from protocols import CircuitCanvasProtocol, DialogProvider

    class MyCanvas(CircuitCanvasProtocol):
        def handle_observer_event(self, event, data):
            ...
"""

from .application import ApplicationShellProtocol as ApplicationShellProtocol
from .canvas import CircuitCanvasProtocol as CircuitCanvasProtocol
from .dialogs import DialogProvider as DialogProvider
from .dialogs import ProgressHandle as ProgressHandle
from .events import EVENT_PAYLOADS as EVENT_PAYLOADS
from .events import ObserverEvent as ObserverEvent
from .palette import ComponentPaletteProtocol as ComponentPaletteProtocol
from .properties import PropertiesPanelProtocol as PropertiesPanelProtocol
from .results import ResultsDisplayProtocol as ResultsDisplayProtocol
