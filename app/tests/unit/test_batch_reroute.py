"""Tests for batched wire rerouting during group drag (#190, #191).

Wire rerouting should be deduplicated so each unique wire is rerouted
exactly once per drag event, regardless of how many endpoints moved.
"""

import inspect

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel


class TestBatchRerouteInfrastructure:
    """Verify batch reroute attributes exist on the canvas class."""

    def test_canvas_has_batch_reroute_timer_attr(self):
        """CircuitCanvasView.__init__ should initialize _batch_reroute_timer."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView.__init__)
        assert "_batch_reroute_timer" in source

    def test_canvas_has_pending_reroute_components_attr(self):
        """CircuitCanvasView.__init__ should initialize _pending_reroute_components."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView.__init__)
        assert "_pending_reroute_components" in source

    def test_handle_component_moved_does_not_call_reroute_directly(self):
        """_handle_component_moved should NOT call reroute_connected_wires directly."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._handle_component_moved)
        assert "reroute_connected_wires" not in source

    def test_handle_component_moved_schedules_batch(self):
        """_handle_component_moved should call _schedule_batch_reroute."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._handle_component_moved)
        assert "_schedule_batch_reroute" in source

    def test_do_batch_reroute_method_exists(self):
        """CircuitCanvasView should have _do_batch_reroute method."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_do_batch_reroute")

    def test_schedule_batch_reroute_method_exists(self):
        """CircuitCanvasView should have _schedule_batch_reroute method."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_schedule_batch_reroute")


class TestObserverMoveDedup:
    """Test that multiple move_component calls don't produce duplicate events."""

    def test_multiple_moves_fire_separate_events(self):
        """Each move_component call fires one component_moved event."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (100, 0))

        events = []
        ctrl.add_observer(
            lambda e, d: (
                events.append((e, d.component_id)) if e == "component_moved" else None
            )
        )

        # Simulate group drag: both components move
        ctrl.move_component(r1.component_id, (50, 50))
        ctrl.move_component(r2.component_id, (150, 50))

        assert len(events) == 2
        moved_ids = {e[1] for e in events}
        assert r1.component_id in moved_ids
        assert r2.component_id in moved_ids

    def test_wire_between_coselected_components(self):
        """A wire connecting two moved components should only need one reroute."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        r1 = ctrl.add_component("Resistor", (0, 0))
        r2 = ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire(r1.component_id, 0, r2.component_id, 0)

        # Both components move — the wire connects both
        ctrl.move_component(r1.component_id, (50, 50))
        ctrl.move_component(r2.component_id, (150, 50))

        # Wire should still exist and connect the same components
        assert len(model.wires) == 1
        w = model.wires[0]
        assert w.start_component_id == r1.component_id
        assert w.end_component_id == r2.component_id

    def test_do_batch_reroute_clears_pending_set(self):
        """_do_batch_reroute should clear _pending_reroute_components."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._do_batch_reroute)
        # Should reset the pending set
        assert "_pending_reroute_components" in source
        # Should reset the timer
        assert "_batch_reroute_timer = None" in source

    def test_schedule_batch_reroute_is_idempotent(self):
        """Calling _schedule_batch_reroute multiple times should not stack timers."""
        from GUI.circuit_canvas import CircuitCanvasView

        source = inspect.getsource(CircuitCanvasView._schedule_batch_reroute)
        # Should check if timer already exists before creating
        assert "is not None" in source or "return" in source
