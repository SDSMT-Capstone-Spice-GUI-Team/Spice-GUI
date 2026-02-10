"""
Tests for simulation/netlist_generator.py — SPICE netlist generation.
"""

import pytest
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator


def _generate(components, wires, nodes, terminal_to_node, analysis_type="DC Operating Point", analysis_params=None):
    """Helper to generate a netlist string from circuit data."""
    gen = NetlistGenerator(
        components=components,
        wires=wires,
        nodes=nodes,
        terminal_to_node=terminal_to_node,
        analysis_type=analysis_type,
        analysis_params=analysis_params or {},
    )
    return gen.generate()


class TestResistor:
    def test_resistor_line(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "R1" in netlist
        assert "1k" in netlist

    def test_voltage_source_dc(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "V1" in netlist
        assert "DC" in netlist
        assert "5V" in netlist


class TestGroundNode:
    def test_ground_maps_to_zero(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        # Ground component itself should not appear as a netlist line
        assert "GND1" not in netlist


class TestAnalysisCommands:
    def test_op_analysis(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n, analysis_type="DC Operating Point")
        assert ".op" in netlist

    def test_dc_sweep(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Sweep",
            analysis_params={"min": "0", "max": "10", "step": "0.1"},
        )
        assert ".dc" in netlist
        assert "V1" in netlist

    def test_ac_sweep(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={
                "sweep_type": "dec",
                "points": "10",
                "fStart": "1",
                "fStop": "1MEG",
            },
        )
        assert ".ac" in netlist

    def test_transient(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Transient",
            analysis_params={"step": "1u", "duration": "10m", "start": "0"},
        )
        assert ".tran" in netlist

    def test_temperature_sweep(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components, wires, nodes, t2n,
            analysis_type="Temperature Sweep",
            analysis_params={
                'tempStart': -40, 'tempStop': 85, 'tempStep': 25,
            },
        )
        assert ".op" in netlist
        assert ".step temp -40 85 25" in netlist

    def test_temperature_sweep_custom_range(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components, wires, nodes, t2n,
            analysis_type="Temperature Sweep",
            analysis_params={
                'tempStart': 0, 'tempStop': 100, 'tempStep': 10,
            },
        )
        assert ".step temp 0 100 10" in netlist


class TestOpAmp:
    def test_opamp_subcircuit(self):
        """Op-Amp should produce .subckt definition and X-prefixed instance."""
        from tests.conftest import make_component, make_wire

        components = {
            "OA1": make_component("Op-Amp", "OA1", "Ideal", (0, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("OA1", 0, "GND1", 0),
            make_wire("OA1", 1, "GND1", 0),
            make_wire("OA1", 2, "GND1", 0),
        ]
        node_gnd = NodeData(
            terminals={("OA1", 0), ("OA1", 1), ("OA1", 2), ("GND1", 0)},
            wire_indices={0, 1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_gnd]
        t2n = {
            ("OA1", 0): node_gnd,
            ("OA1", 1): node_gnd,
            ("OA1", 2): node_gnd,
            ("GND1", 0): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        assert ".subckt OPAMP_IDEAL" in netlist
        assert "XOA1" in netlist


class TestDependentSources:
    def _make_4term_circuit(self, comp_type, comp_id, value):
        """Helper: 4-terminal dependent source wired to ground."""
        from tests.conftest import make_component, make_wire

        components = {
            comp_id: make_component(comp_type, comp_id, value, (0, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
            "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
        }
        wires = [
            make_wire(comp_id, 0, "V1", 0),  # ctrl+ to V1+
            make_wire(comp_id, 1, "GND1", 0),  # ctrl- to GND
            make_wire(comp_id, 2, "V1", 0),  # out+ to V1+
            make_wire(comp_id, 3, "GND1", 0),  # out- to GND
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

    def test_vcvs(self):
        components, wires, nodes, t2n = self._make_4term_circuit("VCVS", "E1", "2")
        netlist = _generate(components, wires, nodes, t2n)
        assert "E1" in netlist
        assert "2" in netlist

    def test_vccs(self):
        components, wires, nodes, t2n = self._make_4term_circuit("VCCS", "G1", "1m")
        netlist = _generate(components, wires, nodes, t2n)
        assert "G1" in netlist

    def test_ccvs_hidden_vsense(self):
        components, wires, nodes, t2n = self._make_4term_circuit("CCVS", "H1", "1k")
        netlist = _generate(components, wires, nodes, t2n)
        assert "Vsense_H1" in netlist
        assert "H1" in netlist

    def test_cccs_hidden_vsense(self):
        components, wires, nodes, t2n = self._make_4term_circuit("CCCS", "F1", "1")
        netlist = _generate(components, wires, nodes, t2n)
        assert "Vsense_F1" in netlist
        assert "F1" in netlist


class TestResistorDivider:
    def test_two_nodes_labeled(self, resistor_divider_circuit):
        components, wires, nodes, t2n = resistor_divider_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "R1" in netlist
        assert "R2" in netlist
        assert "V1" in netlist
