"""Tests for NodeData custom labels and net names."""

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
