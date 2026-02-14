"""Tests for LTspice .asc file parser."""

import pytest
from simulation.asc_parser import (AscParseError, _transform_pin, import_asc,
                                   parse_asc)

# --- Sample .asc content for tests ---

SIMPLE_RC = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
WIRE 192 192 192 160
WIRE 80 192 80 80
WIRE 192 192 80 192
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL cap 176 96 R0
SYMATTR InstName C1
SYMATTR Value 1u
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
"""

VOLTAGE_DIVIDER = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
WIRE 192 192 192 80
WIRE 80 256 80 80
WIRE 192 256 192 192
WIRE 192 256 80 256
FLAG 80 256 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 10k
SYMBOL res 176 176 R0
SYMATTR InstName R2
SYMATTR Value 10k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
"""

WITH_ANALYSIS = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
TEXT -32 280 Left 2 !.tran 10m
"""

UNSUPPORTED_COMPONENT = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
SYMBOL some_exotic_part 300 80 R0
SYMATTR InstName X1
SYMATTR Value exotic
"""

OP_AMP_CIRCUIT = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
WIRE 400 160 368 160
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 10k
SYMBOL Opamps\\\\opamp 336 192 R0
SYMATTR InstName U1
SYMATTR Value Ideal
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 1V
"""

BJT_CIRCUIT = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 256 0
SYMBOL npn 160 112 R0
SYMATTR InstName Q1
SYMATTR Value 2N3904
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 4.7k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 12V
"""

WAVEFORM_SOURCE = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value SINE(0 5 1k)
"""

AC_ANALYSIS = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 1V
TEXT -32 280 Left 2 !.ac dec 100 1 100k
"""

DC_SWEEP = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
TEXT -32 280 Left 2 !.dc V1 0 10 0.1
"""

ROTATED_COMPONENTS = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
SYMBOL res 176 64 R90
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL cap 300 64 M0
SYMATTR InstName C1
SYMATTR Value 1u
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
"""

