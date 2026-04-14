"""Tests for algorithms.graph_ops – pure-function node-graph operations.

These tests exercise the extracted graph algorithms directly, without
going through CircuitModel.  The existing test_circuit_model.py suite
covers the same behaviour via the model's delegating methods.
"""

from algorithms.graph_ops import (
    handle_ground_added,
    rebuild_all_nodes,
    rebuild_nodes_after_wire_removal,
    shift_wire_indices,
    update_nodes_for_wire,
)
from models.component import ComponentData
from models.node import NodeData, reset_node_counter
from models.wire import WireData


def _comp(cid, ctype="Resistor"):
    return ComponentData(component_id=cid, component_type=ctype, value="1k", position=(0, 0))


def _wire(sc, st, ec, et):
    return WireData(
        start_component_id=sc,
        start_terminal=st,
        end_component_id=ec,
        end_terminal=et,
    )


# ------------------------------------------------------------------
# handle_ground_added
# ------------------------------------------------------------------


class TestHandleGroundAdded:
    def test_creates_ground_node(self):
        nodes, ttn = [], {}
        gnd = _comp("GND1", "Ground")
        handle_ground_added(nodes, ttn, gnd)
        assert len(nodes) == 1
        assert nodes[0].is_ground
        assert ("GND1", 0) in ttn

    def test_reuses_existing_ground_node(self):
        nodes, ttn = [], {}
        gnd1 = _comp("GND1", "Ground")
        gnd2 = _comp("GND2", "Ground")
        handle_ground_added(nodes, ttn, gnd1)
        handle_ground_added(nodes, ttn, gnd2)
        assert len(nodes) == 1
        assert ("GND1", 0) in nodes[0].terminals
        assert ("GND2", 0) in nodes[0].terminals


# ------------------------------------------------------------------
# update_nodes_for_wire
# ------------------------------------------------------------------


class TestUpdateNodesForWire:
    def setup_method(self):
        reset_node_counter()

    def test_creates_new_node_for_unconnected_terminals(self):
        nodes, ttn = [], {}
        comps = {"R1": _comp("R1"), "R2": _comp("R2")}
        wire = _wire("R1", 0, "R2", 0)
        update_nodes_for_wire(nodes, ttn, comps, wire, wire_index=0)
        assert len(nodes) == 1
        assert ("R1", 0) in ttn
        assert ("R2", 0) in ttn
        assert ttn[("R1", 0)] is ttn[("R2", 0)]

    def test_extends_existing_node(self):
        nodes, ttn = [], {}
        comps = {"R1": _comp("R1"), "R2": _comp("R2"), "R3": _comp("R3")}
        update_nodes_for_wire(nodes, ttn, comps, _wire("R1", 0, "R2", 0), wire_index=0)
        update_nodes_for_wire(nodes, ttn, comps, _wire("R2", 0, "R3", 0), wire_index=1)
        assert len(nodes) == 1
        assert ("R3", 0) in ttn
        assert ttn[("R1", 0)] is ttn[("R3", 0)]

    def test_merges_two_existing_nodes(self):
        nodes, ttn = [], {}
        comps = {
            "R1": _comp("R1"),
            "R2": _comp("R2"),
            "R3": _comp("R3"),
            "R4": _comp("R4"),
        }
        update_nodes_for_wire(nodes, ttn, comps, _wire("R1", 0, "R2", 0), wire_index=0)
        update_nodes_for_wire(nodes, ttn, comps, _wire("R3", 0, "R4", 0), wire_index=1)
        assert len(nodes) == 2
        # Merge by connecting R2 to R3
        update_nodes_for_wire(nodes, ttn, comps, _wire("R2", 0, "R3", 0), wire_index=2)
        assert len(nodes) == 1
        assert ttn[("R1", 0)] is ttn[("R4", 0)]

    def test_ground_propagation(self):
        nodes, ttn = [], {}
        comps = {"R1": _comp("R1"), "GND1": _comp("GND1", "Ground")}
        update_nodes_for_wire(nodes, ttn, comps, _wire("R1", 0, "GND1", 0), wire_index=0)
        assert nodes[0].is_ground


# ------------------------------------------------------------------
# shift_wire_indices
# ------------------------------------------------------------------


