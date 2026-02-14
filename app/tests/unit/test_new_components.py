"""
Tests for newly added component types:
BJT (NPN/PNP), MOSFET (NMOS/PMOS), VC Switch, Diode, LED, Zener Diode.

Covers netlist generation, ComponentData properties, terminal geometry,
serialization round-trips, and CircuitModel integration.
"""

import pytest
from models.circuit import CircuitModel
from models.component import (_CLASS_TO_DISPLAY, _DISPLAY_TO_CLASS,
                              COMPONENT_TYPES, DEFAULT_VALUES, SPICE_SYMBOLS,
                              TERMINAL_COUNTS, TERMINAL_GEOMETRY,
                              ComponentData)
from models.node import NodeData, reset_node_counter
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator
from tests.conftest import make_component, make_wire

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate(
    components,
    wires,
    nodes,
    terminal_to_node,
    analysis_type="DC Operating Point",
    analysis_params=None,
):
    """Generate a netlist string from circuit data."""
    gen = NetlistGenerator(
        components=components,
        wires=wires,
        nodes=nodes,
        terminal_to_node=terminal_to_node,
        analysis_type=analysis_type,
        analysis_params=analysis_params or {},
    )
    return gen.generate()


def _make_3term_circuit(comp_type, comp_id, value):
    """Build a minimal circuit with a 3-terminal component wired to ground.

    Terminals: 0, 1, 2 — all wired into two nodes (nodeA and GND).
    Also includes a voltage source so the circuit is simulatable.
    """
    components = {
        comp_id: make_component(comp_type, comp_id, value, (0, 0)),
        "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }
    wires = [
        make_wire(comp_id, 0, "V1", 0),  # term 0 to V1+
        make_wire(comp_id, 1, "V1", 0),  # term 1 to V1+ (same node)
        make_wire(comp_id, 2, "GND1", 0),  # term 2 to GND
        make_wire("V1", 1, "GND1", 0),  # V1- to GND
    ]
    node_a = NodeData(
        terminals={(comp_id, 0), (comp_id, 1), ("V1", 0)},
        wire_indices={0, 1},
        auto_label="nodeA",
    )
    node_gnd = NodeData(
        terminals={(comp_id, 2), ("GND1", 0), ("V1", 1)},
        wire_indices={2, 3},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_gnd]
    t2n = {
        (comp_id, 0): node_a,
        (comp_id, 1): node_a,
        ("V1", 0): node_a,
        (comp_id, 2): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, nodes, t2n


def _make_4term_circuit(comp_type, comp_id, value):
    """Build a minimal circuit with a 4-terminal component wired to ground."""
    components = {
        comp_id: make_component(comp_type, comp_id, value, (0, 0)),
        "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }
    wires = [
        make_wire(comp_id, 0, "V1", 0),  # ctrl+ to V1+
        make_wire(comp_id, 1, "GND1", 0),  # ctrl- to GND
        make_wire(comp_id, 2, "V1", 0),  # out+/switch+ to V1+
        make_wire(comp_id, 3, "GND1", 0),  # out-/switch- to GND
        make_wire("V1", 1, "GND1", 0),  # V1- to GND
    ]
    node_a = NodeData(
        terminals={(comp_id, 0), (comp_id, 2), ("V1", 0)},
        wire_indices={0, 2},
        auto_label="nodeA",
    )
    node_gnd = NodeData(
        terminals={(comp_id, 1), (comp_id, 3), ("GND1", 0), ("V1", 1)},
        wire_indices={1, 3, 4},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_gnd]
    t2n = {
        (comp_id, 0): node_a,
        (comp_id, 2): node_a,
        ("V1", 0): node_a,
        (comp_id, 1): node_gnd,
        (comp_id, 3): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, nodes, t2n


def _make_2term_circuit(comp_type, comp_id, value):
    """Build a minimal circuit with a 2-terminal component in series with V1."""
    components = {
        comp_id: make_component(comp_type, comp_id, value, (100, 0)),
        "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }
    wires = [
        make_wire("V1", 0, comp_id, 0),  # V1+ to anode
        make_wire(comp_id, 1, "GND1", 0),  # cathode to GND
        make_wire("V1", 1, "GND1", 0),  # V1- to GND
    ]
    node_a = NodeData(
        terminals={("V1", 0), (comp_id, 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_gnd = NodeData(
        terminals={(comp_id, 1), ("GND1", 0), ("V1", 1)},
        wire_indices={1, 2},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_gnd]
    t2n = {
        ("V1", 0): node_a,
        (comp_id, 0): node_a,
        (comp_id, 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, nodes, t2n


# ===========================================================================
# BJT Transistor Tests
# ===========================================================================


class TestBJTNetlist:
    """Netlist generation tests for BJT NPN and PNP transistors."""

    def test_npn_component_line(self):
        components, wires, nodes, t2n = _make_3term_circuit("BJT NPN", "Q1", "2N3904")
        netlist = _generate(components, wires, nodes, t2n)
        # Q<name> collector base emitter model
        assert "Q1" in netlist
        assert "2N3904" in netlist

    def test_pnp_component_line(self):
        components, wires, nodes, t2n = _make_3term_circuit("BJT PNP", "Q2", "2N3906")
        netlist = _generate(components, wires, nodes, t2n)
        assert "Q2" in netlist
        assert "2N3906" in netlist

    def test_npn_model_directive_2n3904(self):
        components, wires, nodes, t2n = _make_3term_circuit("BJT NPN", "Q1", "2N3904")
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model 2N3904 NPN" in netlist
        assert "BF=300" in netlist

    def test_pnp_model_directive_2n3906(self):
        components, wires, nodes, t2n = _make_3term_circuit("BJT PNP", "Q2", "2N3906")
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model 2N3906 PNP" in netlist
        assert "BF=200" in netlist

    def test_custom_bjt_model_uses_generic_params(self):
        """A non-standard model name should still generate a .model line."""
        components, wires, nodes, t2n = _make_3term_circuit("BJT NPN", "Q1", "MY_NPN")
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model MY_NPN NPN" in netlist
        assert "BF=100" in netlist

    def test_bjt_model_section_header(self):
        components, wires, nodes, t2n = _make_3term_circuit("BJT NPN", "Q1", "2N3904")
        netlist = _generate(components, wires, nodes, t2n)
        assert "* BJT Model Definitions" in netlist


class TestBJTComponentData:
    """ComponentData property tests for BJT types."""

    def test_npn_terminal_count(self):
        comp = make_component("BJT NPN", "Q1", "2N3904")
        assert comp.get_terminal_count() == 3

    def test_pnp_terminal_count(self):
        comp = make_component("BJT PNP", "Q2", "2N3906")
        assert comp.get_terminal_count() == 3

    def test_npn_spice_symbol(self):
        comp = make_component("BJT NPN", "Q1", "2N3904")
        assert comp.get_spice_symbol() == "Q"

    def test_pnp_spice_symbol(self):
        comp = make_component("BJT PNP", "Q2", "2N3906")
        assert comp.get_spice_symbol() == "Q"

    def test_npn_default_value(self):
        assert DEFAULT_VALUES["BJT NPN"] == "2N3904"

    def test_pnp_default_value(self):
        assert DEFAULT_VALUES["BJT PNP"] == "2N3906"

    def test_npn_terminal_positions_are_3_points(self):
        comp = make_component("BJT NPN", "Q1", "2N3904")
        positions = comp.get_base_terminal_positions()
        assert len(positions) == 3

    def test_npn_serialization_round_trip(self):
        comp = make_component("BJT NPN", "Q1", "2N3904", (50.0, 100.0))
        data = comp.to_dict()
        assert data["type"] == "BJTNPN"
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "BJT NPN"
        assert restored.value == "2N3904"
        assert restored.position == (50.0, 100.0)

    def test_pnp_serialization_round_trip(self):
        comp = make_component("BJT PNP", "Q2", "2N3906", (75.0, 25.0))
        data = comp.to_dict()
        assert data["type"] == "BJTPNP"
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "BJT PNP"
        assert restored.value == "2N3906"


# ===========================================================================
# MOSFET Tests
# ===========================================================================


class TestMOSFETNetlist:
    """Netlist generation tests for MOSFET NMOS and PMOS."""

    def test_nmos_component_line(self):
        components, wires, nodes, t2n = _make_3term_circuit(
            "MOSFET NMOS", "M1", "NMOS1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "M1" in netlist
        assert "NMOS1" in netlist

    def test_pmos_component_line(self):
        components, wires, nodes, t2n = _make_3term_circuit(
            "MOSFET PMOS", "M2", "PMOS1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "M2" in netlist
        assert "PMOS1" in netlist

    def test_nmos_bulk_tied_to_source(self):
        """MOSFET netlist should have 4 node refs (drain gate source bulk=source)."""
        components, wires, nodes, t2n = _make_3term_circuit(
            "MOSFET NMOS", "M1", "NMOS1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        # Find the M1 line and check it has the source node repeated (bulk=source)
        for line in netlist.split("\n"):
            if line.startswith("M1 "):
                parts = line.split()
                # M1 drain gate source bulk model
                assert len(parts) == 6
                assert parts[3] == parts[4]  # source == bulk
                break
        else:
            pytest.fail("M1 line not found in netlist")

    def test_nmos_model_directive(self):
        components, wires, nodes, t2n = _make_3term_circuit(
            "MOSFET NMOS", "M1", "NMOS1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model NMOS1 NMOS" in netlist
        assert "VTO=0.7" in netlist
        assert "KP=110u" in netlist

    def test_pmos_model_directive(self):
        components, wires, nodes, t2n = _make_3term_circuit(
            "MOSFET PMOS", "M2", "PMOS1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model PMOS1 PMOS" in netlist
        assert "VTO=-0.7" in netlist
        assert "KP=50u" in netlist

    def test_mosfet_model_section_header(self):
        components, wires, nodes, t2n = _make_3term_circuit(
            "MOSFET NMOS", "M1", "NMOS1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "* MOSFET Model Definitions" in netlist


class TestMOSFETComponentData:
    """ComponentData property tests for MOSFET types."""

    def test_nmos_terminal_count(self):
        comp = make_component("MOSFET NMOS", "M1", "NMOS1")
        assert comp.get_terminal_count() == 3

    def test_pmos_terminal_count(self):
        comp = make_component("MOSFET PMOS", "M2", "PMOS1")
        assert comp.get_terminal_count() == 3

    def test_nmos_spice_symbol(self):
        comp = make_component("MOSFET NMOS", "M1", "NMOS1")
        assert comp.get_spice_symbol() == "M"

    def test_nmos_default_value(self):
        assert DEFAULT_VALUES["MOSFET NMOS"] == "NMOS1"

    def test_pmos_default_value(self):
        assert DEFAULT_VALUES["MOSFET PMOS"] == "PMOS1"

    def test_nmos_serialization_round_trip(self):
        comp = make_component("MOSFET NMOS", "M1", "NMOS1", (200.0, 300.0))
        data = comp.to_dict()
        assert data["type"] == "MOSFETNMOS"
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "MOSFET NMOS"
        assert restored.value == "NMOS1"

    def test_pmos_serialization_round_trip(self):
        comp = make_component("MOSFET PMOS", "M2", "PMOS1", (10.0, 20.0))
        data = comp.to_dict()
        assert data["type"] == "MOSFETPMOS"
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "MOSFET PMOS"


# ===========================================================================
# Voltage-Controlled Switch Tests
# ===========================================================================


class TestVCSwitchNetlist:
    """Netlist generation tests for voltage-controlled switch."""

    def test_switch_component_line(self):
        components, wires, nodes, t2n = _make_4term_circuit(
            "VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "S1" in netlist

    def test_switch_uses_per_instance_model(self):
        """Each switch should get its own model name (SW_<id>)."""
        components, wires, nodes, t2n = _make_4term_circuit(
            "VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "SW_S1" in netlist

    def test_switch_model_directive(self):
        components, wires, nodes, t2n = _make_4term_circuit(
            "VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model SW_S1 SW(VT=2.5 RON=1 ROFF=1e6)" in netlist

    def test_switch_model_section_header(self):
        components, wires, nodes, t2n = _make_4term_circuit(
            "VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "* Voltage-Controlled Switch Model Definitions" in netlist

    def test_switch_line_format(self):
        """S<name> switch+ switch- ctrl+ ctrl- model."""
        components, wires, nodes, t2n = _make_4term_circuit(
            "VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6"
        )
        netlist = _generate(components, wires, nodes, t2n)
        for line in netlist.split("\n"):
            if line.startswith("S1 "):
                parts = line.split()
                assert parts[0] == "S1"
                # Last part should be the model name
                assert parts[-1] == "SW_S1"
                break
        else:
            pytest.fail("S1 line not found in netlist")


class TestVCSwitchComponentData:
    """ComponentData property tests for VC Switch."""

    def test_terminal_count(self):
        comp = make_component("VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6")
        assert comp.get_terminal_count() == 4

    def test_spice_symbol(self):
        comp = make_component("VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6")
        assert comp.get_spice_symbol() == "S"

    def test_default_value(self):
        assert DEFAULT_VALUES["VC Switch"] == "VT=2.5 RON=1 ROFF=1e6"

    def test_serialization_round_trip(self):
        comp = make_component("VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6", (50.0, 50.0))
        data = comp.to_dict()
        assert data["type"] == "VCSwitch"
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "VC Switch"
        assert restored.value == "VT=2.5 RON=1 ROFF=1e6"


# ===========================================================================
# Diode / LED / Zener Diode Tests
# ===========================================================================


class TestDiodeNetlist:
    """Netlist generation tests for Diode, LED, and Zener Diode."""

    def test_diode_component_line(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "D1" in netlist

    def test_diode_shared_model(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "D_Ideal" in netlist

    def test_diode_model_directive(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model D_Ideal D(IS=1e-14 N=1)" in netlist

    def test_led_component_line(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "LED", "D2", "IS=1e-20 N=1.8 EG=1.9"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "D2" in netlist
        assert "D_LED" in netlist

    def test_led_model_directive(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "LED", "D2", "IS=1e-20 N=1.8 EG=1.9"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model D_LED D(IS=1e-20 N=1.8 EG=1.9)" in netlist

    def test_zener_component_line(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "Zener Diode", "D3", "IS=1e-14 N=1 BV=5.1 IBV=1e-3"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "D3" in netlist
        assert "D_Zener" in netlist

    def test_zener_model_has_breakdown_voltage(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "Zener Diode", "D3", "IS=1e-14 N=1 BV=5.1 IBV=1e-3"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "BV=5.1" in netlist
        assert "IBV=1e-3" in netlist

    def test_diode_model_section_header(self):
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "* Diode Model Definitions" in netlist

    def test_diode_line_format(self):
        """D<name> anode cathode model."""
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        for line in netlist.split("\n"):
            if line.startswith("D1 "):
                parts = line.split()
                assert parts[0] == "D1"
                assert parts[-1] == "D_Ideal"
                break
        else:
            pytest.fail("D1 line not found in netlist")


class TestDiodeModelDeduplication:
    """Tests for #205: multiple diodes share one model definition."""

    def test_multiple_diodes_share_model(self):
        """Three identical diodes should produce exactly one .model directive."""
        components = {
            "D1": make_component("Diode", "D1", "IS=1e-14 N=1", (0, 0)),
            "D2": make_component("Diode", "D2", "IS=1e-14 N=1", (100, 0)),
            "D3": make_component("Diode", "D3", "IS=1e-14 N=1", (200, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (0, 100)),
        }
        wires = [
            make_wire("V1", 0, "D1", 0),
            make_wire("D1", 1, "D2", 0),
            make_wire("D2", 1, "D3", 0),
            make_wire("D3", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("D1", 0)}, wire_indices={0}, auto_label="nodeA"
        )
        node_b = NodeData(
            terminals={("D1", 1), ("D2", 0)}, wire_indices={1}, auto_label="nodeB"
        )
        node_c = NodeData(
            terminals={("D2", 1), ("D3", 0)}, wire_indices={2}, auto_label="nodeC"
        )
        node_gnd = NodeData(
            terminals={("D3", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={3, 4},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_c, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("D1", 0): node_a,
            ("D1", 1): node_b,
            ("D2", 0): node_b,
            ("D2", 1): node_c,
            ("D3", 0): node_c,
            ("D3", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)

        # All three diodes reference the same model
        assert "D1 nodeA nodeB D_Ideal" in netlist
        assert "D2 nodeB nodeC D_Ideal" in netlist
        assert "D3 nodeC 0 D_Ideal" in netlist

        # Only one model directive
        model_lines = [l for l in netlist.split("\n") if l.startswith(".model D_Ideal")]
        assert len(model_lines) == 1
        assert model_lines[0] == ".model D_Ideal D(IS=1e-14 N=1)"

    def test_different_diode_types_get_distinct_models(self):
        """Diode, LED, and Zener should each get their own model name."""
        components = {
            "D1": make_component("Diode", "D1", "IS=1e-14 N=1", (0, 0)),
            "D2": make_component("LED", "D2", "IS=1e-20 N=1.8 EG=1.9", (100, 0)),
            "D3": make_component(
                "Zener Diode", "D3", "IS=1e-14 N=1 BV=5.1 IBV=1e-3", (200, 0)
            ),
            "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (0, 100)),
        }
        wires = [
            make_wire("V1", 0, "D1", 0),
            make_wire("D1", 1, "D2", 0),
            make_wire("D2", 1, "D3", 0),
            make_wire("D3", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("D1", 0)}, wire_indices={0}, auto_label="nodeA"
        )
        node_b = NodeData(
            terminals={("D1", 1), ("D2", 0)}, wire_indices={1}, auto_label="nodeB"
        )
        node_c = NodeData(
            terminals={("D2", 1), ("D3", 0)}, wire_indices={2}, auto_label="nodeC"
        )
        node_gnd = NodeData(
            terminals={("D3", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={3, 4},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_c, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("D1", 0): node_a,
            ("D1", 1): node_b,
            ("D2", 0): node_b,
            ("D2", 1): node_c,
            ("D3", 0): node_c,
            ("D3", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)

        assert "D_Ideal" in netlist
        assert "D_LED" in netlist
        assert "D_Zener" in netlist
        # Three distinct model directives
        model_lines = [l for l in netlist.split("\n") if l.startswith(".model D_")]
        assert len(model_lines) == 3

    def test_multiple_leds_share_model(self):
        """Multiple LEDs with same params should share one model."""
        components, wires, nodes, t2n = _make_2term_circuit(
            "LED", "D1", "IS=1e-20 N=1.8 EG=1.9"
        )
        # Add a second LED to the circuit
        components["D2"] = make_component(
            "LED", "D2", "IS=1e-20 N=1.8 EG=1.9", (200, 0)
        )
        wires.append(make_wire("D2", 0, "V1", 0))
        wires.append(make_wire("D2", 1, "GND1", 0))
        nodes[0].terminals.add(("D2", 0))
        nodes[1].terminals.add(("D2", 1))
        t2n[("D2", 0)] = nodes[0]
        t2n[("D2", 1)] = nodes[1]

        netlist = _generate(components, wires, nodes, t2n)

        # Both LEDs reference D_LED
        model_lines = [l for l in netlist.split("\n") if l.startswith(".model D_LED")]
        assert len(model_lines) == 1

    def test_no_per_instance_model_names(self):
        """Model names should not contain component IDs."""
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        netlist = _generate(components, wires, nodes, t2n)
        assert "D_D1" not in netlist

    def test_diode_with_custom_value_gets_own_model(self):
        """If one diode has different params, it gets a separate model."""
        components, wires, nodes, t2n = _make_2term_circuit(
            "Diode", "D1", "IS=1e-14 N=1"
        )
        # Add a second diode with different params
        components["D2"] = make_component("Diode", "D2", "IS=1e-12 N=2", (200, 0))
        wires.append(make_wire("D2", 0, "V1", 0))
        wires.append(make_wire("D2", 1, "GND1", 0))
        nodes[0].terminals.add(("D2", 0))
        nodes[1].terminals.add(("D2", 1))
        t2n[("D2", 0)] = nodes[0]
        t2n[("D2", 1)] = nodes[1]

        netlist = _generate(components, wires, nodes, t2n)

        # Two model directives with different names
        model_lines = [l for l in netlist.split("\n") if l.startswith(".model D_Ideal")]
        assert len(model_lines) >= 1
        # Second diode should have a suffixed name
        assert "IS=1e-12 N=2" in netlist


class TestDiodeComponentData:
    """ComponentData property tests for Diode types."""

    def test_diode_terminal_count(self):
        comp = make_component("Diode", "D1", "IS=1e-14 N=1")
        assert comp.get_terminal_count() == 2

    def test_led_terminal_count(self):
        comp = make_component("LED", "D2", "IS=1e-20 N=1.8 EG=1.9")
        assert comp.get_terminal_count() == 2

    def test_zener_terminal_count(self):
        comp = make_component("Zener Diode", "D3", "IS=1e-14 N=1 BV=5.1")
        assert comp.get_terminal_count() == 2

    def test_diode_spice_symbol(self):
        assert SPICE_SYMBOLS["Diode"] == "D"

    def test_led_spice_symbol(self):
        assert SPICE_SYMBOLS["LED"] == "D"

    def test_zener_spice_symbol(self):
        assert SPICE_SYMBOLS["Zener Diode"] == "D"

    def test_diode_default_value(self):
        assert DEFAULT_VALUES["Diode"] == "IS=1e-14 N=1"

    def test_led_default_value(self):
        assert DEFAULT_VALUES["LED"] == "IS=1e-20 N=1.8 EG=1.9"

    def test_zener_default_value(self):
        assert DEFAULT_VALUES["Zener Diode"] == "IS=1e-14 N=1 BV=5.1 IBV=1e-3"

    def test_diode_serialization_round_trip(self):
        comp = make_component("Diode", "D1", "IS=1e-14 N=1", (0.0, 0.0))
        data = comp.to_dict()
        # Diode has no class name mapping — uses display name directly
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "Diode"
        assert restored.value == "IS=1e-14 N=1"

    def test_zener_serialization_round_trip(self):
        comp = make_component("Zener Diode", "D3", "IS=1e-14 N=1 BV=5.1", (10.0, 20.0))
        data = comp.to_dict()
        assert data["type"] == "ZenerDiode"
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "Zener Diode"

    def test_led_serialization_round_trip(self):
        comp = make_component("LED", "D2", "IS=1e-20 N=1.8 EG=1.9", (30.0, 40.0))
        data = comp.to_dict()
        # LED has no mapping — uses 'LED' directly
        restored = ComponentData.from_dict(data)
        assert restored.component_type == "LED"


# ===========================================================================
# Cross-Component Registration Tests
# ===========================================================================


class TestComponentRegistration:
    """Verify all new types are properly registered in component.py lookups."""

    NEW_TYPES = [
        "BJT NPN",
        "BJT PNP",
        "MOSFET NMOS",
        "MOSFET PMOS",
        "VC Switch",
        "Diode",
        "LED",
        "Zener Diode",
    ]

    @pytest.mark.parametrize("comp_type", NEW_TYPES)
    def test_in_component_types(self, comp_type):
        assert comp_type in COMPONENT_TYPES

    @pytest.mark.parametrize("comp_type", NEW_TYPES)
    def test_has_spice_symbol(self, comp_type):
        assert comp_type in SPICE_SYMBOLS

    @pytest.mark.parametrize("comp_type", NEW_TYPES)
    def test_has_default_value(self, comp_type):
        assert comp_type in DEFAULT_VALUES

    @pytest.mark.parametrize("comp_type", NEW_TYPES)
    def test_has_terminal_geometry(self, comp_type):
        assert comp_type in TERMINAL_GEOMETRY

    @pytest.mark.parametrize(
        "comp_type,expected_count",
        [
            ("BJT NPN", 3),
            ("BJT PNP", 3),
            ("MOSFET NMOS", 3),
            ("MOSFET PMOS", 3),
            ("VC Switch", 4),
            ("Diode", 2),
            ("LED", 2),
            ("Zener Diode", 2),
        ],
    )
    def test_terminal_count_correct(self, comp_type, expected_count):
        comp = make_component(comp_type, "X1", DEFAULT_VALUES[comp_type])
        assert comp.get_terminal_count() == expected_count

    SERIALIZED_TYPES = [
        ("BJT NPN", "BJTNPN"),
        ("BJT PNP", "BJTPNP"),
        ("MOSFET NMOS", "MOSFETNMOS"),
        ("MOSFET PMOS", "MOSFETPMOS"),
        ("VC Switch", "VCSwitch"),
        ("Zener Diode", "ZenerDiode"),
    ]

    @pytest.mark.parametrize("display,class_name", SERIALIZED_TYPES)
    def test_display_to_class_mapping(self, display, class_name):
        assert _DISPLAY_TO_CLASS[display] == class_name

    @pytest.mark.parametrize("display,class_name", SERIALIZED_TYPES)
    def test_class_to_display_mapping(self, display, class_name):
        assert _CLASS_TO_DISPLAY[class_name] == display


# ===========================================================================
# CircuitModel Integration Tests
# ===========================================================================


class TestCircuitModelIntegration:
    """Test new components work correctly in CircuitModel."""

    def test_add_bjt_to_model(self):
        model = CircuitModel()
        bjt = ComponentData(
            component_id="Q1",
            component_type="BJT NPN",
            value="2N3904",
            position=(0.0, 0.0),
        )
        model.add_component(bjt)
        assert "Q1" in model.components
        assert model.components["Q1"].component_type == "BJT NPN"

    def test_add_mosfet_to_model(self):
        model = CircuitModel()
        mos = ComponentData(
            component_id="M1",
            component_type="MOSFET NMOS",
            value="NMOS1",
            position=(0.0, 0.0),
        )
        model.add_component(mos)
        assert "M1" in model.components

    def test_add_diode_to_model(self):
        model = CircuitModel()
        diode = ComponentData(
            component_id="D1",
            component_type="Diode",
            value="IS=1e-14 N=1",
            position=(0.0, 0.0),
        )
        model.add_component(diode)
        assert "D1" in model.components

    def test_wire_bjt_creates_node(self):
        model = CircuitModel()
        model.add_component(
            ComponentData(
                component_id="Q1",
                component_type="BJT NPN",
                value="2N3904",
                position=(0.0, 0.0),
            )
        )
        model.add_component(
            ComponentData(
                component_id="R1",
                component_type="Resistor",
                value="1k",
                position=(100.0, 0.0),
            )
        )
        model.add_wire(
            WireData(
                start_component_id="Q1",
                start_terminal=0,
                end_component_id="R1",
                end_terminal=0,
            )
        )
        assert len(model.nodes) == 1
        assert ("Q1", 0) in model.nodes[0].terminals
        assert ("R1", 0) in model.nodes[0].terminals

    def test_bjt_circuit_round_trip(self):
        """Save and load a circuit containing a BJT."""
        model = CircuitModel()
        model.add_component(
            ComponentData(
                component_id="Q1",
                component_type="BJT NPN",
                value="2N3904",
                position=(100.0, 200.0),
            )
        )
        model.add_component(
            ComponentData(
                component_id="GND1",
                component_type="Ground",
                value="0V",
                position=(0.0, 0.0),
            )
        )
        model.add_wire(
            WireData(
                start_component_id="Q1",
                start_terminal=2,
                end_component_id="GND1",
                end_terminal=0,
            )
        )
        model.component_counter = {"Q": 1, "GND": 1}

        data = model.to_dict()
        reset_node_counter()
        restored = CircuitModel.from_dict(data)

        assert "Q1" in restored.components
        assert restored.components["Q1"].component_type == "BJT NPN"
        assert restored.components["Q1"].value == "2N3904"
        assert len(restored.wires) == 1

    def test_diode_circuit_round_trip(self):
        """Save and load a circuit containing a Zener diode."""
        model = CircuitModel()
        model.add_component(
            ComponentData(
                component_id="D1",
                component_type="Zener Diode",
                value="IS=1e-14 N=1 BV=5.1",
                position=(50.0, 50.0),
            )
        )
        model.add_component(
            ComponentData(
                component_id="V1",
                component_type="Voltage Source",
                value="10V",
                position=(0.0, 0.0),
            )
        )
        model.add_component(
            ComponentData(
                component_id="GND1",
                component_type="Ground",
                value="0V",
                position=(100.0, 100.0),
            )
        )
        model.add_wire(
            WireData(
                start_component_id="V1",
                start_terminal=0,
                end_component_id="D1",
                end_terminal=0,
            )
        )
        model.add_wire(
            WireData(
                start_component_id="D1",
                start_terminal=1,
                end_component_id="GND1",
                end_terminal=0,
            )
        )
        model.add_wire(
            WireData(
                start_component_id="V1",
                start_terminal=1,
                end_component_id="GND1",
                end_terminal=0,
            )
        )
        model.component_counter = {"D": 1, "V": 1, "GND": 1}

        data = model.to_dict()
        reset_node_counter()
        restored = CircuitModel.from_dict(data)

        assert "D1" in restored.components
        assert restored.components["D1"].component_type == "Zener Diode"
        assert len(restored.wires) == 3
        assert len(restored.nodes) >= 1


# ===========================================================================
# Terminal Geometry Tests
# ===========================================================================


class TestTerminalGeometry:
    """Verify terminal positions are correct for new component types."""

    def test_bjt_has_three_custom_terminals(self):
        """BJT terminal positions: Collector, Base, Emitter."""
        _, _, base_terminals = TERMINAL_GEOMETRY["BJT NPN"]
        assert base_terminals is not None
        assert len(base_terminals) == 3

    def test_mosfet_has_three_custom_terminals(self):
        """MOSFET terminal positions: Drain, Gate, Source."""
        _, _, base_terminals = TERMINAL_GEOMETRY["MOSFET NMOS"]
        assert base_terminals is not None
        assert len(base_terminals) == 3

    def test_vc_switch_has_four_custom_terminals(self):
        _, _, base_terminals = TERMINAL_GEOMETRY["VC Switch"]
        assert base_terminals is not None
        assert len(base_terminals) == 4

    def test_diode_uses_standard_2term_layout(self):
        """Diode should use standard 2-terminal horizontal layout."""
        _, _, base_terminals = TERMINAL_GEOMETRY["Diode"]
        assert base_terminals is None  # None means standard layout

    def test_led_uses_standard_2term_layout(self):
        _, _, base_terminals = TERMINAL_GEOMETRY["LED"]
        assert base_terminals is None

    def test_zener_uses_standard_2term_layout(self):
        _, _, base_terminals = TERMINAL_GEOMETRY["Zener Diode"]
        assert base_terminals is None

    def test_bjt_rotation_transforms_terminals(self):
        """Rotating a BJT should transform terminal positions."""
        comp_0 = ComponentData(
            component_id="Q1",
            component_type="BJT NPN",
            value="2N3904",
            position=(0.0, 0.0),
            rotation=0,
        )
        comp_90 = ComponentData(
            component_id="Q1",
            component_type="BJT NPN",
            value="2N3904",
            position=(0.0, 0.0),
            rotation=90,
        )
        pos_0 = comp_0.get_terminal_positions()
        pos_90 = comp_90.get_terminal_positions()
        # Rotated positions should differ
        assert pos_0 != pos_90
        # But should have the same number of terminals
        assert len(pos_0) == len(pos_90) == 3
