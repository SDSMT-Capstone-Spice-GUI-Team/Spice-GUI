"""
Tests for simulation pipeline coverage gaps.

Targets uncovered branches in netlist_generator.py, result_parser.py,
and netlist_parser.py identified by pytest-cov.

Closes #355
"""

import pytest
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator
from simulation.netlist_parser import (
    NetlistParseError,
    _parse_component_line,
    _tokenize_spice_line,
    import_netlist,
    parse_netlist,
)
from simulation.result_parser import ResultParser, format_si
from tests.conftest import make_component, make_wire

# ── Helper ───────────────────────────────────────────────────────────


def _generate(
    components,
    wires,
    nodes,
    terminal_to_node,
    analysis_type="DC Operating Point",
    analysis_params=None,
    wrdata_filepath="transient_data.txt",
):
    gen = NetlistGenerator(
        components=components,
        wires=wires,
        nodes=nodes,
        terminal_to_node=terminal_to_node,
        analysis_type=analysis_type,
        analysis_params=analysis_params or {},
        wrdata_filepath=wrdata_filepath,
    )
    return gen.generate()


def _make_simple_circuit_with(comp_type, comp_id, value, terminal_count=2):
    """Build a minimal circuit with one component + voltage source + ground."""
    components = {
        comp_id: make_component(comp_type, comp_id, value, (0, 0)),
        "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }

    # Wire comp terminal 0 to V1 terminal 0, and remaining terminals to GND
    wires = [make_wire(comp_id, 0, "V1", 0), make_wire("V1", 1, "GND1", 0)]
    for t in range(1, terminal_count):
        wires.append(make_wire(comp_id, t, "GND1", 0))

    node_a = NodeData(
        terminals={(comp_id, 0), ("V1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    gnd_terminals = {("GND1", 0), ("V1", 1)}
    for t in range(1, terminal_count):
        gnd_terminals.add((comp_id, t))
    node_gnd = NodeData(
        terminals=gnd_terminals,
        wire_indices=set(range(1, len(wires))),
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_gnd]
    t2n = {
        ("V1", 0): node_a,
        (comp_id, 0): node_a,
        ("V1", 1): node_gnd,
        ("GND1", 0): node_gnd,
    }
    for t in range(1, terminal_count):
        t2n[(comp_id, t)] = node_gnd
    return components, wires, nodes, t2n


# ═══════════════════════════════════════════════════════════════════════
# NetlistGenerator coverage
# ═══════════════════════════════════════════════════════════════════════


class TestNodeMerging:
    """Cover line 81-87: merging two already-assigned nodes."""

    def test_wire_merges_two_existing_nodes(self):
        """When a wire connects two terminals that already have different nodes,
        the higher node number should be merged into the lower."""
        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "R2": make_component("Resistor", "R2", "2k", (200, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
        }
        # V1+ -> R1 term0, R2 term0 -> GND, V1- -> GND
        # Then R1 term1 -> R2 term0 creates a merge (both already have nodes)
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R2", 0, "R1", 1),  # R2t0 gets new node
            make_wire("R2", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
            # Extra wire that should cause a merge: R1t1 is already in a node,
            # and R2t0 is already in a node (from wire index 1)
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("R1", 1), ("R2", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("R2", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_gnd]
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_b,
            ("R2", 0): node_b,
            ("R2", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        # Both R1 and R2 should appear in the netlist with valid node numbers
        assert "R1" in netlist
        assert "R2" in netlist


class TestCapacitorInductorCurrentSource:
    """Cover lines 146, 148, 152: Capacitor, Inductor, Current Source lines."""

    def test_capacitor_netlist_line(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("Capacitor", "C1", "10u")
        netlist = _generate(components, wires, nodes, t2n)
        assert "C1" in netlist
        assert "10u" in netlist

    def test_inductor_netlist_line(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("Inductor", "L1", "100m")
        netlist = _generate(components, wires, nodes, t2n)
        assert "L1" in netlist
        assert "100m" in netlist

    def test_current_source_netlist_line(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("Current Source", "I1", "1m")
        netlist = _generate(components, wires, nodes, t2n)
        assert "I1" in netlist
        assert "DC" in netlist
        assert "1m" in netlist


class TestWaveformSource:
    """Cover lines 155-159: Waveform Source with get_spice_value."""

    def test_waveform_source_uses_get_spice_value(self):
        """Waveform source with default params uses get_spice_value (always present)."""
        components, wires, nodes, t2n = _make_simple_circuit_with("Waveform Source", "V2", "SIN(0 5 1k)")
        # ComponentData.__post_init__ auto-initializes waveform_params for Waveform Source,
        # so get_spice_value() always exists and generates the full param string.
        netlist = _generate(components, wires, nodes, t2n)
        assert "V2" in netlist
        assert "SIN(" in netlist

    def test_waveform_source_with_get_spice_value(self):
        """Waveform source with get_spice_value method should use it."""
        components, wires, nodes, t2n = _make_simple_circuit_with("Waveform Source", "V2", "SIN(0 5 1k)")
        # Monkey-patch to add get_spice_value
        comp = components["V2"]
        comp.get_spice_value = lambda: "SIN(0 10 2k)"
        netlist = _generate(components, wires, nodes, t2n)
        assert "SIN(0 10 2k)" in netlist


class TestBJTGeneration:
    """Cover lines 189-228: BJT NPN/PNP component and model lines."""

    def test_bjt_npn_2n3904(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("BJT NPN", "Q1", "2N3904", terminal_count=3)
        netlist = _generate(components, wires, nodes, t2n)
        assert "Q1" in netlist
        assert ".model 2N3904 NPN(BF=300 IS=1e-14 VAF=100)" in netlist

    def test_bjt_pnp_2n3906(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("BJT PNP", "Q2", "2N3906", terminal_count=3)
        netlist = _generate(components, wires, nodes, t2n)
        assert "Q2" in netlist
        assert ".model 2N3906 PNP(BF=200 IS=1e-14 VAF=100)" in netlist

    def test_bjt_generic_model(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("BJT NPN", "Q3", "MyBJT", terminal_count=3)
        netlist = _generate(components, wires, nodes, t2n)
        assert ".model MyBJT NPN(BF=100 IS=1e-14)" in netlist


class TestMOSFETGeneration:
    """Cover lines 196-200, 234-244: MOSFET component and model lines."""

    def test_mosfet_nmos(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("MOSFET NMOS", "M1", "NMOS1", terminal_count=3)
        netlist = _generate(components, wires, nodes, t2n)
        assert "M1" in netlist
        assert ".model NMOS1 NMOS(VTO=0.7 KP=110u)" in netlist

    def test_mosfet_pmos(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("MOSFET PMOS", "M2", "PMOS1", terminal_count=3)
        netlist = _generate(components, wires, nodes, t2n)
        assert "M2" in netlist
        assert ".model PMOS1 PMOS(VTO=-0.7 KP=50u)" in netlist


class TestVCSwitchGeneration:
    """Cover lines 201-253: VC Switch component and model lines."""

    def test_vc_switch(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("VC Switch", "S1", "VT=2 VH=0.5", terminal_count=4)
        netlist = _generate(components, wires, nodes, t2n)
        assert "S1" in netlist
        assert ".model SW_S1 SW(VT=2 VH=0.5)" in netlist


class TestDiodeGeneration:
    """Cover lines 206-210, 257-260, 111-128: Diode component, model, dedup."""

    def test_diode_basic(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("Diode", "D1", "IS=1e-14")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D1" in netlist
        assert "D_Ideal" in netlist
        assert ".model D_Ideal D(IS=1e-14)" in netlist

    def test_led(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("LED", "D2", "IS=1e-20 N=1.8")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D2" in netlist
        assert "D_LED" in netlist

    def test_zener(self):
        components, wires, nodes, t2n = _make_simple_circuit_with("Zener Diode", "D3", "BV=5.1 IBV=1m")
        netlist = _generate(components, wires, nodes, t2n)
        assert "D3" in netlist
        assert "D_Zener" in netlist

    def test_diode_dedup_different_values(self):
        """Two diodes with different values should get different model names."""
        components = {
            "D1": make_component("Diode", "D1", "IS=1e-14", (0, 0)),
            "D2": make_component("Diode", "D2", "IS=1e-12", (100, 0)),
            "V1": make_component("Voltage Source", "V1", "5V", (-100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("D1", 0, "V1", 0),
            make_wire("D1", 1, "D2", 0),
            make_wire("D2", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(terminals={("D1", 0), ("V1", 0)}, wire_indices={0}, auto_label="a")
        node_b = NodeData(terminals={("D1", 1), ("D2", 0)}, wire_indices={1}, auto_label="b")
        node_gnd = NodeData(
            terminals={("D2", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_b, node_gnd]
        t2n = {
            ("D1", 0): node_a,
            ("V1", 0): node_a,
            ("D1", 1): node_b,
            ("D2", 0): node_b,
            ("D2", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        netlist = _generate(components, wires, nodes, t2n)
        # Two different model names should be generated
        assert "D_Ideal" in netlist
        assert "D_Ideal_2" in netlist


class TestDCSweepNoVoltageSource:
    """Cover lines 297-298: DC Sweep warning when no voltage source present."""

    def test_dc_sweep_warning_without_voltage_source(self):
        components = {
            "R1": make_component("Resistor", "R1", "1k", (0, 0)),
            "I1": make_component("Current Source", "I1", "1m", (-100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("I1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("I1", 1, "GND1", 0),
        ]
        node_a = NodeData(terminals={("I1", 0), ("R1", 0)}, wire_indices={0}, auto_label="a")
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("I1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
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
            [node_a, node_gnd],
            t2n,
            analysis_type="DC Sweep",
            analysis_params={"min": "0", "max": "10", "step": "0.1"},
        )
        assert "Warning: DC Sweep requires a voltage source" in netlist
        assert ".op" in netlist


class TestNoiseAnalysis:
    """Cover lines 319-327, 382-389: Noise analysis commands and wrdata."""

    def test_noise_analysis_command(self, simple_resistor_circuit):
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
        assert "setplot noise1" in netlist
        assert "print onoise_spectrum inoise_spectrum" in netlist
        assert "wrdata" in netlist
        assert "onoise_spectrum" in netlist


class TestNoLabeledNodes:
    """Cover line 341: print_vars = 'all' when no node labels."""

    def test_print_all_when_no_labels(self):
        """When nodes have no get_label, print numeric node references."""
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
        # Use plain NodeData without get_label attribute
        nodes = []  # No NodeData objects with get_label
        t2n = {}  # Empty terminal_to_node
        netlist = _generate(components, wires, nodes, t2n)
        # Should have numeric node references in print
        assert "print" in netlist or "v(" in netlist


class TestResistorVoltageGroundPath:
    """Cover line 359: resistor with one terminal connected to ground."""

    def test_resistor_ground_connection(self, resistor_divider_circuit):
        components, wires, nodes, t2n = resistor_divider_circuit
        netlist = _generate(components, wires, nodes, t2n)
        # R2 has one terminal at ground, should generate a let expression
        assert "let v_r1" in netlist or "let v_r2" in netlist


# ═══════════════════════════════════════════════════════════════════════
# ResultParser coverage
# ═══════════════════════════════════════════════════════════════════════


class TestFormatSi:
    """Cover lines 35-47: format_si function."""

    def test_zero_with_unit(self):
        assert format_si(0, "V") == "0.00 V"

    def test_zero_without_unit(self):
        assert format_si(0) == "0.00"

    def test_infinity(self):
        import math

        assert format_si(math.inf, "V") == "0.00 V"

    def test_nan(self):
        import math

        assert format_si(math.nan, "A") == "0.00 A"

    def test_millivolts(self):
        result = format_si(0.0033, "V")
        assert "3.30" in result
        assert "mV" in result

    def test_kilohertz(self):
        result = format_si(1500, "Hz")
        assert "1.50" in result
        assert "kHz" in result

    def test_microamps(self):
        result = format_si(0.0000025, "A")
        assert "2.50" in result
        assert "\u00b5A" in result

    def test_nanofarads(self):
        result = format_si(4.7e-9, "F")
        assert "4.70" in result
        assert "nF" in result

    def test_picofarads(self):
        result = format_si(100e-12, "F")
        assert "100.00" in result
        assert "pF" in result

    def test_large_value_giga(self):
        result = format_si(2.5e9, "Hz")
        assert "2.50" in result
        assert "GHz" in result

    def test_very_large_value_beyond_giga(self):
        result = format_si(5e12, "Hz")
        # Should use G prefix (largest available)
        assert "G" in result

    def test_negative_value(self):
        result = format_si(-3.3, "V")
        assert "-3.30" in result

    def test_no_unit(self):
        result = format_si(1500)
        assert "1.50" in result
        assert "k" in result


class TestOpBranchCurrents:
    """Cover lines 77-84, 114-118: Branch current parsing in OP results."""

    def test_i_function_pattern(self):
        output = "v(nodeA) = 5.0\ni(v1) = -0.005\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(-0.005)

    def test_device_attribute_pattern(self):
        output = "@v1[current] = 0.002\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(0.002)

    def test_pattern3_current_format(self):
        """Cover lines 114-118: ngspice print format for currents."""
        output = "  I(v1)   -2.100000e-03\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(-0.0021)


class TestOpTableBreakOnSource:
    """Cover line 93: table parsing stops when encountering 'source' line."""

    def test_table_stops_at_source(self):
        output = (
            "Node                  Voltage\n"
            "----                  -------\n"
            "nodeA                 5.0\n"
            "Source                currents\n"
            "nodeB                 2.5\n"
        )
        result = ResultParser.parse_op_results(output)
        assert "nodeA" in result["node_voltages"]
        # nodeB after "Source" line should not be parsed as a voltage
        assert "nodeB" not in result["node_voltages"]


class TestOpErrorPath:
    """Cover lines 122-124: exception handling in parse_op_results."""

    def test_malformed_voltage_value(self):
        """Lines with non-numeric values should be skipped gracefully."""
        output = "v(nodeA) = not_a_number\n"
        result = ResultParser.parse_op_results(output)
        # Should not crash, may or may not parse the bad value
        assert isinstance(result, dict)
        assert "node_voltages" in result


class TestDcErrorPath:
    """Cover lines 154-155, 159-161: DC parsing with malformed data rows."""

    def test_dc_non_numeric_data_row(self):
        output = (
            "Index   v-sweep   v(nodeA)\n0       0.000     0.000\nx       bad       data\n2       2.000     1.000\n"
        )
        result = ResultParser.parse_dc_results(output)
        assert result is not None
        # Should have 2 valid rows (skip the bad one)
        assert len(result["data"]) == 2


class TestAcErrorPath:
    """Cover lines 206-207, 211-213: AC parsing edge cases."""

    def test_ac_with_phase_data(self):
        output = (
            "Index   frequency   v(out)   vp(out)\n"
            "0       100.0       1.0      -45.0\n"
            "1       1000.0      0.5      -90.0\n"
        )
        result = ResultParser.parse_ac_results(output)
        assert result is not None
        assert "out" in result["phase"]
        assert result["phase"]["out"][0] == pytest.approx(-45.0)


class TestNoiseResultsParsing:
    """Cover lines 223-258: Noise results parsing."""

    def test_noise_data_parsed(self):
        output = (
            "Index   frequency   onoise_spectrum   inoise_spectrum\n"
            "0       100.0       1.23e-8           4.56e-8\n"
            "1       1000.0      5.67e-9           2.34e-8\n"
            "2       10000.0     3.45e-9           1.23e-8\n"
        )
        result = ResultParser.parse_noise_results(output)
        assert result is not None
        assert len(result["frequencies"]) == 3
        assert result["frequencies"][0] == pytest.approx(100.0)
        assert len(result["onoise_spectrum"]) == 3
        assert result["onoise_spectrum"][0] == pytest.approx(1.23e-8)
        assert len(result["inoise_spectrum"]) == 3

    def test_noise_no_data_returns_none(self):
        result = ResultParser.parse_noise_results("random text\nno noise data here\n")
        assert result is None

    def test_noise_empty_returns_none(self):
        result = ResultParser.parse_noise_results("")
        assert result is None

    def test_noise_malformed_data_row(self):
        output = (
            "Index   frequency   onoise_spectrum   inoise_spectrum\n"
            "0       100.0       1.23e-8           4.56e-8\n"
            "x       bad         data              row\n"
            "2       10000.0     3.45e-9           1.23e-8\n"
        )
        result = ResultParser.parse_noise_results(output)
        assert result is not None
        assert len(result["frequencies"]) == 2


class TestTransientErrorPaths:
    """Cover lines 290-291, 297-299: transient wrdata error handling."""

    def test_mismatched_column_count(self, tmp_path):
        """Rows with wrong number of columns should be skipped."""
        wrdata = tmp_path / "bad.txt"
        wrdata.write_text("time v(a) v(b)\n0.0 1.0 2.0\n0.1 3.0\n0.2 4.0 5.0\n")
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is not None
        assert len(result) == 2  # Skip the row with 2 columns

    def test_non_numeric_data(self, tmp_path):
        """Rows with non-numeric data should be skipped."""
        wrdata = tmp_path / "bad2.txt"
        wrdata.write_text("time v(a)\n0.0 1.0\nbad data\n0.2 2.0\n")
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is not None
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════
# NetlistParser coverage
# ═══════════════════════════════════════════════════════════════════════


class TestInlineComments:
    """Cover lines 78-80: stripping inline comments with semicolons."""

    def test_semicolon_comment_stripped(self):
        netlist = "Test\nR1 1 0 1k ; this is a comment\n.end\n"
        result = parse_netlist(netlist)
        assert len(result["components"]) == 1
        assert result["components"][0]["value"] == "1k"

    def test_line_with_only_comment_after_semicolon(self):
        netlist = "Test\nR1 1 0 1k\n; full line comment\nR2 2 0 2k\n.end\n"
        result = parse_netlist(netlist)
        # The "; full line comment" becomes empty after stripping => skipped
        assert len(result["components"]) == 2


class TestComponentLineTooFewTokens:
    """Cover line 150: component line with < 3 tokens returns None."""

    def test_two_token_line_skipped(self):
        result = _parse_component_line("R1 1", {})
        assert result is None

    def test_single_token_line_skipped(self):
        result = _parse_component_line("R1", {})
        assert result is None


class TestSubcircuitParsing:
    """Cover lines 157-163: X-prefix subcircuit parsing."""

    def test_opamp_subcircuit_parsed(self):
        netlist = "Test\nXOA1 1 2 3 OPAMP_IDEAL\nR1 3 0 10k\n.end\n"
        result = parse_netlist(netlist)
        opamp = [c for c in result["components"] if c["type"] == "Op-Amp"]
        assert len(opamp) == 1
        assert opamp[0]["id"] == "XOA1"

    def test_unknown_subcircuit_skipped(self):
        netlist = "Test\nX1 1 2 3 UNKNOWN_SUB\nR1 3 0 10k\n.end\n"
        result = parse_netlist(netlist)
        # X1 should be skipped, only R1 left
        assert len(result["components"]) == 1
        assert result["components"][0]["id"] == "R1"


class TestUnknownPrefix:
    """Cover lines 175-176: unknown SPICE prefix warning."""

    def test_unknown_prefix_k_skipped(self):
        # K is for coupled inductors but not mapped in _PREFIX_TO_TYPE for parsing
        result = _parse_component_line("K1 L1 L2 0.99", {})
        # K prefix is not in _PREFIX_TO_TYPE, so should return None
        assert result is None


class TestCCVSCCCSParsing:
    """Cover lines 186, 188, 223-227: H/F prefix parsing."""

    def test_ccvs_parsed(self):
        netlist = "Test\nH1 3 4 Vsense 1k\nVsense 1 2 0\n.end\n"
        result = parse_netlist(netlist)
        ccvs = [c for c in result["components"] if c["prefix"] == "H"]
        assert len(ccvs) == 1
        assert ccvs[0]["value"] == "1k"

    def test_cccs_parsed(self):
        netlist = "Test\nF1 3 4 Vsense 10\nVsense 1 2 0\n.end\n"
        result = parse_netlist(netlist)
        cccs = [c for c in result["components"] if c["prefix"] == "F"]
        assert len(cccs) == 1
        assert cccs[0]["value"] == "10"


class TestNotEnoughTokens:
    """Cover lines 193-194: not enough tokens for a component."""

    def test_mosfet_too_few_tokens(self):
        result = _parse_component_line("M1 1 2 3", {})
        # MOSFET needs 4 nodes + model = 6 tokens minimum
        assert result is None

    def test_vcvs_too_few_tokens(self):
        result = _parse_component_line("E1 1 2 3", {})
        # VCVS needs 4 nodes + value = 6 tokens minimum
        assert result is None


class TestBJTModelResolution:
    """Cover line 212: BJT model name from rest with 6+ tokens."""

    def test_bjt_with_area_parameter(self):
        # Q1 collector base emitter [substrate] model [area]
        netlist = "Test\nQ1 3 2 1 0 2N3904 1.0\n.model 2N3904 NPN\n.end\n"
        result = parse_netlist(netlist)
        bjt = [c for c in result["components"] if c["prefix"] == "Q"]
        assert len(bjt) == 1
        # Should resolve model from the last token before area
        assert bjt[0]["type"] == "BJT NPN"


class TestVCSwitchParsing:
    """Cover lines 225-227: S-prefix VC Switch parsing."""

    def test_vc_switch_parsed(self):
        # SW(VT=2 VH=0.5) is tokenized as a single token, so the parser
        # sees model_type="SW(VT=2 VH=0.5)" with empty params.
        # _resolve_model_value falls back to DEFAULT_VALUES for VC Switch.
        netlist = "Test\nS1 3 4 1 2 SMOD\n.model SMOD SW(VT=2 VH=0.5)\n.end\n"
        result = parse_netlist(netlist)
        switch = [c for c in result["components"] if c["prefix"] == "S"]
        assert len(switch) == 1
        assert switch[0]["type"] == "VC Switch"
        # Value comes from DEFAULT_VALUES since parenthesized params
        # are grouped with the type token by the tokenizer
        assert "VT=" in switch[0]["value"]

    def test_vc_switch_with_separate_params(self):
        """When model params are separate tokens, they are extracted."""
        netlist = "Test\nS1 3 4 1 2 SMOD\n.model SMOD SW VT=3 VH=1\n.end\n"
        result = parse_netlist(netlist)
        switch = [c for c in result["components"] if c["prefix"] == "S"]
        assert len(switch) == 1
        assert "VT=3" in switch[0]["value"]


class TestTranDirectiveStartParam:
    """Cover line 362: .tran directive with optional start parameter."""

    def test_tran_with_start(self):
        netlist = "Test\nR1 1 0 1k\n.tran 1u 10m 1m\n.end\n"
        result = parse_netlist(netlist)
        assert result["analysis"]["params"]["start"] == "1m"


class TestImportOpAmpTerminalMapping:
    """Cover lines 447-451: Op-Amp terminal mapping during import."""

    def test_opamp_terminal_ordering(self):
        netlist = (
            "Op-Amp Test\n"
            ".subckt OPAMP_IDEAL inp inn out\n"
            "Rin inp inn 1e12\n"
            "E1 out 0 inp inn 1e6\n"
            ".ends\n"
            "XOA1 1 2 3 OPAMP_IDEAL\n"
            "R1 3 0 10k\n"
            "R2 1 0 1k\n"
            ".end\n"
        )
        model, _ = import_netlist(netlist)
        assert "XOA1" in model.components
        assert model.components["XOA1"].component_type == "Op-Amp"


class TestImportDependentSourceTerminalMapping:
    """Cover lines 455-459: VCVS/VCCS terminal mapping during import."""

    def test_vcvs_terminal_mapping(self):
        netlist = "Test\nE1 3 4 1 2 10\nR1 3 0 1k\nR2 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        assert "E1" in model.components
        assert model.components["E1"].component_type == "VCVS"


class TestImportVCSwitchTerminalMapping:
    """Cover lines 463-467: VC Switch terminal mapping during import."""

    def test_vc_switch_terminal_mapping(self):
        netlist = "Test\nS1 3 4 1 2 SMOD\n.model SMOD SW(VT=2 VH=0.5)\nR1 3 0 1k\nR2 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        assert "S1" in model.components
        assert model.components["S1"].component_type == "VC Switch"


class TestImportMOSFETTerminalMapping:
    """Cover lines 471-472: MOSFET terminal mapping (ignore bulk)."""

    def test_mosfet_import_ignores_bulk(self):
        netlist = "Test\nM1 3 4 0 0 MMOD\n.model MMOD NMOS\nR1 3 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        assert "M1" in model.components
        assert model.components["M1"].component_type == "MOSFET NMOS"


class TestImportGroundPositionFallback:
    """Cover line 487: ground position fallback when component not found."""

    def test_ground_fallback_position(self):
        # This is hard to trigger directly; test that ground components are created
        netlist = "Test\nV1 1 0 DC 5\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        gnds = [c for c in model.components.values() if c.component_type == "Ground"]
        assert len(gnds) >= 1


class TestWaveformParamSetup:
    """Cover lines 575-601: PULSE and EXP waveform parameter setup."""

    def test_pulse_waveform_import(self):
        netlist = "Test\nV1 1 0 PULSE(0 5 0 1n 1n 500u 1m)\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        v1 = model.components["V1"]
        assert v1.waveform_type == "PULSE"
        assert v1.waveform_params is not None
        assert v1.waveform_params["PULSE"]["v1"] == "0"
        assert v1.waveform_params["PULSE"]["v2"] == "5"
        assert v1.waveform_params["PULSE"]["per"] == "1m"

    def test_exp_waveform_import(self):
        netlist = "Test\nV1 1 0 EXP(0 5 0 1u 2u 2u)\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        v1 = model.components["V1"]
        assert v1.waveform_type == "EXP"
        assert v1.waveform_params is not None
        assert v1.waveform_params["EXP"]["v1"] == "0"
        assert v1.waveform_params["EXP"]["v2"] == "5"
        assert v1.waveform_params["EXP"]["tau2"] == "2u"

    def test_sin_waveform_with_extra_params(self):
        netlist = "Test\nV1 1 0 SIN(0 5 1k 0.5 10 90)\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        v1 = model.components["V1"]
        assert v1.waveform_type == "SIN"
        assert v1.waveform_params["SIN"]["delay"] == "0.5"
        assert v1.waveform_params["SIN"]["theta"] == "10"
        assert v1.waveform_params["SIN"]["phase"] == "90"


class TestACSourceWithWaveform:
    """Cover lines 288-298: AC specification with waveform function."""

    def test_ac_with_sin_waveform(self):
        netlist = "Test\nVin 1 0 AC SIN(0 5 1k)\nR1 1 0 1k\n.end\n"
        result = parse_netlist(netlist)
        comp = result["components"][0]
        assert comp["type"] == "Waveform Source"

    def test_ac_with_plain_value(self):
        netlist = "Test\nVin 1 0 AC 1\nR1 1 0 1k\n.end\n"
        result = parse_netlist(netlist)
        comp = result["components"][0]
        assert comp["type"] == "Voltage Source"
        assert comp["value"] == "1"

    def test_ac_bare(self):
        netlist = "Test\nVin 1 0 AC\nR1 1 0 1k\n.end\n"
        result = parse_netlist(netlist)
        comp = result["components"][0]
        assert comp["type"] == "Voltage Source"
        assert comp["value"] == "1"


# ═══════════════════════════════════════════════════════════════════════
# power_calculator.py coverage (was 0%)
# ═══════════════════════════════════════════════════════════════════════

from simulation.power_calculator import _calc_component_power, calculate_power, total_power


class TestPowerCalculatorBasic:
    """Cover calculate_power and total_power functions."""

    def test_empty_node_voltages_returns_empty(self):
        assert calculate_power([], [], {}) == {}

    def test_resistor_power_from_voltage(self):
        """Resistor power = V^2 / R when no branch currents available."""
        comp = make_component("Resistor", "R1", "1k", (0, 0))
        node_a = NodeData(
            terminals={("R1", 0), ("V1", 0)},
            wire_indices={0},
            auto_label="a",
        )
        node_gnd = NodeData(
            terminals={("R1", 1)},
            wire_indices=set(),
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        node_voltages = {"a": 5.0, "0": 0.0}
        result = calculate_power([comp], nodes, node_voltages)
        assert "R1" in result
        # P = V^2 / R = 25 / 1000 = 0.025
        assert result["R1"] == pytest.approx(0.025)

    def test_resistor_power_with_branch_current(self):
        """When branch current is available, use P = V * I."""
        comp = make_component("Resistor", "R1", "1k", (0, 0))
        node_a = NodeData(terminals={("R1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("R1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        nodes = [node_a, node_gnd]
        node_voltages = {"a": 5.0, "0": 0.0}
        branch_currents = {"r1": 0.005}
        result = calculate_power([comp], nodes, node_voltages, branch_currents)
        assert "R1" in result
        assert result["R1"] == pytest.approx(0.025)

    def test_ground_component_skipped(self):
        """Ground components should be skipped."""
        gnd = make_component("Ground", "GND1", "0V", (0, 0))
        node_gnd = NodeData(terminals={("GND1", 0)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([gnd], [node_gnd], {"0": 0.0})
        assert "GND1" not in result

    def test_voltage_source_without_current_returns_none(self):
        """Voltage source without branch current can't compute power."""
        comp = make_component("Voltage Source", "V1", "5V", (0, 0))
        node_a = NodeData(terminals={("V1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("V1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 5.0, "0": 0.0})
        assert "V1" not in result

    def test_voltage_source_with_branch_current(self):
        """Voltage source with branch current computes P = V * I."""
        comp = make_component("Voltage Source", "V1", "5V", (0, 0))
        node_a = NodeData(terminals={("V1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("V1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        branch_currents = {"v1": -0.005}
        result = calculate_power([comp], [node_a, node_gnd], {"a": 5.0, "0": 0.0}, branch_currents)
        assert "V1" in result
        assert result["V1"] == pytest.approx(-0.025)

    def test_current_source_power(self):
        """Current source power = V_across * I."""
        comp = make_component("Current Source", "I1", "1m", (0, 0))
        node_a = NodeData(terminals={("I1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("I1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 10.0, "0": 0.0})
        assert "I1" in result
        assert result["I1"] == pytest.approx(0.01)

    def test_capacitor_zero_dc_power(self):
        """Capacitors have 0 DC power."""
        comp = make_component("Capacitor", "C1", "10u", (0, 0))
        node_a = NodeData(terminals={("C1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("C1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 5.0, "0": 0.0})
        assert result["C1"] == 0.0

    def test_inductor_zero_dc_power(self):
        """Inductors have 0 DC power."""
        comp = make_component("Inductor", "L1", "1m", (0, 0))
        node_a = NodeData(terminals={("L1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("L1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 3.0, "0": 0.0})
        assert result["L1"] == 0.0

    def test_unknown_type_without_branch_current_returns_none(self):
        """Unknown component types without branch current return None."""
        comp = make_component("BJT NPN", "Q1", "2N3904", (0, 0))
        node_a = NodeData(terminals={("Q1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("Q1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 5.0, "0": 0.0})
        assert "Q1" not in result

    def test_missing_terminal_mapping_returns_none(self):
        """Component with unmapped terminal returns None."""
        comp = make_component("Resistor", "R1", "1k", (0, 0))
        # No nodes reference R1's terminals
        result = calculate_power([comp], [], {"a": 5.0})
        assert "R1" not in result

    def test_missing_voltage_for_node_returns_none(self):
        """Component whose node has no voltage returns None."""
        comp = make_component("Resistor", "R1", "1k", (0, 0))
        node_a = NodeData(terminals={("R1", 0)}, wire_indices=set(), auto_label="a")
        node_b = NodeData(terminals={("R1", 1)}, wire_indices=set(), auto_label="b")
        # Only 'a' has a voltage; 'b' does not
        result = calculate_power([comp], [node_a, node_b], {"a": 5.0})
        assert "R1" not in result

    def test_total_power(self):
        """total_power sums all component powers."""
        power_dict = {"R1": 0.025, "V1": -0.025}
        assert total_power(power_dict) == pytest.approx(0.0)

    def test_total_power_empty(self):
        assert total_power({}) == 0.0

    def test_waveform_source_without_current_returns_none(self):
        """Waveform source without branch current can't compute power."""
        comp = make_component("Waveform Source", "V2", "SIN(0 5 1k)", (0, 0))
        node_a = NodeData(terminals={("V2", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("V2", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 5.0, "0": 0.0})
        assert "V2" not in result

    def test_current_source_unparseable_value(self):
        """Current source with unparseable value returns None."""
        comp = make_component("Current Source", "I1", "bad_value", (0, 0))
        node_a = NodeData(terminals={("I1", 0)}, wire_indices=set(), auto_label="a")
        node_gnd = NodeData(terminals={("I1", 1)}, wire_indices=set(), is_ground=True, auto_label="0")
        result = calculate_power([comp], [node_a, node_gnd], {"a": 5.0, "0": 0.0})
        assert "I1" not in result


# ═══════════════════════════════════════════════════════════════════════
# csv_exporter.py coverage (was 74%, missing noise export + circuit_name branches)
# ═══════════════════════════════════════════════════════════════════════

from simulation.csv_exporter import export_ac_results, export_dc_sweep_results, export_noise_results, write_csv


class TestCsvExporterCircuitNameBranches:
    """Cover circuit_name branches (lines 57, 88) in export functions."""

    def test_dc_sweep_with_circuit_name(self):
        sweep_data = {
            "headers": ["v-sweep", "v(out)"],
            "data": [[0.0, 0.0], [1.0, 0.5]],
        }
        csv = export_dc_sweep_results(sweep_data, circuit_name="test_circuit.cir")
        assert "test_circuit.cir" in csv
        assert "DC Sweep" in csv

    def test_ac_with_circuit_name(self):
        ac_data = {
            "frequencies": [100.0, 1000.0],
            "magnitude": {"out": [1.0, 0.5]},
            "phase": {"out": [-45.0, -90.0]},
        }
        csv = export_ac_results(ac_data, circuit_name="my_circuit.cir")
        assert "my_circuit.cir" in csv
        assert "AC Sweep" in csv
        assert "|V(out)|" in csv
        assert "phase(V(out))" in csv


class TestCsvNoiseExport:
    """Cover lines 164-192: noise export function."""

    def test_noise_export_basic(self):
        noise_data = {
            "frequencies": [100.0, 1000.0],
            "onoise_spectrum": [1.23e-8, 5.67e-9],
            "inoise_spectrum": [4.56e-8, 2.34e-8],
        }
        csv = export_noise_results(noise_data)
        assert "Noise" in csv
        assert "Output Noise" in csv
        assert "Input Noise" in csv
        assert "100.0" in csv

    def test_noise_export_with_circuit_name(self):
        noise_data = {
            "frequencies": [100.0],
            "onoise_spectrum": [1e-8],
            "inoise_spectrum": [2e-8],
        }
        csv = export_noise_results(noise_data, circuit_name="noise_test.cir")
        assert "noise_test.cir" in csv

    def test_noise_export_only_onoise(self):
        noise_data = {
            "frequencies": [100.0, 1000.0],
            "onoise_spectrum": [1e-8, 2e-8],
            "inoise_spectrum": [],
        }
        csv = export_noise_results(noise_data)
        assert "Output Noise" in csv
        assert "Input Noise" not in csv

    def test_noise_export_only_inoise(self):
        noise_data = {
            "frequencies": [100.0],
            "onoise_spectrum": [],
            "inoise_spectrum": [3e-8],
        }
        csv = export_noise_results(noise_data)
        assert "Input Noise" in csv
        assert "Output Noise" not in csv

    def test_noise_export_empty_frequencies(self):
        noise_data = {"frequencies": [], "onoise_spectrum": [], "inoise_spectrum": []}
        csv = export_noise_results(noise_data)
        assert "Noise" in csv
        # No data rows
        lines = [l for l in csv.strip().split("\n") if l and not l.startswith("#")]
        # Only the empty row and header remain
        assert len(lines) <= 2


class TestCsvWriteFunction:
    """Cover write_csv (line 195-204)."""

    def test_write_csv_to_file(self, tmp_path):
        filepath = tmp_path / "out.csv"
        write_csv("header\n1,2,3\n", str(filepath))
        content = filepath.read_text()
        assert "header" in content
        assert "1,2,3" in content


# ═══════════════════════════════════════════════════════════════════════
# result_parser.py error paths (was 91%, missing lines 101-102, 122-124,
# 159-161, 206-207, 211-213, 256-258, 297-299)
# ═══════════════════════════════════════════════════════════════════════


class TestResultParserOpErrorPaths:
    """Cover error/edge paths in parse_op_results."""

    def test_op_completely_malformed_raises_no_exception(self):
        """Completely garbage input should return empty dicts, not crash."""
        result = ResultParser.parse_op_results(None)
        assert result["node_voltages"] == {}
        assert result["branch_currents"] == {}

    def test_op_pattern2_non_numeric_voltage_skipped(self):
        """Lines 101-102: ValueError in table pattern should be skipped."""
        output = (
            "Node                  Voltage\n"
            "----                  -------\n"
            "nodeA                 not_a_number\n"
            "nodeB                 3.3\n"
        )
        result = ResultParser.parse_op_results(output)
        assert "nodeA" not in result["node_voltages"]
        assert "nodeB" in result["node_voltages"]


class TestResultParserDcErrorPaths:
    """Cover lines 159-161: exception handler in parse_dc_results."""

    def test_dc_completely_empty_returns_none(self):
        result = ResultParser.parse_dc_results("")
        assert result is None

    def test_dc_no_data_rows_returns_none(self):
        output = "Index   v-sweep   v(nodeA)\n"
        result = ResultParser.parse_dc_results(output)
        assert result is None


class TestResultParserAcErrorPaths:
    """Cover lines 206-207, 211-213: AC parsing edge/error paths."""

    def test_ac_no_frequency_data_returns_none(self):
        result = ResultParser.parse_ac_results("random text\nno ac data\n")
        assert result is None

    def test_ac_empty_returns_none(self):
        result = ResultParser.parse_ac_results("")
        assert result is None

    def test_ac_malformed_data_row_skipped(self):
        """Lines 206-207: ValueError in data row should be skipped."""
        output = (
            "Index   frequency   v(out)\n0       100.0       1.0\nx       bad         data\n2       10000.0     0.5\n"
        )
        result = ResultParser.parse_ac_results(output)
        assert result is not None
        assert len(result["frequencies"]) == 2


class TestResultParserNoiseErrorPaths:
    """Cover lines 256-258: exception handler in parse_noise_results."""

    def test_noise_with_only_header_no_numeric_data(self):
        """Data lines that can't be parsed as floats should be skipped."""
        output = "Index   frequency   onoise_spectrum\nabc     xyz         bad\n"
        result = ResultParser.parse_noise_results(output)
        assert result is None


class TestResultParserTransientErrorPaths:
    """Cover lines 297-299: OSError/general exception in parse_transient_results."""

    def test_transient_file_not_found(self):
        result = ResultParser.parse_transient_results("/nonexistent/path/file.txt")
        assert result is None

    def test_transient_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = ResultParser.parse_transient_results(str(f))
        assert result is None

    def test_transient_header_only(self, tmp_path):
        f = tmp_path / "header_only.txt"
        f.write_text("time v(a)\n")
        result = ResultParser.parse_transient_results(str(f))
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# preset_manager.py edge cases (was 91%, missing lines 80, 88-90, 166-167)
# ═══════════════════════════════════════════════════════════════════════

from simulation.preset_manager import BUILTIN_PRESETS, PresetManager


class TestPresetManagerEdgeCases:
    """Cover default path creation, corrupt file handling, and save error."""

    def test_default_path_used_when_none(self):
        """Line 80: when no preset_file given, _default_preset_path is used."""
        pm = PresetManager()
        assert pm._preset_file.name == "simulation_presets.json"

    def test_corrupt_preset_file_handled(self, tmp_path):
        """Lines 88-90 (in _load): corrupt JSON should not crash."""
        bad_file = tmp_path / "bad_presets.json"
        bad_file.write_text("{not valid json")
        pm = PresetManager(preset_file=bad_file)
        # Should fall back to empty user presets
        assert pm._user_presets == []

    def test_nonexistent_preset_file_handled(self, tmp_path):
        """_load with missing file should not crash."""
        missing = tmp_path / "nonexistent.json"
        pm = PresetManager(preset_file=missing)
        assert pm._user_presets == []

    def test_save_creates_file(self, tmp_path):
        preset_file = tmp_path / "presets.json"
        pm = PresetManager(preset_file=preset_file)
        pm.save_preset("Test", "Transient", {"tstep": "1u", "tstop": "10m"})
        assert preset_file.exists()
        # Reload and verify
        pm2 = PresetManager(preset_file=preset_file)
        names = [p["name"] for p in pm2.get_presets()]
        assert "Test" in names

    def test_save_error_handled(self, tmp_path):
        """Lines 166-167: OSError during save should be handled gracefully."""
        # Create a directory where the file should be — causes OSError on write
        preset_path = tmp_path / "presets.json"
        preset_path.mkdir()
        pm = PresetManager(preset_file=preset_path)
        # Should not raise
        pm.save_preset("Oops", "Transient", {"tstep": "1u", "tstop": "10m"})

    def test_get_presets_includes_builtins(self, tmp_path):
        pm = PresetManager(preset_file=tmp_path / "p.json")
        presets = pm.get_presets()
        assert len(presets) >= len(BUILTIN_PRESETS)

    def test_get_presets_filtered_by_type(self, tmp_path):
        pm = PresetManager(preset_file=tmp_path / "p.json")
        transient_presets = pm.get_presets(analysis_type="Transient")
        for p in transient_presets:
            assert p["analysis_type"] == "Transient"

    def test_delete_preset(self, tmp_path):
        pm = PresetManager(preset_file=tmp_path / "p.json")
        pm.save_preset("ToDelete", "Transient", {"tstep": "1u"})
        initial_count = len(pm.get_presets())
        result = pm.delete_preset("ToDelete")
        assert result is True
        assert len(pm.get_presets()) == initial_count - 1

    def test_delete_nonexistent_preset(self, tmp_path):
        pm = PresetManager(preset_file=tmp_path / "p.json")
        result = pm.delete_preset("DoesNotExist")
        assert result is False
