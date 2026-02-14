"""Auto-generate a rubric skeleton from a reference circuit.

Analyzes a CircuitModel to produce checks for component existence,
component values, topology connections, ground presence, and analysis type.

No Qt dependencies — pure Python module.
"""

from models.circuit import CircuitModel
from models.component import DEFAULT_VALUES

from .rubric import Rubric, RubricCheck


def generate_rubric(
    circuit: CircuitModel,
    title: str = "Auto-Generated Rubric",
) -> Rubric:
    """Generate a rubric skeleton from a reference circuit.

    Creates the following checks:
    - ``component_exists`` for each non-ground component
    - ``component_value`` for each component whose value differs from the
      type default (i.e. the instructor intentionally set it)
    - ``topology`` for each wire connection between two non-ground components
    - ``ground`` if a ground component is present
    - ``analysis_type`` if the circuit uses a non-default analysis

    Points are distributed equally across all generated checks (at least 1
    each).  The instructor is expected to open the result in the rubric
    editor and adjust points and feedback.

    Args:
        circuit: The reference solution circuit.
        title: Title for the generated rubric.

    Returns:
        A Rubric populated with auto-generated checks.
    """
    checks: list[RubricCheck] = []
    used_ids: set[str] = set()

    def _unique_id(base: str) -> str:
        candidate = base
        n = 2
        while candidate in used_ids:
            candidate = f"{base}_{n}"
            n += 1
        used_ids.add(candidate)
        return candidate

    # --- component_exists checks ---
    for comp in sorted(circuit.components.values(), key=lambda c: c.component_id):
        if comp.component_type == "Ground":
            continue
        check_id = _unique_id(f"exists_{comp.component_id}")
        checks.append(
            RubricCheck(
                check_id=check_id,
                check_type="component_exists",
                points=1,
                params={
                    "component_id": comp.component_id,
                    "component_type": comp.component_type,
                },
                feedback_pass=f"{comp.component_id} ({comp.component_type}) found.",
                feedback_fail=f"Missing {comp.component_id} ({comp.component_type}).",
            )
        )

    # --- component_value checks ---
    for comp in sorted(circuit.components.values(), key=lambda c: c.component_id):
        if comp.component_type == "Ground":
            continue
        default = DEFAULT_VALUES.get(comp.component_type, "")
        if comp.value and comp.value != default:
            check_id = _unique_id(f"value_{comp.component_id}")
            checks.append(
                RubricCheck(
                    check_id=check_id,
                    check_type="component_value",
                    points=1,
                    params={
                        "component_id": comp.component_id,
                        "expected_value": comp.value,
                        "tolerance_pct": 5.0,
                    },
                    feedback_pass=f"{comp.component_id} has correct value ({comp.value}).",
                    feedback_fail=f"{comp.component_id} value should be {comp.value}.",
                )
            )

    # --- topology checks (from wire connections between non-ground components) ---
    seen_pairs: set[tuple[str, str]] = set()
    for wire in circuit.wires:
        a = wire.start_component_id
        b = wire.end_component_id
        if a == b:
            continue
        comp_a = circuit.components.get(a)
        comp_b = circuit.components.get(b)
        if comp_a is None or comp_b is None:
            continue
        if comp_a.component_type == "Ground" or comp_b.component_type == "Ground":
            continue
        pair = tuple(sorted([a, b]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        check_id = _unique_id(f"connected_{pair[0]}_{pair[1]}")
        checks.append(
            RubricCheck(
                check_id=check_id,
                check_type="topology",
                points=1,
                params={
                    "component_a": pair[0],
                    "component_b": pair[1],
                    "shared_node": True,
                },
                feedback_pass=f"{pair[0]} and {pair[1]} are connected.",
                feedback_fail=f"{pair[0]} and {pair[1]} should be connected.",
            )
        )

    # --- ground check ---
    has_ground = any(c.component_type == "Ground" for c in circuit.components.values())
    if has_ground:
        check_id = _unique_id("has_ground")
        checks.append(
            RubricCheck(
                check_id=check_id,
                check_type="ground",
                points=1,
                params={},
                feedback_pass="Ground connection present.",
                feedback_fail="Circuit must have a ground connection.",
            )
        )

    # --- analysis_type check ---
    if circuit.analysis_type != "DC Operating Point":
        check_id = _unique_id("analysis_type")
        checks.append(
            RubricCheck(
                check_id=check_id,
                check_type="analysis_type",
                points=1,
                params={"expected_type": circuit.analysis_type},
                feedback_pass=f"Analysis type is {circuit.analysis_type}.",
                feedback_fail=f"Analysis type should be {circuit.analysis_type}.",
            )
        )

    # Distribute points equally (minimum 1 per check)
    if checks:
        base_points = max(1, 100 // len(checks))
        for check in checks:
            check.points = base_points
        total = base_points * len(checks)
    else:
        total = 0

    return Rubric(title=title, total_points=total, checks=checks)
