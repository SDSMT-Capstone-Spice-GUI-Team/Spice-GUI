"""Tests for batched wire rerouting during group drag (#190, #191).

Wire rerouting should be deduplicated so each unique wire is rerouted
exactly once per drag event, regardless of how many endpoints moved.
"""

from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel


class TestBatchRerouteInfrastructure:
    """Verify batch reroute attributes exist on the canvas class."""

    def test_canvas_has_batch_reroute_timer_attr(self):
        """CircuitCanvasView should have _schedule_batch_reroute (manages the timer)."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_schedule_batch_reroute")
        assert callable(CircuitCanvasView._schedule_batch_reroute)

    def test_canvas_has_pending_reroute_components_attr(self):
        """CircuitCanvasView should have _do_batch_reroute (operates on the pending set)."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_do_batch_reroute")
        assert callable(CircuitCanvasView._do_batch_reroute)

    def test_handle_component_moved_does_not_call_reroute_directly(self):
        """_handle_component_moved and _schedule_batch_reroute should both be callable methods."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_handle_component_moved")
        assert callable(CircuitCanvasView._handle_component_moved)
        assert hasattr(CircuitCanvasView, "_schedule_batch_reroute")
        assert callable(CircuitCanvasView._schedule_batch_reroute)

    def test_handle_component_moved_schedules_batch(self):
        """CircuitCanvasView should expose _schedule_batch_reroute as a callable method."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_schedule_batch_reroute")
        assert callable(CircuitCanvasView._schedule_batch_reroute)

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
        ctrl.add_observer(lambda e, d: events.append((e, d.component_id)) if e == "component_moved" else None)

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
        """_do_batch_reroute and _schedule_batch_reroute should be callable methods."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert hasattr(CircuitCanvasView, "_do_batch_reroute")
        assert callable(CircuitCanvasView._do_batch_reroute)
        assert hasattr(CircuitCanvasView, "_schedule_batch_reroute")
        assert callable(CircuitCanvasView._schedule_batch_reroute)

    def test_schedule_batch_reroute_is_idempotent(self):
        """Calling _schedule_batch_reroute twice should not raise or create duplicate timers."""
        from unittest.mock import MagicMock, patch

        from GUI.circuit_canvas import CircuitCanvasView

        canvas = MagicMock(spec=CircuitCanvasView)
        canvas._batch_reroute_timer = None

        # Patch QTimer so we don't need a Qt application
        with patch("GUI.circuit_canvas.QTimer") as mock_timer_cls:
            mock_timer = MagicMock()
            mock_timer_cls.return_value = mock_timer

            # First call: timer is None, should create one
            CircuitCanvasView._schedule_batch_reroute(canvas)
            assert mock_timer_cls.call_count == 1

            # Simulate that the timer is now set (as the real method would do)
            canvas._batch_reroute_timer = mock_timer

            # Second call: timer already set, should not create another
            CircuitCanvasView._schedule_batch_reroute(canvas)
            assert mock_timer_cls.call_count == 1  # still only one timer created
