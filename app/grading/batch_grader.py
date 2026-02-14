"""Batch grading engine for processing folders of student submissions.

Scans a folder for circuit files, grades each against a rubric, and
produces aggregate statistics.

No Qt dependencies — pure Python module.
"""

import json
import logging
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from controllers.file_controller import validate_circuit_data
from grading.grader import CircuitGrader, GradingResult
from grading.rubric import Rubric
from models.circuit import CircuitModel

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".json", ".spice-template"}


@dataclass
class BatchGradingResult:
    """Aggregated results from grading a batch of student submissions."""

    rubric_title: str
    total_students: int
    successful: int
    failed: int
    results: list[GradingResult] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def mean_score(self) -> float:
        if not self.results:
            return 0.0
        return statistics.mean(r.percentage for r in self.results)

    @property
    def median_score(self) -> float:
        if not self.results:
            return 0.0
        return statistics.median(r.percentage for r in self.results)

    @property
    def min_score(self) -> float:
        if not self.results:
            return 0.0
        return min(r.percentage for r in self.results)

    @property
    def max_score(self) -> float:
        if not self.results:
            return 0.0
        return max(r.percentage for r in self.results)


class BatchGrader:
    """Grades a folder of student submissions against a rubric."""

    def __init__(self):
        self._grader = CircuitGrader()

    def grade_folder(
        self,
        folder_path: str,
        rubric: Rubric,
        reference_circuit: Optional[CircuitModel] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> BatchGradingResult:
        """Grade all circuit files in a folder.

        Args:
            folder_path: Path to folder containing student .json/.spice-template files.
            rubric: The grading rubric to apply.
            reference_circuit: Optional reference solution circuit.
            progress_callback: Called with (current, total, filename) for progress updates.

        Returns:
            BatchGradingResult with per-student results and aggregate stats.
        """
        folder = Path(folder_path)
        files = sorted(
            f
            for f in folder.iterdir()
            if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS
        )

        result = BatchGradingResult(
            rubric_title=rubric.title,
            total_students=len(files),
            successful=0,
            failed=0,
        )

        for i, filepath in enumerate(files):
            filename = filepath.name
            if progress_callback:
                progress_callback(i, len(files), filename)

            try:
                circuit = self._load_circuit(filepath)
                grade_result = self._grader.grade(
                    student_circuit=circuit,
                    rubric=rubric,
                    reference_circuit=reference_circuit,
                    student_file=filename,
                )
                result.results.append(grade_result)
                result.successful += 1
            except Exception as e:
                logger.warning("Failed to grade %s: %s", filename, e)
                result.errors.append((filename, str(e)))
                result.failed += 1

        if progress_callback:
            progress_callback(len(files), len(files), "Done")

        return result

    @staticmethod
    def _load_circuit(filepath: Path) -> CircuitModel:
        """Load a circuit from a .json or .spice-template file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        # Handle template files (extract starter_circuit)
        if "template_version" in data and "starter_circuit" in data:
            if data["starter_circuit"] is not None:
                validate_circuit_data(data["starter_circuit"])
                return CircuitModel.from_dict(data["starter_circuit"])
            else:
                return CircuitModel()

        validate_circuit_data(data)
        return CircuitModel.from_dict(data)
