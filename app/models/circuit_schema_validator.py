"""Validate circuit JSON data structures (schema validation).

Checks that a parsed JSON dict has the required fields and types before
attempting to deserialise it into a CircuitModel. No controller or Qt
dependencies.

This module is the canonical location for ``validate_circuit_data``.
"""


def validate_circuit_data(data) -> None:
    """
    Validate JSON structure before loading.

    Raises ValueError with a descriptive message if anything is wrong.
    """
    if not isinstance(data, dict):
        raise ValueError("File does not contain a valid circuit object.")

    if "components" not in data or not isinstance(data["components"], list):
        raise ValueError("Missing or invalid 'components' list.")
    if "wires" not in data or not isinstance(data["wires"], list):
        raise ValueError("Missing or invalid 'wires' list.")

    # AUDIT(security): component IDs from untrusted JSON are not checked for type (must be str) or uniqueness; duplicate IDs would silently overwrite earlier components during deserialization
    comp_ids = set()
    for i, comp in enumerate(data["components"]):
        for key in ("id", "type", "value", "pos"):
            if key not in comp:
                raise ValueError(f"Component #{i + 1} is missing required field '{key}'.")
        pos = comp["pos"]
        if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
            raise ValueError(f"Component '{comp.get('id', i)}' has invalid position data.")
        if not isinstance(pos["x"], (int, float)) or not isinstance(pos["y"], (int, float)):
            raise ValueError(f"Component '{comp['id']}' position values must be numeric.")
        comp_ids.add(comp["id"])

    for i, wire in enumerate(data["wires"]):
        for key in ("start_comp", "end_comp", "start_term", "end_term"):
            if key not in wire:
                raise ValueError(f"Wire #{i + 1} is missing required field '{key}'.")
        if wire["start_comp"] not in comp_ids:
            raise ValueError(f"Wire #{i + 1} references unknown component '{wire['start_comp']}'.")
        if wire["end_comp"] not in comp_ids:
            raise ValueError(f"Wire #{i + 1} references unknown component '{wire['end_comp']}'.")
