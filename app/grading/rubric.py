"""Rubric data model for automated circuit grading.

A rubric defines a set of checks to run against a student circuit,
each worth a certain number of points. Rubrics are serialized as
.spice-rubric JSON files.

No Qt dependencies — pure Python module.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

RUBRIC_EXTENSION = ".spice-rubric"

VALID_CHECK_TYPES = frozenset(
    {
        "component_exists",
        "component_value",
        "component_count",
        "topology",
        "ground",
        "analysis_type",
    }
)


@dataclass
class RubricCheck:
    """A single check in a grading rubric.

    The optional ``partial_credit`` field holds a list of tolerance tiers
    for ``component_value`` checks.  Each tier is a pair
    ``[threshold_pct, credit_pct]``.  Tiers are evaluated in order;
    the first matching tier determines the awarded credit percentage.

    Example: ``[[10, 100], [25, 75], [50, 50]]``
    means within 10 % → full credit, within 25 % → 75 %, within 50 % → 50 %.
    """

    check_id: str
    check_type: str
    points: int
    params: dict = field(default_factory=dict)
    feedback_pass: str = ""
    feedback_fail: str = ""
    partial_credit: list | None = None

    def to_dict(self) -> dict:
        d = {
            "check_id": self.check_id,
            "check_type": self.check_type,
            "points": self.points,
            "params": dict(self.params),
            "feedback_pass": self.feedback_pass,
            "feedback_fail": self.feedback_fail,
        }
        if self.partial_credit is not None:
            d["partial_credit"] = [list(tier) for tier in self.partial_credit]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RubricCheck":
        return cls(
            check_id=data["check_id"],
            check_type=data["check_type"],
            points=data["points"],
            params=dict(data.get("params", {})),
            feedback_pass=data.get("feedback_pass", ""),
            feedback_fail=data.get("feedback_fail", ""),
            partial_credit=data.get("partial_credit"),
        )


@dataclass
class Rubric:
    """A complete grading rubric with title and checks."""

    title: str
    total_points: int
    checks: list[RubricCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "total_points": self.total_points,
            "checks": [c.to_dict() for c in self.checks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rubric":
        return cls(
            title=data["title"],
            total_points=data["total_points"],
            checks=[RubricCheck.from_dict(c) for c in data.get("checks", [])],
        )


def validate_rubric(data: dict) -> None:
    """Validate rubric JSON structure.

    Raises ValueError if the rubric is malformed.
    """
    if not isinstance(data, dict):
        raise ValueError("Rubric must be a JSON object.")

    if not data.get("title"):
        raise ValueError("Rubric must have a non-empty 'title'.")

    if "total_points" not in data or not isinstance(data["total_points"], (int, float)):
        raise ValueError("Rubric must have a numeric 'total_points'.")

    if "checks" not in data or not isinstance(data["checks"], list):
        raise ValueError("Rubric must have a 'checks' list.")

    if len(data["checks"]) == 0:
        raise ValueError("Rubric must have at least one check.")

    check_ids = set()
    points_sum = 0
    for i, check in enumerate(data["checks"]):
        if not isinstance(check, dict):
            raise ValueError(f"Check #{i + 1} must be a JSON object.")

        for required in ("check_id", "check_type", "points"):
            if required not in check:
                raise ValueError(f"Check #{i + 1} is missing required field '{required}'.")

        if check["check_type"] not in VALID_CHECK_TYPES:
            raise ValueError(
                f"Check '{check['check_id']}' has invalid type '{check['check_type']}'. "
                f"Valid types: {', '.join(sorted(VALID_CHECK_TYPES))}"
            )

        if check["check_id"] in check_ids:
            raise ValueError(f"Duplicate check_id '{check['check_id']}'.")
        check_ids.add(check["check_id"])

        points_sum += check["points"]

    if points_sum != data["total_points"]:
        raise ValueError(f"Check points sum to {points_sum}, but total_points is {data['total_points']}.")


def save_rubric(rubric: Rubric, filepath) -> None:
    """Save a rubric to a .spice-rubric JSON file."""
    filepath = Path(filepath)
    with open(filepath, "w") as f:
        json.dump(rubric.to_dict(), f, indent=2)


def load_rubric(filepath) -> Rubric:
    """Load and validate a rubric from a .spice-rubric JSON file.

    Raises:
        json.JSONDecodeError: If file is not valid JSON.
        ValueError: If rubric structure is invalid.
        OSError: If the file cannot be read.
    """
    filepath = Path(filepath)
    with open(filepath, "r") as f:
        data = json.load(f)
    validate_rubric(data)
    return Rubric.from_dict(data)
