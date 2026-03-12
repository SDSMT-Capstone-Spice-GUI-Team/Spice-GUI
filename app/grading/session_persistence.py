"""Persistence utilities for grading sessions.

Provides save/load for .spice-grades JSON files and conversion helpers
between GradingResult / BatchGradingResult and GradingSessionData.

No Qt dependencies -- pure Python module.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from grading.batch_grader import BatchGradingResult
from grading.grader import CheckGradeResult, GradingResult
from models.grading_session import GradingSessionData

logger = logging.getLogger(__name__)

GRADES_EXTENSION = ".spice-grades"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_session_data(data: dict) -> None:
    """Validate a grading session dict structure.

    Raises ``ValueError`` with a descriptive message when invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Session data must be a JSON object.")

    if "session_version" not in data or not isinstance(data["session_version"], str):
        raise ValueError("Session data must have a string 'session_version'.")

    if "rubric_title" not in data or not isinstance(data["rubric_title"], str):
        raise ValueError("Session data must have a string 'rubric_title'.")

    if "results" not in data or not isinstance(data["results"], list):
        raise ValueError("Session data must have a 'results' list.")

    for i, result in enumerate(data["results"]):
        if not isinstance(result, dict):
            raise ValueError(f"Result #{i + 1} must be a JSON object.")
        for field in ("student_file", "rubric_title", "total_points", "earned_points"):
            if field not in result:
                raise ValueError(f"Result #{i + 1} is missing required field '{field}'.")

    if "errors" in data and not isinstance(data["errors"], list):
        raise ValueError("'errors' must be a list if present.")


# ---------------------------------------------------------------------------
# Single-result conversion helpers
# ---------------------------------------------------------------------------


def grading_result_to_dict(result: GradingResult) -> dict:
    """Convert a GradingResult to a plain dict for JSON serialization."""
    return {
        "student_file": result.student_file,
        "rubric_title": result.rubric_title,
        "total_points": result.total_points,
        "earned_points": result.earned_points,
        "check_results": [
            {
                "check_id": cr.check_id,
                "passed": cr.passed,
                "points_earned": cr.points_earned,
                "points_possible": cr.points_possible,
                "feedback": cr.feedback,
            }
            for cr in result.check_results
        ],
    }


def dict_to_grading_result(data: dict) -> GradingResult:
    """Reconstruct a GradingResult from a plain dict."""
    check_results = [
        CheckGradeResult(
            check_id=cr["check_id"],
            passed=cr["passed"],
            points_earned=cr["points_earned"],
            points_possible=cr["points_possible"],
            feedback=cr.get("feedback", ""),
        )
        for cr in data.get("check_results", [])
    ]
    return GradingResult(
        student_file=data["student_file"],
        rubric_title=data["rubric_title"],
        total_points=data["total_points"],
        earned_points=data["earned_points"],
        check_results=check_results,
    )


# ---------------------------------------------------------------------------
# Batch <-> Session conversion
# ---------------------------------------------------------------------------


def session_to_batch_result(session: GradingSessionData) -> BatchGradingResult:
    """Reconstruct a :class:`BatchGradingResult` from a loaded session.

    This is the inverse of :func:`batch_result_to_session`.
    """
    results = [dict_to_grading_result(r) for r in session.results]
    return BatchGradingResult(
        rubric_title=session.rubric_title,
        total_students=len(session.results) + len(session.errors),
        successful=len(session.results),
        failed=len(session.errors),
        results=results,
        errors=list(session.errors),
    )


def batch_result_to_session(
    batch_result: BatchGradingResult,
    rubric_path: str = "",
    student_folder: str = "",
) -> GradingSessionData:
    """Convert a BatchGradingResult into a GradingSessionData for persistence."""
    return GradingSessionData(
        session_version="1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        rubric_title=batch_result.rubric_title,
        rubric_path=rubric_path,
        student_folder=student_folder,
        results=[grading_result_to_dict(r) for r in batch_result.results],
        errors=list(batch_result.errors),
    )


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


# AUDIT(quality): no atomic write (write-to-temp-then-rename); a crash mid-write could corrupt the session file
def save_grading_session(filepath, session: GradingSessionData) -> None:
    """Save a grading session to a .spice-grades JSON file.

    Raises:
        OSError: If the file cannot be written.
    """
    filepath = Path(filepath)
    with open(filepath, "w") as f:
        json.dump(session.to_dict(), f, indent=2)


def load_grading_session(filepath) -> GradingSessionData:
    """Load and validate a grading session from a .spice-grades JSON file.

    Raises:
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the session structure is invalid.
        OSError: If the file cannot be read.
    """
    filepath = Path(filepath)
    with open(filepath, "r") as f:
        data = json.load(f)
    validate_session_data(data)
    return GradingSessionData.from_dict(data)


# ---------------------------------------------------------------------------
# Session comparison
# ---------------------------------------------------------------------------


def compare_sessions(old: GradingSessionData, new: GradingSessionData) -> list[dict]:
    """Compare two grading sessions and return per-student score deltas.

    Returns a list of dicts, one per student that appears in *either* session:
    ``{student_file, old_score, new_score, old_pct, new_pct, delta}``

    Students present in only one session have ``None`` for the missing scores.
    """
    old_map: dict[str, dict] = {r["student_file"]: r for r in old.results}
    new_map: dict[str, dict] = {r["student_file"]: r for r in new.results}

    all_students = sorted(set(old_map) | set(new_map))

    comparisons: list[dict] = []
    for student in all_students:
        old_r = old_map.get(student)
        new_r = new_map.get(student)

        old_pct = _pct(old_r) if old_r else None
        new_pct = _pct(new_r) if new_r else None

        if old_pct is not None and new_pct is not None:
            delta = new_pct - old_pct
        else:
            delta = None

        comparisons.append(
            {
                "student_file": student,
                "old_score": (f"{old_r['earned_points']}/{old_r['total_points']}" if old_r else None),
                "new_score": (f"{new_r['earned_points']}/{new_r['total_points']}" if new_r else None),
                "old_pct": old_pct,
                "new_pct": new_pct,
                "delta": delta,
            }
        )

    return comparisons


def _pct(result_dict: dict) -> float:
    """Compute percentage from a serialized result dict."""
    total = result_dict.get("total_points", 0)
    if total == 0:
        return 100.0
    return (result_dict["earned_points"] / total) * 100.0
