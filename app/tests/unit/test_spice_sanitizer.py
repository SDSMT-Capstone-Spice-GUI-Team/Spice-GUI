"""Tests for simulation/spice_sanitizer.py — input sanitization for netlist generation (#761)."""

import pytest
from simulation.spice_sanitizer import (
    sanitize_netlist_text,
    sanitize_spice_identifier,
    sanitize_spice_value,
    validate_output_dir,
    validate_wrdata_filepath,
)


class TestSanitizeSpiceValue:
    """Tests for sanitize_spice_value()."""

    @pytest.mark.parametrize(
        "value",
        [
            "1k",
            "4.7u",
            "10MEG",
            "100",
            "3.3V",
            "2N3904",
            "0.001",
            "1e-3",
            "SINE(0 1 1k)",
            "PULSE(0 5 0 1n 1n 5u 10u)",
            "AC 1",
            "BF=300 IS=1e-14 VAF=100",
            "VTO=0.7 KP=110u",
            "10mH 10mH 0.99",
        ],
    )
    def test_valid_values_pass(self, value):
        assert sanitize_spice_value(value) == value

    def test_strips_whitespace(self):
        assert sanitize_spice_value("  1k  ") == "1k"

    def test_empty_value_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            sanitize_spice_value("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            sanitize_spice_value("   ")

    def test_system_directive_in_value_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive"):
            sanitize_spice_value("1k\n.system rm -rf /")

    def test_shell_directive_in_value_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive"):
            sanitize_spice_value("1k\n.shell echo pwned")

    def test_include_directive_in_value_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive"):
            sanitize_spice_value("1k\n.include /etc/passwd")

    def test_lib_directive_in_value_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive"):
            sanitize_spice_value("1k\n.lib malicious.lib")

    def test_newline_in_value_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive|invalid characters"):
            sanitize_spice_value("1k\nV_malicious 1 0 DC 5")

    def test_carriage_return_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive|invalid characters"):
            sanitize_spice_value("1k\r.system bad")

    def test_non_string_converted(self):
        assert sanitize_spice_value(1000) == "1000"

    def test_semicolon_rejected(self):
        with pytest.raises(ValueError, match="dangerous directive|invalid characters"):
            sanitize_spice_value("1k; .system rm -rf /")

    def test_backtick_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_spice_value("`rm -rf /`")


class TestSanitizeSpiceIdentifier:
    """Tests for sanitize_spice_identifier()."""

    @pytest.mark.parametrize(
        "name",
        ["V1", "R1", "GND1", "nodeA", "OPAMP_IDEAL", "2N3904"],
    )
    def test_valid_identifiers_pass(self, name):
        assert sanitize_spice_identifier(name) == name

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            sanitize_spice_identifier("")

    def test_spaces_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_spice_identifier("V 1")

    def test_special_chars_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_spice_identifier("V1;.system bad")

    def test_newline_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_spice_identifier("V1\n.system bad")


class TestSanitizeNetlistText:
    """Tests for sanitize_netlist_text() — defence-in-depth."""

    def test_system_directive_commented_out(self):
        text = "V1 1 0 DC 5\n.system rm -rf /\n.end"
        result = sanitize_netlist_text(text)
        # The directive is neutralized — it's now a SPICE comment, not an active directive
        assert "* SANITIZED:" in result
        assert "V1 1 0 DC 5" in result
        assert ".end" in result
        # Verify no line starts with .system (ignoring comments)
        for line in result.splitlines():
            stripped = line.lstrip()
            assert not stripped.startswith(".system"), f"Active .system directive found: {line}"

    def test_shell_directive_commented_out(self):
        text = ".shell echo pwned > /tmp/pwned"
        result = sanitize_netlist_text(text)
        assert "* SANITIZED:" in result

    def test_case_insensitive(self):
        text = ".SYSTEM bad_command"
        result = sanitize_netlist_text(text)
        assert "* SANITIZED:" in result

    def test_leading_whitespace_before_directive(self):
        text = "  .system bad_command"
        result = sanitize_netlist_text(text)
        assert "* SANITIZED:" in result

    def test_safe_directives_preserved(self):
        text = ".op\n.dc V1 0 10 0.1\n.tran 1u 10m\n.end"
        result = sanitize_netlist_text(text)
        assert result == text

    def test_meas_directive_preserved(self):
        text = ".meas tran v_max MAX v(out)"
        result = sanitize_netlist_text(text)
        assert result == text


class TestValidateWrdataFilepath:
    """Tests for validate_wrdata_filepath()."""

    def test_simple_relative_path(self):
        assert validate_wrdata_filepath("output/data.txt") == "output/data.txt"

    def test_windows_path(self):
        path = r"simulation_output\wrdata.txt"
        assert validate_wrdata_filepath(path) == path

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_wrdata_filepath("../../etc/passwd")

    def test_path_traversal_in_middle_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_wrdata_filepath("output/../../../etc/passwd")

    def test_windows_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_wrdata_filepath(r"output\..\..\etc\passwd")

    def test_newline_in_path_rejected(self):
        with pytest.raises(ValueError, match="newline"):
            validate_wrdata_filepath("output/data.txt\n.system bad")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_wrdata_filepath("")

    def test_dotdot_in_filename_allowed(self):
        """A filename containing '..' as a substring (not a path component) is OK."""
        assert validate_wrdata_filepath("data..txt") == "data..txt"


class TestValidateOutputDir:
    """Tests for validate_output_dir()."""

    def test_simple_relative_dir(self):
        assert validate_output_dir("simulation_output") == "simulation_output"

    def test_absolute_path_allowed(self):
        assert validate_output_dir("/tmp/sim_output") == "/tmp/sim_output"

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_output_dir("../../../tmp/evil")

    def test_path_traversal_in_middle_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_output_dir("sim_output/../../evil")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_output_dir("")


class TestNetlistGeneratorSanitization:
    """Integration tests: malicious values caught during netlist generation."""

    def test_malicious_system_directive_in_resistor_value(self):
        """A .system directive embedded in a component value must be rejected."""
        from models.node import NodeData
        from simulation.netlist_generator import NetlistGenerator
        from tests.conftest import make_component, make_wire

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "R1": make_component("Resistor", "R1", "1k\n.system rm -rf /", (100, 0)),
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

        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        with pytest.raises(ValueError, match="dangerous directive"):
            gen.generate()

    def test_path_traversal_in_wrdata_filepath_rejected(self):
        """wrdata_filepath with path traversal must be rejected at construction."""
        from simulation.netlist_generator import NetlistGenerator
        from tests.conftest import make_component, make_wire

        with pytest.raises(ValueError, match="path traversal"):
            NetlistGenerator(
                components={},
                wires=[],
                nodes=[],
                terminal_to_node={},
                analysis_type="DC Operating Point",
                analysis_params={},
                wrdata_filepath="../../etc/passwd",
            )

    def test_path_traversal_in_output_dir_rejected(self):
        """NgspiceRunner with path traversal in output_dir must be rejected."""
        from simulation.ngspice_runner import NgspiceRunner

        with pytest.raises(ValueError, match="path traversal"):
            NgspiceRunner(output_dir="../../../tmp/evil")
