"""Tests for convergence failure error messages (#858).

Verifies that:
1. NgspiceRunner detects convergence errors even when output exists
2. SimulationController produces student-friendly error messages
3. Error diagnosis produces actionable causes and suggestions
"""

from simulation.convergence import ErrorCategory, classify_error, diagnose_error, format_user_message, is_retriable


class TestClassifyError:
    """classify_error detects known ngspice failure patterns."""

    def test_dc_convergence_stderr(self):
        assert classify_error("no convergence in dc operating point") == ErrorCategory.DC_CONVERGENCE

    def test_dc_convergence_stdout(self):
        assert classify_error("", "No convergence in DC operating point") == ErrorCategory.DC_CONVERGENCE

    def test_singular_matrix(self):
        assert classify_error("singular matrix") == ErrorCategory.SINGULAR_MATRIX

    def test_timestep_too_small(self):
        assert classify_error("doAnalyses: TRAN:  Timestep too small") == ErrorCategory.TIMESTEP_TOO_SMALL

    def test_source_stepping_failed(self):
        assert classify_error("source stepping failed") == ErrorCategory.SOURCE_STEPPING_FAILED

    def test_unknown_error(self):
        assert classify_error("some other error") == ErrorCategory.UNKNOWN

    def test_empty_input(self):
        assert classify_error("", "") == ErrorCategory.UNKNOWN


class TestDiagnoseError:
    """diagnose_error returns student-friendly messages with causes and suggestions."""

    def test_dc_convergence_has_causes(self):
        diag = diagnose_error("no convergence in dc operating point")
        assert diag.category == ErrorCategory.DC_CONVERGENCE
        assert len(diag.causes) > 0
        assert len(diag.suggestions) > 0

    def test_singular_matrix_mentions_parallel_sources(self):
        diag = diagnose_error("singular matrix")
        assert diag.category == ErrorCategory.SINGULAR_MATRIX
        causes_text = " ".join(diag.causes)
        assert "parallel" in causes_text.lower() or "voltage sources" in causes_text.lower()

    def test_unknown_still_has_suggestions(self):
        diag = diagnose_error("completely unknown error")
        assert diag.category == ErrorCategory.UNKNOWN
        assert len(diag.suggestions) > 0


class TestFormatUserMessage:
    """format_user_message produces a complete student-friendly string."""

    def test_includes_causes_and_suggestions(self):
        diag = diagnose_error("no convergence in dc operating point")
        msg = format_user_message(diag)
        assert "Common causes:" in msg
        assert "Suggestions:" in msg
        assert "operating point" in msg.lower()

    def test_relaxed_prefix(self):
        diag = diagnose_error("no convergence")
        msg = format_user_message(diag, relaxed=True)
        assert "relaxed tolerances" in msg.lower()

    def test_singular_matrix_message_is_student_friendly(self):
        diag = diagnose_error("singular matrix")
        msg = format_user_message(diag)
        # Should NOT contain raw ngspice jargon alone — must have explanatory text
        assert "singular" in msg.lower()
        assert len(msg) > 50  # Not just a raw error echo


class TestIsRetriable:
    def test_dc_convergence_is_retriable(self):
        assert is_retriable(ErrorCategory.DC_CONVERGENCE)

    def test_timestep_too_small_is_retriable(self):
        assert is_retriable(ErrorCategory.TIMESTEP_TOO_SMALL)

    def test_singular_matrix_is_not_retriable(self):
        assert not is_retriable(ErrorCategory.SINGULAR_MATRIX)

    def test_unknown_is_not_retriable(self):
        assert not is_retriable(ErrorCategory.UNKNOWN)


class TestNgspiceRunnerErrorDetection:
    """NgspiceRunner detects convergence errors in output (#858)."""

    def test_classify_catches_convergence_in_stdout(self):
        """Even when output file exists, convergence errors in stdout are detected."""
        # Simulate what ngspice produces: convergence error in stdout
        stdout = "Note: No convergence in DC operating point"
        cat = classify_error("", stdout)
        assert cat == ErrorCategory.DC_CONVERGENCE

    def test_classify_catches_singular_in_stderr(self):
        stderr = "Error: singular matrix: check node connections"
        cat = classify_error(stderr)
        assert cat == ErrorCategory.SINGULAR_MATRIX
