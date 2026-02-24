"""
Tests for issue #432 — diode model parameters must appear in the generated netlist.

Verifies that Diode, LED, and Zener Diode components produce correct
SPICE netlist lines with their edited model parameters.
"""

from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator


def _make_component(component_type, component_id, value, position=(0.0, 0.0)):
    return ComponentData(
        component_id=component_id,
        component_type=component_type,
        value=value,
        position=position,
    )


def _make_wire(start_id, start_term, end_id, end_term):
    return WireData(
        start_component_id=start_id,
        start_terminal=start_term,
        end_component_id=end_id,
        end_terminal=end_term,
    )


def _build_diode_circuit(diode_type, diode_id, diode_value):
    """Build a simple V-diode-R-GND circuit for netlist testing."""
    components = {
        "V1": _make_component("Voltage Source", "V1", "5V", (0, 0)),
        diode_id: _make_component(diode_type, diode_id, diode_value, (100, 0)),
        "R1": _make_component("Resistor", "R1", "1k", (200, 0)),
        "GND1": _make_component("Ground", "GND1", "0V", (200, 100)),
    }
    wires = [
        _make_wire("V1", 0, diode_id, 0),
        _make_wire(diode_id, 1, "R1", 0),
        _make_wire("R1", 1, "GND1", 0),
        _make_wire("V1", 1, "GND1", 0),
    ]
    node_a = NodeData(
        terminals={("V1", 0), (diode_id, 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_b = NodeData(
        terminals={(diode_id, 1), ("R1", 0)},
        wire_indices={1},
        auto_label="nodeB",
    )
    node_gnd = NodeData(
        terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
        wire_indices={2, 3},
        is_ground=True,
        auto_label="0",
    )
    t2n = {
        ("V1", 0): node_a,
        (diode_id, 0): node_a,
        (diode_id, 1): node_b,
        ("R1", 0): node_b,
        ("R1", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, [node_a, node_b, node_gnd], t2n


def _generate(components, wires, nodes, t2n):
    gen = NetlistGenerator(
        components=components,
        wires=wires,
        nodes=nodes,
        terminal_to_node=t2n,
        analysis_type="DC Operating Point",
        analysis_params={},
    )
    return gen.generate()


class TestDiodeInNetlist:
    """Verify that diodes appear in the netlist with correct model directives (#432)."""

    def test_diode_component_line(self):
        components, wires, nodes, t2n = _build_diode_circuit("Diode", "D1", "IS=1e-14 N=1")
        netlist = _generate(components, wires, nodes, t2n)
        # D1 should appear as a component line
        assert "D1 " in netlist
        # A .model directive should be present
        assert ".model" in netlist
        assert "D(" in netlist

    def test_diode_edited_params_in_model_directive(self):
        components, wires, nodes, t2n = _build_diode_circuit("Diode", "D1", "IS=5e-12 N=2.0 RS=10")
        netlist = _generate(components, wires, nodes, t2n)
        assert "IS=5e-12" in netlist
        assert "N=2.0" in netlist
        assert "RS=10" in netlist

    def test_led_in_netlist(self):
        components, wires, nodes, t2n = _build_diode_circuit("LED", "D1", "IS=1e-20 N=1.8 EG=1.9")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D1 " in netlist
        assert "IS=1e-20" in netlist
        assert "N=1.8" in netlist

    def test_zener_in_netlist(self):
        components, wires, nodes, t2n = _build_diode_circuit("Zener Diode", "D1", "IS=1e-14 N=1 BV=5.1 IBV=1e-3")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D1 " in netlist
        assert "BV=5.1" in netlist
        assert "IBV=1e-3" in netlist

    def test_zener_edited_breakdown_voltage(self):
        components, wires, nodes, t2n = _build_diode_circuit("Zener Diode", "D1", "IS=1e-14 N=1 BV=5.1 IBV=1e-3")
        # Simulate editing the breakdown voltage
        components["D1"].value = "IS=1e-14 N=1 BV=3.3 IBV=5e-3"
        netlist = _generate(components, wires, nodes, t2n)
        assert "BV=3.3" in netlist
        assert "IBV=5e-3" in netlist

    def test_multiple_diodes_share_model(self):
        """Two diodes with the same parameters should share a model name."""
        components = {
            "V1": _make_component("Voltage Source", "V1", "5V", (0, 0)),
            "D1": _make_component("Diode", "D1", "IS=1e-14 N=1", (100, 0)),
            "D2": _make_component("Diode", "D2", "IS=1e-14 N=1", (200, 0)),
            "R1": _make_component("Resistor", "R1", "1k", (300, 0)),
            "GND1": _make_component("Ground", "GND1", "0V", (300, 100)),
        }
        wires = [
            _make_wire("V1", 0, "D1", 0),
            _make_wire("D1", 1, "D2", 0),
            _make_wire("D2", 1, "R1", 0),
            _make_wire("R1", 1, "GND1", 0),
            _make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(terminals={("V1", 0), ("D1", 0)}, wire_indices={0}, auto_label="nodeA")
        node_b = NodeData(terminals={("D1", 1), ("D2", 0)}, wire_indices={1}, auto_label="nodeB")
        node_c = NodeData(terminals={("D2", 1), ("R1", 0)}, wire_indices={2}, auto_label="nodeC")
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={3, 4},
            is_ground=True,
            auto_label="0",
        )
        t2n = {
            ("V1", 0): node_a,
            ("D1", 0): node_a,
            ("D1", 1): node_b,
            ("D2", 0): node_b,
            ("D2", 1): node_c,
            ("R1", 0): node_c,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, [node_a, node_b, node_c, node_gnd], t2n)
        # Both D1 and D2 should reference the same model
        model_count = netlist.count(".model D_Ideal D(")
        assert model_count == 1

    def test_different_diode_types_get_different_models(self):
        """Diode and LED should get separate model directives."""
        components = {
            "V1": _make_component("Voltage Source", "V1", "5V", (0, 0)),
            "D1": _make_component("Diode", "D1", "IS=1e-14 N=1", (100, 0)),
            "D2": _make_component("LED", "D2", "IS=1e-20 N=1.8", (200, 0)),
            "R1": _make_component("Resistor", "R1", "1k", (300, 0)),
            "GND1": _make_component("Ground", "GND1", "0V", (300, 100)),
        }
        wires = [
            _make_wire("V1", 0, "D1", 0),
            _make_wire("D1", 1, "D2", 0),
            _make_wire("D2", 1, "R1", 0),
            _make_wire("R1", 1, "GND1", 0),
            _make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(terminals={("V1", 0), ("D1", 0)}, wire_indices={0}, auto_label="nodeA")
        node_b = NodeData(terminals={("D1", 1), ("D2", 0)}, wire_indices={1}, auto_label="nodeB")
        node_c = NodeData(terminals={("D2", 1), ("R1", 0)}, wire_indices={2}, auto_label="nodeC")
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={3, 4},
            is_ground=True,
            auto_label="0",
        )
        t2n = {
            ("V1", 0): node_a,
            ("D1", 0): node_a,
            ("D1", 1): node_b,
            ("D2", 0): node_b,
            ("D2", 1): node_c,
            ("R1", 0): node_c,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, [node_a, node_b, node_c, node_gnd], t2n)
        assert "D_Ideal" in netlist
        assert "D_LED" in netlist
