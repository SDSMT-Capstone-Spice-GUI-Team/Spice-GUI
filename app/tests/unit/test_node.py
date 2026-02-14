"""Tests for NodeData custom labels and net names."""

from unittest.mock import MagicMock

from models.circuit import CircuitModel
from models.node import NodeData, _generate_label, reset_node_counter


class TestNodeCustomLabel:
    def test_custom_label_overrides_auto_label(self):
        node = NodeData(auto_label="nodeA")
        node.set_custom_label("Vout")
        assert node.get_label() == "Vout"

    def test_clear_custom_label_reverts_to_auto(self):
        node = NodeData(auto_label="nodeA")
        node.set_custom_label("Vout")
        assert node.get_label() == "Vout"
        node.set_custom_label(None)
        assert node.get_label() == "nodeA"

    def test_ground_with_custom_label_shows_ground_suffix(self):
        node = NodeData(is_ground=True, auto_label="0")
        node.set_custom_label("GND_NET")
        assert node.get_label() == "GND_NET (ground)"

    def test_ground_without_custom_label_shows_zero(self):
        node = NodeData(is_ground=True, auto_label="0")
        assert node.get_label() == "0"

    def test_set_custom_label_accepts_none(self):
        node = NodeData(auto_label="nodeA")
        node.set_custom_label(None)
        assert node.custom_label is None
        assert node.get_label() == "nodeA"


class TestNodeLabelGeneration:
    def test_generate_single_letter_labels(self):
        assert _generate_label(0) == "nodeA"
        assert _generate_label(25) == "nodeZ"

    def test_generate_double_letter_labels(self):
        assert _generate_label(26) == "nodeAA"
        assert _generate_label(27) == "nodeAB"

    def test_auto_label_increments(self):
        reset_node_counter()
        n1 = NodeData()
        n2 = NodeData()
        assert n1.auto_label == "nodeA"
        assert n2.auto_label == "nodeB"

    def test_ground_node_auto_label_is_zero(self):
        node = NodeData(is_ground=True)
        assert node.auto_label == "0"


class TestNodeMerge:
    def test_merge_preserves_custom_label(self):
        node1 = NodeData(auto_label="nodeA")
        node1.set_custom_label("Vout")
        node1.add_terminal("R1", 0)

        node2 = NodeData(auto_label="nodeB")
        node2.add_terminal("R2", 0)

        node1.merge_with(node2)
        assert node1.custom_label == "Vout"
        assert ("R2", 0) in node1.terminals

    def test_merge_adopts_other_custom_label_when_self_has_none(self):
        """Bug fix: merge_with must preserve other's custom label."""
        node1 = NodeData(auto_label="nodeA")
        node1.add_terminal("R1", 0)

        node2 = NodeData(auto_label="nodeB")
        node2.set_custom_label("Vcc")
        node2.add_terminal("R2", 0)

        node1.merge_with(node2)
        assert node1.custom_label == "Vcc"

    def test_merge_keeps_self_label_over_other(self):
        """When both nodes have custom labels, self's label wins."""
        node1 = NodeData(auto_label="nodeA")
        node1.set_custom_label("Vout")
        node1.add_terminal("R1", 0)

        node2 = NodeData(auto_label="nodeB")
        node2.set_custom_label("Vcc")
        node2.add_terminal("R2", 0)

        node1.merge_with(node2)
        assert node1.custom_label == "Vout"

    def test_merge_ground_preserves_custom_label(self):
        """Merging ground node should not overwrite a custom label."""
        node1 = NodeData(auto_label="nodeA")
        node1.set_custom_label("GND_NET")
        node1.add_terminal("R1", 0)

        node2 = NodeData(is_ground=True, auto_label="0")
        node2.add_terminal("R2", 0)

        node1.merge_with(node2)
        assert node1.is_ground is True
        assert node1.custom_label == "GND_NET"


