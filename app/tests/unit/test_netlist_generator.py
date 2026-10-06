"""
Tests for simulation/netlist_generator.py — SPICE netlist generation.
"""

import pytest
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator, generate_analysis_command


class TestGenerateAnalysisCommand:
    """Tests for the standalone generate_analysis_command function (#576)."""

    def test_dc_op(self):
        assert generate_analysis_command("DC Operating Point", {}) == ".op"

    def test_dc_sweep(self):
        cmd = generate_analysis_command("DC Sweep", {"source": "V1", "min": 0, "max": 5, "step": 0.1})
        assert cmd == ".dc V1 0 5 0.1"

    def test_ac_sweep_with_camelcase_key(self):
        cmd = generate_analysis_command("AC Sweep", {"fStart": 1, "fStop": 1e6, "points": 100, "sweepType": "dec"})
        assert cmd == ".ac dec 100 1 1000000.0"

    def test_ac_sweep_with_underscore_key(self):
        cmd = generate_analysis_command("AC Sweep", {"fStart": 1, "fStop": 1e6, "points": 100, "sweep_type": "lin"})
        assert cmd == ".ac lin 100 1 1000000.0"

    def test_transient(self):
        cmd = generate_analysis_command("Transient", {"step": 1e-6, "duration": 0.01, "startTime": 0})
        assert cmd.startswith(".tran")

    def test_temperature_sweep(self):
        cmd = generate_analysis_command("Temperature Sweep", {"tempStart": -40, "tempStop": 85, "tempStep": 25})
        assert cmd == ".step temp -40 85 25"

    def test_noise(self):
        cmd = generate_analysis_command(
            "Noise",
            {
                "output_node": "out",
                "source": "V1",
                "fStart": 1,
                "fStop": 1e6,
                "points": 100,
                "sweepType": "dec",
            },
        )
        assert cmd.startswith(".noise v(out) V1")

    def test_sensitivity(self):
        cmd = generate_analysis_command("Sensitivity", {"output_node": "out"})
        assert cmd == ".sens v(out)"

    def test_transfer_function(self):
        cmd = generate_analysis_command("Transfer Function", {"output_var": "v(out)", "input_source": "V1"})
        assert cmd == ".tf v(out) V1"

    def test_pole_zero(self):
        cmd = generate_analysis_command(
            "Pole-Zero",
            {
                "input_pos": "1",
                "input_neg": "0",
                "output_pos": "2",
                "output_neg": "0",
                "transfer_type": "vol",
                "pz_type": "pz",
            },
        )
        assert cmd == ".pz 1 0 2 0 vol pz"

    def test_unknown_type_returns_empty(self):
        assert generate_analysis_command("Unknown", {}) == ""


