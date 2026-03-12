"""
Tests for simulation/result_parser.py — ngspice output parsing.
"""

import os

import pytest
from simulation.result_parser import ResultParseError, ResultParser

# ── parse_op_results ─────────────────────────────────────────────────


class TestParseOpResults:
    def test_pattern1_equals(self):
        output = "v(nodeA) = 5.00000\nv(nodeB) = 2.50000\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["nodeA"] == pytest.approx(5.0)
        assert result["node_voltages"]["nodeB"] == pytest.approx(2.5)

    def test_pattern1_colon(self):
        output = "v(out): 3.3\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["out"] == pytest.approx(3.3)

    def test_pattern3_print_format(self):
        output = "  V(nodeA)                        5.000000e+00\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["nodeA"] == pytest.approx(5.0)

    def test_pattern2_table_format(self):
        output = (
            "Node                  Voltage\n"
            "----                  -------\n"
            "nodeA                 5.0\n"
            "nodeB                 2.5\n"
        )
        result = ResultParser.parse_op_results(output)
        assert "nodeA" in result["node_voltages"]
        assert result["node_voltages"]["nodeA"] == pytest.approx(5.0)

    def test_empty_string(self):
        result = ResultParser.parse_op_results("")
        assert result["node_voltages"] == {}
        assert result["branch_currents"] == {}

    def test_garbage_input(self):
        result = ResultParser.parse_op_results("random garbage text\nnothing useful\n")
        assert result["node_voltages"] == {}
        assert result["branch_currents"] == {}

    def test_bad_line_does_not_discard_valid_data(self):
        """A single unparseable line must not lose previously parsed results (#529)."""
        output = "v(nodeA) = 5.00000\nv(bad) = NOT_A_NUMBER\nv(nodeB) = 2.50000\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["nodeA"] == pytest.approx(5.0)
        assert result["node_voltages"]["nodeB"] == pytest.approx(2.5)
        assert "bad" not in result["node_voltages"]

    def test_bad_current_line_preserves_other_data(self):
        """An unparseable branch current should not discard voltages (#529)."""
        output = "v(nodeA) = 3.30000\ni(v1) = GARBAGE\n  V(nodeB)   1.000000e+00\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["nodeA"] == pytest.approx(3.3)
        assert result["node_voltages"]["nodeB"] == pytest.approx(1.0)

    def test_mixed_good_and_bad_print_format(self):
        """Pattern 3 bad lines should be skipped, not abort (#529)."""
        output = "  V(nodeA)   5.000000e+00\n  V(nodeB)   CORRUPT_VALUE\n  V(nodeC)   2.500000e+00\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["nodeA"] == pytest.approx(5.0)
        assert result["node_voltages"]["nodeC"] == pytest.approx(2.5)
        assert "nodeB" not in result["node_voltages"]

    # ── scientific notation edge cases (issue #779) ───────────────────

    def test_scientific_notation_fractional_no_leading_digit(self):
        """.5e3 (no leading digit before decimal) is valid scientific notation."""
        output = "v(a) = .5e3\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["a"] == pytest.approx(500.0)

    def test_scientific_notation_positive_exponent_uppercase_e(self):
        """+1.5E+3 (positive sign, uppercase E) must parse correctly."""
        output = "v(b) = +1.5E+3\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["b"] == pytest.approx(1500.0)

    def test_scientific_notation_negative_exponent(self):
        """1.5e-3 remains parseable after regex tightening."""
        output = "v(c) = 1.5e-3\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["c"] == pytest.approx(0.0015)

    def test_scientific_notation_print_format_variants(self):
        """Pattern 3 (print format) handles scientific notation variants."""
        output = "  V(x)   .5e3\n  V(y)   +1.5E+3\n  V(z)   1.5e-3\n"
        result = ResultParser.parse_op_results(output)
        assert result["node_voltages"]["x"] == pytest.approx(500.0)
        assert result["node_voltages"]["y"] == pytest.approx(1500.0)
        assert result["node_voltages"]["z"] == pytest.approx(0.0015)

    def test_branch_current_scientific_notation(self):
        """Branch current regex also handles scientific notation variants."""
        output = "i(v1) = .5e-3\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(0.0005)


# ── parse_dc_results ─────────────────────────────────────────────────


class TestParseDcResults:
    def test_valid_sweep(self):
        output = (
            "Index   v-sweep   v(nodeA)\n0       0.000     0.000\n1       1.000     0.500\n2       2.000     1.000\n"
        )
        result = ResultParser.parse_dc_results(output)
        assert result is not None
        assert len(result["data"]) == 3
        assert result["data"][0][1] == pytest.approx(0.0)
        assert result["data"][2][2] == pytest.approx(1.0)

    def test_no_data_returns_none(self):
        output = "Some random text\nwith no sweep data\n"
        result = ResultParser.parse_dc_results(output)
        assert result is None

    def test_empty_string(self):
        result = ResultParser.parse_dc_results("")
        assert result is None


