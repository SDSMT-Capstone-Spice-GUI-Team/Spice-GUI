"""Rubric validation and construction utilities.

Pure-Python business logic extracted from the rubric editor dialog.
No Qt dependencies.
"""

from grading.rubric import Rubric, RubricCheck

# Parameter definitions per check type: list of (param_key, label, widget_hint, default)
# widget_hint is "str", "int", "float", or "bool" — used by the UI to create widgets.
CHECK_TYPE_PARAMS: dict[str, list[tuple[str, str, str, object]]] = {
    "component_exists": [
        ("component_id", "Component ID", "str", ""),
        ("component_type", "Component Type", "str", ""),
        ("min_count", "Min Count", "int", 1),
    ],
    "component_value": [
        ("component_id", "Component ID", "str", ""),
        ("expected_value", "Expected Value", "str", ""),
        ("tolerance_pct", "Tolerance (%)", "float", 0.0),
    ],
    "component_count": [
        ("component_type", "Component Type", "str", ""),
        ("expected_count", "Expected Count", "int", 0),
    ],
    "topology": [
        ("component_a", "Component A", "str", ""),
        ("component_b", "Component B", "str", ""),
        ("shared_node", "Shared Node (connected)", "bool", True),
    ],
    "ground": [
        ("component_id", "Component ID (optional)", "str", ""),
    ],
    "analysis_type": [
        ("expected_type", "Expected Analysis Type", "str", ""),
    ],
}


def get_required_params(check_type: str) -> list[str]:
    """Return required parameter keys for a check type."""
    reqs: dict[str, list[str]] = {
        "component_exists": [],
        "component_value": ["component_id", "expected_value"],
        "component_count": ["component_type", "expected_count"],
        "topology": ["component_a", "component_b"],
        "ground": [],
        "analysis_type": ["expected_type"],
    }
    return reqs.get(check_type, [])


def validate_rubric(title: str, checks_data: list[dict]) -> list[str]:
    """Validate a rubric definition and return a list of error messages.

    Args:
        title: The rubric title string.
        checks_data: List of check data dicts, each containing at least
            ``check_id``, ``check_type``, ``points``, and ``params``.

    Returns:
        A list of human-readable error strings (empty if valid).
    """
    errors: list[str] = []

    if not title.strip():
        errors.append("Rubric title is required.")

    if not checks_data:
        errors.append("At least one check is required.")

    check_ids: set[str] = set()
    for i, data in enumerate(checks_data):
        cid = data.get("check_id", "")
        if not cid:
            errors.append(f"Check #{i + 1} has no ID.")
        elif cid in check_ids:
            errors.append(f"Duplicate check ID: '{cid}'.")
        check_ids.add(cid)

        ctype = data.get("check_type", "")
        required = get_required_params(ctype)
        params = data.get("params", {})
        for rp in required:
            if not params.get(rp):
                errors.append(f"Check '{cid}': missing required parameter '{rp}'.")

    return errors


def generate_check_id(existing_ids: set[str]) -> str:
    """Generate a unique check ID of the form ``check_N``."""
    n = 1
    while f"check_{n}" in existing_ids:
        n += 1
    return f"check_{n}"


def calculate_total_points(checks_data: list[dict]) -> int:
    """Sum the points across all check data dicts."""
    return sum(d.get("points", 0) for d in checks_data)


def build_rubric(title: str, checks_data: list[dict]) -> Rubric:
    """Construct a :class:`Rubric` from a title and a list of check data dicts.

    Each dict must be compatible with :meth:`RubricCheck.from_dict`.
    """
    checks = [RubricCheck.from_dict(d) for d in checks_data]
    total = sum(d.get("points", 0) for d in checks_data)
    return Rubric(title=title.strip(), total_points=total, checks=checks)
