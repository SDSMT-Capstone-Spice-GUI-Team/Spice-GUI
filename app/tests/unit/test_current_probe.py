"""Tests for Current Probe component (#457)."""

from models.component import (
    COMPONENT_CATEGORIES,
    COMPONENT_COLORS,
    COMPONENT_TYPES,
    DEFAULT_VALUES,
    SPICE_SYMBOLS,
    TERMINAL_GEOMETRY,
    ComponentData,
)
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator
from tests.conftest import make_component, make_wire


class TestCurrentProbeRegistration:
    """Current Probe is registered in all component dictionaries."""

    def test_in_types(self):
        assert "Current Probe" in COMPONENT_TYPES

    def test_spice_symbol(self):
        assert SPICE_SYMBOLS["Current Probe"] == "VP"

    def test_in_other_category(self):
        assert "Current Probe" in COMPONENT_CATEGORIES["Other"]

    def test_default_value_is_zero(self):
        assert DEFAULT_VALUES["Current Probe"] == "0"

    def test_has_color(self):
        assert "Current Probe" in COMPONENT_COLORS

    def test_has_geometry(self):
        assert "Current Probe" in TERMINAL_GEOMETRY

    def test_two_terminals(self):
        comp = make_component("Current Probe", "VP1", "0", (0, 0))
        assert comp.get_terminal_count() == 2


class TestCurrentProbeComponentData:
    def test_serialization_roundtrip(self):
        comp = make_component("Current Probe", "VP1", "0", (50, 100))
        d = comp.to_dict()
        assert d["type"] == "CurrentProbe"
        restored = ComponentData.from_dict(d)
        assert restored.component_type == "Current Probe"
        assert restored.value == "0"


def _build_probe_circuit():
    """V1 -- CurrentProbe -- R1 -- GND, with V1- to GND."""
    components = {
        "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
        "VP1": make_component("Current Probe", "VP1", "0", (100, 0)),
        "R1": make_component("Resistor", "R1", "1k", (200, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
    }
    wires = [
        make_wire("V1", 0, "VP1", 0),
        make_wire("VP1", 1, "R1", 0),
        make_wire("R1", 1, "GND1", 0),
        make_wire("V1", 1, "GND1", 0),
    ]
    node_a = NodeData(
        terminals={("V1", 0), ("VP1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_b = NodeData(
        terminals={("VP1", 1), ("R1", 0)},
        wire_indices={1},
        auto_label="nodeB",
    )
    node_gnd = NodeData(
        terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
        wire_indices={2, 3},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_b, node_gnd]
    t2n = {
        ("V1", 0): node_a,
        ("VP1", 0): node_a,
        ("VP1", 1): node_b,
        ("R1", 0): node_b,
        ("R1", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, nodes, t2n


class TestCurrentProbeNetlist:
    """Current Probe generates a 0V source and prints i(probe_id)."""

    def test_probe_is_zero_volt_source(self):
        components, wires, nodes, t2n = _build_probe_circuit()
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        # Should appear as a 0V source line
        assert "VP1 nodeA nodeB 0" in netlist

    def test_probe_prints_current(self):
        components, wires, nodes, t2n = _build_probe_circuit()
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        # Should include print/wrdata with i(VP1)
        assert "i(VP1)" in netlist
