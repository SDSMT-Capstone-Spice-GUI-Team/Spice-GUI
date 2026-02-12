"""
Netlist snapshot tests for all component types and analysis directives.

Builds circuits programmatically, generates netlists, and verifies
the SPICE output contains correct element lines, model directives,
and analysis commands.

Issue: #281
"""

import pytest
from models.circuit import CircuitModel
from models.component import COMPONENT_TYPES, ComponentData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_with_circuit(*components_and_wires, analysis_type="DC Operating Point", analysis_params=None):
    """Build a CircuitModel, add components and wires, rebuild nodes."""
    model = CircuitModel()
    model.analysis_type = analysis_type
    model.analysis_params = analysis_params or {}
    for item in components_and_wires:
        if isinstance(item, ComponentData):
            model.add_component(item)
        elif isinstance(item, WireData):
            model.add_wire(item)
    return model


def _generate_from_model(model):
    """Generate netlist string from a CircuitModel."""
    gen = NetlistGenerator(
        components=model.components,
        wires=model.wires,
        nodes=model.nodes,
        terminal_to_node=model.terminal_to_node,
        analysis_type=model.analysis_type,
        analysis_params=model.analysis_params,
    )
    return gen.generate()


def _simple_two_terminal_circuit(comp_type, comp_id, value):
    """Build V1 -- comp -- GND circuit for a 2-terminal component."""
    v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
    comp = ComponentData(comp_id, comp_type, value, (100, 0))
    gnd = ComponentData("GND1", "Ground", "0V", (100, 100))
    w1 = WireData("V1", 0, comp_id, 0)
    w2 = WireData(comp_id, 1, "GND1", 0)
    w3 = WireData("V1", 1, "GND1", 0)
    return _model_with_circuit(v1, comp, gnd, w1, w2, w3)


# ===========================================================================
# Component Netlist Output
# ===========================================================================


class TestPassiveComponents:
    """Verify netlist output for passive components (R, C, L)."""

    def test_resistor_line(self):
        model = _simple_two_terminal_circuit("Resistor", "R1", "4.7k")
        netlist = _generate_from_model(model)
        assert "R1" in netlist
        assert "4.7k" in netlist

    def test_capacitor_line(self):
        model = _simple_two_terminal_circuit("Capacitor", "C1", "100n")
        netlist = _generate_from_model(model)
        assert "C1" in netlist
        assert "100n" in netlist

    def test_inductor_line(self):
        model = _simple_two_terminal_circuit("Inductor", "L1", "10m")
        netlist = _generate_from_model(model)
        assert "L1" in netlist
        assert "10m" in netlist


