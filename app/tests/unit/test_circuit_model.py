"""Tests for CircuitModel central data store."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.node import reset_node_counter
from models.wire import WireData


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
        model.analysis_type = "Transient"
        model.analysis_params = {"step": "1m", "duration": "10m"}
        model.clear()
        assert len(model.components) == 0
        assert len(model.wires) == 0
        assert len(model.nodes) == 0
        assert len(model.terminal_to_node) == 0
        assert len(model.component_counter) == 0
        assert model.analysis_type == "DC Operating Point"
        assert model.analysis_params == {}


class TestSerialization:
    def test_to_dict_matches_format(self):
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(100.0, 200.0)))
        model.add_component(_voltage_source("V1", pos=(50.0, 50.0)))
        model.add_wire(_wire("R1", 1, "V1", 0))
        model.component_counter = {"R": 1, "V": 1}

        data = model.to_dict()
        assert "components" in data
        assert "wires" in data
        assert "counters" in data
        assert len(data["components"]) == 2
        assert len(data["wires"]) == 1
        assert data["counters"] == {"R": 1, "V": 1}

    def test_from_dict_restores_state(self):
        data = {
            "components": [
                {
                    "type": "Resistor",
                    "id": "R1",
                    "value": "1k",
                    "pos": {"x": 100.0, "y": 200.0},
                    "rotation": 0,
                },
                {
                    "type": "VoltageSource",
                    "id": "V1",
                    "value": "5V",
                    "pos": {"x": 50.0, "y": 50.0},
                    "rotation": 0,
                },
            ],
            "wires": [
                {"start_comp": "R1", "start_term": 1, "end_comp": "V1", "end_term": 0},
            ],
            "counters": {"R": 1, "V": 1},
        }
        model = CircuitModel.from_dict(data)
        assert len(model.components) == 2
        assert "R1" in model.components
        assert "V1" in model.components
        assert model.components["V1"].component_type == "Voltage Source"
        assert len(model.wires) == 1
        assert model.component_counter == {"R": 1, "V": 1}
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
        assert data == {"components": [], "wires": [], "counters": {}}

        reset_node_counter()
        model2 = CircuitModel.from_dict(data)
        assert model2.to_dict() == data

    def test_analysis_settings_persisted(self):
        """Analysis type and params survive save/load round-trip."""
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(0.0, 0.0)))
        model.analysis_type = "Transient"
        model.analysis_params = {"step": "1m", "duration": "10m", "start": 0}

        data = model.to_dict()
        assert data["analysis_type"] == "Transient"
        assert data["analysis_params"] == {"step": "1m", "duration": "10m", "start": 0}

        reset_node_counter()
        model2 = CircuitModel.from_dict(data)
        assert model2.analysis_type == "Transient"
        assert model2.analysis_params == {"step": "1m", "duration": "10m", "start": 0}

    def test_default_analysis_omitted_from_dict(self):
        """Default DC Operating Point should not bloat the JSON."""
        model = CircuitModel()
        data = model.to_dict()
        assert "analysis_type" not in data
        assert "analysis_params" not in data

    def test_from_dict_without_analysis_uses_defaults(self):
        """Loading old circuit files without analysis fields uses defaults."""
        data = {
            "components": [],
            "wires": [],
            "counters": {},
        }
        model = CircuitModel.from_dict(data)
        assert model.analysis_type == "DC Operating Point"
        assert model.analysis_params == {}

    def test_net_names_round_trip(self):
        """Custom net names survive save/load round-trip."""
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(100.0, 200.0)))
        model.add_component(_voltage_source("V1", pos=(50.0, 50.0)))
        model.add_wire(_wire("R1", 1, "V1", 0))
        model.component_counter = {"R": 1, "V": 1}

        # Set a custom net name on the node
        node = model.nodes[0]
        node.set_custom_label("Vout")
        assert node.get_label() == "Vout"

        data = model.to_dict()
        assert "net_names" in data
        assert len(data["net_names"]) == 1

        reset_node_counter()
        model2 = CircuitModel.from_dict(data)
        # The node should have the custom label restored
        assert len(model2.nodes) == 1
        assert model2.nodes[0].custom_label == "Vout"
        assert model2.nodes[0].get_label() == "Vout"

    def test_net_names_multiple_labels(self):
        """Multiple net names are all persisted and restored."""
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(0.0, 0.0)))
        model.add_component(_resistor("R2", pos=(100.0, 0.0)))
        model.add_component(_voltage_source("V1", pos=(50.0, 50.0)))
        model.add_wire(_wire("R1", 1, "R2", 0))  # node between R1 and R2
        model.add_wire(_wire("V1", 0, "R1", 0))  # node between V1 and R1
        model.component_counter = {"R": 2, "V": 1}

        # Name both nodes
        node_between_r1_r2 = model.terminal_to_node[("R1", 1)]
        node_between_v1_r1 = model.terminal_to_node[("V1", 0)]
        node_between_r1_r2.set_custom_label("Vmid")
        node_between_v1_r1.set_custom_label("Vin")

        data = model.to_dict()
        assert len(data["net_names"]) == 2

        reset_node_counter()
        model2 = CircuitModel.from_dict(data)
        restored_mid = model2.terminal_to_node[("R1", 1)]
        restored_in = model2.terminal_to_node[("V1", 0)]
        assert restored_mid.custom_label == "Vmid"
        assert restored_in.custom_label == "Vin"

    def test_net_names_omitted_when_none(self):
        """net_names key is omitted from JSON when no custom labels exist."""
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(0.0, 0.0)))
        model.add_component(_resistor("R2", pos=(100.0, 0.0)))
        model.add_wire(_wire("R1", 1, "R2", 0))
        model.component_counter = {"R": 2}

        data = model.to_dict()
        assert "net_names" not in data

    def test_net_names_cleared_label_not_persisted(self):
        """A label set then cleared (None) is not saved."""
        model = CircuitModel()
        model.add_component(_resistor("R1", pos=(0.0, 0.0)))
        model.add_component(_resistor("R2", pos=(100.0, 0.0)))
        model.add_wire(_wire("R1", 1, "R2", 0))

        node = model.nodes[0]
        node.set_custom_label("Vout")
        node.set_custom_label(None)  # Clear it

        data = model.to_dict()
        assert "net_names" not in data

    def test_old_files_without_net_names_load_fine(self):
        """Circuit files from before net names feature load without error."""
        data = {
            "components": [
                {
                    "type": "Resistor",
                    "id": "R1",
                    "value": "1k",
                    "pos": {"x": 0.0, "y": 0.0},
                    "rotation": 0,
                },
            ],
            "wires": [],
            "counters": {"R": 1},
        }
        model = CircuitModel.from_dict(data)
        assert len(model.components) == 1
        # No custom labels should be set
        for node in model.nodes:
            assert node.custom_label is None

    def test_no_pyqt_imports(self):
        """Verify CircuitModel has no Qt dependencies."""
        import models.circuit as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
