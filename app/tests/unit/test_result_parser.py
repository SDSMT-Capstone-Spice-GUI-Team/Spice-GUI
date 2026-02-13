"""
Tests for simulation/result_parser.py — ngspice output parsing.
"""

import math
import os

import pytest
from simulation.result_parser import ResultParser, format_si

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

    def test_branch_current_i_pattern(self):
        """Branch current via i(device) = value syntax."""
        output = "v(out) = 5.0\ni(v1) = -2.1e-03\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(-2.1e-3)

    def test_branch_current_at_device_pattern(self):
        """Branch current via @device[current] = value syntax."""
        output = "@r1[current] = 0.005\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["r1"] == pytest.approx(0.005)

    def test_pattern3_print_current(self):
        """Print format branch current: I(v1)  -2.100000e-03."""
        output = "  I(V1)   -2.100000e-03\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(-2.1e-3)

    def test_table_format_stops_at_source_line(self):
        """Table parsing stops when it encounters a 'source' line."""
        output = (
            "Node                  Voltage\n"
            "----                  -------\n"
            "nodeA                 3.3\n"
            "Source currents:\n"
            "should_not_parse      999\n"
        )
        result = ResultParser.parse_op_results(output)
        assert "nodeA" in result["node_voltages"]
        assert "should_not_parse" not in result["node_voltages"]

    def test_mixed_voltages_and_currents(self):
        """Output containing both voltages and currents."""
        output = "v(nodeA) = 5.0\nv(nodeB) = 2.5\ni(v1) = -0.005\ni(v2) = 0.001\n"
        result = ResultParser.parse_op_results(output)
        assert len(result["node_voltages"]) == 2
        assert len(result["branch_currents"]) == 2


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

    def test_invalid_data_rows_skipped(self):
        """Non-numeric data rows after header should be skipped."""
        output = "Index   v-sweep   v(out)\n0       0.000     0.000\nbad     data      row\n1       1.000     0.500\n"
        result = ResultParser.parse_dc_results(output)
        assert result is not None
        assert len(result["data"]) == 2

    def test_headers_stored(self):
        """Headers should be stored in the result dict."""
        output = "Index   v-sweep   v(nodeA)\n0   0.0   0.0\n"
        result = ResultParser.parse_dc_results(output)
        assert "headers" in result
        assert "v-sweep" in result["headers"]


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

    def test_multiple_nodes(self):
        """AC results with magnitude and phase for multiple nodes."""
        output = (
            "Index   frequency   v(out)   vp(out)   v(in)   vp(in)\n"
            "0       100.0       1.0      -10.0     0.5     -5.0\n"
        )
        result = ResultParser.parse_ac_results(output)
        assert result is not None
        assert "out" in result["magnitude"]
        assert "in" in result["magnitude"]
        assert "out" in result["phase"]
        assert "in" in result["phase"]

    def test_headers_stored(self):
        """Headers should be stored in the result dict."""
        output = "Index   frequency   v(out)   vp(out)\n0   100.0   1.0   -45.0\n"
        result = ResultParser.parse_ac_results(output)
        assert "headers" in result


# ── parse_noise_results ─────────────────────────────────────────────


class TestParseNoiseResults:
    def test_valid_noise_data(self):
        output = (
            "Index   frequency   onoise_spectrum   inoise_spectrum\n"
            "0       100.0       1.5e-8            2.3e-7\n"
            "1       1000.0      1.2e-9            1.8e-8\n"
        )
        result = ResultParser.parse_noise_results(output)
        assert result is not None
        assert len(result["frequencies"]) == 2
        assert result["frequencies"][0] == pytest.approx(100.0)
        assert len(result["onoise_spectrum"]) == 2
        assert len(result["inoise_spectrum"]) == 2

    def test_no_data_returns_none(self):
        result = ResultParser.parse_noise_results("just noise\n")
        assert result is None

    def test_empty_returns_none(self):
        result = ResultParser.parse_noise_results("")
        assert result is None

    def test_partial_header_missing_inoise(self):
        """Only onoise present in header."""
        output = "Index   frequency   onoise_spectrum\n0       100.0       1.5e-8\n"
        result = ResultParser.parse_noise_results(output)
        assert result is not None
        assert len(result["onoise_spectrum"]) == 1
        assert len(result["inoise_spectrum"]) == 0


# ── parse_sensitivity_results ───────────────────────────────────────


class TestParseSensitivityResults:
    def test_valid_sensitivity_data(self):
        output = (
            "DC Sensitivities of output v(out)\n"
            "\n"
            "Element name    Element value    Sensitivity     Normalized\n"
            "R1              1.000e+03        5.000e-04       5.000e-01\n"
            "R2              2.000e+03        2.500e-04       5.000e-01\n"
            "\n"
        )
        result = ResultParser.parse_sensitivity_results(output)
        assert result is not None
        assert len(result) == 2
        assert result[0]["element"] == "R1"
        assert result[0]["value"] == pytest.approx(1000.0)
        assert result[0]["sensitivity"] == pytest.approx(5e-4)
        assert result[0]["normalized_sensitivity"] == pytest.approx(0.5)

    def test_three_column_sensitivity(self):
        """Sensitivity with only 3 columns (no element value)."""
        output = "DC Sensitivities of output v(out)\n\nR1   5.000e-04   5.000e-01\n\n"
        result = ResultParser.parse_sensitivity_results(output)
        assert result is not None
        assert result[0]["value"] == 0.0
        assert result[0]["sensitivity"] == pytest.approx(5e-4)

    def test_no_data_returns_none(self):
        result = ResultParser.parse_sensitivity_results("random text\n")
        assert result is None

    def test_empty_returns_none(self):
        result = ResultParser.parse_sensitivity_results("")
        assert result is None

    def test_header_with_volts_unit_skipped(self):
        """Lines with 'volts/' should be skipped as header/unit lines."""
        output = "DC Sensitivities of output v(out)\nelement name   volts/unit    volts/volt\nR1   1e3   5e-4   0.5\n\n"
        result = ResultParser.parse_sensitivity_results(output)
        assert result is not None
        assert result[0]["element"] == "R1"


