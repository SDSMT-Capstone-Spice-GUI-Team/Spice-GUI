"""Persistence utilities for grading sessions.

Provides save/load for .spice-grades JSON files and conversion helpers
between GradingResult / BatchGradingResult and GradingSessionData.

No Qt dependencies -- pure Python module.
"""

import json
import logging
import os
import tempfile
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
    rubric_hash: str = "",
) -> GradingSessionData:
    """Convert a BatchGradingResult into a GradingSessionData for persistence."""
    return GradingSessionData(
        session_version="1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        rubric_title=batch_result.rubric_title,
        rubric_hash=rubric_hash,
        rubric_path=rubric_path,
        student_folder=student_folder,
        results=[grading_result_to_dict(r) for r in batch_result.results],
        errors=list(batch_result.errors),
    )


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def _to_relative(path_str: str, anchor: Path) -> str:
    """Convert an absolute path to a relative path based on *anchor* directory.

    Returns the original string unchanged when it is empty or already relative.
    """
    if not path_str:
        return path_str
    p = Path(path_str)
    if not p.is_absolute():
        return path_str
    try:
        return str(p.relative_to(anchor))
    except ValueError:
        # On different drive / no common prefix — use os.path.relpath
        return os.path.relpath(path_str, anchor)


def _to_absolute(path_str: str, anchor: Path) -> str:
    """Resolve a (possibly relative) path against *anchor* directory.

    Returns the original string unchanged when it is empty.
    """
    if not path_str:
        return path_str
    p = Path(path_str)
    if p.is_absolute():
        return path_str
    return str((anchor / p).resolve())


def save_grading_session(filepath, session: GradingSessionData) -> None:
    """Save a grading session to a .spice-grades JSON file.

    Paths are stored relative to the session file's directory so the
    file remains portable across machines.

    Raises:
        OSError: If the file cannot be written.
    """
    filepath = Path(filepath)
    anchor = filepath.parent.resolve()

    data = session.to_dict()
    data["rubric_path"] = _to_relative(data.get("rubric_path", ""), anchor)
    data["student_folder"] = _to_relative(data.get("student_folder", ""), anchor)

    fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, filepath)
    except BaseException:
        os.unlink(tmp)
        raise


def load_grading_session(filepath) -> GradingSessionData:
    """Load and validate a grading session from a .spice-grades JSON file.

    Relative paths stored in the file are resolved against the session
    file's directory.

    Raises:
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the session structure is invalid.
        OSError: If the file cannot be read.
    """
    filepath = Path(filepath)
    anchor = filepath.parent.resolve()

    from controllers.file_controller import check_file_size

    check_file_size(filepath)
    with open(filepath, "r") as f:
        data = json.load(f)
    validate_session_data(data)

    data["rubric_path"] = _to_absolute(data.get("rubric_path", ""), anchor)
    data["student_folder"] = _to_absolute(data.get("student_folder", ""), anchor)

    return GradingSessionData.from_dict(data)


# ---------------------------------------------------------------------------
# Session comparison
# ---------------------------------------------------------------------------


def compare_sessions(old: GradingSessionData, new: GradingSessionData) -> dict:
    """Compare two grading sessions and return per-student score deltas.

    Returns a dict with:
    - ``rubric_changed``: ``True`` if the rubric content hashes differ
      (or if either session has no hash recorded), ``None`` if neither
      session has a hash.
    - ``students``: a list of dicts, one per student in *either* session:
      ``{student_file, old_score, new_score, old_pct, new_pct, delta}``

    Students present in only one session have ``None`` for the missing scores.
    """
    old_map: dict[str, dict] = {r["student_file"]: r for r in old.results}
    new_map: dict[str, dict] = {r["student_file"]: r for r in new.results}

    all_students = sorted(set(old_map) | set(new_map))

    students: list[dict] = []
    for student in all_students:
        old_r = old_map.get(student)
        new_r = new_map.get(student)

        old_pct = _pct(old_r) if old_r else None
        new_pct = _pct(new_r) if new_r else None

        if old_pct is not None and new_pct is not None:
            delta = new_pct - old_pct
        else:
            delta = None

        students.append(
            {
                "student_file": student,
                "old_score": (f"{old_r['earned_points']}/{old_r['total_points']}" if old_r else None),
                "new_score": (f"{new_r['earned_points']}/{new_r['total_points']}" if new_r else None),
                "old_pct": old_pct,
                "new_pct": new_pct,
                "delta": delta,
            }
        )

    # Determine whether the rubric changed between sessions.
    if old.rubric_hash and new.rubric_hash:
        rubric_changed = old.rubric_hash != new.rubric_hash
    elif old.rubric_hash or new.rubric_hash:
        # One session has a hash but the other doesn't — can't confirm match.
        rubric_changed = True
    else:
        rubric_changed = None

    return {
        "rubric_changed": rubric_changed,
        "students": students,
    }


def _pct(result_dict: dict) -> float:
    """Compute percentage from a serialized result dict."""
    total = result_dict.get("total_points", 0)
    if total == 0:
        return 100.0
    return (result_dict["earned_points"] / total) * 100.0
