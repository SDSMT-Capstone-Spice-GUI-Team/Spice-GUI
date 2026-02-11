"""Tests for wire rerouting deduplication (#189).

Verifies that component drags trigger wire rerouting through exactly one
path (the observer/controller path) instead of two (observer + timer).
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel


class TestObserverRerouteOnMove:
    """The observer path should fire component_moved on move_component."""

    def test_move_component_fires_event(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        events = []
        ctrl.add_observer(lambda e, d: events.append(e))

        ctrl.move_component(comp.component_id, (100, 100))

        assert "component_moved" in events

    def test_move_component_updates_model_position(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        ctrl.move_component(comp.component_id, (200, 300))

        assert model.components[comp.component_id].position == (200, 300)

    def test_move_component_passes_data_to_observer(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0, 0))

        data_received = []
        ctrl.add_observer(lambda e, d: data_received.append(d) if e == "component_moved" else None)

        ctrl.move_component(comp.component_id, (50, 75))

        assert len(data_received) == 1
        assert data_received[0].position == (50, 75)


class TestTimerPathRemoved:
    """The old timer-based wire reroute path should not exist."""

    def test_no_schedule_wire_update_method(self):
        """ComponentGraphicsItem should not have schedule_wire_update."""
        from GUI.component_item import ComponentGraphicsItem

        assert not hasattr(ComponentGraphicsItem, "schedule_wire_update")

    def test_no_update_wires_after_drag_method(self):
        """ComponentGraphicsItem should not have update_wires_after_drag."""
        from GUI.component_item import ComponentGraphicsItem

        assert not hasattr(ComponentGraphicsItem, "update_wires_after_drag")

    def test_no_wire_update_timer_attribute(self):
        """ComponentGraphicsItem should not have self.update_timer in init."""
        import inspect

        from GUI.component_item import ComponentGraphicsItem

        source = inspect.getsource(ComponentGraphicsItem.__init__)
        assert "self.update_timer" not in source

    def test_no_last_position_attribute(self):
        """ComponentGraphicsItem should not reference last_position in init."""
        import inspect

        from GUI.component_item import ComponentGraphicsItem

        source = inspect.getsource(ComponentGraphicsItem.__init__)
        assert "last_position" not in source


class TestSingleReroutePath:
    """Verify only one code path exists from drag to reroute."""

    def test_itemchange_does_not_call_schedule_wire_update(self):
        """itemChange source should not reference schedule_wire_update."""
        import inspect

        from GUI.component_item import ComponentGraphicsItem

        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        assert "schedule_wire_update" not in source

    def test_itemchange_schedules_controller_update(self):
        """itemChange source should still schedule controller updates."""
        import inspect

        from GUI.component_item import ComponentGraphicsItem

        source = inspect.getsource(ComponentGraphicsItem.itemChange)
        assert "_schedule_controller_update" in source
