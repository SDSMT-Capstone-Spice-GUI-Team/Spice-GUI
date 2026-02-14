"""Tests for simulation.waveform_math — expression evaluation over sim vectors."""

import importlib
import math
import sys
from pathlib import Path

import pytest

# Import directly to bypass simulation/__init__.py (headless matplotlib issue).
_mod_path = Path(__file__).resolve().parent.parent.parent / "simulation" / "waveform_math.py"
_spec = importlib.util.spec_from_file_location("simulation.waveform_math", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("simulation.waveform_math", _mod)
_spec.loader.exec_module(_mod)

evaluate_expression = _mod.evaluate_expression
evaluate_expression_over_vectors = _mod.evaluate_expression_over_vectors
extract_variable_refs = _mod.extract_variable_refs
validate_expression = _mod.validate_expression


# ---------------------------------------------------------------------------
# extract_variable_refs
# ---------------------------------------------------------------------------


class TestExtractVariableRefs:
    def test_simple_voltage(self):
        assert extract_variable_refs("v(out)") == ["v(out)"]

    def test_multiple_refs(self):
        refs = extract_variable_refs("v(out) - v(in)")
        assert refs == ["v(out)", "v(in)"]

    def test_current_ref(self):
        refs = extract_variable_refs("i(R1)")
        assert refs == ["i(R1)"]

    def test_mixed(self):
        refs = extract_variable_refs("v(out) * i(R1)")
        assert "v(out)" in refs
        assert "i(R1)" in refs

    def test_no_refs(self):
        assert extract_variable_refs("1 + 2") == []

    def test_nested_expression(self):
        refs = extract_variable_refs("abs(v(out))")
        assert refs == ["v(out)"]


# ---------------------------------------------------------------------------
# evaluate_expression — scalar
# ---------------------------------------------------------------------------


class TestEvaluateExpression:
    def test_simple_subtraction(self):
        result = evaluate_expression("v(out) - v(in)", {"v(out)": 5.0, "v(in)": 2.0})
        assert result == pytest.approx(3.0)

    def test_multiplication(self):
        result = evaluate_expression("v(out) * i(R1)", {"v(out)": 5.0, "i(R1)": 0.01})
        assert result == pytest.approx(0.05)

    def test_abs_function(self):
        result = evaluate_expression("abs(v(out))", {"v(out)": -3.5})
        assert result == pytest.approx(3.5)

    def test_log10(self):
        result = evaluate_expression("log10(v(out))", {"v(out)": 1000.0})
        assert result == pytest.approx(3.0)

    def test_db_conversion(self):
        result = evaluate_expression("20 * log10(abs(v(out)))", {"v(out)": 10.0})
        assert result == pytest.approx(20.0)

    def test_sqrt(self):
        result = evaluate_expression("sqrt(v(out))", {"v(out)": 9.0})
        assert result == pytest.approx(3.0)

    def test_trig_sin(self):
        result = evaluate_expression("sin(v(phase))", {"v(phase)": math.pi / 2})
        assert result == pytest.approx(1.0)

    def test_constant_pi(self):
        result = evaluate_expression("pi", {})
        assert result == pytest.approx(math.pi)

    def test_constant_e(self):
        result = evaluate_expression("e", {})
        assert result == pytest.approx(math.e)

    def test_parenthesized(self):
        result = evaluate_expression("(v(a) + v(b)) / 2", {"v(a)": 10.0, "v(b)": 6.0})
        assert result == pytest.approx(8.0)

    def test_power(self):
        result = evaluate_expression("v(x) ** 2", {"v(x)": 3.0})
        assert result == pytest.approx(9.0)

    def test_unary_neg(self):
        result = evaluate_expression("-v(out)", {"v(out)": 5.0})
        assert result == pytest.approx(-5.0)

    def test_complex_expression(self):
        # (v(out) - v(in)) / v(in) * 100  — percentage gain
        result = evaluate_expression(
            "(v(out) - v(in)) / v(in) * 100",
            {"v(out)": 11.0, "v(in)": 10.0},
        )
        assert result == pytest.approx(10.0)

    def test_unknown_variable_raises(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            evaluate_expression("v(missing)", {})

    def test_syntax_error_raises(self):
        with pytest.raises(ValueError, match="Invalid expression syntax"):
            evaluate_expression("v(out) +", {"v(out)": 1.0})

    def test_bare_number(self):
        result = evaluate_expression("42", {})
        assert result == pytest.approx(42.0)

    def test_nested_function_calls(self):
        result = evaluate_expression("abs(sqrt(v(x)))", {"v(x)": 16.0})
        assert result == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# evaluate_expression_over_vectors
# ---------------------------------------------------------------------------


class TestEvaluateOverVectors:
    def test_basic_vector_subtraction(self):
        data = {
            "v(out)": [5.0, 6.0, 7.0],
            "v(in)": [2.0, 2.0, 2.0],
        }
        result = evaluate_expression_over_vectors("v(out) - v(in)", data)
        assert result == pytest.approx([3.0, 4.0, 5.0])

    def test_power_calculation(self):
        data = {
            "v(out)": [10.0, 20.0],
            "i(R1)": [0.1, 0.2],
        }
        result = evaluate_expression_over_vectors("v(out) * i(R1)", data)
        assert result == pytest.approx([1.0, 4.0])

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="No vector data"):
            evaluate_expression_over_vectors("v(out)", {})

    def test_mismatched_lengths_raises(self):
        data = {
            "v(out)": [1.0, 2.0, 3.0],
            "v(in)": [1.0, 2.0],
        }
        with pytest.raises(ValueError, match="length mismatch"):
            evaluate_expression_over_vectors("v(out) - v(in)", data)

    def test_single_point(self):
        data = {"v(x)": [42.0]}
        result = evaluate_expression_over_vectors("v(x) * 2", data)
        assert result == pytest.approx([84.0])

    def test_db_conversion_vector(self):
        data = {"v(out)": [1.0, 10.0, 100.0]}
        result = evaluate_expression_over_vectors("20 * log10(v(out))", data)
        assert result == pytest.approx([0.0, 20.0, 40.0])


# ---------------------------------------------------------------------------
# validate_expression
# ---------------------------------------------------------------------------


class TestValidateExpression:
    def test_valid_simple(self):
        errors = validate_expression("v(out) - v(in)", available_vars=["v(out)", "v(in)"])
        assert errors == []

    def test_empty_expression(self):
        errors = validate_expression("")
        assert len(errors) == 1
        assert "empty" in errors[0].lower()

    def test_whitespace_only(self):
        errors = validate_expression("   ")
        assert len(errors) == 1

    def test_unknown_variable(self):
        errors = validate_expression("v(missing)", available_vars=["v(out)"])
        assert any("Unknown variable" in e for e in errors)

    def test_syntax_error(self):
        errors = validate_expression("v(out) +")
        assert any("Syntax error" in e or "syntax" in e.lower() for e in errors)

    def test_valid_without_available_vars(self):
        # When available_vars is None, variable checking is skipped
        errors = validate_expression("v(anything)")
        assert errors == []

    def test_multiple_errors(self):
        errors = validate_expression("v(a) + v(b)", available_vars=["v(c)"])
        assert len(errors) == 2  # both v(a) and v(b) unknown

    def test_pure_math(self):
        errors = validate_expression("1 + 2 * 3")
        assert errors == []

    def test_function_call_valid(self):
        errors = validate_expression("abs(v(out))", available_vars=["v(out)"])
        assert errors == []