class TestShiftWireIndices:
    def test_removes_deleted_index(self):
        node = NodeData()
        node.wire_indices = {0, 1, 2}
        shift_wire_indices([node], removed_index=1)
        assert node.wire_indices == {0, 1}  # was {0, 2} → shifted

    def test_decrements_higher_indices(self):
        node = NodeData()
        node.wire_indices = {3, 5, 7}
        shift_wire_indices([node], removed_index=4)
        assert node.wire_indices == {3, 4, 6}

    def test_keeps_lower_indices(self):
        node = NodeData()
        node.wire_indices = {0, 1}
        shift_wire_indices([node], removed_index=5)
        assert node.wire_indices == {0, 1}


# ------------------------------------------------------------------
# rebuild_nodes_after_wire_removal
# ------------------------------------------------------------------


class TestRebuildNodesAfterWireRemoval:
    def setup_method(self):
        reset_node_counter()

    def test_splits_node_when_bridge_wire_removed(self):
        """Removing a wire that bridges two clusters should split the node."""
        nodes, ttn = [], {}
        comps = {"R1": _comp("R1"), "R2": _comp("R2"), "R3": _comp("R3")}
        wires = [
            _wire("R1", 0, "R2", 0),  # wire 0: merges R1:0 and R2:0
            _wire("R2", 0, "R3", 0),  # wire 1: extends with R3:0 (shares R2:0)
        ]
        for i, w in enumerate(wires):
            update_nodes_for_wire(nodes, ttn, comps, w, wire_index=i)
        assert len(nodes) == 1
        affected = nodes[0]

        # Remove wire 1 (bridge between R2:0 and R3:0)
        del wires[1]
        shift_wire_indices(nodes, removed_index=1)
        rebuild_nodes_after_wire_removal(nodes, ttn, comps, wires, affected)

        # R1:0 and R2:0 still connected via wire 0; R3:0 now orphaned (no node)
        assert len(nodes) == 1
        assert ("R1", 0) in ttn
        assert ("R2", 0) in ttn
        assert ("R3", 0) not in ttn

    def test_preserves_custom_label(self):
        nodes, ttn = [], {}
        comps = {"R1": _comp("R1"), "R2": _comp("R2"), "R3": _comp("R3")}
        wires = [
            _wire("R1", 0, "R2", 0),  # wire 0
            _wire("R2", 0, "R3", 0),  # wire 1 (shares R2:0)
        ]
        for i, w in enumerate(wires):
            update_nodes_for_wire(nodes, ttn, comps, w, wire_index=i)
        nodes[0].set_custom_label("VCC")

        affected = nodes[0]
        del wires[1]
        shift_wire_indices(nodes, removed_index=1)
        rebuild_nodes_after_wire_removal(nodes, ttn, comps, wires, affected)

        assert nodes[0].custom_label == "VCC"


# ------------------------------------------------------------------
# rebuild_all_nodes
# ------------------------------------------------------------------


class TestRebuildAllNodes:
    def setup_method(self):
        reset_node_counter()

    def test_basic_rebuild(self):
        comps = {"R1": _comp("R1"), "R2": _comp("R2")}
        wires = [_wire("R1", 0, "R2", 0)]
        nodes, ttn = [], {}
        rebuild_all_nodes(nodes, ttn, comps, wires)
        assert len(nodes) == 1
        assert ("R1", 0) in ttn
        assert ("R2", 0) in ttn

    def test_preserves_custom_labels(self):
        comps = {"R1": _comp("R1"), "R2": _comp("R2")}
        wires = [_wire("R1", 0, "R2", 0)]
        nodes, ttn = [], {}
        rebuild_all_nodes(nodes, ttn, comps, wires)
        nodes[0].set_custom_label("Vout")

        rebuild_all_nodes(nodes, ttn, comps, wires)
        assert nodes[0].custom_label == "Vout"

    def test_ground_nodes_rebuilt(self):
        comps = {"R1": _comp("R1"), "GND1": _comp("GND1", "Ground")}
        wires = [_wire("R1", 0, "GND1", 0)]
        nodes, ttn = [], {}
        rebuild_all_nodes(nodes, ttn, comps, wires)
        assert len(nodes) == 1
        assert nodes[0].is_ground
