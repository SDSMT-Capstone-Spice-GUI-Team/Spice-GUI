"""Tests for wire rerouting deduplication (#189, #190).

Verifies that component drags trigger wire rerouting through exactly one
path (the observer/controller path) instead of two (observer + timer),
and that co-selected wires are only rerouted once.
"""

import ast
import inspect
import textwrap
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
        from GUI.component_item import ComponentGraphicsItem

        tree = ast.parse(textwrap.dedent(inspect.getsource(ComponentGraphicsItem.__init__)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "update_timer":
                raise AssertionError("Found update_timer reference in ComponentGraphicsItem.__init__")

    def test_no_last_position_attribute(self):
        """ComponentGraphicsItem should not reference last_position in init."""
        from GUI.component_item import ComponentGraphicsItem

        tree = ast.parse(textwrap.dedent(inspect.getsource(ComponentGraphicsItem.__init__)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "last_position":
                raise AssertionError("Found last_position reference in ComponentGraphicsItem.__init__")
            if isinstance(node, ast.Name) and node.id == "last_position":
                raise AssertionError("Found last_position reference in ComponentGraphicsItem.__init__")


class TestSingleReroutePath:
    """Verify only one code path exists from drag to reroute."""

    def test_itemchange_does_not_call_schedule_wire_update(self):
        """itemChange source should not reference schedule_wire_update."""
        from GUI.component_item import ComponentGraphicsItem

        tree = ast.parse(textwrap.dedent(inspect.getsource(ComponentGraphicsItem.itemChange)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "schedule_wire_update":
                raise AssertionError("Found schedule_wire_update in itemChange")
            if isinstance(node, ast.Name) and node.id == "schedule_wire_update":
                raise AssertionError("Found schedule_wire_update in itemChange")

    def test_itemchange_schedules_controller_update(self):
        """itemChange source should still schedule controller updates."""
        from GUI.component_item import ComponentGraphicsItem

        tree = ast.parse(textwrap.dedent(inspect.getsource(ComponentGraphicsItem.itemChange)))
        found = any(
            (isinstance(node, ast.Attribute) and node.attr == "_schedule_controller_update")
            or (isinstance(node, ast.Name) and node.id == "_schedule_controller_update")
            for node in ast.walk(tree)
        )
        assert found, "_schedule_controller_update not found in itemChange"


class TestCoSelectedRerouteDedup:
    """Tests for #190: wires between co-selected components rerouted once."""

    def test_reroute_checks_isSelected(self):
        """reroute_connected_wires should check isSelected on other endpoint."""
        from GUI.circuit_canvas import CircuitCanvasView

        tree = ast.parse(textwrap.dedent(inspect.getsource(CircuitCanvasView.reroute_connected_wires)))
        found = any(
            (isinstance(node, ast.Attribute) and node.attr == "isSelected")
            or (isinstance(node, ast.Name) and node.id == "isSelected")
            for node in ast.walk(tree)
        )
        assert found, "isSelected not found in reroute_connected_wires"

    def test_reroute_uses_component_id_tiebreaker(self):
        """Deterministic tiebreaker: lower component_id handles the wire."""
        from GUI.circuit_canvas import CircuitCanvasView

        tree = ast.parse(textwrap.dedent(inspect.getsource(CircuitCanvasView.reroute_connected_wires)))
        found = any(
            (isinstance(node, ast.Attribute) and node.attr == "component_id")
            or (isinstance(node, ast.Name) and node.id == "component_id")
            for node in ast.walk(tree)
        )
        assert found, "component_id not found in reroute_connected_wires"

    def test_reroute_skips_when_other_has_lower_id(self):
        """Wire should not be rerouted if other endpoint has lower ID and is selected."""
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = Mock(spec=CircuitCanvasView)
        canvas.scene = Mock()
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
        canvas.scene = Mock()
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
        canvas.scene = Mock()
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
