"""Tests for SPICE netlist parser and import functionality."""

import pytest
from simulation.netlist_parser import (
    NetlistParseError,
    _extract_paren_params,
    _tokenize_spice_line,
    import_netlist,
    parse_netlist,
)

# ── Tokenizer ─────────────────────────────────────────────────────────


class TestTokenizer:
    """Test SPICE line tokenization."""

    def test_simple_tokens(self):
        tokens = _tokenize_spice_line("R1 1 2 1k")
        assert tokens == ["R1", "1", "2", "1k"]

    def test_paren_preserved(self):
        tokens = _tokenize_spice_line("Vin 1 0 SIN(0 5 1k)")
        assert tokens == ["Vin", "1", "0", "SIN(0 5 1k)"]

    def test_pulse_preserved(self):
        tokens = _tokenize_spice_line("V1 4 0 pulse(0 10 0 1ns 1ns 2ms 4ms)")
        assert tokens == ["V1", "4", "0", "pulse(0 10 0 1ns 1ns 2ms 4ms)"]

    def test_dc_value(self):
        tokens = _tokenize_spice_line("Vin 1 0 DC 10")
        assert tokens == ["Vin", "1", "0", "DC", "10"]


class TestExtractParenParams:
    def test_sin_params(self):
        params = _extract_paren_params("SIN(0 5 1k)")
        assert params == ["0", "5", "1k"]

    def test_no_parens(self):
        params = _extract_paren_params("DC 10")
        assert params == []


# ── parse_netlist ─────────────────────────────────────────────────────


class TestParseNetlist:
    """Test the parse_netlist function."""

    def test_simple_resistor_circuit(self):
        netlist = "Simple Circuit\nVin 1 0 DC 10\nR1 1 2 250\nR2 2 0 500\n.op\n.end\n"
        result = parse_netlist(netlist)
        assert result["title"] == "Simple Circuit"
        assert len(result["components"]) == 3  # Vin, R1, R2
        assert result["analysis"]["type"] == "DC Operating Point"

    def test_rc_circuit(self):
        netlist = "RC Circuit\nr1 1 2 1k\nc1 2 0 1u\nvin 1 0 DC 5\n.tran 0.02ms 20ms\n.end\n"
        result = parse_netlist(netlist)
        assert len(result["components"]) == 3
        assert result["analysis"]["type"] == "Transient"
        assert result["analysis"]["params"]["step"] == "0.02ms"
        assert result["analysis"]["params"]["duration"] == "20ms"

    def test_comments_skipped(self):
        netlist = "Test\n* This is a comment\nR1 1 0 1k\n.end\n"
        result = parse_netlist(netlist)
        assert len(result["components"]) == 1

    def test_control_block_skipped(self):
        netlist = "Test\nR1 1 0 1k\n.control\nrun\nprint v(1)\n.endc\n.end\n"
        result = parse_netlist(netlist)
        assert len(result["components"]) == 1

    def test_empty_netlist_raises(self):
        with pytest.raises(NetlistParseError):
            parse_netlist("")

    def test_no_components_raises(self):
        with pytest.raises(NetlistParseError):
            parse_netlist("Title Only\n.end\n")

    def test_model_directive_parsed(self):
        netlist = "Diode Test\nD1 1 2 DMOD\n.model DMOD D\n.end\n"
        result = parse_netlist(netlist)
        assert "DMOD" in result["models"]
        assert result["models"]["DMOD"]["type"] == "D"

    def test_ac_directive(self):
        netlist = "AC Test\nR1 1 0 1k\n.ac dec 10 1 1Meg\n.end\n"
        result = parse_netlist(netlist)
        assert result["analysis"]["type"] == "AC Sweep"
        assert result["analysis"]["params"]["sweep_type"] == "dec"

    def test_dc_directive(self):
        netlist = "DC Test\nR1 1 0 1k\n.dc Vin 0 10 0.1\n.end\n"
        result = parse_netlist(netlist)
        assert result["analysis"]["type"] == "DC Sweep"
        assert result["analysis"]["params"]["source"] == "Vin"

    def test_subcircuit_skipped(self):
        netlist = "Sub test\n.subckt MYBLOCK in out\nR1 in out 1k\n.ends\nR2 1 0 10k\n.end\n"
        result = parse_netlist(netlist)
        # Only R2 should be parsed (R1 is inside subcircuit)
        assert len(result["components"]) == 1
        assert result["components"][0]["id"] == "R2"