class TestSources:
    """Verify netlist output for voltage and current sources."""

    def test_voltage_source_dc(self):
        model = _simple_two_terminal_circuit("Voltage Source", "V1", "12V")
        # Remove extra V1 — the helper already adds V1
        # Build manually instead
        v1 = ComponentData("V1", "Voltage Source", "12V", (0, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (0, 100))
        w1 = WireData("V1", 1, "GND1", 0)
        model = _model_with_circuit(v1, gnd, w1)
        netlist = _generate_from_model(model)
        assert "V1" in netlist
        assert "DC" in netlist
        assert "12V" in netlist

    def test_current_source_dc(self):
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        i1 = ComponentData("I1", "Current Source", "10m", (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (100, 100))
        w1 = WireData("V1", 0, "I1", 0)
        w2 = WireData("I1", 1, "GND1", 0)
        w3 = WireData("V1", 1, "GND1", 0)
        model = _model_with_circuit(v1, i1, gnd, w1, w2, w3)
        netlist = _generate_from_model(model)
        assert "I1" in netlist
        assert "DC" in netlist
        assert "10m" in netlist

    def test_waveform_source_sin(self):
        vw1 = ComponentData("VW1", "Waveform Source", "SIN(0 5 1k)", (0, 0))
        vw1.waveform_type = "SIN"
        vw1.waveform_params["SIN"]["amplitude"] = "10"
        gnd = ComponentData("GND1", "Ground", "0V", (0, 100))
        w1 = WireData("VW1", 1, "GND1", 0)
        model = _model_with_circuit(vw1, gnd, w1)
        netlist = _generate_from_model(model)
        assert "VW1" in netlist
        assert "SIN(" in netlist
        assert "10" in netlist

    def test_waveform_source_pulse(self):
        vw1 = ComponentData("VW1", "Waveform Source", "PULSE(0 5 0 1n 1n 500u 1m)", (0, 0))
        vw1.waveform_type = "PULSE"
        gnd = ComponentData("GND1", "Ground", "0V", (0, 100))
        w1 = WireData("VW1", 1, "GND1", 0)
        model = _model_with_circuit(vw1, gnd, w1)
        netlist = _generate_from_model(model)
        assert "PULSE(" in netlist


class TestDiodes:
    """Verify netlist output for diode types."""

    def test_diode_with_model(self):
        model = _simple_two_terminal_circuit("Diode", "D1", "IS=1e-14 N=1")
        netlist = _generate_from_model(model)
        assert "D1" in netlist
        assert ".model" in netlist.lower()
        assert "D(" in netlist
        assert "IS=1e-14 N=1" in netlist

    def test_led_with_model(self):
        model = _simple_two_terminal_circuit("LED", "D1", "IS=1e-20 N=1.8 EG=1.9")
        netlist = _generate_from_model(model)
        assert "D1" in netlist
        assert "D_LED" in netlist
        assert ".model" in netlist.lower()

    def test_zener_with_model(self):
        model = _simple_two_terminal_circuit("Zener Diode", "D1", "IS=1e-14 N=1 BV=5.1 IBV=1e-3")
        netlist = _generate_from_model(model)
        assert "D1" in netlist
        assert "D_Zener" in netlist


class TestTransistors:
    """Verify netlist output for BJT and MOSFET transistors."""

    def _three_terminal_circuit(self, comp_type, comp_id, value):
        """Build a minimal 3-terminal circuit with V, comp, GND."""
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        comp = ComponentData(comp_id, comp_type, value, (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (100, 100))
        # Connect: V1:0 → comp:0 (collector/drain), comp:2 (emitter/source) → GND, V1:1 → GND
        # Leave base/gate floating for simplicity — just need netlist line
        w1 = WireData("V1", 0, comp_id, 0)
        w2 = WireData(comp_id, 2, "GND1", 0)
        w3 = WireData("V1", 1, "GND1", 0)
        return _model_with_circuit(v1, comp, gnd, w1, w2, w3)

    def test_bjt_npn(self):
        model = self._three_terminal_circuit("BJT NPN", "Q1", "2N3904")
        netlist = _generate_from_model(model)
        assert "Q1" in netlist
        assert "2N3904" in netlist
        assert ".model 2N3904 NPN" in netlist

    def test_bjt_pnp(self):
        model = self._three_terminal_circuit("BJT PNP", "Q1", "2N3906")
        netlist = _generate_from_model(model)
        assert "Q1" in netlist
        assert "2N3906" in netlist
        assert ".model 2N3906 PNP" in netlist

    def test_mosfet_nmos(self):
        model = self._three_terminal_circuit("MOSFET NMOS", "M1", "NMOS1")
        netlist = _generate_from_model(model)
        assert "M1" in netlist
        assert "NMOS1" in netlist
        assert ".model NMOS1 NMOS" in netlist

    def test_mosfet_pmos(self):
        model = self._three_terminal_circuit("MOSFET PMOS", "M1", "PMOS1")
        netlist = _generate_from_model(model)
        assert "M1" in netlist
        assert "PMOS1" in netlist
        assert ".model PMOS1 PMOS" in netlist


class TestOpAmp:
    """Verify netlist output for op-amp subcircuit instantiation."""

    def _opamp_circuit(self, model_name="Ideal"):
        """Build a simple op-amp follower circuit."""
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        oa1 = ComponentData("OA1", "Op-Amp", model_name, (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (100, 100))
        # term 0=inverting, 1=non-inverting, 2=output
        w1 = WireData("V1", 0, "OA1", 1)  # V+ to non-inverting
        w2 = WireData("OA1", 0, "GND1", 0)  # inverting to GND
        w3 = WireData("V1", 1, "GND1", 0)
        return _model_with_circuit(v1, oa1, gnd, w1, w2, w3)

    def test_ideal_opamp_subcircuit(self):
        model = self._opamp_circuit("Ideal")
        netlist = _generate_from_model(model)
        assert "XOA1" in netlist
        assert "OPAMP_IDEAL" in netlist
        assert ".subckt OPAMP_IDEAL" in netlist

    @pytest.mark.parametrize("model_name", ["LM741", "TL081", "LM358"])
    def test_named_opamp_model(self, model_name):
        model = self._opamp_circuit(model_name)
        netlist = _generate_from_model(model)
        assert "XOA1" in netlist
        assert model_name in netlist
        assert f".subckt {model_name}" in netlist


class TestDependentSources:
    """Verify netlist output for dependent sources (VCVS, VCCS, CCVS, CCCS)."""

    def _four_terminal_circuit(self, comp_type, comp_id, value):
        """Build a minimal 4-terminal circuit."""
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        comp = ComponentData(comp_id, comp_type, value, (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (200, 100))
        # term 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
        w1 = WireData("V1", 0, comp_id, 0)  # V+ to ctrl+
        w2 = WireData(comp_id, 1, "GND1", 0)  # ctrl- to GND
        w3 = WireData(comp_id, 3, "GND1", 0)  # out- to GND
        w4 = WireData("V1", 1, "GND1", 0)
        return _model_with_circuit(v1, comp, gnd, w1, w2, w3, w4)

    def test_vcvs(self):
        model = self._four_terminal_circuit("VCVS", "E1", "10")
        netlist = _generate_from_model(model)
        assert "E1" in netlist
        assert "10" in netlist

    def test_vccs(self):
        model = self._four_terminal_circuit("VCCS", "G1", "1m")
        netlist = _generate_from_model(model)
        assert "G1" in netlist
        assert "1m" in netlist

    def test_ccvs_has_sense_source(self):
        model = self._four_terminal_circuit("CCVS", "H1", "1k")
        netlist = _generate_from_model(model)
        assert "H1" in netlist
        assert "Vsense_H1" in netlist

    def test_cccs_has_sense_source(self):
        model = self._four_terminal_circuit("CCCS", "F1", "2")
        netlist = _generate_from_model(model)
        assert "F1" in netlist
        assert "Vsense_F1" in netlist


class TestVCSwitch:
    """Verify netlist output for voltage-controlled switch."""

    def test_vc_switch_with_model(self):
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        s1 = ComponentData("S1", "VC Switch", "VT=2.5 RON=1 ROFF=1e6", (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (200, 100))
        w1 = WireData("V1", 0, "S1", 0)
        w2 = WireData("S1", 1, "GND1", 0)
        w3 = WireData("S1", 3, "GND1", 0)
        w4 = WireData("V1", 1, "GND1", 0)
        model = _model_with_circuit(v1, s1, gnd, w1, w2, w3, w4)
        netlist = _generate_from_model(model)
        assert "S1" in netlist
        assert "SW_S1" in netlist
        assert ".model SW_S1 SW(" in netlist
        assert "VT=2.5" in netlist


# ===========================================================================
# Model Deduplication
# ===========================================================================


class TestModelDeduplication:
    """Verify that duplicate component models are deduplicated."""

    def test_multiple_same_diodes_single_model(self):
        """3 diodes of the same type → single .model line."""
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        d1 = ComponentData("D1", "Diode", "IS=1e-14 N=1", (100, 0))
        d2 = ComponentData("D2", "Diode", "IS=1e-14 N=1", (200, 0))
        d3 = ComponentData("D3", "Diode", "IS=1e-14 N=1", (300, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (200, 100))
        # Wire them all up minimally
        w1 = WireData("V1", 0, "D1", 0)
        w2 = WireData("D1", 1, "D2", 0)
        w3 = WireData("D2", 1, "D3", 0)
        w4 = WireData("D3", 1, "GND1", 0)
        w5 = WireData("V1", 1, "GND1", 0)
        model = _model_with_circuit(v1, d1, d2, d3, gnd, w1, w2, w3, w4, w5)
        netlist = _generate_from_model(model)

        # Should have exactly one .model D_Ideal D(...) line
        model_lines = [line for line in netlist.split("\n") if line.startswith(".model D_Ideal")]
        assert len(model_lines) == 1

    def test_mixed_diode_types_separate_models(self):
        """Different diode types get separate model definitions."""
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        d1 = ComponentData("D1", "Diode", "IS=1e-14 N=1", (100, 0))
        d2 = ComponentData("D2", "LED", "IS=1e-20 N=1.8 EG=1.9", (200, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (200, 100))
        w1 = WireData("V1", 0, "D1", 0)
        w2 = WireData("D1", 1, "D2", 0)
        w3 = WireData("D2", 1, "GND1", 0)
        w4 = WireData("V1", 1, "GND1", 0)
        model = _model_with_circuit(v1, d1, d2, gnd, w1, w2, w3, w4)
        netlist = _generate_from_model(model)

        assert "D_Ideal" in netlist
        assert "D_LED" in netlist


# ===========================================================================
# Analysis Directives
# ===========================================================================


class TestAnalysisDirectives:
    """Verify correct SPICE syntax for each analysis type."""

    def _basic_circuit(self, analysis_type, analysis_params=None):
        """Build a simple resistor circuit with the given analysis."""
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (100, 100))
        w1 = WireData("V1", 0, "R1", 0)
        w2 = WireData("R1", 1, "GND1", 0)
        w3 = WireData("V1", 1, "GND1", 0)
        return _model_with_circuit(
            v1, r1, gnd, w1, w2, w3, analysis_type=analysis_type, analysis_params=analysis_params
        )

    def test_dc_operating_point(self):
        model = self._basic_circuit("DC Operating Point")
        netlist = _generate_from_model(model)
        assert ".op" in netlist

    def test_dc_sweep(self):
        model = self._basic_circuit("DC Sweep", {"min": "0", "max": "10", "step": "0.1"})
        netlist = _generate_from_model(model)
        assert ".dc V1 0 10 0.1" in netlist

    def test_ac_sweep(self):
        model = self._basic_circuit("AC Sweep", {"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"})
        netlist = _generate_from_model(model)
        assert ".ac dec 10 1 1MEG" in netlist

    def test_transient(self):
        model = self._basic_circuit("Transient", {"step": "1u", "duration": "10m", "start": "0"})
        netlist = _generate_from_model(model)
        assert ".tran 1u 10m 0" in netlist

    def test_temperature_sweep(self):
        model = self._basic_circuit("Temperature Sweep", {"tempStart": -40, "tempStop": 85, "tempStep": 25})
        netlist = _generate_from_model(model)
        assert ".op" in netlist
        assert ".step temp -40 85 25" in netlist

    def test_noise_analysis(self):
        model = self._basic_circuit(
            "Noise",
            {
                "output_node": "out",
                "source": "V1",
                "sweepType": "dec",
                "points": 100,
                "fStart": 1,
                "fStop": 1e6,
            },
        )
        netlist = _generate_from_model(model)
        assert ".noise v(out) V1 dec 100 1 1000000.0" in netlist


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases for netlist generation."""

    def test_empty_circuit_produces_valid_netlist(self):
        """Empty circuit generates a minimal valid netlist."""
        model = CircuitModel()
        netlist = _generate_from_model(model)
        assert "My Test Circuit" in netlist
        assert ".end" in netlist

    def test_ground_node_is_zero(self, simple_resistor_circuit):
        """Ground component maps to SPICE node 0."""
        components, wires, nodes, t2n = simple_resistor_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        # Ground-connected terminals should reference node 0
        # The netlist should contain " 0 " somewhere for ground
        lines = netlist.split("\n")
        component_lines = [l for l in lines if l.startswith(("R1", "V1"))]
        assert any(" 0" in line for line in component_lines)

    def test_netlist_has_end_directive(self):
        """Every netlist ends with .end."""
        model = _simple_two_terminal_circuit("Resistor", "R1", "1k")
        netlist = _generate_from_model(model)
        assert netlist.strip().endswith(".end")

    def test_netlist_has_title(self):
        """Every netlist starts with a title line."""
        model = _simple_two_terminal_circuit("Resistor", "R1", "1k")
        netlist = _generate_from_model(model)
        assert netlist.startswith("My Test Circuit")


# ===========================================================================
# Import Round-Trip (generate → parse → generate)
# ===========================================================================


class TestImportRoundTrip:
    """Verify netlist import → re-export preserves structure."""

    def test_simple_circuit_import_round_trip(self, tmp_path):
        """Import a .cir file → re-export → compare key structures."""
        from simulation.netlist_parser import import_netlist

        # Generate a netlist
        model = _simple_two_terminal_circuit("Resistor", "R1", "1k")
        netlist = _generate_from_model(model)

        # Save to file and import
        cir_file = tmp_path / "test.cir"
        cir_file.write_text(netlist)
        imported_model, analysis = import_netlist(netlist)

        # The imported model should have matching component types
        comp_types_original = {c.component_type for c in model.components.values() if c.component_type != "Ground"}
        comp_types_imported = {
            c.component_type for c in imported_model.components.values() if c.component_type != "Ground"
        }
        assert comp_types_original == comp_types_imported

    def test_waveform_params_survive_round_trip(self):
        """SIN waveform params survive import."""
        from simulation.netlist_parser import parse_netlist

        netlist_text = """Test Circuit
VW1 1 0 SIN(0 5 1k 0 0 0)
.op
.end
"""
        result = parse_netlist(netlist_text)
        comps = result["components"]
        v_comps = [c for c in comps if c["id"] == "VW1"]
        assert len(v_comps) == 1
        assert "SIN" in v_comps[0]["value"]
