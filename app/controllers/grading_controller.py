"""Controller layer for grading operations.

Wraps the grading subsystem so that GUI dialogs and panels never import
directly from ``grading.*`` modules.  All grading business logic is
accessed through this controller.

No Qt dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from grading.batch_grader import BatchGradingResult
    from grading.check_analytics import CheckAnalytics
    from grading.grader import GradingResult
    from grading.rubric import Rubric
    from models.circuit import CircuitModel
    from models.grading_session import GradingSessionData


# ---------------------------------------------------------------------------
# Constants re-exported for the GUI layer
# ---------------------------------------------------------------------------

GRADES_EXTENSION = ".spice-grades"


def get_check_type_params() -> dict:
    """Return the CHECK_TYPE_PARAMS mapping for the rubric editor."""
    from grading.rubric_validator import CHECK_TYPE_PARAMS

    return CHECK_TYPE_PARAMS


# ---------------------------------------------------------------------------
# Rubric operations
# ---------------------------------------------------------------------------


def load_rubric(filepath) -> Rubric:
    """Load and validate a rubric from a .spice-rubric file."""
    from grading.rubric import load_rubric as _load_rubric

    return _load_rubric(filepath)


def save_rubric(rubric: Rubric, filepath) -> None:
    """Save a rubric to a .spice-rubric file."""
    from grading.rubric import save_rubric as _save_rubric

    _save_rubric(rubric, filepath)


def generate_rubric_from_circuit(
    circuit: CircuitModel,
    title: str = "Auto-Generated Rubric",
    total_points: int = 100,
) -> Rubric:
    """Auto-generate a rubric skeleton from a reference circuit."""
    from grading.rubric_generator import generate_rubric_from_circuit as _generate

    return _generate(circuit, title=title, total_points=total_points)


# ---------------------------------------------------------------------------
# Rubric editor helpers
# ---------------------------------------------------------------------------


def validate_rubric(title: str, checks_data: list[dict]) -> list[str]:
    """Validate a rubric definition; return error messages (empty if valid)."""
    from grading.rubric_validator import validate_rubric as _validate

    return _validate(title, checks_data)


def generate_check_id(existing_ids: set[str]) -> str:
    """Generate a unique check ID of the form ``check_N``."""
    from grading.rubric_validator import generate_check_id as _gen

    return _gen(existing_ids)


def calculate_total_points(checks_data: list[dict]) -> int:
    """Sum the points across all check data dicts."""
    from grading.rubric_validator import calculate_total_points as _calc

    return _calc(checks_data)


def build_rubric(title: str, checks_data: list[dict]) -> Rubric:
    """Construct a Rubric from a title and a list of check data dicts."""
    from grading.rubric_validator import build_rubric as _build

    return _build(title, checks_data)


# ---------------------------------------------------------------------------
# Single-circuit grading
# ---------------------------------------------------------------------------


def create_grader():
    """Create a new CircuitGrader instance."""
    from grading.grader import CircuitGrader

    return CircuitGrader()


def grade_circuit(
    student_circuit: CircuitModel,
    rubric: Rubric,
    reference_circuit: Optional[CircuitModel] = None,
    student_file: str = "",
) -> GradingResult:
    """Grade a single student circuit against a rubric."""
    grader = create_grader()
    return grader.grade(
        student_circuit=student_circuit,
        rubric=rubric,
        reference_circuit=reference_circuit,
        student_file=student_file,
    )


# ---------------------------------------------------------------------------
# Batch grading
# ---------------------------------------------------------------------------


def create_batch_grader():
    """Create a new BatchGrader instance."""
    from grading.batch_grader import BatchGrader

    return BatchGrader()


# ---------------------------------------------------------------------------
# Component mapper
# ---------------------------------------------------------------------------


def extract_component_ids(check_id: str) -> list[str]:
    """Extract component IDs embedded in a check ID string."""
    from grading.component_mapper import extract_component_ids as _extract

    return _extract(check_id)


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


def save_grading_session(filepath, session: GradingSessionData) -> None:
    """Save a grading session to a .spice-grades file."""
    from grading.session_persistence import save_grading_session as _save

    _save(filepath, session)


def load_grading_session(filepath) -> GradingSessionData:
    """Load and validate a grading session from a .spice-grades file."""
    from grading.session_persistence import load_grading_session as _load

    return _load(filepath)


def batch_result_to_session(
    batch_result: BatchGradingResult,
    rubric_path: str = "",
    student_folder: str = "",
) -> GradingSessionData:
    """Convert a BatchGradingResult into a GradingSessionData for persistence."""
    from grading.session_persistence import batch_result_to_session as _convert

    return _convert(batch_result, rubric_path=rubric_path, student_folder=student_folder)


def session_to_batch_result(session: GradingSessionData) -> BatchGradingResult:
    """Reconstruct a BatchGradingResult from a loaded session."""
    from grading.session_persistence import session_to_batch_result as _convert

    return _convert(session)


def compare_sessions(old: GradingSessionData, new: GradingSessionData) -> list[dict]:
    """Compare two grading sessions and return per-student score deltas."""
    from grading.session_persistence import compare_sessions as _compare

    return _compare(old, new)


# ---------------------------------------------------------------------------
# Analytics & export
# ---------------------------------------------------------------------------


def compute_check_analytics(result: BatchGradingResult) -> list[CheckAnalytics]:
    """Compute per-check pass/fail analytics from batch grading results."""
    from grading.check_analytics import compute_check_analytics as _compute

    return _compute(result)


def create_histogram_figure(result: BatchGradingResult, num_bins: int = 10):
    """Create a matplotlib Figure showing the score distribution histogram."""
    from grading.histogram import create_histogram_figure as _create

    return _create(result, num_bins)


def save_histogram_png(result: BatchGradingResult, filepath: str, num_bins: int = 10) -> None:
    """Save score distribution histogram as a PNG image."""
    from grading.histogram import save_histogram_png as _save

    _save(result, filepath, num_bins)


def export_gradebook_csv(result: BatchGradingResult, filepath: str) -> None:
    """Export batch grading results as a CSV gradebook."""
    from grading.grade_exporter import export_gradebook_csv as _export

    _export(result, filepath)


def export_single_result_csv(result: GradingResult, filepath: str) -> None:
    """Export a single student's grading result to a CSV file."""
    from grading.grade_exporter import export_single_result_csv as _export

    _export(result, filepath)


def export_student_reports(result: BatchGradingResult, output_dir: str) -> list[str]:
    """Export individual HTML feedback reports for all students."""
    from grading.feedback_exporter import export_student_reports as _export

    return _export(result, output_dir)