# ── Component parsing ─────────────────────────────────────────────────


class TestComponentParsing:
    """Test parsing of individual component types."""

    def test_resistor(self):
        result = parse_netlist("Test\nR1 1 2 1k\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Resistor"
        assert comp["value"] == "1k"
        assert comp["nodes"] == ["1", "2"]

    def test_capacitor(self):
        result = parse_netlist("Test\nC1 2 0 1u\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Capacitor"
        assert comp["value"] == "1u"

    def test_inductor(self):
        result = parse_netlist("Test\nL1 3 4 10m\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Inductor"
        assert comp["value"] == "10m"

    def test_voltage_source_dc(self):
        result = parse_netlist("Test\nVin 1 0 DC 10\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Voltage Source"
        assert comp["value"] == "10"

    def test_voltage_source_bare(self):
        result = parse_netlist("Test\nV1 1 0 5\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Voltage Source"
        assert comp["value"] == "5"

    def test_waveform_sin(self):
        result = parse_netlist("Test\nVin 1 0 SIN(0 5 1k)\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Waveform Source"
        assert "SIN" in comp["value"]

    def test_waveform_pulse(self):
        result = parse_netlist("Test\nV1 4 0 pulse(0 10 0 1ns 1ns 2ms 4ms)\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Waveform Source"

    def test_current_source(self):
        result = parse_netlist("Test\nI1 1 0 DC 1A\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Current Source"

    def test_diode(self):
        result = parse_netlist("Test\nD1 1 2 DMOD\n.model DMOD D\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "Diode"
        assert comp["nodes"] == ["1", "2"]

    def test_bjt_npn(self):
        result = parse_netlist("Test\nQ1 3 2 1 2N3904\n.model 2N3904 NPN\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "BJT NPN"
        assert comp["nodes"] == ["3", "2", "1"]

    def test_bjt_pnp_from_model(self):
        result = parse_netlist("Test\nQ1 3 2 1 2N3906\n.model 2N3906 PNP\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "BJT PNP"

    def test_mosfet_nmos(self):
        result = parse_netlist("Test\nM1 3 4 0 0 MMOD\n.model MMOD NMOS\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "MOSFET NMOS"
        assert comp["nodes"] == ["3", "4", "0", "0"]

    def test_mosfet_pmos_from_model(self):
        result = parse_netlist("Test\nM1 3 4 0 0 PM\n.model PM PMOS\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "MOSFET PMOS"

    def test_vcvs(self):
        result = parse_netlist("Test\nE1 3 4 1 2 10\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "VCVS"
        assert comp["value"] == "10"

    def test_vccs(self):
        result = parse_netlist("Test\nG1 3 4 1 2 0.01\n.end\n")
        comp = result["components"][0]
        assert comp["type"] == "VCCS"

    def test_ac_sin_source(self):
        netlist = "Test\nVin 1 0 AC sin(0 100 60 0 0 90)\n.end\n"
        result = parse_netlist(netlist)
        comp = result["components"][0]
        assert comp["type"] == "Waveform Source"


# ── import_netlist (full integration) ─────────────────────────────────


class TestImportNetlist:
    """Test the full import_netlist function that builds a CircuitModel."""

    def test_simple_resistor_circuit(self):
        netlist = "Simple Circuit\nVin 1 0 DC 10\nR1 1 2 250\nR2 2 0 500\n.op\n.end\n"
        model, analysis = import_netlist(netlist)
        # Should have Vin, R1, R2 + Ground components
        assert "Vin" in model.components
        assert "R1" in model.components
        assert "R2" in model.components
        assert model.components["R1"].component_type == "Resistor"
        assert model.components["R1"].value == "250"
        assert model.components["Vin"].component_type == "Voltage Source"
        assert analysis["type"] == "DC Operating Point"

    def test_ground_components_created(self):
        netlist = "Test\nV1 1 0 DC 5\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        # Should create Ground components for node 0 connections
        ground_ids = [c for c in model.components if c.startswith("GND")]
        assert len(ground_ids) >= 1

    def test_wires_created(self):
        netlist = "Test\nV1 1 0 DC 5\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        # Should have wires connecting components
        assert len(model.wires) > 0

    def test_components_have_positions(self):
        netlist = "Test\nR1 1 2 1k\nR2 2 0 2k\n.end\n"
        model, _ = import_netlist(netlist)
        r1 = model.components["R1"]
        r2 = model.components["R2"]
        # Components should have different positions
        assert r1.position != r2.position

    def test_counter_updated(self):
        netlist = "Test\nR1 1 2 1k\nR3 2 0 2k\n.end\n"
        model, _ = import_netlist(netlist)
        # Counter should be at least 3 (max of R1=1, R3=3)
        assert model.component_counter.get("R", 0) >= 3

    def test_analysis_set(self):
        netlist = "Test\nR1 1 0 1k\n.tran 1u 1m\n.end\n"
        model, analysis = import_netlist(netlist)
        assert model.analysis_type == "Transient"
        assert model.analysis_params["step"] == "1u"

    def test_node_connections_correct(self):
        """Components sharing a node should be wired together."""
        netlist = "Test\nV1 1 0 DC 5\nR1 1 2 1k\nR2 2 0 2k\n.end\n"
        model, _ = import_netlist(netlist)
        # Node 1 connects V1 terminal 0 and R1 terminal 0
        # Node 2 connects R1 terminal 1 and R2 terminal 0
        # Node 0 connects V1 terminal 1, R2 terminal 1 to GND
        non_gnd_wires = [
            w
            for w in model.wires
            if not w.start_component_id.startswith("GND") and not w.end_component_id.startswith("GND")
        ]
        # Should have at least 2 signal wires (node 1 and node 2)
        assert len(non_gnd_wires) >= 2

    def test_waveform_source_params(self):
        netlist = "Test\nV1 1 0 SIN(0 5 1k)\nR1 1 0 1k\n.end\n"
        model, _ = import_netlist(netlist)
        v1 = model.components["V1"]
        assert v1.component_type == "Waveform Source"
        assert v1.waveform_type == "SIN"
        assert v1.waveform_params is not None
        assert v1.waveform_params["SIN"]["amplitude"] == "5"

    def test_four_resistor_example(self):
        """Test with the actual Simple4ResistorCircuit example."""
        netlist = (
            "Simple 4 Resistor Circuit\nVin 1 0 DC 10\nR1 1 2 250\nR2 2 3 250\nR3 2 0 500\nR4 3 0 250\n.op\n.end\n"
        )
        model, analysis = import_netlist(netlist)
        assert len([c for c in model.components if not c.startswith("GND")]) == 5
        assert analysis["type"] == "DC Operating Point"

    def test_diode_circuit(self):
        netlist = "Diode Test\nVin 1 0 DC 5\nD1 1 2 DMOD\nR1 2 0 100k\n.model DMOD D\n.end\n"
        model, _ = import_netlist(netlist)
        assert "D1" in model.components
        assert model.components["D1"].component_type == "Diode"


# ── FileController integration ────────────────────────────────────────


class TestFileControllerImport:
    """Test FileController.import_netlist()."""

    def test_import_from_file(self, tmp_path):
        from controllers.file_controller import FileController

        netlist_file = tmp_path / "test.cir"
        netlist_file.write_text("Test Circuit\nV1 1 0 DC 5\nR1 1 0 1k\n.op\n.end\n")

        fc = FileController()
        fc.import_netlist(netlist_file)

        assert "V1" in fc.model.components
        assert "R1" in fc.model.components
        assert fc.model.analysis_type == "DC Operating Point"
        assert fc.current_file is None  # Not set for imports

    def test_import_nonexistent_file(self, tmp_path):
        from controllers.file_controller import FileController

        fc = FileController()
        with pytest.raises(OSError):
            fc.import_netlist(tmp_path / "nonexistent.cir")

    def test_import_invalid_netlist(self, tmp_path):
        from controllers.file_controller import FileController

        bad_file = tmp_path / "bad.cir"
        bad_file.write_text("Just a title\n.end\n")

        fc = FileController()
        with pytest.raises(NetlistParseError):
            fc.import_netlist(bad_file)
