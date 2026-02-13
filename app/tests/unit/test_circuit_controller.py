"""Tests for CircuitController."""

import pytest
from controllers.circuit_controller import CircuitController
from models.annotation import AnnotationData
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
        assert recorded[-1] == ("component_added", comp)

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
        assert ("component_removed", "R1") in recorded

    def test_remove_component_removes_connected_wires(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.remove_component("R1")
        # Should see wire_removed before component_removed
        wire_events = [e for e in recorded if e[0] == "wire_removed"]
        assert len(wire_events) == 1

    def test_rotate_component(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.rotate_component("R1")
        assert recorded[-1][0] == "component_rotated"
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
        assert recorded[-1][0] == "component_value_changed"

    def test_move_component(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.move_component("R1", (50.0, 75.0))
        assert controller.model.components["R1"].position == (50.0, 75.0)
        assert recorded[-1][0] == "component_moved"

    def test_flip_component_horizontal(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.flip_component("R1", horizontal=True)
        assert controller.model.components["R1"].flip_h is True
        assert controller.model.components["R1"].flip_v is False
        assert recorded[-1][0] == "component_flipped"

    def test_flip_component_vertical(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.flip_component("R1", horizontal=False)
        assert controller.model.components["R1"].flip_v is True
        assert controller.model.components["R1"].flip_h is False
        assert recorded[-1][0] == "component_flipped"

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
        assert recorded[-1] == ("wire_added", wire)

    def test_remove_wire(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.remove_wire(0)
        assert ("wire_removed", 0) in recorded
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
        assert recorded[-1][0] == "wire_routed"


class TestDuplicateWirePrevention:
    """Tests for duplicate wire detection and prevention."""

    def test_has_duplicate_wire_false_when_no_wires(self, controller):
        """No duplicate when no wires exist."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        assert controller.has_duplicate_wire("R1", 0, "R2", 0) is False

    def test_has_duplicate_wire_true_for_exact_match(self, controller):
        """Detect duplicate when same terminal pair already connected."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 0, "R2", 0)
        assert controller.has_duplicate_wire("R1", 0, "R2", 0) is True

    def test_has_duplicate_wire_true_for_reverse_direction(self, controller):
        """Detect duplicate even when terminals are specified in reverse order."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 0, "R2", 1)
        assert controller.has_duplicate_wire("R2", 1, "R1", 0) is True

    def test_different_terminal_not_duplicate(self, controller):
        """Different terminal on same component is NOT a duplicate."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 0, "R2", 0)
        assert controller.has_duplicate_wire("R1", 0, "R2", 1) is False

    def test_add_wire_returns_none_for_duplicate(self, controller):
        """add_wire should return None and not add a duplicate."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        wire1 = controller.add_wire("R1", 0, "R2", 0)
        assert wire1 is not None
        wire2 = controller.add_wire("R1", 0, "R2", 0)
        assert wire2 is None
        assert len(controller.model.wires) == 1

    def test_add_wire_returns_none_for_reverse_duplicate(self, controller):
        """add_wire should reject reverse-direction duplicate."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 0, "R2", 1)
        wire2 = controller.add_wire("R2", 1, "R1", 0)
        assert wire2 is None
        assert len(controller.model.wires) == 1

    def test_multi_wire_terminal_allowed(self, controller):
        """Multiple wires from same terminal to different targets are allowed."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_component("Resistor", (200.0, 0.0))
        wire1 = controller.add_wire("R1", 0, "R2", 0)
        wire2 = controller.add_wire("R1", 0, "R3", 0)
        assert wire1 is not None
        assert wire2 is not None
        assert len(controller.model.wires) == 2


class TestCircuitOperations:
    def test_clear_circuit(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.clear_circuit()
        assert ("circuit_cleared", None) in recorded
        assert len(controller.model.components) == 0

    def test_rebuild_nodes(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.rebuild_nodes()
        assert ("nodes_rebuilt", None) in recorded


class TestErrorBoundaryComponentOperations:
    """Error-boundary tests: operations on nonexistent component IDs."""

    def test_remove_nonexistent_component_no_crash(self, controller, events):
        """remove_component with unknown ID does not crash or notify observers."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.remove_component("nonexistent")
        # Only component_removed is emitted (no wire_removed), no crash
        assert ("component_removed", "nonexistent") in recorded

    def test_rotate_nonexistent_no_observer_notification(self, controller, events):
        """rotate_component with unknown ID does not notify observers."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.rotate_component("nonexistent")
        assert len(recorded) == 0

    def test_flip_nonexistent_no_observer_notification(self, controller, events):
        """flip_component with unknown ID does not notify observers."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.flip_component("nonexistent", horizontal=True)
        controller.flip_component("nonexistent", horizontal=False)
        assert len(recorded) == 0

    def test_update_value_nonexistent_no_crash(self, controller, events):
        """update_component_value with unknown ID does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.update_component_value("nonexistent", "10k")
        assert len(recorded) == 0

    def test_move_nonexistent_no_crash(self, controller, events):
        """move_component with unknown ID does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.move_component("nonexistent", (100.0, 200.0))
        assert len(recorded) == 0

    def test_multiple_operations_on_nonexistent_safe(self, controller):
        """Sequence of operations on nonexistent IDs does not crash."""
        controller.rotate_component("ghost")
        controller.flip_component("ghost")
        controller.move_component("ghost", (0.0, 0.0))
        controller.update_component_value("ghost", "1M")
        controller.remove_component("ghost")
        # Should reach here without any exception


class TestErrorBoundaryWireOperations:
    """Error-boundary tests: wire operations with invalid indices."""

    def test_remove_wire_negative_index_no_crash(self, controller, events):
        """remove_wire with negative index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.remove_wire(-1)
        assert len(recorded) == 0

    def test_remove_wire_out_of_bounds_no_crash(self, controller, events):
        """remove_wire with out-of-bounds index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.remove_wire(100)
        assert len(recorded) == 0

    def test_update_wire_waypoints_invalid_index_no_crash(self, controller, events):
        """update_wire_waypoints with invalid index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.update_wire_waypoints(-1, [(10.0, 20.0)])
        controller.update_wire_waypoints(99, [(10.0, 20.0)])
        assert len(recorded) == 0

    def test_add_wire_duplicate_returns_none(self, controller, events):
        """add_wire returns None for duplicate wire (duplicate check)."""
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 0, "R2", 0)
        controller.add_observer(callback)
        result = controller.add_wire("R1", 0, "R2", 0)
        assert result is None
        assert len(recorded) == 0

    def test_add_wire_with_nonexistent_components(self, controller):
        """add_wire referencing missing components still creates wire data."""
        # The controller does not validate component existence for add_wire.
        # It only checks for duplicate wires.
        wire = controller.add_wire("MISSING1", 0, "MISSING2", 1)
        assert wire is not None
        assert wire.start_component_id == "MISSING1"


class TestErrorBoundaryAnnotationOperations:
    """Error-boundary tests: annotation operations with invalid indices."""

    def test_remove_annotation_negative_index_no_crash(self, controller, events):
        """remove_annotation with negative index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.remove_annotation(-1)
        assert len(recorded) == 0

    def test_remove_annotation_out_of_bounds_no_crash(self, controller, events):
        """remove_annotation with out-of-bounds index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.remove_annotation(99)
        assert len(recorded) == 0

    def test_update_annotation_text_negative_index_no_crash(self, controller, events):
        """update_annotation_text with negative index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.update_annotation_text(-1, "New text")
        assert len(recorded) == 0

    def test_update_annotation_text_out_of_bounds_no_crash(self, controller, events):
        """update_annotation_text with out-of-bounds index does not crash or notify."""
        recorded, callback = events
        controller.add_observer(callback)
        controller.update_annotation_text(99, "New text")
        assert len(recorded) == 0

    def test_add_then_remove_annotation_boundary(self, controller, events):
        """add_annotation followed by remove with same index works correctly."""
        recorded, callback = events
        controller.add_observer(callback)
        ann = AnnotationData(text="Test", x=10.0, y=20.0)
        idx = controller.add_annotation(ann)
        # Now remove at that index
        controller.remove_annotation(idx)
        # Remove again at same index (now out of bounds)
        controller.remove_annotation(idx)
        add_events = [e for e in recorded if e[0] == "annotation_added"]
        remove_events = [e for e in recorded if e[0] == "annotation_removed"]
        assert len(add_events) == 1
        assert len(remove_events) == 1  # Only the first remove notifies


class TestObserverErrorIsolation:
    """Tests that a failing observer does not prevent other observers from being notified."""

    def test_failing_observer_does_not_block_others(self, controller):
        """When one observer raises, other observers still get notified."""
        results = []

        def good_observer_1(event, data):
            results.append(("good1", event))

        def bad_observer(event, data):
            raise RuntimeError("Observer crashed!")

        def good_observer_2(event, data):
            results.append(("good2", event))

        controller.add_observer(good_observer_1)
        controller.add_observer(bad_observer)
        controller.add_observer(good_observer_2)

        controller.clear_circuit()

        assert ("good1", "circuit_cleared") in results
        assert ("good2", "circuit_cleared") in results

    def test_type_error_in_observer_isolated(self, controller):
        """TypeError in observer is caught and other observers still run."""
        results = []

        def broken_observer(event, data):
            raise TypeError("Bad type in observer")

        def working_observer(event, data):
            results.append(event)

        controller.add_observer(broken_observer)
        controller.add_observer(working_observer)

        controller.add_component("Resistor", (0.0, 0.0))

        assert "component_added" in results

    def test_attribute_error_in_observer_isolated(self, controller):
        """AttributeError in observer is caught and other observers still run."""
        results = []

        def broken_observer(event, data):
            raise AttributeError("Missing attribute")

        def working_observer(event, data):
            results.append(event)

        controller.add_observer(broken_observer)
        controller.add_observer(working_observer)

        controller.add_component("Resistor", (0.0, 0.0))

        assert "component_added" in results


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import controllers.circuit_controller as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
