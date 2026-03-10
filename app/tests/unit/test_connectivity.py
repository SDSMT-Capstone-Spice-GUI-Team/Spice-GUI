"""Tests for utils.connectivity – pure-function connectivity analysis."""

from models.component import ComponentData
from models.node import NodeData
from utils.connectivity import find_floating_terminals


def _comp(cid, ctype="Resistor"):
    return ComponentData(component_id=cid, component_type=ctype, value="1k", position=(0, 0))


class TestFindFloatingTerminals:
    def test_empty_circuit(self):
        assert find_floating_terminals({}, {}) == set()

    def test_single_unconnected_resistor(self):
        comps = {"R1": _comp("R1")}
        floating = find_floating_terminals(comps, {})
        assert floating == {("R1", 0), ("R1", 1)}

    def test_fully_connected(self):
        comps = {"R1": _comp("R1"), "V1": _comp("V1", "Voltage Source")}
        node = NodeData()
        ttn = {
            ("R1", 0): node,
            ("R1", 1): node,
            ("V1", 0): node,
            ("V1", 1): node,
        }
        floating = find_floating_terminals(comps, ttn)
        assert floating == set()

    def test_partially_connected(self):
        comps = {"R1": _comp("R1")}
        node = NodeData()
        ttn = {("R1", 0): node}
        floating = find_floating_terminals(comps, ttn)
        assert floating == {("R1", 1)}

    def test_ground_excluded(self):
        comps = {"GND1": _comp("GND1", "Ground")}
        floating = find_floating_terminals(comps, {})
        assert floating == set()

    def test_ground_mixed_with_other(self):
        comps = {
            "R1": _comp("R1"),
            "GND1": _comp("GND1", "Ground"),
        }
        floating = find_floating_terminals(comps, {})
        # Only R1 terminals should be floating, not ground
        assert floating == {("R1", 0), ("R1", 1)}

    def test_multiple_components(self):
        comps = {
            "R1": _comp("R1"),
            "R2": _comp("R2"),
        }
        node = NodeData()
        ttn = {("R1", 0): node, ("R2", 0): node}
        floating = find_floating_terminals(comps, ttn)
        assert floating == {("R1", 1), ("R2", 1)}
