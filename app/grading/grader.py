"""Grading engine that executes rubric checks against student circuits.

Orchestrates the CircuitComparer to run each rubric check and produces
a scored GradingResult.

No Qt dependencies — pure Python module.
"""

from dataclasses import dataclass, field
from typing import Optional

from grading.circuit_comparer import CircuitComparer
from grading.rubric import Rubric, RubricCheck
from models.circuit import CircuitModel


@dataclass
class CheckGradeResult:
    """Result of a single rubric check."""

    check_id: str
    passed: bool
    points_earned: int
    points_possible: int
    feedback: str


@dataclass
class GradingResult:
    """Aggregated grading result for a student submission."""

    student_file: str
    rubric_title: str
    total_points: int
    earned_points: int
    check_results: list[CheckGradeResult] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        if self.total_points == 0:
            return 100.0
        return (self.earned_points / self.total_points) * 100.0


class CircuitGrader:
    """Executes rubric checks against a student circuit."""

    def __init__(self):
        self._comparer = CircuitComparer()

    def grade(
        self,
        student_circuit: CircuitModel,
        rubric: Rubric,
        reference_circuit: Optional[CircuitModel] = None,
        student_file: str = "",
    ) -> GradingResult:
        """Grade a student circuit against a rubric.

        Args:
            student_circuit: The student's submitted circuit.
            rubric: The grading rubric to apply.
            reference_circuit: Optional reference solution (used by some checks).
            student_file: Filename for the result record.

        Returns:
            GradingResult with per-check scores and feedback.
        """
        result = GradingResult(
            student_file=student_file,
            rubric_title=rubric.title,
            total_points=rubric.total_points,
            earned_points=0,
        )

        for check in rubric.checks:
            check_result = self._execute_check(
                check, student_circuit, reference_circuit
            )
            result.check_results.append(check_result)
            result.earned_points += check_result.points_earned

        return result

    def _execute_check(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        """Execute a single rubric check and return the graded result."""
        handler = _CHECK_HANDLERS.get(check.check_type)
        if handler is None:
            return CheckGradeResult(
                check_id=check.check_id,
                passed=False,
                points_earned=0,
                points_possible=check.points,
                feedback=f"Unknown check type: {check.check_type}",
            )
        return handler(self, check, student, reference)

    def _check_component_exists(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        component_id = check.params.get("component_id", "")
        component_type = check.params.get("component_type", "")

        if component_id:
            cr = self._comparer.check_component_exists(
                student, component_id, component_type
            )
            passed = cr.passed
        elif component_type:
            # Check by type count
            min_count = check.params.get("min_count", 1)
            count = sum(
                1
                for c in student.components.values()
                if c.component_type == component_type
            )
            passed = count >= min_count
        else:
            passed = False

        return CheckGradeResult(
            check_id=check.check_id,
            passed=passed,
            points_earned=check.points if passed else 0,
            points_possible=check.points,
            feedback=check.feedback_pass if passed else check.feedback_fail,
        )

    def _check_component_value(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        component_id = check.params.get("component_id", "")
        expected_value = check.params.get("expected_value", "")
        tolerance_pct = check.params.get("tolerance_pct", 0.0)

        cr = self._comparer.check_component_value(
            student, component_id, expected_value, tolerance_pct
        )

        return CheckGradeResult(
            check_id=check.check_id,
            passed=cr.passed,
            points_earned=check.points if cr.passed else 0,
            points_possible=check.points,
            feedback=check.feedback_pass if cr.passed else check.feedback_fail,
        )

    def _check_component_count(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        component_type = check.params.get("component_type", "")
        expected_count = check.params.get("expected_count", 0)

        actual_count = sum(
            1 for c in student.components.values() if c.component_type == component_type
        )
        passed = actual_count == expected_count

        return CheckGradeResult(
            check_id=check.check_id,
            passed=passed,
            points_earned=check.points if passed else 0,
            points_possible=check.points,
            feedback=check.feedback_pass if passed else check.feedback_fail,
        )

    def _check_topology(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        component_a = check.params.get("component_a", "")
        component_b = check.params.get("component_b", "")

        cr = self._comparer.check_topology(student, component_a, component_b)
        expected_connected = check.params.get("shared_node", True)
        passed = cr.passed == expected_connected

        return CheckGradeResult(
            check_id=check.check_id,
            passed=passed,
            points_earned=check.points if passed else 0,
            points_possible=check.points,
            feedback=check.feedback_pass if passed else check.feedback_fail,
        )

    def _check_ground(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        has_ground = any(n.is_ground for n in student.nodes)
        component_id = check.params.get("component_id", "")

        if component_id:
            # Check that a specific component is connected to ground
            passed = False
            for node in student.nodes:
                if node.is_ground:
                    comp_ids = {t[0] for t in node.terminals}
                    if component_id in comp_ids:
                        passed = True
                    break
        else:
            passed = has_ground

        return CheckGradeResult(
            check_id=check.check_id,
            passed=passed,
            points_earned=check.points if passed else 0,
            points_possible=check.points,
            feedback=check.feedback_pass if passed else check.feedback_fail,
        )

    def _check_analysis_type(
        self,
        check: RubricCheck,
        student: CircuitModel,
        reference: Optional[CircuitModel],
    ) -> CheckGradeResult:
        expected_type = check.params.get("expected_type", "")
        cr = self._comparer.check_analysis_type(student, expected_type)

        return CheckGradeResult(
            check_id=check.check_id,
            passed=cr.passed,
            points_earned=check.points if cr.passed else 0,
            points_possible=check.points,
            feedback=check.feedback_pass if cr.passed else check.feedback_fail,
        )


# Map check types to handler methods
_CHECK_HANDLERS = {
    "component_exists": CircuitGrader._check_component_exists,
    "component_value": CircuitGrader._check_component_value,
    "component_count": CircuitGrader._check_component_count,
    "topology": CircuitGrader._check_topology,
    "ground": CircuitGrader._check_ground,
    "analysis_type": CircuitGrader._check_analysis_type,
}
