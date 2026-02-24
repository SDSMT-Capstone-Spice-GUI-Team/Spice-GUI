"""Controller for .spice-assignment bundle files.

Handles save/load of assignment bundles that combine a template and rubric.
No Qt dependencies.
"""

import json
from pathlib import Path

from grading.rubric import Rubric, validate_rubric
from models.assignment import AssignmentBundle
from models.template import TemplateData


def validate_assignment_data(data: dict) -> None:
    """Validate assignment bundle JSON structure.

    Raises:
        ValueError: If the data is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Assignment must be a JSON object")
    if "template" not in data and "rubric" not in data:
        raise ValueError("Assignment must contain at least a 'template' or 'rubric'")
    if "rubric" in data and data["rubric"] is not None:
        validate_rubric(data["rubric"])


def save_assignment(bundle: AssignmentBundle, filepath) -> None:
    """Save an assignment bundle to a .spice-assignment file.

    Args:
        bundle: The assignment bundle to save.
        filepath: Path to write the file.
    """
    filepath = Path(filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(bundle.to_dict(), f, indent=2)


def load_assignment(filepath) -> AssignmentBundle:
    """Load an assignment bundle from a .spice-assignment file.

    Args:
        filepath: Path to the assignment file.

    Returns:
        An AssignmentBundle with template and/or rubric data.

    Raises:
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the data structure is invalid.
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate_assignment_data(data)
    return AssignmentBundle.from_dict(data)


def extract_template(bundle: AssignmentBundle) -> TemplateData:
    """Extract the template from an assignment bundle.

    Returns:
        The template data, or an empty template if none is bundled.
    """
    if bundle.template is not None:
        return bundle.template
    return TemplateData()


def extract_rubric(bundle: AssignmentBundle) -> Rubric:
    """Extract the rubric from an assignment bundle.

    Returns:
        The rubric object.

    Raises:
        ValueError: If no rubric is present in the bundle.
    """
    if bundle.rubric is None:
        raise ValueError("Assignment bundle does not contain a rubric")
    return Rubric.from_dict(bundle.rubric)
