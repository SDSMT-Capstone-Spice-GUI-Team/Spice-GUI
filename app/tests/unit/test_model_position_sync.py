"""Tests for immediate model position sync during drag (issue #192).

Model positions should be updated synchronously during drag (lightweight
attribute assignment), while observer notifications (expensive wire rerouting)
are debounced.
"""

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel
from models.component import ComponentData


class TestImmediateModelSync:
    """Test that model positions are available immediately after update."""

    def test_model_position_updated_directly(self):
        """Direct attribute assignment on ComponentData updates position."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Simulate what _schedule_controller_update now does:
        # direct attribute assignment on the model component
        model.components[comp_id].position = (100, 200)

        assert model.components[comp_id].position == (100, 200)

    def test_model_position_readable_mid_drag(self):
        """Model position should be accurate after direct sync (no debounce)."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Simulate a sequence of drag positions (direct sync)
        for x in range(0, 200, 20):
            model.components[comp_id].position = (float(x), 50.0)
            # Position should be readable at every intermediate step
            assert model.components[comp_id].position == (float(x), 50.0)

    def test_move_component_still_notifies_observers(self):
        """controller.move_component() should still fire notifications."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        events = []
        controller.add_observer(lambda e, d: events.append((e, d)))

        controller.move_component(comp_id, (100, 200))

        move_events = [(e, d) for e, d in events if e == "component_moved"]
        assert len(move_events) == 1
        assert move_events[0][1].position == (100, 200)

    def test_direct_position_set_does_not_notify(self):
        """Direct attribute assignment should NOT fire observer notifications."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        events = []
        controller.add_observer(lambda e, d: events.append((e, d)))

        # Direct assignment (what _schedule_controller_update does for immediacy)
        model.components[comp_id].position = (100, 200)

        move_events = [e for e, d in events if e == "component_moved"]
        assert len(move_events) == 0

    def test_position_consistent_after_direct_then_controller(self):
        """Position should be consistent whether set directly or via controller."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Direct set (immediate sync during drag)
        model.components[comp_id].position = (100, 200)
        assert model.components[comp_id].position == (100, 200)

        # Controller set (debounced notification fires)
        controller.move_component(comp_id, (100, 200))
        assert model.components[comp_id].position == (100, 200)

    def test_group_drag_positions_all_sync_immediately(self):
        """All components in a group drag should sync positions immediately."""
        model = CircuitModel()
        controller = CircuitController(model)

        comps = []
        for i in range(5):
            c = controller.add_component("Resistor", (i * 100.0, 0.0))
            comps.append(c)

        # Simulate group drag: all move by (50, 50)
        for c in comps:
            new_pos = (c.position[0] + 50.0, c.position[1] + 50.0)
            model.components[c.component_id].position = new_pos

        # All should be at new positions immediately
        for i, c in enumerate(comps):
            expected = (i * 100.0 + 50.0, 50.0)
            assert model.components[c.component_id].position == expected

    def test_rapid_position_updates_keep_model_current(self):
        """Rapid successive position updates should all be reflected in model."""
        model = CircuitModel()
        controller = CircuitController(model)

        comp = controller.add_component("Resistor", (0, 0))
        comp_id = comp.component_id

        # Simulate rapid drag (many position changes, only last notification fires)
        positions = [(x * 10.0, x * 5.0) for x in range(100)]
        for pos in positions:
            model.components[comp_id].position = pos

        # Model should reflect the very last position
        assert model.components[comp_id].position == (990.0, 495.0)
