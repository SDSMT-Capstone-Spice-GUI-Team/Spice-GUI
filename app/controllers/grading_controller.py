"""Controller for batch grading persistence and analytics.

Mediates between the GUI layer and the grading/export modules so that
dialogs do not import business logic directly.

No Qt dependencies — pure Python module.
"""

import logging
from typing import Callable, Optional

from grading.batch_grader import BatchGrader, BatchGradingResult
from grading.rubric import Rubric
from models.circuit import CircuitModel

logger = logging.getLogger(__name__)


class GradingController:
    """Orchestrates batch grading, export, and analytics operations."""

    def __init__(self):
        self._grader = BatchGrader()
        self._last_result: Optional[BatchGradingResult] = None

    @property
    def last_result(self) -> Optional[BatchGradingResult]:
        """The most recent batch grading result, or ``None``."""
        return self._last_result

    def grade_folder(
        self,
        folder_path: str,
        rubric: Rubric,
        reference_circuit: Optional[CircuitModel] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> BatchGradingResult:
        """Grade all circuit files in *folder_path* against *rubric*.

        The result is stored as :attr:`last_result` for subsequent
        export or analytics calls.

        Args:
            folder_path: Directory containing student submissions.
            rubric: Grading rubric to apply.
            reference_circuit: Optional reference solution circuit.
            progress_callback: ``(current, total, filename)`` progress hook.

        Returns:
            Aggregated :class:`BatchGradingResult`.
        """
        result = self._grader.grade_folder(
            folder_path=folder_path,
            rubric=rubric,
            reference_circuit=reference_circuit,
            progress_callback=progress_callback,
        )
        self._last_result = result
        return result

    def export_csv(self, result: BatchGradingResult, filepath: str) -> None:
        """Export *result* as a CSV gradebook.

        Raises:
            OSError: If the file cannot be written.
        """
        from grading.grade_exporter import export_gradebook_csv

        export_gradebook_csv(result, filepath)


# ---------------------------------------------------------------------------
# Module-level helpers used by grading_panel.py and similar GUI modules
# ---------------------------------------------------------------------------


def create_grader():
    """Return a new CircuitGrader instance."""
    from grading.grader import CircuitGrader

    return CircuitGrader()


def extract_component_ids(check_id: str) -> list:
    """Return component IDs referenced in a rubric check ID string.

    The check ID may encode the component ID as a suffix after the last '_'.
    Returns an empty list when no component ID can be inferred.
    """
    parts = check_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1]:
        return [parts[1]]
    return []


def export_single_result_csv(result, filepath: str) -> None:
    """Write a single student grading result to a CSV file.

    Raises:
        OSError: If the file cannot be written.
    """
    import csv

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Student File", "Rubric", "Score", "Percentage"])
        writer.writerow(
            [
                result.student_file,
                result.rubric_title,
                f"{result.earned_points}/{result.total_points}",
                f"{result.percentage:.1f}%",
            ]
        )
        writer.writerow([])
        writer.writerow(["Check ID", "Passed", "Points Earned", "Points Possible", "Feedback"])
        for cr in result.check_results:
            writer.writerow([cr.check_id, cr.passed, cr.points_earned, cr.points_possible, cr.feedback])


def export_student_reports(batch_result, output_folder: str) -> list:
    """Export individual HTML feedback reports for each student.

    Delegates to grading.feedback_exporter.
    """
    from grading.feedback_exporter import export_student_reports as _export  # delegates to grading.feedback_exporter

    return _export(batch_result, output_folder)


def load_rubric(filepath: str):
    """Load a rubric from a JSON file. Delegates to grading.rubric."""
    from grading.rubric import load_rubric as _load

    return _load(filepath)