# ── parse_tf_results ────────────────────────────────────────────────


class TestParseTfResults:
    def test_valid_tf_output(self):
        output = (
            "Transfer function, output/input = 5.000000e-01\n"
            "Output impedance at v(out) = 5.000000e+02\n"
            "v1#Input impedance = 1.000000e+03\n"
        )
        result = ResultParser.parse_tf_results(output)
        assert result is not None
        assert result["transfer_function"] == pytest.approx(0.5)
        assert result["output_impedance"] == pytest.approx(500.0)
        assert result["input_impedance"] == pytest.approx(1000.0)

    def test_partial_tf_only_transfer(self):
        output = "Transfer function, output/input = 2.5\n"
        result = ResultParser.parse_tf_results(output)
        assert result is not None
        assert result["transfer_function"] == pytest.approx(2.5)
        assert "output_impedance" not in result

    def test_no_data_returns_none(self):
        result = ResultParser.parse_tf_results("nothing here\n")
        assert result is None

    def test_empty_returns_none(self):
        result = ResultParser.parse_tf_results("")
        assert result is None


# ── parse_pz_results ────────────────────────────────────────────────


class TestParsePzResults:
    def test_valid_pz_data(self):
        output = (
            "pole(1) = -1.00000e+03, 0.00000e+00\n"
            "pole(2) = -5.00000e+05, 3.00000e+05\n"
            "zero(1) = -2.00000e+04, 0.00000e+00\n"
        )
        result = ResultParser.parse_pz_results(output)
        assert result is not None
        assert len(result["poles"]) == 2
        assert len(result["zeros"]) == 1

    def test_pole_real_only(self):
        output = "pole(1) = -1.00000e+03, 0.00000e+00\n"
        result = ResultParser.parse_pz_results(output)
        assert result is not None
        pole = result["poles"][0]
        assert pole["real"] == pytest.approx(-1000.0)
        assert pole["imag"] == pytest.approx(0.0)
        assert not pole["is_unstable"]
        assert pole["frequency_hz"] == pytest.approx(1000.0 / (2 * math.pi))

    def test_unstable_pole(self):
        """Pole with positive real part should be flagged as unstable."""
        output = "pole(1) = 1.00000e+03, 0.00000e+00\n"
        result = ResultParser.parse_pz_results(output)
        assert result["poles"][0]["is_unstable"] is True

    def test_no_data_returns_none(self):
        result = ResultParser.parse_pz_results("nothing useful\n")
        assert result is None

    def test_empty_returns_none(self):
        result = ResultParser.parse_pz_results("")
        assert result is None


# ── parse_measurement_results ───────────────────────────────────────


class TestParseMeasurementResults:
    def test_valid_measurement(self):
        stdout = "  rise_time  =  1.23456e-06\n  peak_v  =  4.95\n"
        result = ResultParser.parse_measurement_results(stdout)
        assert result is not None
        assert result["rise_time"] == pytest.approx(1.23456e-6)
        assert result["peak_v"] == pytest.approx(4.95)

    def test_failed_measurement(self):
        stdout = "  rise_time  =  failed\n"
        result = ResultParser.parse_measurement_results(stdout)
        assert result is not None
        assert result["rise_time"] is None

    def test_mixed_success_and_failure(self):
        stdout = "  delay  =  1.5e-06\n  overshoot  =  failed\n"
        result = ResultParser.parse_measurement_results(stdout)
        assert result is not None
        assert result["delay"] == pytest.approx(1.5e-6)
        assert result["overshoot"] is None

    def test_no_measurements_returns_none(self):
        result = ResultParser.parse_measurement_results("some random text\n")
        assert result is None

    def test_empty_returns_none(self):
        result = ResultParser.parse_measurement_results("")
        assert result is None

    def test_none_input_returns_none(self):
        result = ResultParser.parse_measurement_results(None)
        assert result is None


# ── format_si ───────────────────────────────────────────────────────


class TestFormatSi:
    def test_zero(self):
        assert format_si(0, "V") == "0.00 V"

    def test_millivolts(self):
        assert format_si(0.0033, "V") == "3.30 mV"

    def test_kilohertz(self):
        assert format_si(1500, "Hz") == "1.50 kHz"

    def test_negative_value(self):
        result = format_si(-0.0033, "V")
        assert "-3.30 mV" == result

    def test_nan(self):
        assert format_si(float("nan"), "V") == "0.00 V"

    def test_inf(self):
        assert format_si(float("inf"), "A") == "0.00 A"

    def test_large_value_uses_giga(self):
        result = format_si(5e9, "Hz")
        assert "5.00 GHz" == result

    def test_very_large_value_above_giga(self):
        """Values > 1 THz still use G prefix."""
        result = format_si(1e12, "Hz")
        assert "G" in result

    def test_no_unit(self):
        result = format_si(1000)
        assert result == "1.00 k"


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
