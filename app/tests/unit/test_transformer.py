"""
Tests for the Transformer (coupled inductor) component.

Covers model registration, netlist generation, and structural assertions.
"""

import pytest
from models.component import (
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def transformer_circuit():
    """
    Simple transformer circuit:

    V1 (AC source) → primary winding → GND
    Secondary winding → R1 (load) → GND

    Terminals: 0=prim+, 1=prim-, 2=sec+, 3=sec-
    """
    components = {
        "V1": make_component("Voltage Source", "V1", "10V", (0, 0)),
        "K1": make_component("Transformer", "K1", "10mH 10mH 0.99", (100, 0)),
        "R1": make_component("Resistor", "R1", "1k", (200, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }
    wires = [
        make_wire("V1", 0, "K1", 0),  # V1+ to primary+
        make_wire("V1", 1, "K1", 1),  # V1- to primary-
        make_wire("K1", 2, "R1", 0),  # secondary+ to R1
        make_wire("K1", 3, "R1", 1),  # secondary- to R1 (return)
        make_wire("K1", 1, "GND1", 0),  # primary- to GND
        make_wire("R1", 1, "GND1", 0),  # R1 return to GND
    ]

    node_v1p = NodeData(
        terminals={("V1", 0), ("K1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_gnd = NodeData(
        terminals={("V1", 1), ("K1", 1), ("GND1", 0), ("K1", 3), ("R1", 1)},
        wire_indices={1, 4, 5},
        is_ground=True,
        auto_label="0",
    )
    node_sec = NodeData(
        terminals={("K1", 2), ("R1", 0)},
        wire_indices={2},
        auto_label="nodeB",
    )
    nodes = [node_v1p, node_gnd, node_sec]

    terminal_to_node = {
        ("V1", 0): node_v1p,
        ("K1", 0): node_v1p,
        ("V1", 1): node_gnd,
        ("K1", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("K1", 2): node_sec,
        ("R1", 0): node_sec,
        ("K1", 3): node_gnd,
        ("R1", 1): node_gnd,
    }

    return components, wires, nodes, terminal_to_node


# ---------------------------------------------------------------------------
# Model registration
# ---------------------------------------------------------------------------


class TestTransformerModel:
    def test_in_component_types(self):
        assert "Transformer" in COMPONENT_TYPES

    def test_spice_symbol(self):
        assert SPICE_SYMBOLS["Transformer"] == "K"

    def test_terminal_count(self):
        assert TERMINAL_COUNTS["Transformer"] == 4

    def test_default_value(self):
        assert DEFAULT_VALUES["Transformer"] == "10mH 10mH 0.99"

    def test_color_defined(self):
        assert "Transformer" in COMPONENT_COLORS

    def test_terminal_geometry(self):
        geom = TERMINAL_GEOMETRY["Transformer"]
        _, _, base_terminals = geom
        assert base_terminals is not None
        assert len(base_terminals) == 4

    def test_component_data_terminal_count(self):
        comp = ComponentData(
            component_id="K1",
            component_type="Transformer",
            value="10mH 10mH 0.99",
            position=(0, 0),
        )
        assert comp.get_terminal_count() == 4

    def test_component_data_spice_symbol(self):
        comp = ComponentData(
            component_id="K1",
            component_type="Transformer",
            value="10mH 10mH 0.99",
            position=(0, 0),
        )
        assert comp.get_spice_symbol() == "K"

    def test_serialization_round_trip(self):
        comp = ComponentData(
            component_id="K1",
            component_type="Transformer",
            value="5mH 20mH 0.95",
            position=(10, 20),
            rotation=90,
        )
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.component_type == "Transformer"
        assert restored.value == "5mH 20mH 0.95"
        assert restored.position == (10, 20)
        assert restored.rotation == 90


# ---------------------------------------------------------------------------
# Netlist generation
# ---------------------------------------------------------------------------


class TestTransformerNetlist:
    def test_emits_two_inductor_lines(self, transformer_circuit):
        components, wires, nodes, t2n = transformer_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        assert "L_prim_K1" in netlist
        assert "L_sec_K1" in netlist

    def test_emits_coupling_statement(self, transformer_circuit):
        components, wires, nodes, t2n = transformer_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        assert "K_K1 L_prim_K1 L_sec_K1 0.99" in netlist

    def test_inductor_values_from_component(self, transformer_circuit):
        components, wires, nodes, t2n = transformer_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        lines = netlist.split("\n")
        prim_lines = [l for l in lines if l.startswith("L_prim_K1")]
        sec_lines = [l for l in lines if l.startswith("L_sec_K1")]
        assert len(prim_lines) == 1
        assert "10mH" in prim_lines[0]
        assert len(sec_lines) == 1
        assert "10mH" in sec_lines[0]

    def test_custom_values(self):
        """Transformer with custom inductance and coupling."""
        components = {
            "K1": make_component("Transformer", "K1", "5mH 20mH 0.95", (0, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("K1", 0, "GND1", 0),
            make_wire("K1", 1, "GND1", 0),
            make_wire("K1", 2, "GND1", 0),
            make_wire("K1", 3, "GND1", 0),
        ]
        node_gnd = NodeData(
            terminals={("K1", 0), ("K1", 1), ("K1", 2), ("K1", 3), ("GND1", 0)},
            wire_indices={0, 1, 2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_gnd]
        t2n = {
            ("K1", 0): node_gnd,
            ("K1", 1): node_gnd,
            ("K1", 2): node_gnd,
            ("K1", 3): node_gnd,
            ("GND1", 0): node_gnd,
        }
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        lines = netlist.split("\n")
        prim_line = [l for l in lines if l.startswith("L_prim_K1")][0]
        sec_line = [l for l in lines if l.startswith("L_sec_K1")][0]
        coupling_line = [l for l in lines if l.startswith("K_K1")][0]
        assert "5mH" in prim_line
        assert "20mH" in sec_line
        assert "0.95" in coupling_line

    def test_partial_value_defaults(self):
        """When value only has one inductance, defaults are used for missing parts."""
        components = {
            "K1": make_component("Transformer", "K1", "15mH", (0, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("K1", 0, "GND1", 0),
            make_wire("K1", 1, "GND1", 0),
            make_wire("K1", 2, "GND1", 0),
            make_wire("K1", 3, "GND1", 0),
        ]
        node_gnd = NodeData(
            terminals={("K1", 0), ("K1", 1), ("K1", 2), ("K1", 3), ("GND1", 0)},
            wire_indices={0, 1, 2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_gnd]
        t2n = {
            ("K1", 0): node_gnd,
            ("K1", 1): node_gnd,
            ("K1", 2): node_gnd,
            ("K1", 3): node_gnd,
            ("GND1", 0): node_gnd,
        }
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        lines = netlist.split("\n")
        prim_line = [l for l in lines if l.startswith("L_prim_K1")][0]
        sec_line = [l for l in lines if l.startswith("L_sec_K1")][0]
        coupling_line = [l for l in lines if l.startswith("K_K1")][0]
        assert "15mH" in prim_line
        assert "10mH" in sec_line  # default secondary
        assert "0.99" in coupling_line  # default coupling

    def test_no_ground_line_for_transformer(self, transformer_circuit):
        """Transformer itself should not appear as a bare K1 component line."""
        components, wires, nodes, t2n = transformer_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        lines = netlist.split("\n")
        # Should not have a line starting with just "K1 " (that would be wrong)
        bare_k1_lines = [l for l in lines if l.startswith("K1 ")]
        assert len(bare_k1_lines) == 0


# ---------------------------------------------------------------------------
# GUI class registry
# ---------------------------------------------------------------------------


class TestTransformerGUI:
    def test_in_component_classes(self):
        from GUI.component_item import COMPONENT_CLASSES

        assert "Transformer" in COMPONENT_CLASSES

    def test_class_type_name(self):
        from GUI.component_item import Transformer

        assert Transformer.type_name == "Transformer"

    def test_tooltip_defined(self):
        from GUI.component_palette import COMPONENT_TOOLTIPS

        assert "Transformer" in COMPONENT_TOOLTIPS

    def test_color_key_in_constants(self):
        from GUI.styles.constants import COMPONENTS

        assert "Transformer" in COMPONENTS
        assert COMPONENTS["Transformer"]["terminals"] == 4
        assert COMPONENTS["Transformer"]["symbol"] == "K"
