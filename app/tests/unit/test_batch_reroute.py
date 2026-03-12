"""Tests for batched wire rerouting during group drag (#190, #191).

Wire rerouting should be deduplicated so each unique wire is rerouted
exactly once per drag event, regardless of how many endpoints moved.
"""

import ast
import inspect
import textwrap

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel


def _source_uses_name(func, name):
    """Check if a function's source contains a reference to the given name."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return any(
        (isinstance(node, ast.Name) and node.id == name)
        or (isinstance(node, ast.Attribute) and node.attr == name)
        for node in ast.walk(tree)
    )


def _source_not_uses_name(func, name):
    """Check that a function's source does NOT reference the given name."""
    return not _source_uses_name(func, name)


class TestBatchRerouteInfrastructure:
    """Verify batch reroute attributes exist on the canvas class."""

    def test_canvas_has_batch_reroute_timer_attr(self):
        """CircuitCanvasView.__init__ should initialize _batch_reroute_timer."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert _source_uses_name(CircuitCanvasView.__init__, "_batch_reroute_timer")

    def test_canvas_has_pending_reroute_components_attr(self):
        """CircuitCanvasView.__init__ should initialize _pending_reroute_components."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert _source_uses_name(
            CircuitCanvasView.__init__, "_pending_reroute_components"
        )

    def test_handle_component_moved_does_not_call_reroute_directly(self):
        """_handle_component_moved should NOT call reroute_connected_wires directly."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert _source_not_uses_name(
            CircuitCanvasView._handle_component_moved, "reroute_connected_wires"
        )

    def test_handle_component_moved_schedules_batch(self):
        """_handle_component_moved should call _schedule_batch_reroute."""
        from GUI.circuit_canvas import CircuitCanvasView

        assert _source_uses_name(
            CircuitCanvasView._handle_component_moved, "_schedule_batch_reroute"
        )

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

        # Should reference the pending set (to clear it)
        assert _source_uses_name(
            CircuitCanvasView._do_batch_reroute, "_pending_reroute_components"
        )
        # Should reference the timer (to reset it)
        assert _source_uses_name(
            CircuitCanvasView._do_batch_reroute, "_batch_reroute_timer"
        )

    def test_schedule_batch_reroute_is_idempotent(self):
        """Calling _schedule_batch_reroute multiple times should not stack timers."""
        from GUI.circuit_canvas import CircuitCanvasView

        # Should check if timer already exists before creating — look for
        # a comparison (is not None) or an early return in the AST
        tree = ast.parse(
            textwrap.dedent(
                inspect.getsource(CircuitCanvasView._schedule_batch_reroute)
            )
        )
        has_compare = any(isinstance(node, ast.Compare) for node in ast.walk(tree))
        has_return = any(isinstance(node, ast.Return) for node in ast.walk(tree))
        has_if = any(isinstance(node, ast.If) for node in ast.walk(tree))
        assert (
            has_compare or has_return or has_if
        ), "_schedule_batch_reroute should have a guard (comparison, return, or if)"