MULTIPLE_GROUNDS = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 192 0
FLAG 300 192 0
SYMBOL res 176 64 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
"""

DIODE_AND_MOSFET = """\
Version 4
SHEET 1 880 680
WIRE 192 80 80 80
FLAG 80 256 0
SYMBOL diode 176 80 R0
SYMATTR InstName D1
SYMATTR Value IS=1e-14
SYMBOL nmos 256 128 R0
SYMATTR InstName M1
SYMATTR Value NMOS1
SYMBOL voltage 80 80 R0
SYMATTR InstName V1
SYMATTR Value 5V
"""


class TestParseAsc:
    def test_parses_simple_rc(self):
        result = parse_asc(SIMPLE_RC)
        assert len(result["components"]) == 3
        assert len(result["wires"]) == 4
        assert len(result["flags"]) == 1

    def test_parses_component_names(self):
        result = parse_asc(SIMPLE_RC)
        names = {c["inst_name"] for c in result["components"]}
        assert names == {"R1", "C1", "V1"}

    def test_parses_component_values(self):
        result = parse_asc(SIMPLE_RC)
        values = {c["inst_name"]: c["value"] for c in result["components"]}
        assert values["R1"] == "1k"
        assert values["C1"] == "1u"
        assert values["V1"] == "5V"

    def test_parses_positions(self):
        result = parse_asc(SIMPLE_RC)
        positions = {c["inst_name"]: (c["x"], c["y"]) for c in result["components"]}
        assert positions["R1"] == (176, 64)
        assert positions["V1"] == (80, 80)

    def test_parses_rotations(self):
        result = parse_asc(ROTATED_COMPONENTS)
        rotations = {c["inst_name"]: c["rotation"] for c in result["components"]}
        assert rotations["R1"] == "R90"
        assert rotations["C1"] == "M0"
        assert rotations["V1"] == "R0"

    def test_parses_wires(self):
        result = parse_asc(SIMPLE_RC)
        assert all(len(w) == 4 for w in result["wires"])
        assert (192, 80, 80, 80) in result["wires"]

    def test_parses_flags(self):
        result = parse_asc(SIMPLE_RC)
        assert (80, 192, "0") in result["flags"]

    def test_parses_tran_analysis(self):
        result = parse_asc(WITH_ANALYSIS)
        assert result["analysis"] is not None
        assert result["analysis"]["type"] == "Transient"
        assert result["analysis"]["params"]["duration"] == "10m"

    def test_parses_ac_analysis(self):
        result = parse_asc(AC_ANALYSIS)
        assert result["analysis"]["type"] == "AC Sweep"
        assert result["analysis"]["params"]["sweep_type"] == "dec"
        assert result["analysis"]["params"]["fStop"] == "100k"

    def test_parses_dc_analysis(self):
        result = parse_asc(DC_SWEEP)
        assert result["analysis"]["type"] == "DC Sweep"
        assert result["analysis"]["params"]["source"] == "V1"
        assert result["analysis"]["params"]["step"] == "0.1"

    def test_empty_file_raises(self):
        with pytest.raises(AscParseError):
            parse_asc("")

    def test_no_content_raises(self):
        with pytest.raises(AscParseError, match="No components"):
            parse_asc("Version 4\nSHEET 1 880 680\n")

    def test_handles_crlf(self):
        crlf_content = SIMPLE_RC.replace("\n", "\r\n")
        result = parse_asc(crlf_content)
        assert len(result["components"]) == 3


class TestImportAsc:
    def test_creates_components(self):
        model, _analysis, _warnings = import_asc(SIMPLE_RC)
        assert "R1" in model.components
        assert "C1" in model.components
        assert "V1" in model.components

    def test_component_types(self):
        model, _analysis, _warnings = import_asc(SIMPLE_RC)
        assert model.components["R1"].component_type == "Resistor"
        assert model.components["C1"].component_type == "Capacitor"
        assert model.components["V1"].component_type == "Voltage Source"

    def test_component_values(self):
        model, _analysis, _warnings = import_asc(VOLTAGE_DIVIDER)
        assert model.components["R1"].value == "10k"
        assert model.components["R2"].value == "10k"
        assert model.components["V1"].value == "5V"

    def test_creates_wires(self):
        model, _analysis, _warnings = import_asc(VOLTAGE_DIVIDER)
        assert len(model.wires) > 0

    def test_creates_ground_components(self):
        model, _analysis, _warnings = import_asc(SIMPLE_RC)
        ground_comps = [
            c for c in model.components.values() if c.component_type == "Ground"
        ]
        assert len(ground_comps) >= 1

    def test_sets_analysis_type(self):
        model, analysis, _warnings = import_asc(WITH_ANALYSIS)
        assert analysis is not None
        assert model.analysis_type == "Transient"

    def test_unsupported_component_warning(self):
        _model, _analysis, warnings = import_asc(UNSUPPORTED_COMPONENT)
        assert any("some_exotic_part" in w for w in warnings)

    def test_unsupported_component_skipped(self):
        model, _analysis, _warnings = import_asc(UNSUPPORTED_COMPONENT)
        assert "X1" not in model.components
        # But supported components should still be there
        assert "R1" in model.components
        assert "V1" in model.components

    def test_counter_tracking(self):
        model, _analysis, _warnings = import_asc(VOLTAGE_DIVIDER)
        assert model.component_counter.get("R", 0) >= 2
        assert model.component_counter.get("V", 0) >= 1

    def test_op_amp_import(self):
        model, _analysis, _warnings = import_asc(OP_AMP_CIRCUIT)
        assert "U1" in model.components
        assert model.components["U1"].component_type == "Op-Amp"

    def test_bjt_import(self):
        model, _analysis, _warnings = import_asc(BJT_CIRCUIT)
        assert "Q1" in model.components
        assert model.components["Q1"].component_type == "BJT NPN"
        assert model.components["Q1"].value == "2N3904"

    def test_diode_and_mosfet_import(self):
        model, _analysis, _warnings = import_asc(DIODE_AND_MOSFET)
        assert "D1" in model.components
        assert model.components["D1"].component_type == "Diode"
        assert "M1" in model.components
        assert model.components["M1"].component_type == "MOSFET NMOS"

    def test_nodes_rebuilt(self):
        model, _analysis, _warnings = import_asc(SIMPLE_RC)
        assert len(model.nodes) > 0

    def test_rotated_components(self):
        model, _analysis, _warnings = import_asc(ROTATED_COMPONENTS)
        assert model.components["R1"].rotation == 90
        assert model.components["C1"].flip_h is True

    def test_multiple_grounds(self):
        model, _analysis, _warnings = import_asc(MULTIPLE_GROUNDS)
        ground_comps = [
            c for c in model.components.values() if c.component_type == "Ground"
        ]
        assert len(ground_comps) >= 1

    def test_waveform_source_detection(self):
        model, _analysis, _warnings = import_asc(WAVEFORM_SOURCE)
        assert model.components["V1"].component_type == "Waveform Source"

    def test_ac_analysis_import(self):
        model, analysis, _warnings = import_asc(AC_ANALYSIS)
        assert model.analysis_type == "AC Sweep"
        assert analysis["params"]["fStart"] == "1"


class TestTransformPin:
    def test_r0_no_change(self):
        assert _transform_pin(10, 20, "R0") == (10, 20)

    def test_r90(self):
        assert _transform_pin(10, 20, "R90") == (20, -10)

    def test_r180(self):
        assert _transform_pin(10, 20, "R180") == (-10, -20)

    def test_r270(self):
        assert _transform_pin(10, 20, "R270") == (-20, 10)

    def test_m0_mirror(self):
        assert _transform_pin(10, 20, "M0") == (-10, 20)

    def test_m90_mirror(self):
        assert _transform_pin(10, 20, "M90") == (20, 10)

    def test_m180_mirror(self):
        assert _transform_pin(10, 20, "M180") == (10, -20)

    def test_m270_mirror(self):
        assert _transform_pin(10, 20, "M270") == (-20, -10)

    def test_none_defaults_to_r0(self):
        assert _transform_pin(10, 20, None) == (10, 20)


class TestFileControllerIntegration:
    def test_import_asc_via_controller(self, tmp_path):
        """Test the full import pipeline through FileController."""
        from controllers.file_controller import FileController

        asc_file = tmp_path / "test.asc"
        asc_file.write_text(VOLTAGE_DIVIDER)

        ctrl = FileController()
        warnings = ctrl.import_asc(asc_file)

        assert "R1" in ctrl.model.components
        assert "R2" in ctrl.model.components
        assert "V1" in ctrl.model.components
        assert ctrl.current_file is None
        assert isinstance(warnings, list)

    def test_import_asc_with_unsupported(self, tmp_path):
        """Unsupported components should produce warnings but not fail."""
        from controllers.file_controller import FileController

        asc_file = tmp_path / "test.asc"
        asc_file.write_text(UNSUPPORTED_COMPONENT)

        ctrl = FileController()
        warnings = ctrl.import_asc(asc_file)

        assert len(warnings) > 0
        assert "R1" in ctrl.model.components

    def test_import_asc_invalid_raises(self, tmp_path):
        """Invalid .asc content should raise AscParseError."""
        from controllers.file_controller import FileController
        from simulation.asc_parser import AscParseError

        asc_file = tmp_path / "bad.asc"
        asc_file.write_text("")

        ctrl = FileController()
        with pytest.raises(AscParseError):
            ctrl.import_asc(asc_file)
