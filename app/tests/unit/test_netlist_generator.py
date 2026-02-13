"""
Tests for simulation/netlist_generator.py — SPICE netlist generation.
"""

import pytest
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator


def _generate(
    components,
    wires,
    nodes,
    terminal_to_node,
    analysis_type="DC Operating Point",
    analysis_params=None,
    spice_options=None,
    measurements=None,
):
    """Helper to generate a netlist string from circuit data."""
    gen = NetlistGenerator(
        components=components,
        wires=wires,
        nodes=nodes,
        terminal_to_node=terminal_to_node,
        analysis_type=analysis_type,
        analysis_params=analysis_params or {},
        spice_options=spice_options,
        measurements=measurements,
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
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Temperature Sweep",
            analysis_params={
                "tempStart": -40,
                "tempStop": 85,
                "tempStep": 25,
            },
        )
        assert ".op" in netlist
        assert ".step temp -40 85 25" in netlist

    def test_temperature_sweep_custom_range(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Temperature Sweep",
            analysis_params={
                "tempStart": 0,
                "tempStop": 100,
                "tempStep": 10,
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


class TestWrdataPathCrossPlatform:
    """Verify wrdata file paths use forward slashes for ngspice compatibility."""

    def test_backslashes_converted_to_forward_slashes(self, simple_resistor_circuit):
        """On Windows, os.path.join produces backslashes; ngspice needs forward slashes."""
        components, wires, nodes, t2n = simple_resistor_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Transient",
            analysis_params={"duration": 0.01, "step": 1e-5, "startTime": 0},
            wrdata_filepath=r"simulation_output\wrdata_20260210.txt",
        )
        netlist = gen.generate()
        assert "simulation_output/wrdata_20260210.txt" in netlist
        assert "\\" not in netlist.split("wrdata ")[1].split("\n")[0]

    def test_forward_slashes_preserved(self, simple_resistor_circuit):
        """Unix paths with forward slashes should pass through unchanged."""
        components, wires, nodes, t2n = simple_resistor_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Transient",
            analysis_params={"duration": 0.01, "step": 1e-5, "startTime": 0},
            wrdata_filepath="simulation_output/wrdata_20260210.txt",
        )
        netlist = gen.generate()
        assert "simulation_output/wrdata_20260210.txt" in netlist

    def test_windows_absolute_path(self, simple_resistor_circuit):
        """Windows absolute paths should be converted."""
        components, wires, nodes, t2n = simple_resistor_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Transient",
            analysis_params={"duration": 0.01, "step": 1e-5, "startTime": 0},
            wrdata_filepath=r"C:\Users\test\AppData\Local\wrdata.txt",
        )
        netlist = gen.generate()
        assert "C:/Users/test/AppData/Local/wrdata.txt" in netlist


# ── Missing analysis types ──────────────────────────────────────────


class TestNoiseAnalysis:
    def test_noise_command(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Noise",
            analysis_params={
                "output_node": "out",
                "source": "V1",
                "sweepType": "dec",
                "points": 100,
                "fStart": 1,
                "fStop": 1e6,
            },
        )
        assert ".noise v(out) V1 dec 100 1 1000000.0" in netlist

    def test_noise_default_params(self, simple_resistor_circuit):
        """Noise analysis with no params uses defaults."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n, analysis_type="Noise", analysis_params={})
        assert ".noise v(out) V1 dec 100 1 1000000.0" in netlist

    def test_noise_control_block(self, simple_resistor_circuit):
        """Noise analysis uses setplot noise1 and prints noise spectra."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n, analysis_type="Noise", analysis_params={})
        assert "setplot noise1" in netlist
        assert "onoise_spectrum" in netlist
        assert "inoise_spectrum" in netlist


class TestSensitivityAnalysis:
    def test_sensitivity_command(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Sensitivity",
            analysis_params={"output_node": "out"},
        )
        assert ".sens v(out)" in netlist

    def test_sensitivity_default_output(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Sensitivity",
            analysis_params={},
        )
        assert ".sens v(out)" in netlist


