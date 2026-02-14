"""Tests for simulation.param_directive — .param directive processing."""

import importlib
import math
import sys
from pathlib import Path

import pytest

# Import directly to bypass simulation/__init__.py (headless matplotlib issue).
_mod_path = Path(__file__).resolve().parent.parent.parent / "simulation" / "param_directive.py"
_spec = importlib.util.spec_from_file_location("simulation.param_directive", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("simulation.param_directive", _mod)
_spec.loader.exec_module(_mod)

ParamDirectiveProcessor = _mod.ParamDirectiveProcessor
format_param_value = _mod.format_param_value
parse_spice_value = _mod.parse_spice_value


# ---------------------------------------------------------------------------
# parse_spice_value
# ---------------------------------------------------------------------------


class TestParseSpiceValue:
    def test_plain_integer(self):
        assert parse_spice_value("100") == 100.0

    def test_plain_float(self):
        assert parse_spice_value("4.7") == 4.7

    def test_kilo(self):
        assert parse_spice_value("1k") == 1000.0

    def test_kilo_float(self):
        assert parse_spice_value("4.7k") == 4700.0

    def test_meg(self):
        assert parse_spice_value("2.2meg") == 2.2e6

    def test_micro(self):
        assert parse_spice_value("100u") == pytest.approx(100e-6)

    def test_nano(self):
        assert parse_spice_value("10n") == pytest.approx(10e-9)

    def test_pico(self):
        assert parse_spice_value("22p") == pytest.approx(22e-12)

    def test_milli(self):
        assert parse_spice_value("3.3m") == pytest.approx(3.3e-3)

    def test_femto(self):
        assert parse_spice_value("1f") == 1e-15

    def test_tera(self):
        assert parse_spice_value("1t") == 1e12

    def test_giga(self):
        assert parse_spice_value("2g") == 2e9

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_spice_value("")

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_spice_value("abc")

    def test_whitespace_stripped(self):
        assert parse_spice_value("  1k  ") == 1000.0


# ---------------------------------------------------------------------------
# format_param_value
# ---------------------------------------------------------------------------


class TestFormatParamValue:
    def test_zero(self):
        assert format_param_value(0) == "0"

    def test_kilo(self):
        result = format_param_value(1000)
        assert "k" in result.lower() or result == "1000"

    def test_micro(self):
        result = format_param_value(1e-6)
        assert "u" in result.lower() or "e" in result.lower()

    def test_plain_integer(self):
        result = format_param_value(42)
        assert result == "42"

    def test_small_value(self):
        result = format_param_value(1e-12)
        assert "p" in result.lower() or "e" in result.lower()


# ---------------------------------------------------------------------------
# ParamDirectiveProcessor — basic define/resolve
# ---------------------------------------------------------------------------


class TestParamProcessorBasic:
    def test_define_and_resolve_simple(self):
        proc = ParamDirectiveProcessor()
        proc.define("Rval", "1k")
        resolved = proc.resolve_all()
        assert resolved["Rval"] == pytest.approx(1000.0)

    def test_define_multiple(self):
        proc = ParamDirectiveProcessor()
        proc.define("R1", "1k")
        proc.define("R2", "10k")
        resolved = proc.resolve_all()
        assert resolved["R1"] == pytest.approx(1000.0)
        assert resolved["R2"] == pytest.approx(10000.0)

    def test_plain_float(self):
        proc = ParamDirectiveProcessor()
        proc.define("gain", "100")
        resolved = proc.resolve_all()
        assert resolved["gain"] == pytest.approx(100.0)

    def test_raw_params(self):
        proc = ParamDirectiveProcessor()
        proc.define("R1", "1k")
        assert proc.raw_params == {"R1": "1k"}


# ---------------------------------------------------------------------------
# Parametric expressions
# ---------------------------------------------------------------------------


class TestParamExpressions:
    def test_braced_expression(self):
        proc = ParamDirectiveProcessor()
        proc.define("R1", "1k")
        proc.define("R2", "10k")
        proc.define("gain", "{R2 / R1}")
        resolved = proc.resolve_all()
        assert resolved["gain"] == pytest.approx(10.0)

    def test_expression_with_math(self):
        proc = ParamDirectiveProcessor()
        proc.define("R", "1k")
        proc.define("C", "1u")
        proc.define("fc", "{1 / (2 * pi * R * C)}")
        resolved = proc.resolve_all()
        expected = 1 / (2 * math.pi * 1000 * 1e-6)
        assert resolved["fc"] == pytest.approx(expected)

    def test_dependency_order(self):
        # Define in reverse dependency order — should still resolve
        proc = ParamDirectiveProcessor()
        proc.define("result", "{a + b}")
        proc.define("b", "{a * 2}")
        proc.define("a", "5")
        resolved = proc.resolve_all()
        assert resolved["a"] == pytest.approx(5.0)
        assert resolved["b"] == pytest.approx(10.0)
        assert resolved["result"] == pytest.approx(15.0)

    def test_circular_dependency_raises(self):
        proc = ParamDirectiveProcessor()
        proc.define("x", "{y}")
        proc.define("y", "{x}")
        with pytest.raises(ValueError, match="Cannot resolve"):
            proc.resolve_all()

    def test_undefined_reference_raises(self):
        proc = ParamDirectiveProcessor()
        proc.define("x", "{missing_param}")
        with pytest.raises(ValueError, match="Cannot resolve"):
            proc.resolve_all()

    def test_sqrt_expression(self):
        proc = ParamDirectiveProcessor()
        proc.define("val", "{sqrt(144)}")
        resolved = proc.resolve_all()
        assert resolved["val"] == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# parse_directives from netlist text
# ---------------------------------------------------------------------------


class TestParseDirectives:
    def test_single_param(self):
        text = ".param Rval = 1k\n.op\n"
        proc = ParamDirectiveProcessor()
        names = proc.parse_directives(text)
        assert names == ["Rval"]
        resolved = proc.resolve_all()
        assert resolved["Rval"] == pytest.approx(1000.0)

    def test_multiple_params(self):
        text = """\
.param R1 = 1k
.param R2 = 10k
.param gain = {R2/R1}
"""
        proc = ParamDirectiveProcessor()
        names = proc.parse_directives(text)
        assert len(names) == 3
        resolved = proc.resolve_all()
        assert resolved["gain"] == pytest.approx(10.0)

    def test_case_insensitive(self):
        text = ".PARAM Rval = 1k\n"
        proc = ParamDirectiveProcessor()
        names = proc.parse_directives(text)
        assert names == ["Rval"]

    def test_ignores_non_param_lines(self):
        text = """\
My Test Circuit
.param Rval = 1k
R1 1 0 1k
.op
.end
"""
        proc = ParamDirectiveProcessor()
        names = proc.parse_directives(text)
        assert names == ["Rval"]


# ---------------------------------------------------------------------------
# substitute
# ---------------------------------------------------------------------------


class TestSubstitute:
    def test_simple_substitute(self):
        proc = ParamDirectiveProcessor()
        proc.define("Rval", "1k")
        proc.resolve_all()
        result = proc.substitute("{Rval}")
        assert float(parse_spice_value(result)) == pytest.approx(1000.0)

    def test_expression_substitute(self):
        proc = ParamDirectiveProcessor()
        proc.define("R1", "1k")
        proc.define("R2", "10k")
        proc.resolve_all()
        result = proc.substitute("{R2 / R1}")
        assert float(result) == pytest.approx(10.0)

    def test_substitute_in_context(self):
        proc = ParamDirectiveProcessor()
        proc.define("Rval", "1k")
        proc.resolve_all()
        result = proc.substitute("R1 1 0 {Rval}")
        # The numeric part should be substituted
        assert "{" not in result
        assert "Rval" not in result

    def test_no_braces_unchanged(self):
        proc = ParamDirectiveProcessor()
        proc.resolve_all()
        assert proc.substitute("R1 1 0 1k") == "R1 1 0 1k"


# ---------------------------------------------------------------------------
# is_parametric
# ---------------------------------------------------------------------------


class TestIsParametric:
    def test_braced_is_parametric(self):
        proc = ParamDirectiveProcessor()
        assert proc.is_parametric("{Rval}") is True

    def test_expression_is_parametric(self):
        proc = ParamDirectiveProcessor()
        assert proc.is_parametric("{R1 + R2}") is True

    def test_plain_value_not_parametric(self):
        proc = ParamDirectiveProcessor()
        assert proc.is_parametric("1k") is False

    def test_empty_not_parametric(self):
        proc = ParamDirectiveProcessor()
        assert proc.is_parametric("") is False


# ---------------------------------------------------------------------------
# emit_directives
# ---------------------------------------------------------------------------


class TestEmitDirectives:
    def test_emit_simple(self):
        proc = ParamDirectiveProcessor()
        proc.define("R1", "1k")
        proc.define("gain", "{R2 / R1}")
        lines = proc.emit_directives()
        assert len(lines) == 2
        assert any(".param R1 = 1k" in line for line in lines)
        assert any(".param gain = {R2 / R1}" in line for line in lines)

    def test_emit_sorted(self):
        proc = ParamDirectiveProcessor()
        proc.define("z_param", "1")
        proc.define("a_param", "2")
        lines = proc.emit_directives()
        assert lines[0].startswith(".param a_param")
        assert lines[1].startswith(".param z_param")

    def test_emit_empty(self):
        proc = ParamDirectiveProcessor()
        assert proc.emit_directives() == []
