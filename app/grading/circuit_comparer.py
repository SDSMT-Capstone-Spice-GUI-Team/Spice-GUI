"""Circuit comparison engine for structural and parametric checks.

Compares two CircuitModel instances to identify differences in components,
values, topology, and analysis settings. Foundation for automated grading.

No Qt dependencies — pure Python module.
"""

from dataclasses import dataclass, field

from models.circuit import CircuitModel
from simulation.monte_carlo import parse_spice_value


@dataclass
class CheckResult:
    """Result of a single comparison check."""

    check_type: str
    component_id: str
    passed: bool
    expected: str
    actual: str
    message: str


@dataclass
class ComparisonResult:
    """Aggregated result of comparing two circuits."""

    matches: list[CheckResult] = field(default_factory=list)
    mismatches: list[CheckResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Overall match ratio (0.0–1.0)."""
        total = len(self.matches) + len(self.mismatches)
        if total == 0:
            return 1.0
        return len(self.matches) / total

    @property
    def all_results(self) -> list[CheckResult]:
        """All check results in order."""
        return self.matches + self.mismatches

    def add(self, result: CheckResult) -> None:
        """Add a check result to the appropriate list."""
        if result.passed:
            self.matches.append(result)
        else:
            self.mismatches.append(result)


def compare_values(expected_str: str, actual_str: str, tolerance_pct: float = 0.0) -> bool:
    """Compare two SPICE value strings with optional tolerance.

    Args:
        expected_str: Expected value (e.g., "1k", "4.7u").
        actual_str: Actual value to check.
        tolerance_pct: Allowed deviation in percent (0 = exact match).

    Returns:
        True if values match within tolerance, False otherwise.
        Returns False if either value cannot be parsed.
    """
    expected = parse_spice_value(expected_str)
    actual = parse_spice_value(actual_str)

    if expected is None or actual is None:
        return expected_str.strip() == actual_str.strip()

    if expected == 0:
        return actual == 0

    deviation = abs(actual - expected) / abs(expected) * 100
    return deviation <= tolerance_pct


class CircuitComparer:
    """Compares two CircuitModel instances structurally and parametrically."""

    def compare(self, reference: CircuitModel, student: CircuitModel) -> ComparisonResult:
        """Run all comparison checks between reference and student circuits.

        Args:
            reference: The instructor's solution circuit.
            student: The student's submitted circuit.

        Returns:
            ComparisonResult with all check outcomes.
        """
        result = ComparisonResult()
        self._check_component_existence(reference, student, result)
        self._check_component_values(reference, student, result)
        self._check_component_counts(reference, student, result)
        self._check_topology(reference, student, result)
        self._check_ground(reference, student, result)
        self._check_analysis(reference, student, result)
        return result

    def check_component_exists(self, student: CircuitModel, component_id: str, component_type: str) -> CheckResult:
        """Check if a specific component exists in the student circuit.

        Args:
            student: The student's circuit.
            component_id: Expected component ID (e.g., "R1").
            component_type: Expected component type (e.g., "Resistor").

        Returns:
            CheckResult for this single check.
        """
        comp = student.components.get(component_id)
        if comp is None:
            return CheckResult(
                check_type="component_exists",
                component_id=component_id,
                passed=False,
                expected=f"{component_type} {component_id}",
                actual="not found",
                message=f"Missing {component_type} '{component_id}'",
            )
        if comp.component_type != component_type:
            return CheckResult(
                check_type="component_exists",
                component_id=component_id,
                passed=False,
                expected=component_type,
                actual=comp.component_type,
                message=f"'{component_id}' is a {comp.component_type}, expected {component_type}",
            )
        return CheckResult(
            check_type="component_exists",
            component_id=component_id,
            passed=True,
            expected=f"{component_type} {component_id}",
            actual=f"{comp.component_type} {component_id}",
            message=f"{component_type} '{component_id}' present",
        )

    def check_component_value(
        self,
        student: CircuitModel,
        component_id: str,
        expected_value: str,
        tolerance_pct: float = 0.0,
    ) -> CheckResult:
        """Check if a component has the expected value.

        Args:
            student: The student's circuit.
            component_id: Component to check.
            expected_value: Expected value string (e.g., "1k").
            tolerance_pct: Allowed deviation in percent.

        Returns:
            CheckResult for this single check.
        """
        comp = student.components.get(component_id)
        if comp is None:
            return CheckResult(
                check_type="component_value",
                component_id=component_id,
                passed=False,
                expected=expected_value,
                actual="component not found",
                message=f"Cannot check value — '{component_id}' not found",
            )

        passed = compare_values(expected_value, comp.value, tolerance_pct)
        if passed:
            msg = f"'{component_id}' value correct ({comp.value})"
        else:
            msg = f"'{component_id}' value is {comp.value}, expected {expected_value}"
            if tolerance_pct > 0:
                msg += f" (within {tolerance_pct}%)"

        return CheckResult(
            check_type="component_value",
            component_id=component_id,
            passed=passed,
            expected=expected_value,
            actual=comp.value,
            message=msg,
        )

    def check_topology(
        self,
        circuit: CircuitModel,
        component_a: str,
        component_b: str,
    ) -> CheckResult:
        """Check if two components share a node (are directly connected).

        Args:
            circuit: Circuit to check.
            component_a: First component ID.
            component_b: Second component ID.

        Returns:
            CheckResult indicating whether they share a node.
        """
        connected = _components_share_node(circuit, component_a, component_b)

        if connected:
            return CheckResult(
                check_type="topology",
                component_id=f"{component_a}-{component_b}",
                passed=True,
                expected="connected",
                actual="connected",
                message=f"'{component_a}' and '{component_b}' are connected",
            )
        return CheckResult(
            check_type="topology",
            component_id=f"{component_a}-{component_b}",
            passed=False,
            expected="connected",
            actual="not connected",
            message=f"'{component_a}' and '{component_b}' should share a node",
        )

    def check_analysis_type(self, student: CircuitModel, expected_type: str) -> CheckResult:
        """Check if the analysis type matches.

        Args:
            student: The student's circuit.
            expected_type: Expected analysis type string.

        Returns:
            CheckResult for analysis type check.
        """
        passed = student.analysis_type == expected_type
        return CheckResult(
            check_type="analysis_type",
            component_id="",
            passed=passed,
            expected=expected_type,
            actual=student.analysis_type,
            message=(
                f"Analysis type correct ({expected_type})"
                if passed
                else f"Analysis type is '{student.analysis_type}', expected '{expected_type}'"
            ),
        )

    # -- Internal comparison methods for compare() --

    def _check_component_existence(
        self, reference: CircuitModel, student: CircuitModel, result: ComparisonResult
    ) -> None:
        """Check that all reference components exist in the student circuit."""
        for comp_id, comp in reference.components.items():
            if comp.component_type == "Ground":
                continue
            result.add(self.check_component_exists(student, comp_id, comp.component_type))

    def _check_component_values(self, reference: CircuitModel, student: CircuitModel, result: ComparisonResult) -> None:
        """Check that matching components have the same values."""
        for comp_id, ref_comp in reference.components.items():
            if ref_comp.component_type == "Ground":
                continue
            student_comp = student.components.get(comp_id)
            if student_comp is None:
                continue  # Already reported by existence check
            if student_comp.component_type != ref_comp.component_type:
                continue  # Already reported by existence check
            result.add(self.check_component_value(student, comp_id, ref_comp.value))

    def _check_component_counts(self, reference: CircuitModel, student: CircuitModel, result: ComparisonResult) -> None:
        """Check that the count of each component type matches."""
        ref_counts = _count_by_type(reference)
        student_counts = _count_by_type(student)

        for comp_type, expected_count in ref_counts.items():
            actual_count = student_counts.get(comp_type, 0)
            passed = actual_count == expected_count
            result.add(
                CheckResult(
                    check_type="component_count",
                    component_id="",
                    passed=passed,
                    expected=f"{expected_count} {comp_type}(s)",
                    actual=f"{actual_count} {comp_type}(s)",
                    message=(
                        f"Correct number of {comp_type}s ({expected_count})"
                        if passed
                        else f"Expected {expected_count} {comp_type}(s), found {actual_count}"
                    ),
                )
            )

    def _check_topology(self, reference: CircuitModel, student: CircuitModel, result: ComparisonResult) -> None:
        """Check that components sharing nodes in the reference also share them in the student."""
        # Find pairs of non-ground components that share a node in the reference
        pairs_checked = set()
        for node in reference.nodes:
            comp_ids = {t[0] for t in node.terminals}
            # Filter to non-ground components
            comp_ids = {
                cid
                for cid in comp_ids
                if cid in reference.components and reference.components[cid].component_type != "Ground"
            }
            for a in sorted(comp_ids):
                for b in sorted(comp_ids):
                    if a >= b:
                        continue
                    pair = (a, b)
                    if pair in pairs_checked:
                        continue
                    pairs_checked.add(pair)
                    # Only check if both exist in student
                    if a in student.components and b in student.components:
                        result.add(self.check_topology(student, a, b))

    def _check_ground(self, reference: CircuitModel, student: CircuitModel, result: ComparisonResult) -> None:
        """Check that ground is present and connects the expected components."""
        ref_ground_comps = set()
        student_ground_comps = set()

        for node in reference.nodes:
            if node.is_ground:
                ref_ground_comps = {t[0] for t in node.terminals}
                break

        has_ground = False
        for node in student.nodes:
            if node.is_ground:
                student_ground_comps = {t[0] for t in node.terminals}
                has_ground = True
                break

        if ref_ground_comps and not has_ground:
            result.add(
                CheckResult(
                    check_type="ground",
                    component_id="GND",
                    passed=False,
                    expected="ground node present",
                    actual="no ground node",
                    message="Circuit is missing a ground connection",
                )
            )
            return

        if ref_ground_comps and has_ground:
            # Check that ground connects the same non-Ground components
            ref_connected = {
                cid
                for cid in ref_ground_comps
                if cid in reference.components and reference.components[cid].component_type != "Ground"
            }
            student_connected = {
                cid
                for cid in student_ground_comps
                if cid in student.components and student.components[cid].component_type != "Ground"
            }

            for cid in ref_connected:
                if cid in student.components:
                    passed = cid in student_connected
                    result.add(
                        CheckResult(
                            check_type="ground",
                            component_id=cid,
                            passed=passed,
                            expected=f"'{cid}' connected to ground",
                            actual=f"'{cid}' {'connected' if passed else 'not connected'} to ground",
                            message=(
                                f"'{cid}' correctly connected to ground"
                                if passed
                                else f"'{cid}' should be connected to ground"
                            ),
                        )
                    )

    def _check_analysis(self, reference: CircuitModel, student: CircuitModel, result: ComparisonResult) -> None:
        """Check that analysis type and parameters match."""
        result.add(self.check_analysis_type(student, reference.analysis_type))


def _components_share_node(circuit: CircuitModel, comp_a: str, comp_b: str) -> bool:
    """Check if two components share at least one node in the circuit."""
    for node in circuit.nodes:
        comp_ids = {t[0] for t in node.terminals}
        if comp_a in comp_ids and comp_b in comp_ids:
            return True
    return False


def _count_by_type(circuit: CircuitModel) -> dict[str, int]:
    """Count components by type, excluding Ground."""
    counts: dict[str, int] = {}
    for comp in circuit.components.values():
        if comp.component_type == "Ground":
            continue
        counts[comp.component_type] = counts.get(comp.component_type, 0) + 1
    return counts