class TestRebuildNodesPreservesLabels:
    """Tests that rebuild_nodes() preserves custom labels."""

    def _make_circuit_with_labeled_node(self):
        """Create a circuit with two components, a wire, and a custom label."""
        from models.component import ComponentData
        from models.wire import WireData

        model = CircuitModel()
        comp1 = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100, 100),
        )
        comp2 = ComponentData(
            component_id="R2",
            component_type="Resistor",
            value="2k",
            position=(200, 100),
        )
        model.add_component(comp1)
        model.add_component(comp2)

        wire = WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="R2",
            end_terminal=0,
        )
        model.add_wire(wire)
        return model

    def test_rebuild_preserves_custom_label(self):
        model = self._make_circuit_with_labeled_node()
        # Find the node connecting R1 and R2 and label it
        for node in model.nodes:
            if ("R1", 1) in node.terminals:
                node.set_custom_label("Vmid")
                break

        model.rebuild_nodes()

        # After rebuild, the node connecting R1:1 and R2:0 should still have "Vmid"
        found = False
        for node in model.nodes:
            if ("R1", 1) in node.terminals:
                assert node.custom_label == "Vmid"
                found = True
                break
        assert found, "Node with terminal (R1, 1) not found after rebuild"

    def test_rebuild_without_labels_works(self):
        model = self._make_circuit_with_labeled_node()
        model.rebuild_nodes()
        # No crash, no labels set
        for node in model.nodes:
            assert node.custom_label is None

    def test_rebuild_preserves_multiple_labels(self):
        from models.component import ComponentData
        from models.wire import WireData

        model = CircuitModel()
        for i, name in enumerate(["R1", "R2", "R3"]):
            model.add_component(
                ComponentData(
                    component_id=name,
                    component_type="Resistor",
                    value="1k",
                    position=(100 * (i + 1), 100),
                )
            )
        model.add_wire(
            WireData(
                start_component_id="R1",
                start_terminal=1,
                end_component_id="R2",
                end_terminal=0,
            )
        )
        model.add_wire(
            WireData(
                start_component_id="R2",
                start_terminal=1,
                end_component_id="R3",
                end_terminal=0,
            )
        )

        # Label both junction nodes
        for node in model.nodes:
            if ("R1", 1) in node.terminals:
                node.set_custom_label("Va")
            elif ("R2", 1) in node.terminals:
                node.set_custom_label("Vb")

        model.rebuild_nodes()

        labels_found = set()
        for node in model.nodes:
            if node.custom_label:
                labels_found.add(node.custom_label)
        assert labels_found == {"Va", "Vb"}


class TestSetNetNamePublicAPI:
    """Tests that CircuitController.set_net_name() works correctly."""

    def test_set_net_name_sets_label(self):
        from controllers.circuit_controller import CircuitController

        ctrl = CircuitController()
        node = NodeData(auto_label="nodeA")
        node.add_terminal("R1", 0)

        ctrl.set_net_name(node, "Vout")
        assert node.custom_label == "Vout"

    def test_set_net_name_notifies_observers(self):
        from controllers.circuit_controller import CircuitController

        ctrl = CircuitController()
        observer = MagicMock()
        ctrl.add_observer(observer)

        node = NodeData(auto_label="nodeA")
        ctrl.set_net_name(node, "Vcc")

        observer.assert_called_once_with("net_name_changed", node)

    def test_set_net_name_clear_label(self):
        from controllers.circuit_controller import CircuitController

        ctrl = CircuitController()
        node = NodeData(auto_label="nodeA")
        node.set_custom_label("Vout")

        ctrl.set_net_name(node, None)
        assert node.custom_label is None
        assert node.get_label() == "nodeA"

    def test_canvas_does_not_call_private_notify(self):
        """Verify the canvas code no longer calls controller._notify directly."""
        import inspect

        from GUI.circuit_canvas import CircuitCanvas

        source = inspect.getsource(CircuitCanvas.label_node)
        assert (
            "_notify" not in source
        ), "label_node still calls _notify directly — use set_net_name instead"
