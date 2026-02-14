"""Tests for partial credit scoring in the grading engine."""

import pytest
from grading.rubric import Rubric, RubricCheck


def _make_value_rubric(tolerance_pct=10, partial_credit=None):
    """Build a minimal rubric with a single component_value check."""
    check = RubricCheck(
        check_id="r1_value",
        check_type="component_value",
        points=20,
        params={
            "component_id": "R1",
            "expected_value": "1k",
            "tolerance_pct": tolerance_pct,
        },
        feedback_pass="Correct value",
        feedback_fail="Wrong value",
        partial_credit=partial_credit,
    )
    return Rubric(title="Partial Credit Test", total_points=20, checks=[check])


def _build_student(r_value="1k"):
    """Build a minimal circuit with one resistor."""
    from models.circuit import CircuitModel
    from models.component import ComponentData

    model = CircuitModel()
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value=r_value,
        position=(0.0, 0.0),
    )
    return model


def _grade(student, rubric):
    from grading.grader import CircuitGrader

    return CircuitGrader().grade(student, rubric, student_file="test.json")


class TestPartialCreditSerialization:
    """RubricCheck partial_credit field serializes and deserializes correctly."""

    def test_to_dict_without_partial_credit(self):
        check = RubricCheck(check_id="x", check_type="ground", points=5)
        d = check.to_dict()
        assert "partial_credit" not in d

    def test_to_dict_with_partial_credit(self):
        check = RubricCheck(
            check_id="x",
            check_type="component_value",
            points=20,
            partial_credit=[[10, 100], [25, 75], [50, 50]],
        )
        d = check.to_dict()
        assert d["partial_credit"] == [[10, 100], [25, 75], [50, 50]]

    def test_from_dict_round_trip(self):
        tiers = [[10, 100], [25, 75], [50, 50]]
        check = RubricCheck(
            check_id="x",
            check_type="component_value",
            points=20,
            partial_credit=tiers,
        )
        restored = RubricCheck.from_dict(check.to_dict())
        assert restored.partial_credit == tiers

    def test_from_dict_without_partial_credit(self):
        check = RubricCheck(check_id="x", check_type="ground", points=5)
        restored = RubricCheck.from_dict(check.to_dict())
        assert restored.partial_credit is None

    def test_backward_compatible_no_partial_credit_key(self):
        """Old rubrics without partial_credit key still load correctly."""
        data = {
            "check_id": "r1",
            "check_type": "component_value",
            "points": 10,
            "params": {"component_id": "R1", "expected_value": "1k"},
        }
        check = RubricCheck.from_dict(data)
        assert check.partial_credit is None


class TestPartialCreditGrading:
    """CircuitGrader evaluates partial credit tiers correctly."""

    def test_exact_value_full_credit(self):
        """Exact match awards full credit regardless of partial_credit tiers."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[10, 100], [25, 75], [50, 50]],
        )
        student = _build_student("1k")
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 20
        assert cr.passed is True

    def test_within_tolerance_full_credit(self):
        """Within tolerance → full credit, partial_credit tiers not evaluated."""
        rubric = _make_value_rubric(
            tolerance_pct=10,
            partial_credit=[[15, 100], [25, 75]],
        )
        student = _build_student("1.05k")  # 5% off, within 10% tolerance
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 20
        assert cr.passed is True

    def test_first_tier_match(self):
        """Value outside tolerance but within first partial credit tier."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[15, 100], [25, 75], [50, 50]],
        )
        student = _build_student("1.1k")  # 10% off — within first tier (15%)
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 20  # 100% credit
        assert cr.passed is True

    def test_second_tier_match(self):
        """Value matches the second partial credit tier."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[10, 100], [25, 75], [50, 50]],
        )
        student = _build_student("1.2k")  # 20% off — within second tier (25%)
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 15.0  # 75% of 20
        assert cr.passed is False

    def test_third_tier_match(self):
        """Value matches the third partial credit tier."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[10, 100], [25, 75], [50, 50]],
        )
        student = _build_student("1.4k")  # 40% off — within third tier (50%)
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 10.0  # 50% of 20

    def test_beyond_all_tiers_zero_credit(self):
        """Value beyond all tiers gets zero credit."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[10, 100], [25, 75], [50, 50]],
        )
        student = _build_student("5k")  # 400% off — beyond all tiers
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 0
        assert cr.passed is False

    def test_without_partial_credit_binary(self):
        """Without partial_credit, scoring is binary pass/fail."""
        rubric = _make_value_rubric(tolerance_pct=5, partial_credit=None)
        student = _build_student("1.2k")  # 20% off, fails 5% tolerance
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 0
        assert cr.passed is False

    def test_missing_component_zero_credit(self):
        """Missing component gets zero credit even with partial_credit tiers."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[50, 100]],
        )
        from models.circuit import CircuitModel

        student = CircuitModel()  # No components
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert cr.points_earned == 0

    def test_partial_credit_feedback_message(self):
        """Partial credit result has informative feedback."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[10, 100], [25, 75]],
        )
        student = _build_student("1.2k")  # 20% off, matches 25% tier
        result = _grade(student, rubric)
        cr = result.check_results[0]
        assert "75%" in cr.feedback
        assert "R1" in cr.feedback

    def test_total_earned_with_partial(self):
        """GradingResult.earned_points accumulates partial credit."""
        check1 = RubricCheck(
            check_id="r1_value",
            check_type="component_value",
            points=20,
            params={
                "component_id": "R1",
                "expected_value": "1k",
                "tolerance_pct": 5,
            },
            partial_credit=[[25, 75]],
        )
        check2 = RubricCheck(
            check_id="has_r1",
            check_type="component_exists",
            points=10,
            params={"component_id": "R1", "component_type": "Resistor"},
        )
        rubric = Rubric(title="Test", total_points=30, checks=[check1, check2])
        student = _build_student("1.2k")  # 20% off, gets 75% partial on value
        result = _grade(student, rubric)

        # 75% of 20 = 15, plus 10 for exists = 25
        assert result.earned_points == 25.0
        assert result.total_points == 30

    def test_percentage_with_partial_credit(self):
        """GradingResult.percentage works with partial credit."""
        rubric = _make_value_rubric(
            tolerance_pct=5,
            partial_credit=[[25, 50]],
        )
        student = _build_student("1.2k")  # 20% off, gets 50% partial
        result = _grade(student, rubric)
        # 50% of 20 = 10 earned, 20 total → 50%
        assert result.percentage == 50.0
