"""Tests for simulation.measurement_builder.build_directive."""

import pytest
from simulation.measurement_builder import ANALYSIS_DOMAIN_MAP, MEAS_TYPES, build_directive


class TestAnalysisDomainMap:
    def test_transient_maps_to_tran(self):
        assert ANALYSIS_DOMAIN_MAP["Transient"] == "tran"

    def test_ac_sweep_maps_to_ac(self):
        assert ANALYSIS_DOMAIN_MAP["AC Sweep"] == "ac"

    def test_dc_sweep_maps_to_dc(self):
        assert ANALYSIS_DOMAIN_MAP["DC Sweep"] == "dc"


class TestMeasTypes:
    def test_meas_types_is_nonempty(self):
        assert len(MEAS_TYPES) > 0

    def test_all_entries_are_two_tuples(self):
        for entry in MEAS_TYPES:
            assert len(entry) == 2


class TestBuildDirectiveRangeTypes:
    @pytest.mark.parametrize("meas_type", ["AVG", "RMS", "MIN", "MAX", "PP", "INTEG"])
    def test_basic_range_directive(self, meas_type):
        result = build_directive("tran", "m1", meas_type, {"variable": "v(out)"})
        assert result == f".meas tran m1 {meas_type} v(out)"

    def test_from_val_appended(self):
        result = build_directive("dc", "gain", "AVG", {"variable": "v(out)", "from_val": "0"})
        assert "FROM=0" in result

    def test_to_val_appended(self):
        result = build_directive("dc", "gain", "AVG", {"variable": "v(out)", "to_val": "1"})
        assert "TO=1" in result

    def test_from_and_to_both_appended(self):
        result = build_directive("dc", "gain", "AVG", {"variable": "v(out)", "from_val": "0", "to_val": "1"})
        assert "FROM=0" in result
        assert "TO=1" in result

    def test_empty_from_val_not_appended(self):
        result = build_directive("tran", "x", "AVG", {"variable": "v(out)", "from_val": ""})
        assert "FROM" not in result

    def test_default_variable_is_v_out(self):
        result = build_directive("tran", "x", "AVG", {})
        assert "v(out)" in result


class TestBuildDirectiveFindAt:
    def test_basic_find_at(self):
        result = build_directive("tran", "rise_time", "FIND_AT", {"variable": "v(out)", "at_val": "1e-3"})
        assert result == ".meas tran rise_time FIND v(out) AT=1e-3"

    def test_default_at_val_is_zero(self):
        result = build_directive("tran", "x", "FIND_AT", {"variable": "v(out)"})
        assert "AT=0" in result


class TestBuildDirectiveFindWhen:
    def test_basic_find_when(self):
        result = build_directive(
            "tran", "t1", "FIND_WHEN", {"variable": "v(out)", "when_var": "v(in)", "when_val": "0.5"}
        )
        assert ".meas tran t1 FIND v(out) WHEN v(in)=0.5" == result

    def test_cross_parameter_appended(self):
        result = build_directive(
            "tran",
            "t1",
            "FIND_WHEN",
            {"variable": "v(out)", "when_var": "v(in)", "when_val": "0.5", "cross": "CROSS=1"},
        )
        assert "CROSS=1" in result

    def test_empty_cross_not_appended(self):
        result = build_directive("tran", "t1", "FIND_WHEN", {"variable": "v(out)", "cross": ""})
        assert "CROSS" not in result


class TestBuildDirectiveTrigTarg:
    def test_basic_trig_targ(self):
        result = build_directive(
            "tran",
            "delay",
            "TRIG_TARG",
            {
                "trig_var": "v(in)",
                "trig_val": "0.5",
                "trig_edge": "RISE=1",
                "targ_var": "v(out)",
                "targ_val": "0.5",
                "targ_edge": "RISE=1",
            },
        )
        assert ".meas tran delay TRIG v(in) VAL=0.5 RISE=1 TARG v(out) VAL=0.5 RISE=1" == result

    def test_trig_targ_starts_with_meas(self):
        result = build_directive("ac", "bw", "TRIG_TARG", {})
        assert result.startswith(".meas ac bw TRIG")
