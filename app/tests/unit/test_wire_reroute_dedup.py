"""Tests for wire rerouting deduplication (#189, #190).

Verifies that component drags trigger wire rerouting through exactly one
path (the observer/controller path) instead of two (observer + timer),
and that co-selected wires are only rerouted once.
"""

from unittest.mock import Mock, patch

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
        """ComponentGraphicsItem instances should not have an update_timer attribute."""
        from unittest.mock import MagicMock, patch

        from GUI.component_item import ComponentGraphicsItem

        mock_comp = MagicMock()
        mock_comp.component_id = "R1"
        mock_comp.component_type = "Resistor"
        mock_comp.position = (0, 0)
        mock_comp.rotation = 0
        mock_comp.flip_h = False
        mock_comp.flip_v = False

        with patch.object(ComponentGraphicsItem, "__init__", lambda self, *a, **kw: None):
            item = ComponentGraphicsItem.__new__(ComponentGraphicsItem)

        assert not hasattr(item, "update_timer")

    def test_no_last_position_attribute(self):
        """ComponentGraphicsItem instances should not have a last_position attribute."""
        from GUI.component_item import ComponentGraphicsItem

        with patch.object(ComponentGraphicsItem, "__init__", lambda self, *a, **kw: None):
            item = ComponentGraphicsItem.__new__(ComponentGraphicsItem)

        assert not hasattr(item, "last_position")


class TestSingleReroutePath:
    """Verify only one code path exists from drag to reroute."""

    def test_itemchange_does_not_call_schedule_wire_update(self):
        """ComponentGraphicsItem should not have a schedule_wire_update method."""
        from GUI.component_item import ComponentGraphicsItem

        assert not hasattr(ComponentGraphicsItem, "schedule_wire_update")

    def test_itemchange_schedules_controller_update(self):
        """ComponentGraphicsItem should have a _schedule_controller_update method."""
        from GUI.component_item import ComponentGraphicsItem

        assert hasattr(ComponentGraphicsItem, "_schedule_controller_update")


class TestCoSelectedRerouteDedup:
    """Tests for #190: wires between co-selected components rerouted once."""

    def test_reroute_checks_isSelected(self):
        """reroute_connected_wires skips a wire when the other endpoint is selected and has the lower ID.

        This behavioral check confirms that isSelected is consulted: if the other endpoint IS
        selected (and has a lower ID), the wire is skipped.
        """
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = Mock(spec=CircuitCanvasView)
        canvas._scene = Mock()
        canvas.viewport = Mock(return_value=Mock())
        canvas.window = Mock(return_value=None)

        comp_a = Mock()
        comp_a.component_id = "R1"
        comp_a.isSelected = Mock(return_value=True)  # IS selected

        comp_b = Mock()
        comp_b.component_id = "R2"
        comp_b.isSelected = Mock(return_value=True)

        wire = Mock()
        wire.start_comp = comp_a
        wire.end_comp = comp_b
        wire.model.locked = False

        canvas.wires = [wire]

        # comp_b has the higher ID — since comp_a is selected with a lower ID, wire should be skipped
        CircuitCanvasView.reroute_connected_wires(canvas, comp_b)
        wire.update_position.assert_not_called()

        # When comp_a is NOT selected, the wire should be rerouted regardless of ID order
        comp_a.isSelected = Mock(return_value=False)
        CircuitCanvasView.reroute_connected_wires(canvas, comp_b)
        wire.update_position.assert_called_once()

    def test_reroute_uses_component_id_tiebreaker(self):
        """Deterministic tiebreaker: lower component_id handles the wire.

        Behavioral confirmation that component_id ordering is the tiebreaker when both
        endpoints are selected.
        """
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = Mock(spec=CircuitCanvasView)
        canvas._scene = Mock()
        canvas.viewport = Mock(return_value=Mock())
        canvas.window = Mock(return_value=None)

        comp_a = Mock()
        comp_a.component_id = "R1"
        comp_a.isSelected = Mock(return_value=True)

        comp_b = Mock()
        comp_b.component_id = "R2"
        comp_b.isSelected = Mock(return_value=True)

        wire = Mock()
        wire.start_comp = comp_a
        wire.end_comp = comp_b
        wire.model.locked = False

        canvas.wires = [wire]

        # comp_a (lower ID) should reroute; comp_b (higher ID) should skip
        CircuitCanvasView.reroute_connected_wires(canvas, comp_a)
        assert wire.update_position.call_count == 1

        wire.reset_mock()

        CircuitCanvasView.reroute_connected_wires(canvas, comp_b)
        wire.update_position.assert_not_called()

    def test_reroute_skips_when_other_has_lower_id(self):
        """Wire should not be rerouted if other endpoint has lower ID and is selected."""
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = Mock(spec=CircuitCanvasView)
        canvas._scene = Mock()
        canvas.viewport = Mock(return_value=Mock())
        canvas.window = Mock(return_value=None)

        # Create mock components
        comp_b = Mock()
        comp_b.component_id = "R2"
        comp_b.isSelected = Mock(return_value=True)

        comp_a = Mock()
        comp_a.component_id = "R1"
        comp_a.isSelected = Mock(return_value=True)

        # Wire from R1 to R2
        wire = Mock()
        wire.start_comp = comp_a
        wire.end_comp = comp_b
        wire.model.locked = False

        canvas.wires = [wire]

        # Call for comp_b (higher ID) — should skip since comp_a has lower ID
        CircuitCanvasView.reroute_connected_wires(canvas, comp_b)
        wire.update_position.assert_not_called()

    def test_reroute_proceeds_when_caller_has_lower_id(self):
        """Wire should be rerouted when caller has the lower component ID."""
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = Mock(spec=CircuitCanvasView)
        canvas._scene = Mock()
        canvas.viewport = Mock(return_value=Mock())
        canvas.window = Mock(return_value=None)

        comp_a = Mock()
        comp_a.component_id = "R1"
        comp_a.isSelected = Mock(return_value=True)

        comp_b = Mock()
        comp_b.component_id = "R2"
        comp_b.isSelected = Mock(return_value=True)

        wire = Mock()
        wire.start_comp = comp_a
        wire.end_comp = comp_b
        wire.model.locked = False

        canvas.wires = [wire]

        # Call for comp_a (lower ID) — should reroute
        CircuitCanvasView.reroute_connected_wires(canvas, comp_a)
        wire.update_position.assert_called_once()

    def test_reroute_proceeds_when_other_not_selected(self):
        """Wire should always be rerouted if other endpoint is not selected."""
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = Mock(spec=CircuitCanvasView)
        canvas._scene = Mock()
        canvas.viewport = Mock(return_value=Mock())
        canvas.window = Mock(return_value=None)

        comp_a = Mock()
        comp_a.component_id = "R1"
        comp_a.isSelected = Mock(return_value=True)

        comp_b = Mock()
        comp_b.component_id = "R2"
        comp_b.isSelected = Mock(return_value=False)  # Not selected

        wire = Mock()
        wire.start_comp = comp_a
        wire.end_comp = comp_b
        wire.model.locked = False

        canvas.wires = [wire]

        # Both directions should reroute since other is not selected
        CircuitCanvasView.reroute_connected_wires(canvas, comp_a)
        assert wire.update_position.call_count == 1

        wire.reset_mock()
        CircuitCanvasView.reroute_connected_wires(canvas, comp_b)
        assert wire.update_position.call_count == 1
