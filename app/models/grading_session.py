"""Data model for grading session persistence.

Stores grading results, rubric metadata, and timestamps so instructors
can save, resume, and compare grading sessions.

No Qt dependencies -- pure Python module.
"""

from dataclasses import dataclass, field


@dataclass
class GradingSessionData:
    """Serializable snapshot of a grading session.

    Attributes:
        session_version: Schema version for forward compatibility.
        timestamp: ISO-8601 timestamp when session was created/saved.
        rubric_title: Title of the rubric used.
        rubric_path: Optional filesystem path to the rubric file.
        student_folder: Optional filesystem path to the student submissions folder.
        results: List of serialized GradingResult dicts.
        errors: List of (filename, error_message) pairs for failed submissions.
    """

    session_version: str = "1.0"
    timestamp: str = ""
    rubric_title: str = ""
    rubric_path: str = ""
    student_folder: str = ""
    results: list[dict] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON encoding."""
        return {
            "session_version": self.session_version,
            "timestamp": self.timestamp,
            "rubric_title": self.rubric_title,
            "rubric_path": self.rubric_path,
            "student_folder": self.student_folder,
            "results": list(self.results),
            "errors": [list(e) for e in self.errors],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GradingSessionData":
        """Deserialize from a plain dict (e.g. loaded from JSON)."""
        return cls(
            session_version=data.get("session_version", "1.0"),
            timestamp=data.get("timestamp", ""),
            rubric_title=data.get("rubric_title", ""),
            rubric_path=data.get("rubric_path", ""),
            student_folder=data.get("student_folder", ""),
            results=list(data.get("results", [])),
            errors=[tuple(e) for e in data.get("errors", [])],
        )
