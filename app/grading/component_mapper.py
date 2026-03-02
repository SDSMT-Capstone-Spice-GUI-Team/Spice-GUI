"""Map rubric check IDs to circuit component IDs.

Pure-Python utility extracted from the grading panel GUI.
No Qt dependencies.
"""

import re


def extract_component_ids(check_id: str) -> list[str]:
    """Extract component IDs embedded in a check ID string.

    Parses patterns like ``R1``, ``C1``, ``V1``, ``GND1`` from the
    check_id.  Common non-component tokens (e.g. "check") are filtered out.

    Args:
        check_id: The rubric check ID string to parse.

    Returns:
        A list of uppercase component IDs found in the string.
    """
    matches = re.findall(r"([A-Za-z]+\d+)", check_id)
    skip = {"check"}
    return [m.upper() for m in matches if m.lower() not in skip]
