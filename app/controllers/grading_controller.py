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
