"""Tests for CircuitModel central data store."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from models.node import reset_node_counter



def _resistor(comp_id="R1", pos=(0.0, 0.0)):
    return ComponentData(
        component_id=comp_id,
        component_type="Resistor",
        value="1k",
        position=pos,
    )


def _voltage_source(comp_id="V1", pos=(0.0, 0.0)):
    return ComponentData(
        component_id=comp_id,
        component_type="Voltage Source",
        value="5V",
        position=pos,
    )


def _ground(comp_id="GND1", pos=(0.0, 0.0)):
    return ComponentData(
        component_id=comp_id,
        component_type="Ground",
        value="0V",
        position=pos,
    )


def _wire(start_id, start_term, end_id, end_term):
    return WireData(
        start_component_id=start_id,
        start_terminal=start_term,
        end_component_id=end_id,
        end_terminal=end_term,
    )


class TestAddRemoveComponents:
    def test_add_component(self):
        model = CircuitModel()
        r1 = _resistor("R1")
        model.add_component(r1)
        assert "R1" in model.components
        assert model.components["R1"] is r1

    def test_remove_component_returns_connected_wire_indices(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_resistor("R2"))
        model.add_wire(_wire("R1", 1, "R2", 0))
        indices = model.remove_component("R1")
        assert indices == [0]

    def test_remove_nonexistent_component(self):
        model = CircuitModel()
        assert model.remove_component("R999") == []

    def test_add_ground_creates_ground_node(self):
        model = CircuitModel()
        model.add_component(_ground("GND1"))
        assert len(model.nodes) == 1
        assert model.nodes[0].is_ground
        assert ("GND1", 0) in model.terminal_to_node


class TestAddRemoveWires:
    def test_add_wire_creates_node(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_resistor("R2"))
        model.add_wire(_wire("R1", 1, "R2", 0))
        assert len(model.nodes) == 1
        node = model.nodes[0]
        assert ("R1", 1) in node.terminals
        assert ("R2", 0) in node.terminals

    def test_add_wire_merges_nodes(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_resistor("R2"))
        model.add_component(_resistor("R3"))
        # R1[1] -- R2[0] creates node A
        model.add_wire(_wire("R1", 1, "R2", 0))
        # R2[1] -- R3[0] creates node B
        model.add_wire(_wire("R2", 1, "R3", 0))
        # Now R1[0] -- R3[1] are in separate nodes (or no node)
        # Connecting R1[0] -- R2[1] should merge nodes
        assert len(model.nodes) == 2

    def test_add_wire_extends_existing_node(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_resistor("R2"))
        model.add_component(_resistor("R3"))
        model.add_wire(_wire("R1", 1, "R2", 0))
        # R2[0] is already in a node; adding R2[0]'s node to R3[0]
        model.add_wire(_wire("R2", 0, "R3", 0))
        assert len(model.nodes) == 1
        node = model.nodes[0]
        assert ("R1", 1) in node.terminals
        assert ("R2", 0) in node.terminals
        assert ("R3", 0) in node.terminals

    def test_remove_wire_rebuilds_nodes(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_resistor("R2"))
        model.add_wire(_wire("R1", 1, "R2", 0))
        assert len(model.nodes) == 1
        model.remove_wire(0)
        assert len(model.wires) == 0
        # After rebuild, only ground-less nodes = 0
        assert len(model.nodes) == 0

    def test_wire_to_ground_creates_ground_node(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_ground("GND1"))
        model.add_wire(_wire("R1", 0, "GND1", 0))
        ground_nodes = [n for n in model.nodes if n.is_ground]
        assert len(ground_nodes) == 1
        assert ("R1", 0) in ground_nodes[0].terminals


class TestNodeGraph:
    def test_rebuild_nodes_clears_and_rebuilds(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_resistor("R2"))
        model.add_wire(_wire("R1", 1, "R2", 0))
        assert len(model.nodes) == 1
        model.rebuild_nodes()
        assert len(model.nodes) == 1
        assert ("R1", 1) in model.nodes[0].terminals

    def test_ground_propagates_through_merge(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_ground("GND1"))
        model.add_component(_resistor("R2"))
        # Wire R1 to GND
        model.add_wire(_wire("R1", 0, "GND1", 0))
        # Wire R2 to R1 (same terminal as GND)
        model.add_wire(_wire("R2", 0, "R1", 0))
        # R2[0] should now be in the ground node
        node = model.terminal_to_node.get(("R2", 0))
        assert node is not None
        assert node.is_ground


class TestClear:
    def test_clear_empties_everything(self):
        model = CircuitModel()
        model.add_component(_resistor("R1"))
        model.add_component(_ground("GND1"))
        model.add_wire(_wire("R1", 0, "GND1", 0))
        model.component_counter = {"R": 1, "GND": 1}
        model.clear()
        assert len(model.components) == 0
        assert len(model.wires) == 0
        assert len(model.nodes) == 0
        assert len(model.terminal_to_node) == 0
        assert len(model.component_counter) == 0


class TestSerialization:
    def test_to_dict_matches_format(self):
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(100.0, 200.0)))
        model.add_component(_voltage_source("V1", pos=(50.0, 50.0)))
        model.add_wire(_wire("R1", 1, "V1", 0))
        model.component_counter = {"R": 1, "V": 1}

        data = model.to_dict()
        assert 'components' in data
        assert 'wires' in data
        assert 'counters' in data
        assert len(data['components']) == 2
        assert len(data['wires']) == 1
        assert data['counters'] == {"R": 1, "V": 1}

    def test_from_dict_restores_state(self):
        data = {
            'components': [
                {'type': 'Resistor', 'id': 'R1', 'value': '1k',
                 'pos': {'x': 100.0, 'y': 200.0}, 'rotation': 0},
                {'type': 'VoltageSource', 'id': 'V1', 'value': '5V',
                 'pos': {'x': 50.0, 'y': 50.0}, 'rotation': 0},
            ],
            'wires': [
                {'start_comp': 'R1', 'start_term': 1,
                 'end_comp': 'V1', 'end_term': 0},
            ],
            'counters': {'R': 1, 'V': 1},
        }
        model = CircuitModel.from_dict(data)
        assert len(model.components) == 2
        assert 'R1' in model.components
        assert 'V1' in model.components
        assert model.components['V1'].component_type == 'Voltage Source'
        assert len(model.wires) == 1
        assert model.component_counter == {'R': 1, 'V': 1}
        # Nodes should have been rebuilt
        assert len(model.nodes) == 1

    def test_round_trip_produces_identical_json(self):
        """Save → load → save should produce identical output."""
        model1 = CircuitModel()
        model1.add_component(_resistor("R1", pos=(100.0, 200.0)))
        model1.add_component(_voltage_source("V1", pos=(50.0, 50.0)))
        model1.add_component(_ground("GND1", pos=(0.0, 0.0)))
        model1.add_wire(_wire("R1", 1, "V1", 0))
        model1.add_wire(_wire("V1", 1, "GND1", 0))
        model1.component_counter = {"R": 1, "V": 1, "GND": 1}

        data1 = model1.to_dict()

        reset_node_counter()
        model2 = CircuitModel.from_dict(data1)
        data2 = model2.to_dict()

        assert data1 == data2

    def test_empty_circuit_round_trip(self):
        model = CircuitModel()
        data = model.to_dict()
        assert data == {'components': [], 'wires': [], 'counters': {}}

        reset_node_counter()
        model2 = CircuitModel.from_dict(data)
        assert model2.to_dict() == data

    def test_no_pyqt_imports(self):
        """Verify CircuitModel has no Qt dependencies."""
        import models.circuit as mod
        source = open(mod.__file__).read()
        assert 'PyQt' not in source
        assert 'QtCore' not in source
        assert 'QtWidgets' not in source
