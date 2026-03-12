"""Tests for CircuitController."""

from pathlib import Path

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


class TestNodeManagementThroughController:
    """Verify that the model's node graph is updated when operations go through the controller."""

    def test_add_wire_creates_node(self, controller):
        """Adding a wire through the controller should create a node in the model."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        assert len(controller.model.nodes) == 1
        node = controller.model.nodes[0]
        assert ("R1", 1) in node.terminals
        assert ("R2", 0) in node.terminals

    def test_add_wire_merges_nodes(self, controller):
        """Wires connecting existing nodes should merge them."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_component("Resistor", (200.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_wire("R2", 1, "R3", 0)
        # R1[1]-R2[0] is one node, R2[1]-R3[0] is another
        assert len(controller.model.nodes) == 2

    def test_remove_wire_updates_nodes(self, controller):
        """Removing a wire should update the node graph."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        assert len(controller.model.nodes) == 1
        controller.remove_wire(0)
        assert len(controller.model.nodes) == 0

    def test_ground_component_creates_ground_node(self, controller):
        """Adding a Ground component should create a ground node in the model."""
        controller.add_component("Ground", (0.0, 0.0))
        ground_nodes = [n for n in controller.model.nodes if n.is_ground]
        assert len(ground_nodes) == 1
        assert ground_nodes[0].auto_label == "0"

    def test_clear_circuit_clears_nodes(self, controller):
        """Clearing the circuit should clear all nodes."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.clear_circuit()
        assert len(controller.model.nodes) == 0
        assert len(controller.model.terminal_to_node) == 0

    def test_rebuild_nodes_preserves_connectivity(self, controller):
        """Rebuilding nodes should reproduce the same connectivity."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        original_count = len(controller.model.nodes)
        controller.rebuild_nodes()
        assert len(controller.model.nodes) == original_count

    def test_paste_creates_nodes(self, controller):
        """Pasting components with wires should create nodes in the model."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.copy_components(["R1", "R2"])
        new_comps, new_wires = controller.paste_components()
        assert len(new_comps) == 2
        assert len(new_wires) == 1
        # Original + pasted: 2 nodes (one for each wire)
        assert len(controller.model.nodes) == 2


class TestNodeAccessAPI:
    """Verify node access methods on the controller."""

    def test_get_nodes_and_terminal_map_empty(self, controller):
        """Returns empty collections when no wires exist."""
        nodes, term_map = controller.get_nodes_and_terminal_map()
        assert nodes == []
        assert term_map == {}

    def test_get_nodes_and_terminal_map_with_wire(self, controller):
        """Returns node and terminal mapping after a wire is added."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        nodes, term_map = controller.get_nodes_and_terminal_map()
        assert len(nodes) == 1
        assert ("R1", 1) in term_map
        assert ("R2", 0) in term_map
        # Returns copies, not references to internal state
        nodes.clear()
        assert len(controller.model.nodes) == 1

    def test_find_node_for_terminal_found(self, controller):
        """Finds the correct node for a connected terminal."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        node = controller.find_node_for_terminal("R1", 1)
        assert node is not None
        assert ("R1", 1) in node.terminals

    def test_find_node_for_terminal_not_found(self, controller):
        """Returns None for an unconnected terminal."""
        controller.add_component("Resistor", (0.0, 0.0))
        assert controller.find_node_for_terminal("R1", 0) is None

    def test_set_net_name_updates_node(self, controller, events):
        """set_net_name updates the node label and notifies observers."""
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        node = controller.model.nodes[0]
        controller.set_net_name(node, "Vout")
        assert node.custom_label == "Vout"
        assert recorded[-1][0] == "net_name_changed"


class TestClipboardPublicAPI:
    """Verify clipboard operations use public controller API."""

    def test_set_clipboard(self, controller):
        """set_clipboard replaces internal clipboard."""
        from models.clipboard import ClipboardData

        controller.add_component("Resistor", (0.0, 0.0))
        comp_dict = controller.model.components["R1"].to_dict()
        cb = ClipboardData(components=[comp_dict], wires=[], paste_count=0)
        controller.set_clipboard(cb)
        assert controller.has_clipboard_content()

    def test_get_clipboard_paste_count(self, controller):
        """get_clipboard_paste_count reflects paste operations."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        assert controller.get_clipboard_paste_count() == 0
        controller.paste_components()
        assert controller.get_clipboard_paste_count() == 1
        controller.paste_components()
        assert controller.get_clipboard_paste_count() == 2


class TestWireRoutingAPI:
    """Verify wire routing result and lock state are persisted through the controller."""

    def test_update_wire_routing_result(self, controller, events):
        """update_wire_routing_result stores pathfinding metadata."""
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        wps = [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]
        controller.update_wire_routing_result(0, wps, runtime=0.05, iterations=42, routing_failed=False)
        wire = controller.model.wires[0]
        assert wire.waypoints == wps
        assert wire.runtime == 0.05
        assert wire.iterations == 42
        assert wire.routing_failed is False
        assert recorded[-1][0] == "wire_routed"

    def test_set_wire_locked(self, controller, events):
        """set_wire_locked updates the lock flag and notifies."""
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Resistor", (100.0, 0.0))
        controller.add_wire("R1", 1, "R2", 0)
        controller.add_observer(callback)
        controller.set_wire_locked(0, True)
        assert controller.model.wires[0].locked is True
        assert recorded[-1][0] == "wire_lock_changed"

    def test_set_wire_locked_invalid_index(self, controller):
        """set_wire_locked with invalid index does nothing."""
        controller.set_wire_locked(99, True)  # Should not raise

    def test_set_component_rotation(self, controller, events):
        """set_component_rotation sets exact rotation value."""
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        controller.set_component_rotation("R1", 180)
        assert controller.model.components["R1"].rotation == 180
        assert recorded[-1][0] == "component_rotated"


class TestControllerAccessors:
    """Test public accessor methods that encapsulate model access."""

    def test_get_component(self, controller):
        comp = controller.add_component("Resistor", (0.0, 0.0))
        assert controller.get_component(comp.component_id) is comp
        assert controller.get_component("nonexistent") is None

    def test_get_components_returns_copy(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        result = controller.get_components()
        assert isinstance(result, dict)
        assert len(result) == 1
        # Modifying the returned dict shouldn't affect the model
        result.clear()
        assert len(controller.model.components) == 1

    def test_get_wires_returns_copy(self, controller):
        result = controller.get_wires()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_annotations_returns_copy(self, controller):
        result = controller.get_annotations()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_component_counter(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        counter = controller.get_component_counter()
        assert len(counter) >= 1
        # Modifying returned dict shouldn't affect model
        counter["__test__"] = 999
        assert "__test__" not in controller.model.component_counter

    def test_to_dict(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        result = controller.to_dict()
        assert "components" in result
        assert "wires" in result

    def test_push_already_executed(self, controller):
        """push_already_executed adds command to undo stack and clears redo."""
        from unittest.mock import MagicMock

        cmd = MagicMock()
        controller.push_already_executed(cmd)
        assert controller.undo_manager._undo_stack[-1] is cmd
        assert len(controller.undo_manager._redo_stack) == 0


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import controllers.circuit_controller as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
