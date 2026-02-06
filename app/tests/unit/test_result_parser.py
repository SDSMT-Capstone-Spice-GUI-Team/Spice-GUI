"""
Tests for simulation/result_parser.py — ngspice output parsing.
"""
import os
import pytest
from simulation.result_parser import ResultParser


# ── parse_op_results ─────────────────────────────────────────────────

class TestParseOpResults:

    def test_pattern1_equals(self):
        output = "v(nodeA) = 5.00000\nv(nodeB) = 2.50000\n"
        result = ResultParser.parse_op_results(output)
        assert result["nodeA"] == pytest.approx(5.0)
        assert result["nodeB"] == pytest.approx(2.5)

    def test_pattern1_colon(self):
        output = "v(out): 3.3\n"
        result = ResultParser.parse_op_results(output)
        assert result["out"] == pytest.approx(3.3)

    def test_pattern3_print_format(self):
        output = "  V(nodeA)                        5.000000e+00\n"
        result = ResultParser.parse_op_results(output)
        assert result["nodeA"] == pytest.approx(5.0)

    def test_pattern2_table_format(self):
        output = (
            "Node                  Voltage\n"
            "----                  -------\n"
            "nodeA                 5.0\n"
            "nodeB                 2.5\n"
        )
        result = ResultParser.parse_op_results(output)
        assert "nodeA" in result
        assert result["nodeA"] == pytest.approx(5.0)

    def test_empty_string(self):
        result = ResultParser.parse_op_results("")
        assert result == {}

    def test_garbage_input(self):
        result = ResultParser.parse_op_results("random garbage text\nnothing useful\n")
        assert result == {}


# ── parse_dc_results ─────────────────────────────────────────────────

class TestParseDcResults:

    def test_valid_sweep(self):
        output = (
            "Index   v-sweep   v(nodeA)\n"
            "0       0.000     0.000\n"
            "1       1.000     0.500\n"
            "2       2.000     1.000\n"
        )
        result = ResultParser.parse_dc_results(output)
        assert result is not None
        assert len(result['data']) == 3
        assert result['data'][0][1] == pytest.approx(0.0)
        assert result['data'][2][2] == pytest.approx(1.0)

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
        assert len(result['frequencies']) == 2
        assert result['frequencies'][0] == pytest.approx(100.0)
        assert "out" in result['magnitude']
        assert len(result['magnitude']['out']) == 2
        assert "out" in result['phase']
        assert result['phase']['out'][1] == pytest.approx(-90.0)

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
            "time v(nodeA) v(nodeB)\n"
            "0.000000e+00 5.000000e+00 2.500000e+00\n"
            "1.000000e-03 4.900000e+00 2.450000e+00\n"
        )
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is not None
        assert len(result) == 2
        assert result[0]["time"] == pytest.approx(0.0)
        assert result[0]["nodeA"] == pytest.approx(5.0)

    def test_header_sanitization(self, tmp_path):
        wrdata = tmp_path / "tran2.txt"
        wrdata.write_text(
            "time v(out) i(v1#branch)\n"
            "0.0 1.0 0.001\n"
        )
        result = ResultParser.parse_transient_results(str(wrdata))
        assert result is not None
        headers = list(result[0].keys())
        assert "out" in headers
        assert "i_v1#branch" in headers

    def test_missing_file_returns_none(self):
        result = ResultParser.parse_transient_results("/nonexistent/path.txt")
        assert result is None

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