class TestTransferFunctionAnalysis:
    def test_tf_command(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Transfer Function",
            analysis_params={"output_var": "v(out)", "input_source": "V1"},
        )
        assert ".tf v(out) V1" in netlist

    def test_tf_default_params(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Transfer Function",
            analysis_params={},
        )
        assert ".tf v(out) V1" in netlist


class TestPoleZeroAnalysis:
    def test_pz_command(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Pole-Zero",
            analysis_params={
                "input_pos": "1",
                "input_neg": "0",
                "output_pos": "2",
                "output_neg": "0",
                "transfer_type": "vol",
                "pz_type": "pz",
            },
        )
        assert ".pz 1 0 2 0 vol pz" in netlist

    def test_pz_default_params(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Pole-Zero",
            analysis_params={},
        )
        assert ".pz 1 0 2 0 vol pz" in netlist


class TestOperationalPointAlias:
    def test_operational_point_alias(self, simple_resistor_circuit):
        """'Operational Point' alias should produce .op command."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n, analysis_type="Operational Point")
        assert ".op" in netlist


class TestDcSweepNoSource:
    def test_dc_sweep_no_voltage_source_warning(self):
        """DC Sweep with no voltage source should produce warning comment."""
        from tests.conftest import make_component, make_wire

        components = {
            "R1": make_component("Resistor", "R1", "1k", (0, 0)),
            "I1": make_component("Current Source", "I1", "1A", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire("I1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("I1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("I1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("I1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("I1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("I1", 1): node_gnd,
        }
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Sweep",
            analysis_params={"min": "0", "max": "10", "step": "0.1"},
        )
        assert "Warning: DC Sweep requires a voltage source" in netlist
        assert ".op" in netlist


# ── Semiconductor model directives ──────────────────────────────────


class TestBJTModels:
    def _make_bjt_circuit(self, bjt_type, comp_id, model_name):
        from tests.conftest import make_component, make_wire

        components = {
            comp_id: make_component(bjt_type, comp_id, model_name, (0, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire(comp_id, 0, "V1", 0),  # collector
            make_wire(comp_id, 1, "V1", 0),  # base
            make_wire(comp_id, 2, "GND1", 0),  # emitter
            make_wire("V1", 1, "GND1", 0),
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

    def test_bjt_npn_2n3904(self):
        components, wires, nodes, t2n = self._make_bjt_circuit("BJT NPN", "Q1", "2N3904")
        netlist = _generate(components, wires, nodes, t2n)
        assert "Q1" in netlist
        assert ".model 2N3904 NPN(BF=300 IS=1e-14 VAF=100)" in netlist

    def test_bjt_pnp_2n3906(self):
        components, wires, nodes, t2n = self._make_bjt_circuit("BJT PNP", "Q2", "2N3906")
        netlist = _generate(components, wires, nodes, t2n)
        assert "Q2" in netlist
        assert ".model 2N3906 PNP(BF=200 IS=1e-14 VAF=100)" in netlist

    def test_bjt_generic_model(self):
        """Unknown BJT model name gets generic parameters."""
        components, wires, nodes, t2n = self._make_bjt_circuit("BJT NPN", "Q3", "MyCustomBJT")
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model MyCustomBJT NPN(BF=100 IS=1e-14)" in netlist


class TestMOSFETModels:
    def _make_mosfet_circuit(self, mos_type, comp_id, model_name):
        from tests.conftest import make_component, make_wire

        components = {
            comp_id: make_component(mos_type, comp_id, model_name, (0, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire(comp_id, 0, "V1", 0),  # drain
            make_wire(comp_id, 1, "V1", 0),  # gate
            make_wire(comp_id, 2, "GND1", 0),  # source
            make_wire("V1", 1, "GND1", 0),
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

    def test_nmos_model(self):
        components, wires, nodes, t2n = self._make_mosfet_circuit("MOSFET NMOS", "M1", "NMOS1")
        netlist = _generate(components, wires, nodes, t2n)
        assert "M1" in netlist
        assert ".model NMOS1 NMOS(VTO=0.7 KP=110u)" in netlist
        # MOSFET should have 4 nodes (drain gate source bulk)
        # bulk tied to source

    def test_pmos_model(self):
        components, wires, nodes, t2n = self._make_mosfet_circuit("MOSFET PMOS", "M2", "PMOS1")
        netlist = _generate(components, wires, nodes, t2n)
        assert "M2" in netlist
        assert ".model PMOS1 PMOS(VTO=-0.7 KP=50u)" in netlist


class TestDiodeModels:
    def _make_diode_circuit(self, diode_type, comp_id, value):
        from tests.conftest import make_component, make_wire

        components = {
            comp_id: make_component(diode_type, comp_id, value, (0, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire(comp_id, 0, "V1", 0),  # anode
            make_wire(comp_id, 1, "GND1", 0),  # cathode
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={(comp_id, 0), ("V1", 0)},
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
            (comp_id, 0): node_a,
            ("V1", 0): node_a,
            (comp_id, 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        return components, wires, nodes, t2n

    def test_diode_model(self):
        components, wires, nodes, t2n = self._make_diode_circuit("Diode", "D1", "IS=1e-14 N=1")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D1" in netlist
        assert ".model D_Ideal D(IS=1e-14 N=1)" in netlist

    def test_led_model(self):
        components, wires, nodes, t2n = self._make_diode_circuit("LED", "D2", "IS=1e-20 N=1.8 EG=1.9")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D2" in netlist
        assert "D_LED" in netlist

    def test_zener_model(self):
        components, wires, nodes, t2n = self._make_diode_circuit("Zener Diode", "D3", "IS=1e-14 N=1 BV=5.1 IBV=1e-3")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D3" in netlist
        assert "D_Zener" in netlist


class TestVCSwitch:
    def test_vc_switch_model(self):
        from tests.conftest import make_component, make_wire

        components = {
            "S1": make_component("VC Switch", "S1", "VT=2.5 RON=1 ROFF=1e6", (0, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire("S1", 0, "V1", 0),
            make_wire("S1", 1, "GND1", 0),
            make_wire("S1", 2, "V1", 0),
            make_wire("S1", 3, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("S1", 0), ("S1", 2), ("V1", 0)},
            wire_indices={0, 2},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("S1", 1), ("S1", 3), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 3, 4},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("S1", 0): node_a,
            ("S1", 2): node_a,
            ("V1", 0): node_a,
            ("S1", 1): node_gnd,
            ("S1", 3): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        assert "S1" in netlist
        assert ".model SW_S1 SW(VT=2.5 RON=1 ROFF=1e6)" in netlist


# ── Transformer ─────────────────────────────────────────────────────


class TestTransformer:
    def test_transformer_coupled_inductors(self):
        from tests.conftest import make_component, make_wire

        components = {
            "K1": make_component("Transformer", "K1", "10mH 10mH 0.99", (0, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire("K1", 0, "V1", 0),  # prim+
            make_wire("K1", 1, "GND1", 0),  # prim-
            make_wire("K1", 2, "V1", 0),  # sec+
            make_wire("K1", 3, "GND1", 0),  # sec-
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("K1", 0), ("K1", 2), ("V1", 0)},
            wire_indices={0, 2},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("K1", 1), ("K1", 3), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 3, 4},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("K1", 0): node_a,
            ("K1", 2): node_a,
            ("V1", 0): node_a,
            ("K1", 1): node_gnd,
            ("K1", 3): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        assert "L_prim_K1" in netlist
        assert "L_sec_K1" in netlist
        assert "K_K1 L_prim_K1 L_sec_K1 0.99" in netlist
        assert "10mH" in netlist


# ── Initial conditions ──────────────────────────────────────────────


class TestInitialConditions:
    def test_capacitor_initial_condition(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        # Replace R1 with a Capacitor that has an initial condition
        from tests.conftest import make_component

        cap = make_component("Capacitor", "C1", "1u", (100, 0))
        cap.initial_condition = "5V"
        components["C1"] = cap
        del components["R1"]
        # Re-wire
        wires[0] = WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="C1",
            end_terminal=0,
        )
        wires[1] = WireData(
            start_component_id="C1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        )
        # Fix t2n
        t2n[("C1", 0)] = t2n.pop(("R1", 0))
        t2n[("C1", 1)] = t2n.pop(("R1", 1))
        netlist = _generate(components, wires, nodes, t2n)
        assert "C1" in netlist
        assert "IC=5V" in netlist

    def test_inductor_initial_condition(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        from tests.conftest import make_component

        ind = make_component("Inductor", "L1", "1m", (100, 0))
        ind.initial_condition = "0.5A"
        components["L1"] = ind
        del components["R1"]
        wires[0] = WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="L1",
            end_terminal=0,
        )
        wires[1] = WireData(
            start_component_id="L1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        )
        t2n[("L1", 0)] = t2n.pop(("R1", 0))
        t2n[("L1", 1)] = t2n.pop(("R1", 1))
        netlist = _generate(components, wires, nodes, t2n)
        assert "L1" in netlist
        assert "IC=0.5A" in netlist

    def test_no_initial_condition(self, simple_resistor_circuit):
        """Components without IC should not contain 'IC=' in the netlist."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "IC=" not in netlist


