"""Tests for AC Voltage Source and AC Current Source components (#735)."""

import pytest
from models.component import (
    COMPONENT_CATEGORIES,
    COMPONENT_COLORS,
    COMPONENT_TYPES,
    DEFAULT_VALUES,
    SPICE_SYMBOLS,
    TERMINAL_COUNTS,
    TERMINAL_GEOMETRY,
    ComponentData,
)
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator
from tests.conftest import make_component, make_wire


class TestACSourceRegistration:
    """AC sources are registered in all component dictionaries."""

    def test_ac_voltage_source_in_types(self):
        assert "AC Voltage Source" in COMPONENT_TYPES

    def test_ac_current_source_in_types(self):
        assert "AC Current Source" in COMPONENT_TYPES

    def test_ac_voltage_source_spice_symbol(self):
        assert SPICE_SYMBOLS["AC Voltage Source"] == "VAC"

    def test_ac_current_source_spice_symbol(self):
        assert SPICE_SYMBOLS["AC Current Source"] == "IAC"

    def test_ac_sources_in_sources_category(self):
        assert "AC Voltage Source" in COMPONENT_CATEGORIES["Sources"]
        assert "AC Current Source" in COMPONENT_CATEGORIES["Sources"]

    def test_ac_sources_have_default_values(self):
        assert "AC Voltage Source" in DEFAULT_VALUES
        assert "AC Current Source" in DEFAULT_VALUES

    def test_ac_sources_have_colors(self):
        assert "AC Voltage Source" in COMPONENT_COLORS
        assert "AC Current Source" in COMPONENT_COLORS

    def test_ac_sources_have_terminal_geometry(self):
        assert "AC Voltage Source" in TERMINAL_GEOMETRY
        assert "AC Current Source" in TERMINAL_GEOMETRY

    def test_ac_sources_have_two_terminals(self):
        # Default is 2, so they shouldn't appear in TERMINAL_COUNTS
        assert TERMINAL_COUNTS.get("AC Voltage Source", 2) == 2
        assert TERMINAL_COUNTS.get("AC Current Source", 2) == 2


class TestACSourceComponentData:
    """ComponentData works correctly with AC source types."""

    def test_create_ac_voltage_source(self):
        comp = make_component("AC Voltage Source", "VAC1", "1V 0", (0, 0))
        assert comp.component_type == "AC Voltage Source"
        assert comp.get_terminal_count() == 2

    def test_create_ac_current_source(self):
        comp = make_component("AC Current Source", "IAC1", "1A 0", (0, 0))
        assert comp.component_type == "AC Current Source"
        assert comp.get_terminal_count() == 2

    def test_ac_voltage_source_serialization_roundtrip(self):
        comp = make_component("AC Voltage Source", "VAC1", "1V 0", (50, 100))
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.component_type == "AC Voltage Source"
        assert restored.value == "1V 0"

    def test_ac_current_source_serialization_roundtrip(self):
        comp = make_component("AC Current Source", "IAC1", "2A 45", (50, 100))
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.component_type == "AC Current Source"
        assert restored.value == "2A 45"


def _build_ac_circuit(source_type, source_id, source_value):
    """Build a simple AC source + resistor + ground circuit."""
    components = {
        source_id: make_component(source_type, source_id, source_value, (0, 0)),
        "R1": make_component("Resistor", "R1", "1k", (100, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }
    wires = [
        make_wire(source_id, 0, "R1", 0),
        make_wire("R1", 1, "GND1", 0),
        make_wire(source_id, 1, "GND1", 0),
    ]
    node_a = NodeData(
        terminals={(source_id, 0), ("R1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_gnd = NodeData(
        terminals={("R1", 1), ("GND1", 0), (source_id, 1)},
        wire_indices={1, 2},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_gnd]
    t2n = {
        (source_id, 0): node_a,
        ("R1", 0): node_a,
        ("R1", 1): node_gnd,
        ("GND1", 0): node_gnd,
        (source_id, 1): node_gnd,
    }
    return components, wires, nodes, t2n


class TestACSourceNetlist:
    """AC sources generate correct SPICE netlist lines."""

    def test_ac_voltage_source_netlist(self):
        components, wires, nodes, t2n = _build_ac_circuit("AC Voltage Source", "VAC1", "1V 0")
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="AC Sweep",
            analysis_params={"fStart": 1, "fStop": 1e6, "points": 100},
        )
        netlist = gen.generate()
        assert "VAC1" in netlist
        assert "AC 1V 0" in netlist

    def test_ac_current_source_netlist(self):
        components, wires, nodes, t2n = _build_ac_circuit("AC Current Source", "IAC1", "1A 0")
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="AC Sweep",
            analysis_params={"fStart": 1, "fStop": 1e6, "points": 100},
        )
        netlist = gen.generate()
        assert "IAC1" in netlist
        assert "AC 1A 0" in netlist

    def test_ac_voltage_source_with_phase(self):
        components, wires, nodes, t2n = _build_ac_circuit("AC Voltage Source", "VAC1", "5V 45")
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="AC Sweep",
            analysis_params={"fStart": 1, "fStop": 1e6, "points": 100},
        )
        netlist = gen.generate()
        assert "AC 5V 45" in netlist
