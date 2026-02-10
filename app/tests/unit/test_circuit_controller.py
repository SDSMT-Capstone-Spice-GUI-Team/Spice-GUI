"""Tests for CircuitController."""

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel
from models.component import ComponentData

@pytest.fixture
def controller():
    return CircuitController()


@pytest.fixture
def events():
    """Fixture that returns a list and a callback that appends events to it."""
    recorded = []

    def callback(event, data):
        recorded.append((event, data))

    return recorded, callback


class TestObserverPattern:
    def test_add_observer(self, controller, events):
        recorded, callback = events
        controller.add_observer(callback)
        controller.clear_circuit()
        assert len(recorded) == 1

    def test_remove_observer(self, controller, events):
        recorded, callback = events
        controller.add_observer(callback)
        controller.remove_observer(callback)
        controller.clear_circuit()
        assert len(recorded) == 0

    def test_duplicate_observer_not_added(self, controller, events):
        recorded, callback = events
        controller.add_observer(callback)
        controller.add_observer(callback)
        controller.clear_circuit()
        assert len(recorded) == 1

    def test_remove_nonexistent_observer_safe(self, controller, events):
        _, callback = events
        controller.remove_observer(callback)  # Should not raise


class TestComponentOperations:
    def test_add_component_generates_id(self, controller, events):
        recorded, callback = events
        controller.add_observer(callback)
        comp = controller.add_component("Resistor", (100.0, 200.0))
        assert comp.component_id == "R1"
        assert comp.component_type == "Resistor"
        assert comp.position == (100.0, 200.0)
        assert comp.value == "1k"
        assert recorded[-1] == ('component_added', comp)

    def test_add_multiple_components_increments_counter(self, controller):
        r1 = controller.add_component("Resistor", (0.0, 0.0))
        r2 = controller.add_component("Resistor", (100.0, 0.0))
        v1 = controller.add_component("Voltage Source", (50.0, 50.0))
        assert r1.component_id == "R1"
        assert r2.component_id == "R2"
        assert v1.component_id == "V1"

    def test_remove_component_notifies(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.remove_component("R1")
        assert ('component_removed', 'R1') in recorded

    def test_remove_component_removes_connected_wires(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.remove_component("R1")
        # Should see wire_removed before component_removed
        wire_events = [e for e in recorded if e[0] == 'wire_removed']
        assert len(wire_events) == 1

    def test_rotate_component(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.rotate_component("R1")
        assert recorded[-1][0] == 'component_rotated'
        assert controller.model.components["R1"].rotation == 90

    def test_rotate_component_counterclockwise(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.rotate_component("R1", clockwise=False)
        assert controller.model.components["R1"].rotation == 270

    def test_rotate_nonexistent_component_safe(self, controller):
        controller.rotate_component("R999")  # Should not raise

    def test_update_value(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.update_component_value("R1", "10k")
        assert controller.model.components["R1"].value == "10k"
        assert recorded[-1][0] == 'component_value_changed'

    def test_move_component(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.move_component("R1", (50.0, 75.0))
        assert controller.model.components["R1"].position == (50.0, 75.0)
        assert recorded[-1][0] == 'component_moved'


    def test_flip_component_horizontal(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.flip_component("R1", horizontal=True)
        assert controller.model.components["R1"].flip_h is True
        assert controller.model.components["R1"].flip_v is False
        assert recorded[-1][0] == 'component_flipped'

    def test_flip_component_vertical(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.flip_component("R1", horizontal=False)
        assert controller.model.components["R1"].flip_v is True
        assert controller.model.components["R1"].flip_h is False
        assert recorded[-1][0] == 'component_flipped'

    def test_flip_component_toggles(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.flip_component("R1", horizontal=True)
        assert controller.model.components["R1"].flip_h is True
        controller.flip_component("R1", horizontal=True)
        assert controller.model.components["R1"].flip_h is False

    def test_flip_nonexistent_component_safe(self, controller):
        controller.flip_component("R999")  # Should not raise


class TestWireOperations:
    def test_add_wire(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_observer(callback)
        wire = controller.add_wire("R1", 1, "R2", 0)
        assert wire.start_component_id == "R1"
        assert wire.end_component_id == "R2"
        assert recorded[-1] == ('wire_added', wire)

    def test_remove_wire(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.remove_wire(0)
        assert ('wire_removed', 0) in recorded
        assert len(controller.model.wires) == 0

    def test_remove_wire_invalid_index_safe(self, controller):
        controller.remove_wire(99)  # Should not raise

    def test_update_waypoints(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        pts = [(10.0, 0.0), (50.0, 0.0), (90.0, 0.0)]
        controller.update_wire_waypoints(0, pts)
        assert controller.model.wires[0].waypoints == pts
        assert recorded[-1][0] == 'wire_routed'


class TestCircuitOperations:
    def test_clear_circuit(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.clear_circuit()
        assert ('circuit_cleared', None) in recorded
        assert len(controller.model.components) == 0

    def test_rebuild_nodes(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.rebuild_nodes()
        assert ('nodes_rebuilt', None) in recorded


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import controllers.circuit_controller as mod
        source = open(mod.__file__).read()
        assert 'PyQt' not in source
        assert 'QtCore' not in source
        assert 'QtWidgets' not in source
