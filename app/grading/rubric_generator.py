"""Auto-generate a rubric skeleton from a reference circuit.

Analyzes the reference circuit to produce checks for component existence,
component values, topology (connections), ground, and analysis type.
Points are distributed equally across checks; the instructor adjusts later.

No Qt dependencies — pure Python module.
"""

from models.circuit import CircuitModel

from .rubric import Rubric, RubricCheck

# Component types that carry a meaningful user-set value
_VALUE_TYPES = frozenset(
    {
        "Resistor",
        "Capacitor",
        "Inductor",
        "Voltage Source",
        "Current Source",
        "Waveform Source",
        "VCVS",
        "CCVS",
        "VCCS",
        "CCCS",
    }
)


def generate_rubric_from_circuit(
    circuit: CircuitModel,
    title: str = "Auto-Generated Rubric",
    total_points: int = 100,
) -> Rubric:
    """Generate a rubric skeleton from a reference circuit.

    Produces the following check types:
    - ``component_exists`` for each non-Ground component
    - ``component_value`` for each component with a meaningful value
    - ``topology`` for each wire connection (pair of connected components)
    - ``ground`` if a ground node exists
    - ``analysis_type`` for the configured analysis (when not the default)

    Points are distributed equally (remainder added to the first check).

    Args:
        circuit: Reference solution circuit to analyze.
        title: Rubric title.
        total_points: Target total points for the rubric.

    Returns:
        A :class:`Rubric` ready for review in the rubric editor.
    """
    checks: list[RubricCheck] = []

    # 1. Component existence checks (skip Ground components)
    for comp_id, comp in sorted(circuit.components.items()):
        if comp.component_type == "Ground":
            continue
        checks.append(
            RubricCheck(
                check_id=f"exists_{comp_id}",
                check_type="component_exists",
                points=0,  # assigned below
                params={"component_id": comp_id, "component_type": comp.component_type},
                feedback_pass=f"{comp_id} ({comp.component_type}) found.",
                feedback_fail=f"{comp_id} ({comp.component_type}) is missing.",
            )
        )

    # 2. Component value checks (only for types that carry meaningful values)
    for comp_id, comp in sorted(circuit.components.items()):
        if comp.component_type not in _VALUE_TYPES:
            continue
        # Skip if the value is the factory default (instructor likely wants
        # value checks only for intentionally-set values, but we include them
        # all and let the instructor prune).
        checks.append(
            RubricCheck(
                check_id=f"value_{comp_id}",
                check_type="component_value",
                points=0,
                params={
                    "component_id": comp_id,
                    "expected_value": comp.value,
                    "tolerance_pct": 5.0,
                },
                feedback_pass=f"{comp_id} value matches expected ({comp.value}).",
                feedback_fail=f"{comp_id} value does not match expected ({comp.value}).",
            )
        )

    # 3. Topology checks — one per wire connection (unique component pairs)
    seen_pairs: set[tuple[str, str]] = set()
    for wire in circuit.wires:
        a = wire.start_component_id
        b = wire.end_component_id
        pair = tuple(sorted((a, b)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        checks.append(
            RubricCheck(
                check_id=f"topo_{pair[0]}_{pair[1]}",
                check_type="topology",
                points=0,
                params={
                    "component_a": pair[0],
                    "component_b": pair[1],
                    "shared_node": True,
                },
                feedback_pass=f"{pair[0]} and {pair[1]} are connected.",
                feedback_fail=f"{pair[0]} and {pair[1]} should be connected but are not.",
            )
        )

    # 4. Ground check — if any ground node exists
    has_ground = any(n.is_ground for n in circuit.nodes)
    if has_ground:
        checks.append(
            RubricCheck(
                check_id="ground_exists",
                check_type="ground",
                points=0,
                params={},
                feedback_pass="Circuit has a ground connection.",
                feedback_fail="Circuit is missing a ground connection.",
            )
        )

    # 5. Analysis type check — if not the default
    if circuit.analysis_type != "DC Operating Point":
        checks.append(
            RubricCheck(
                check_id="analysis_type",
                check_type="analysis_type",
                points=0,
                params={"expected_type": circuit.analysis_type},
                feedback_pass=f"Analysis type is {circuit.analysis_type}.",
                feedback_fail=f"Expected analysis type {circuit.analysis_type}.",
            )
        )

    # Distribute points equally
    if checks:
        base_points = total_points // len(checks)
        remainder = total_points - base_points * len(checks)
        for i, check in enumerate(checks):
            check.points = base_points + (1 if i < remainder else 0)

    return Rubric(title=title, total_points=total_points, checks=checks)
