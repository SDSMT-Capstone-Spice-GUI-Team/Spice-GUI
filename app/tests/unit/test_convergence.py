"""Tests for simulation.convergence error classification and retry helpers."""

import pytest
from simulation.convergence import (RELAXED_OPTIONS, ErrorCategory,
                                    ErrorDiagnosis, classify_error,
                                    diagnose_error, format_options_lines,
                                    format_user_message, is_retriable)


class TestClassifyError:
    """Test error classification from ngspice output."""

    def test_dc_convergence_from_stderr(self):
        stderr = "Error: no convergence in DC operating point"
        assert classify_error(stderr) == ErrorCategory.DC_CONVERGENCE

    def test_timestep_too_small(self):
        stderr = "doAnalyses: TRAN:  Timestep too small; timestep = 1e-20"
        assert classify_error(stderr) == ErrorCategory.TIMESTEP_TOO_SMALL

    def test_singular_matrix(self):
        stderr = "Error: singular matrix"
        assert classify_error(stderr) == ErrorCategory.SINGULAR_MATRIX

    def test_source_stepping_failed(self):
        stderr = "Warning: source stepping failed"
        assert classify_error(stderr) == ErrorCategory.SOURCE_STEPPING_FAILED

    def test_unknown_error(self):
        stderr = "some random error message"
        assert classify_error(stderr) == ErrorCategory.UNKNOWN

    def test_empty_stderr(self):
        assert classify_error("") == ErrorCategory.UNKNOWN

    def test_fallback_to_stdout(self):
        stderr = ""
        stdout = "Error: no convergence in DC operating point"
        assert classify_error(stderr, stdout) == ErrorCategory.DC_CONVERGENCE

    def test_case_insensitive(self):
        stderr = "ERROR: SINGULAR MATRIX"
        assert classify_error(stderr) == ErrorCategory.SINGULAR_MATRIX

    def test_singular_matrix_takes_priority_over_convergence(self):
        # Singular matrix appears before generic "no convergence" in pattern list
        stderr = "singular matrix\nno convergence"
        assert classify_error(stderr) == ErrorCategory.SINGULAR_MATRIX

    def test_generic_no_convergence(self):
        stderr = "Error(TRAN): no convergence in transient analysis"
        assert classify_error(stderr) == ErrorCategory.DC_CONVERGENCE


class TestDiagnoseError:
    """Test full diagnosis generation."""

    def test_returns_diagnosis_for_dc_convergence(self):
        diag = diagnose_error("no convergence in DC operating point")
        assert isinstance(diag, ErrorDiagnosis)
        assert diag.category == ErrorCategory.DC_CONVERGENCE
        assert "stable DC operating point" in diag.message
        assert len(diag.causes) > 0
        assert len(diag.suggestions) > 0

    def test_returns_diagnosis_for_unknown(self):
        diag = diagnose_error("something weird happened")
        assert diag.category == ErrorCategory.UNKNOWN
        assert "unexpected reason" in diag.message


class TestIsRetriable:
    """Test retriable classification."""

    def test_dc_convergence_is_retriable(self):
        assert is_retriable(ErrorCategory.DC_CONVERGENCE) is True

    def test_timestep_is_retriable(self):
        assert is_retriable(ErrorCategory.TIMESTEP_TOO_SMALL) is True

    def test_source_stepping_is_retriable(self):
        assert is_retriable(ErrorCategory.SOURCE_STEPPING_FAILED) is True

    def test_singular_matrix_is_not_retriable(self):
        assert is_retriable(ErrorCategory.SINGULAR_MATRIX) is False

    def test_unknown_is_not_retriable(self):
        assert is_retriable(ErrorCategory.UNKNOWN) is False


class TestFormatOptionsLines:
    """Test SPICE options line formatting."""

    def test_default_relaxed_options(self):
        lines = format_options_lines()
        assert len(lines) == 1
        assert lines[0].startswith(".options ")
        assert "reltol=0.01" in lines[0]
        assert "itl1=500" in lines[0]

    def test_custom_options(self):
        lines = format_options_lines({"reltol": "0.05"})
        assert lines == [".options reltol=0.05"]

    def test_empty_options(self):
        lines = format_options_lines({})
        assert lines == []


class TestFormatUserMessage:
    """Test student-friendly message formatting."""

    def test_includes_message_and_causes(self):
        diag = diagnose_error("singular matrix")
        msg = format_user_message(diag)
        assert "singular" in msg.lower()
        assert "Common causes:" in msg
        assert "Suggestions:" in msg

    def test_relaxed_prefix(self):
        diag = diagnose_error("no convergence in DC operating point")
        msg = format_user_message(diag, relaxed=True)
        assert msg.startswith("Simulation converged with relaxed tolerances")

    def test_no_relaxed_prefix_by_default(self):
        diag = diagnose_error("no convergence in DC operating point")
        msg = format_user_message(diag, relaxed=False)
        assert "relaxed tolerances" not in msg