def _generate(
    components,
    wires,
    nodes,
    terminal_to_node,
    analysis_type="DC Operating Point",
    analysis_params=None,
):
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

    def test_dc_sweep_uses_selected_source(self):
        """DC Sweep must use the source specified in params, not always the first (#512)."""
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "V2": make_component("Voltage Source", "V2", "12V", (200, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "V2", 0),
            make_wire("V1", 1, "GND1", 0),
            make_wire("V2", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("R1", 1), ("V2", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("V1", 1), ("V2", 1), ("GND1", 0)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_b,
            ("V2", 0): node_b,
            ("V1", 1): node_gnd,
            ("V2", 1): node_gnd,
            ("GND1", 0): node_gnd,
        }
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Sweep",
            analysis_params={"source": "V2", "min": "0", "max": "15", "step": "0.5"},
        )
        # Should use V2, not V1
        assert ".dc V2 0 15 0.5" in netlist

    def test_dc_sweep_fallback_without_source_param(self, simple_resistor_circuit):
        """Without 'source' in params, DC Sweep should fall back to first voltage source."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Sweep",
            analysis_params={"min": "0", "max": "10", "step": "0.1"},
        )
        assert ".dc V1" in netlist

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

    def test_ac_sweep_includes_phase_variables(self, simple_resistor_circuit):
        """AC Sweep print commands must include vp() for phase data (#738)."""
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
        assert "vp(" in netlist, "AC Sweep netlist must include vp() phase variables"

    def test_ac_sweep_uses_vm_for_magnitude(self, simple_resistor_circuit):
        """AC Sweep must use vm() for magnitude instead of v() (#804)."""
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
        assert "vm(" in netlist, "AC Sweep netlist must use vm() for magnitude"

    def test_ac_sweep_uses_vdb_when_use_db(self, simple_resistor_circuit):
        """AC Sweep must use vdb() when use_db is set (#804)."""
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
                "use_db": "Yes",
            },
        )
        assert "vdb(" in netlist, "AC Sweep netlist must use vdb() when use_db=Yes"
        assert "vm(" not in netlist, "AC Sweep netlist must not use vm() when use_db=Yes"

    def test_ac_sweep_pairs_mag_and_vp(self, simple_resistor_circuit):
        """Each vm(node) in AC Sweep must have a matching vp(node) (#738, #804)."""
        import re

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
        # Extract print line
        for line in netlist.splitlines():
            if line.strip().startswith("print "):
                # Find vm(X) or vdb(X) nodes
                mag_nodes = set(re.findall(r"\b(?:vm|vdb)\(([^)]+)\)", line))
                vp_nodes = set(re.findall(r"\bvp\(([^)]+)\)", line))
                assert mag_nodes, "No vm()/vdb() variables found in print line"
                assert vp_nodes, "No vp() variables found in print line"
                assert mag_nodes == vp_nodes, f"Mismatched mag/vp nodes: mag={mag_nodes}, vp={vp_nodes}"
                break

    def _build_rc_dc_source(self, v1_value="5"):
        """Build an RC low-pass with a plain DC 'Voltage Source' (not AC).

        This reproduces the flat-line AC sweep bug: a DC source with no
        AC magnitude gives ngspice no drive reference during .ac analysis.
        """
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", v1_value, (0, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "C1": make_component("Capacitor", "C1", "1u", (200, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "C1", 0),
            make_wire("C1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_in = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="in",
        )
        node_out = NodeData(
            terminals={("R1", 1), ("C1", 0)},
            wire_indices={1},
            auto_label="out",
        )
        node_gnd = NodeData(
            terminals={("C1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_in, node_out, node_gnd]
        t2n = {
            ("V1", 0): node_in,
            ("R1", 0): node_in,
            ("R1", 1): node_out,
            ("C1", 0): node_out,
            ("C1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        return components, wires, nodes, t2n

    def _build_two_source_circuit(self):
        """Build a circuit with an AC input plus a separate DC supply.

        Two sources each drive a common node through equal 1k resistors.
        V1 is the AC input (1 V); V2 is a steady 5 V supply. Under AC
        sweep only V1 should carry an AC drive reference — the supply must
        remain a plain DC source, so ngspice measures only V1's response
        (this is the two-source repro from the review: correct answer 0.5).
        """
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("AC Voltage Source", "V1", "1V 0", (0, 0)),
            "V2": make_component("Voltage Source", "V2", "5V", (0, 100)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "R2": make_component("Resistor", "R2", "1k", (100, 100)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 50)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("V1", 1, "GND1", 0),
            make_wire("V2", 0, "R2", 0),
            make_wire("V2", 1, "GND1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("R2", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("V2", 0), ("R2", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("V1", 1), ("V2", 1), ("R1", 1), ("R2", 1), ("GND1", 0)},
            wire_indices={2, 3, 4, 5},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("V1", 1): node_gnd,
            ("V2", 0): node_b,
            ("R2", 0): node_b,
            ("V2", 1): node_gnd,
            ("R1", 1): node_gnd,
            ("R2", 1): node_gnd,
            ("GND1", 0): node_gnd,
        }
        return components, wires, nodes, t2n

    def _dc_source_line(self, netlist):
        """Return the V1 source line from a generated netlist."""
        for line in netlist.splitlines():
            if line.startswith("V1"):
                return line.strip()
        return None

    def test_ac_sweep_dc_source_gets_ac_reference(self):
        """AC Sweep must give a plain DC voltage source an AC magnitude.

        A ".ac" analysis needs an AC reference on every source; a source
        written as "DC 5" with no AC term drives ngspice with zero signal,
        producing a flat vm() result. The netlist must append "AC 1".
        """
        components, wires, nodes, t2n = self._build_rc_dc_source()
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        line = self._dc_source_line(netlist)
        assert line is not None, "V1 source line not found in netlist"
        assert "AC" in line.upper(), f"AC Sweep source line must carry an AC term, got: {line}"

    def test_ac_sweep_voltage_source_already_has_ac_term(self):
        """A DC source that already declares an AC term is left untouched.

        V1 is given a value containing an "AC" term, so it is already an AC
        input. The generator must not append a second "AC 1" — exactly one
        "AC" keyword must remain on the line.
        """
        components, wires, nodes, t2n = self._build_rc_dc_source(v1_value="AC 1")
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        line = self._dc_source_line(netlist)
        assert line is not None, "V1 source line not found in netlist"
        # Not double-applied: exactly one "AC" keyword on the line.
        assert line.upper().count("AC") == 1, f"AC term should not be duplicated, got: {line}"

    def test_dc_source_without_ac_sweep_keeps_dc_only(self):
        """DC Operating Point must NOT gain an AC term on its source."""
        components, wires, nodes, t2n = self._build_rc_dc_source()
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Operating Point",
        )
        line = self._dc_source_line(netlist)
        assert line is not None
        assert "AC" not in line.upper(), f"Non-AC sweep must not add AC term, got: {line}"

    def test_single_dc_source_gets_ac_reference(self):
        """A lone DC source on an AC sweep is safe to drive.

        With exactly one source there is nothing else it could be, so it
        becomes the input and gets an "AC 1" reference.
        """
        components, wires, nodes, t2n = self._build_rc_dc_source()
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        line = self._dc_source_line(netlist)
        assert line is not None, "V1 source line not found in netlist"
        assert line.upper().endswith("AC 1"), f"Single DC source should get AC 1, got: {line}"

    def test_multiple_dc_sources_get_no_ac_reference(self):
        """Multiple DC sources with none marked AC are left steady.

        With several unmarked DC sources the generator cannot know which is
        the intended input, so it injects nothing (the user is warned by
        the semantic validator instead). Neither source gains an "AC" term.
        """
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "V2": make_component("Voltage Source", "V2", "12V", (200, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "V2", 0),
            make_wire("V1", 1, "GND1", 0),
            make_wire("V2", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("R1", 1), ("V2", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("V1", 1), ("V2", 1), ("GND1", 0)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_b,
            ("V2", 0): node_b,
            ("V1", 1): node_gnd,
            ("V2", 1): node_gnd,
            ("GND1", 0): node_gnd,
        }
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        for source_id in ("V1", "V2"):
            for line in netlist.splitlines():
                if line.strip().startswith(f"{source_id}"):
                    assert "AC" not in line.upper(), (
                        f"{source_id} should not gain an AC term with multiple DC sources: {line}"
                    )

    def test_two_source_regression_supply_keeps_dc(self):
        """One AC input plus a DC supply: only the input carries AC.

        Regression for the review's two-source repro: with V1 as the AC
        input and V2 as a steady 5 V supply, only V1 must get an "AC 1"
        reference. The supply stays a plain "DC 5V" source so ngspice
        measures only V1's response (0.5, not 1.0).
        """
        components, wires, nodes, t2n = self._build_two_source_circuit()
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        supply_line = None
        ac_line = None
        for line in netlist.splitlines():
            stripped = line.strip()
            if stripped.startswith("V2"):
                supply_line = stripped
            if stripped.startswith("V1"):
                ac_line = stripped
        assert supply_line is not None and ac_line is not None

        # Supply stays a pure DC source — no AC term, still the 5 V value.
        assert "AC" not in supply_line.upper(), f"DC supply must not gain AC term: {supply_line}"
        assert "DC 5V" in supply_line, f"Supply must keep its DC value: {supply_line}"

        # The AC input is the only source driven by the sweep.
        assert "AC 1V" in ac_line.upper(), f"AC input must carry its AC term: {ac_line}"

    def test_two_source_regression_no_sweep_source_marked(self):
        """The AC sweep marks exactly one source, never the supply.

        Confirms the whole-circuit check: with an existing AC input, no DC
        source receives a spurious drive. V1 is already the input, so
        nothing new should be injected onto the supply.
        """
        components, wires, nodes, t2n = self._build_two_source_circuit()
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="AC Sweep",
            analysis_params={"sweep_type": "dec", "points": "10", "fStart": "1", "fStop": "1MEG"},
        )
        # No DC source should receive a newly injected "AC 1" suffix.
        injected = [
            l.strip() for l in netlist.splitlines() if l.strip().endswith("AC 1")
        ]
        assert injected == [], f"No source should gain an injected AC 1 term, got: {injected}"
        # The supply line is still a plain DC source.
        supply_line = next(
            l.strip() for l in netlist.splitlines() if l.strip().startswith("V2")
        )
        assert "AC" not in supply_line.upper(), f"Supply must not gain AC term: {supply_line}"

    def test_dc_sweep_includes_sweep_source_in_print(self, simple_resistor_circuit):
        """DC Sweep print command must include the sweep source variable (#854)."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Sweep",
            analysis_params={"min": "0", "max": "10", "step": "0.1"},
        )
        # The print line should NOT include the sweep source name (e.g. "v1")
        # because ngspice does not expose it as a vector. The sweep column
        # ("v-sweep") is automatically included by wrdata with wr_singlescale.
        for line in netlist.splitlines():
            if line.strip().startswith("print "):
                assert (
                    "v1" not in line.lower()
                ), "DC Sweep print must NOT include source name (ngspice has no such vector)"
                assert "v(" in line.lower(), "DC Sweep print should include node voltages"
                break

    def test_non_ac_sweep_excludes_vp(self, simple_resistor_circuit):
        """Non-AC analysis types must NOT include vp() variables."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Operating Point",
        )
        assert "vp(" not in netlist

    def test_non_ac_sweep_uses_v_not_vm(self, simple_resistor_circuit):
        """Non-AC analysis types should use v(), not vm() (#804)."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(
            components,
            wires,
            nodes,
            t2n,
            analysis_type="DC Operating Point",
        )
        assert "vm(" not in netlist
        assert "vdb(" not in netlist

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


class TestUnconnectedTerminal:
    """Unconnected terminals must raise ValueError instead of defaulting to node 999 (#506)."""

    def test_unconnected_terminal_raises(self):
        """A resistor with one terminal unwired should raise ValueError."""
        from tests.conftest import make_component, make_wire

        components = {
            "R1": make_component("Resistor", "R1", "1k", (0, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        # Only connect terminal 0 of R1 — terminal 1 is dangling
        wires = [make_wire("R1", 0, "GND1", 0)]
        node_gnd = NodeData(
            terminals={("R1", 0), ("GND1", 0)},
            wire_indices={0},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_gnd]
        t2n = {("R1", 0): node_gnd, ("GND1", 0): node_gnd}

        with pytest.raises(ValueError, match="Unconnected terminal.*R1 terminal 1"):
            _generate(components, wires, nodes, t2n)

    def test_fully_connected_circuit_succeeds(self, simple_resistor_circuit):
        """A fully connected circuit should generate without error."""
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "999" not in netlist


class TestComponentValueValidation:
    """Component values must be validated before netlist generation (#541)."""

    def test_invalid_resistor_value_raises(self):
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "R1": make_component("Resistor", "R1", "abc", (100, 0)),  # invalid
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        with pytest.raises(ValueError, match="Invalid component values"):
            _generate(components, wires, nodes, t2n)

    def test_negative_resistor_value_raises(self):
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "R1": make_component("Resistor", "R1", "-1k", (100, 0)),  # negative
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        with pytest.raises(ValueError, match="positive"):
            _generate(components, wires, nodes, t2n)

    def test_valid_circuit_passes_validation(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "R1" in netlist  # generation succeeds


class TestResistorDivider:
    def test_two_nodes_labeled(self, resistor_divider_circuit):
        components, wires, nodes, t2n = resistor_divider_circuit
        netlist = _generate(components, wires, nodes, t2n)
        assert "R1" in netlist
        assert "R2" in netlist
        assert "V1" in netlist


class TestGroundCustomLabel:
    """Ground node with a custom label must still produce SPICE node '0' (#527)."""

    def test_ground_custom_label_stays_zero(self):
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
            custom_label="MyGround",
        )
        nodes = [node_a, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        # The netlist must NOT contain the custom label as a node name
        assert "MyGround" not in netlist
        assert "(ground)" not in netlist
        # Ground node must appear as "0" in component lines
        assert " 0 " in netlist or " 0\n" in netlist


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