# ── Spice options and measurements ──────────────────────────────────


class TestSpiceOptions:
    def test_extra_spice_options(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            spice_options={"RELTOL": "0.01", "ABSTOL": "1e-10"},
        )
        assert ".options RELTOL=0.01 ABSTOL=1e-10" in netlist

    def test_no_extra_options(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        # Should not have .options line beyond the standard TEMP/TNOM
        assert ".options" not in netlist


class TestMeasurements:
    def test_meas_directives(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Transient",
            analysis_params={"step": "1u", "duration": "10m", "start": "0"},
            measurements=[".meas TRAN rise_time TRIG v(out) VAL=0.5 RISE=1 TARG v(out) VAL=4.5 RISE=1"],
        )
        assert "Measurement Directives" in netlist
        assert ".meas TRAN rise_time" in netlist

    def test_meas_prefix_added(self, simple_resistor_circuit):
        """Measurement without .meas prefix should get it added."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="Transient",
            analysis_params={"step": "1u", "duration": "10m", "start": "0"},
            measurements=["TRAN peak_v MAX v(out)"],
        )
        assert ".meas TRAN peak_v MAX v(out)" in netlist

    def test_no_measurements(self, simple_resistor_circuit):
        """No measurement section when list is empty."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "Measurement Directives" not in netlist


# ── Waveform Source ─────────────────────────────────────────────────


class TestWaveformSource:
    def test_waveform_source_spice_value(self):
        """Waveform Source should use get_spice_value() for netlist."""
        from tests.conftest import make_component, make_wire

        ws = make_component("Waveform Source", "VW1", "SIN(0 5 1k)", (0, 0))
        components = {
            "VW1": ws,
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire("VW1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("VW1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("VW1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("VW1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("VW1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("VW1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        # Should contain the waveform source line with SIN()
        assert "VW1" in netlist
        assert "SIN(" in netlist


# ── Current Source ──────────────────────────────────────────────────


class TestCurrentSource:
    def test_current_source_line(self):
        from tests.conftest import make_component, make_wire

        components = {
            "I1": make_component("Current Source", "I1", "1A", (0, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 0)),
        }
        wires = [
            make_wire("I1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("I1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("I1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("I1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("I1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("I1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        assert "I1" in netlist
        assert "DC 1A" in netlist