# ── parse_ac_results ─────────────────────────────────────────────────


class TestParseAcResults:
    def test_valid_ac_data(self):
        output = (
            "Index   frequency   v(out)   vp(out)\n"
            "0       100.0       1.0      -45.0\n"
            "1       1000.0      0.5      -90.0\n"
        )
        result = ResultParser.parse_ac_results(output)
        assert result is not None
        assert len(result["frequencies"]) == 2
        assert result["frequencies"][0] == pytest.approx(100.0)
        assert "out" in result["magnitude"]
        assert len(result["magnitude"]["out"]) == 2
        assert "out" in result["phase"]
        assert result["phase"]["out"][1] == pytest.approx(-90.0)

    def test_no_frequency_returns_none(self):
        result = ResultParser.parse_ac_results("just some text\n")
        assert result is None

    def test_empty_returns_none(self):
        result = ResultParser.parse_ac_results("")
        assert result is None


# ── parse_transient_results ──────────────────────────────────────────


class TestParseTransientResults:
    def test_valid_wrdata(self, tmp_path):
        wrdata = tmp_path / "tran.txt"
        wrdata.write_text(
            "time v(nodeA) v(nodeB)\n0.000000e+00 5.000000e+00 2.500000e+00\n1.000000e-03 4.900000e+00 2.450000e+00\n"
        )
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is not None
        assert len(result) == 2
        assert result[0]["time"] == pytest.approx(0.0)
        assert result[0]["nodeA"] == pytest.approx(5.0)

    def test_header_sanitization(self, tmp_path):
        wrdata = tmp_path / "tran2.txt"
        wrdata.write_text("time v(out) i(v1#branch)\n0.0 1.0 0.001\n")
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is not None
        headers = list(result[0].keys())
        assert "out" in headers
        assert "i_v1#branch" in headers

    def test_missing_file_raises_parse_error(self):
        with pytest.raises(ResultParseError, match="wrdata file not found"):
            ResultParser.parse_transient_results("/nonexistent/path.txt")

    def test_empty_file_returns_none(self, tmp_path):
        wrdata = tmp_path / "empty.txt"
        wrdata.write_text("")
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is None

    def test_header_only_returns_none(self, tmp_path):
        wrdata = tmp_path / "header_only.txt"
        wrdata.write_text("time v(nodeA)\n")
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is None


# ── format_results_as_table ──────────────────────────────────────────


class TestFormatResultsAsTable:
    def test_valid_data(self):
        data = [
            {"time": 0.0, "voltage": 5.0},
            {"time": 1.0, "voltage": 4.5},
        ]
        table = ResultParser.format_results_as_table(data)
        assert "time" in table
        assert "voltage" in table
        assert "---" in table  # separator

    def test_empty_list(self):
        result = ResultParser.format_results_as_table([])
        assert "No data" in result

    def test_none_input(self):
        result = ResultParser.format_results_as_table(None)
        assert "No data" in result


# ── ResultParseError propagation ────────────────────────────────────


class TestParseErrorPropagation:
    """Verify that parse failures raise ResultParseError instead of returning None."""

    def test_dc_parse_error_on_non_string(self):
        with pytest.raises(ResultParseError, match="DC results"):
            ResultParser.parse_dc_results(None)

    def test_ac_parse_error_on_non_string(self):
        with pytest.raises(ResultParseError, match="AC results"):
            ResultParser.parse_ac_results(None)

    def test_noise_parse_error_on_non_string(self):
        with pytest.raises(ResultParseError, match="noise results"):
            ResultParser.parse_noise_results(None)

    def test_sensitivity_parse_error_on_non_string(self):
        with pytest.raises(ResultParseError, match="sensitivity results"):
            ResultParser.parse_sensitivity_results(None)

    def test_tf_parse_error_on_non_string(self):
        with pytest.raises(ResultParseError, match="TF results"):
            ResultParser.parse_tf_results(None)

    def test_pz_parse_error_on_non_string(self):
        with pytest.raises(ResultParseError, match="PZ results"):
            ResultParser.parse_pz_results(None)

    def test_transient_parse_error_on_missing_file(self):
        with pytest.raises(ResultParseError, match="wrdata file not found"):
            ResultParser.parse_transient_results("/nonexistent/path.txt")
