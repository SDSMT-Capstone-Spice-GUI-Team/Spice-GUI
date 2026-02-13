"""Tests for rubric data model and grading engine."""

import json

import pytest
from grading.grader import CircuitGrader, GradingResult
from grading.rubric import Rubric, RubricCheck, load_rubric, save_rubric, validate_rubric
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

# --- Helpers ---


def _build_rc_filter(r_value="1k", c_value="100n", analysis="AC Sweep"):
    """Build a V1-R1-C1-GND RC low-pass filter."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5V",
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value=r_value,
        position=(100.0, 0.0),
    )
    model.components["C1"] = ComponentData(
        component_id="C1",
        component_type="Capacitor",
        value=c_value,
        position=(200.0, 0.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
    )
    model.wires = [
        WireData(start_component_id="V1", start_terminal=1, end_component_id="R1", end_terminal=0),
        WireData(start_component_id="R1", start_terminal=1, end_component_id="C1", end_terminal=0),
        WireData(start_component_id="C1", start_terminal=1, end_component_id="GND1", end_terminal=0),
        WireData(start_component_id="V1", start_terminal=0, end_component_id="GND1", end_terminal=0),
    ]
    model.component_counter = {"V": 1, "R": 1, "C": 1, "GND": 1}
    model.analysis_type = analysis
    model.rebuild_nodes()
    return model


def _build_rc_rubric():
    """Build a rubric for an RC low-pass filter assignment."""
    return Rubric(
        title="RC Low-Pass Filter",
        total_points=100,
        checks=[
            RubricCheck(
                check_id="r1_exists",
                check_type="component_exists",
                points=15,
                params={"component_id": "R1", "component_type": "Resistor"},
                feedback_pass="Resistor R1 present",
                feedback_fail="Missing resistor R1",
            ),
            RubricCheck(
                check_id="c1_exists",
                check_type="component_exists",
                points=15,
                params={"component_id": "C1", "component_type": "Capacitor"},
                feedback_pass="Capacitor C1 present",
                feedback_fail="Missing capacitor C1",
            ),
            RubricCheck(
                check_id="r1_value",
                check_type="component_value",
                points=20,
                params={"component_id": "R1", "expected_value": "1k", "tolerance_pct": 10},
                feedback_pass="R1 value correct",
                feedback_fail="R1 value should be approximately 1k",
            ),
            RubricCheck(
                check_id="rc_connected",
                check_type="topology",
                points=25,
                params={"component_a": "R1", "component_b": "C1", "shared_node": True},
                feedback_pass="R1 and C1 are connected",
                feedback_fail="R1 and C1 must share a node",
            ),
            RubricCheck(
                check_id="has_ground",
                check_type="ground",
                points=10,
                params={},
                feedback_pass="Ground present",
                feedback_fail="Circuit needs a ground connection",
            ),
            RubricCheck(
                check_id="ac_sweep",
                check_type="analysis_type",
                points=15,
                params={"expected_type": "AC Sweep"},
                feedback_pass="AC Sweep selected",
                feedback_fail="Use AC Sweep for frequency response",
            ),
        ],
    )


# --- Tests: Rubric data model ---


class TestRubricCheck:
    def test_to_dict(self):
        check = RubricCheck(
            check_id="r1",
            check_type="component_exists",
            points=10,
            params={"component_id": "R1"},
            feedback_pass="OK",
            feedback_fail="Missing",
        )
        d = check.to_dict()
        assert d["check_id"] == "r1"
        assert d["points"] == 10
        assert d["params"]["component_id"] == "R1"

    def test_from_dict_round_trip(self):
        check = RubricCheck(
            check_id="r1",
            check_type="component_value",
            points=20,
            params={"expected_value": "1k", "tolerance_pct": 5},
            feedback_pass="OK",
            feedback_fail="Wrong",
        )
        restored = RubricCheck.from_dict(check.to_dict())
        assert restored.check_id == "r1"
        assert restored.check_type == "component_value"
        assert restored.params["tolerance_pct"] == 5


class TestRubric:
    def test_to_dict(self):
        rubric = _build_rc_rubric()
        d = rubric.to_dict()
        assert d["title"] == "RC Low-Pass Filter"
        assert d["total_points"] == 100
        assert len(d["checks"]) == 6

    def test_from_dict_round_trip(self):
        rubric = _build_rc_rubric()
        restored = Rubric.from_dict(rubric.to_dict())
        assert restored.title == rubric.title
        assert restored.total_points == rubric.total_points
        assert len(restored.checks) == len(rubric.checks)
        assert restored.checks[0].check_id == "r1_exists"


class TestValidateRubric:
    def test_valid_rubric(self):
        rubric = _build_rc_rubric()
        validate_rubric(rubric.to_dict())  # Should not raise

    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="JSON object"):
            validate_rubric([])

    def test_missing_title(self):
        with pytest.raises(ValueError, match="title"):
            validate_rubric({"total_points": 10, "checks": []})

    def test_missing_total_points(self):
        with pytest.raises(ValueError, match="total_points"):
            validate_rubric({"title": "Test", "checks": []})

    def test_empty_checks(self):
        with pytest.raises(ValueError, match="at least one"):
            validate_rubric({"title": "Test", "total_points": 10, "checks": []})

    def test_invalid_check_type(self):
        data = {
            "title": "Test",
            "total_points": 10,
            "checks": [
                {"check_id": "x", "check_type": "invalid_type", "points": 10},
            ],
        }
        with pytest.raises(ValueError, match="invalid type"):
            validate_rubric(data)

    def test_duplicate_check_ids(self):
        data = {
            "title": "Test",
            "total_points": 20,
            "checks": [
                {"check_id": "dup", "check_type": "ground", "points": 10},
                {"check_id": "dup", "check_type": "ground", "points": 10},
            ],
        }
        with pytest.raises(ValueError, match="Duplicate"):
            validate_rubric(data)

    def test_points_sum_mismatch(self):
        data = {
            "title": "Test",
            "total_points": 50,
            "checks": [
                {"check_id": "a", "check_type": "ground", "points": 10},
            ],
        }
        with pytest.raises(ValueError, match="sum to 10"):
            validate_rubric(data)

    def test_missing_check_field(self):
        data = {
            "title": "Test",
            "total_points": 10,
            "checks": [
                {"check_id": "a", "check_type": "ground"},  # missing points
            ],
        }
        with pytest.raises(ValueError, match="points"):
            validate_rubric(data)


class TestRubricSaveLoad:
    def test_save_creates_file(self, tmp_path):
        rubric = _build_rc_rubric()
        filepath = tmp_path / "test.spice-rubric"
        save_rubric(rubric, filepath)
        assert filepath.exists()

    def test_round_trip(self, tmp_path):
        rubric = _build_rc_rubric()
        filepath = tmp_path / "test.spice-rubric"
        save_rubric(rubric, filepath)
        loaded = load_rubric(filepath)
        assert loaded.title == rubric.title
        assert loaded.total_points == rubric.total_points
        assert len(loaded.checks) == len(rubric.checks)

    def test_load_invalid_json_raises(self, tmp_path):
        filepath = tmp_path / "bad.spice-rubric"
        filepath.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            load_rubric(filepath)

    def test_load_invalid_rubric_raises(self, tmp_path):
        filepath = tmp_path / "bad.spice-rubric"
        filepath.write_text(json.dumps({"title": "", "total_points": 0, "checks": []}))
        with pytest.raises(ValueError):
            load_rubric(filepath)


# --- Tests: Grading engine ---


class TestCircuitGraderFullMarks:
    def test_correct_circuit_gets_full_marks(self):
        student = _build_rc_filter(r_value="1k", c_value="100n", analysis="AC Sweep")
        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(student, rubric, student_file="student.json")
        assert result.earned_points == 100
        assert result.percentage == 100.0
        assert all(cr.passed for cr in result.check_results)

    def test_result_metadata(self):
        student = _build_rc_filter()
        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(student, rubric, student_file="test.json")
        assert result.student_file == "test.json"
        assert result.rubric_title == "RC Low-Pass Filter"
        assert result.total_points == 100


class TestCircuitGraderPartialMarks:
    def test_missing_component_loses_points(self):
        student = _build_rc_filter()
        del student.components["C1"]
        student.rebuild_nodes()

        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(student, rubric)

        # C1 existence check should fail
        c1_result = next(cr for cr in result.check_results if cr.check_id == "c1_exists")
        assert c1_result.passed is False
        assert c1_result.points_earned == 0

        # Total should be less than 100
        assert result.earned_points < 100

    def test_wrong_value_loses_points(self):
        student = _build_rc_filter(r_value="10k")  # Wrong value
        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(student, rubric)

        r1_value = next(cr for cr in result.check_results if cr.check_id == "r1_value")
        assert r1_value.passed is False
        assert r1_value.feedback == "R1 value should be approximately 1k"

    def test_value_within_tolerance_passes(self):
        student = _build_rc_filter(r_value="1.05k")  # Within 10%
        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(student, rubric)

        r1_value = next(cr for cr in result.check_results if cr.check_id == "r1_value")
        assert r1_value.passed is True

    def test_wrong_analysis_loses_points(self):
        student = _build_rc_filter(analysis="Transient")
        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(student, rubric)

        ac_check = next(cr for cr in result.check_results if cr.check_id == "ac_sweep")
        assert ac_check.passed is False
        assert ac_check.points_earned == 0


class TestCircuitGraderTopology:
    def test_disconnected_topology_fails(self):
        """R1 and C1 not connected should fail topology check."""
        model = CircuitModel()
        model.components["V1"] = ComponentData(
            component_id="V1", component_type="Voltage Source", value="5V", position=(0.0, 0.0)
        )
        model.components["R1"] = ComponentData(
            component_id="R1", component_type="Resistor", value="1k", position=(100.0, 0.0)
        )
        model.components["C1"] = ComponentData(
            component_id="C1", component_type="Capacitor", value="100n", position=(200.0, 0.0)
        )
        model.components["GND1"] = ComponentData(
            component_id="GND1", component_type="Ground", value="0V", position=(0.0, 100.0)
        )
        # Wire V1-R1 and C1-GND but NOT R1-C1
        model.wires = [
            WireData(start_component_id="V1", start_terminal=1, end_component_id="R1", end_terminal=0),
            WireData(start_component_id="C1", start_terminal=1, end_component_id="GND1", end_terminal=0),
            WireData(start_component_id="V1", start_terminal=0, end_component_id="GND1", end_terminal=0),
        ]
        model.analysis_type = "AC Sweep"
        model.rebuild_nodes()

        rubric = _build_rc_rubric()
        grader = CircuitGrader()
        result = grader.grade(model, rubric)

        topo_check = next(cr for cr in result.check_results if cr.check_id == "rc_connected")
        assert topo_check.passed is False


class TestCircuitGraderGround:
    def test_missing_ground_fails(self):
        model = CircuitModel()
        model.components["R1"] = ComponentData(
            component_id="R1", component_type="Resistor", value="1k", position=(0.0, 0.0)
        )
        model.rebuild_nodes()

        rubric = Rubric(
            title="Ground Test",
            total_points=10,
            checks=[
                RubricCheck(
                    check_id="gnd",
                    check_type="ground",
                    points=10,
                    params={},
                    feedback_pass="OK",
                    feedback_fail="No ground",
                )
            ],
        )
        grader = CircuitGrader()
        result = grader.grade(model, rubric)
        assert result.check_results[0].passed is False

    def test_ground_with_component_check(self):
        student = _build_rc_filter()
        rubric = Rubric(
            title="Ground Component Test",
            total_points=10,
            checks=[
                RubricCheck(
                    check_id="c1_grounded",
                    check_type="ground",
                    points=10,
                    params={"component_id": "C1"},
                    feedback_pass="C1 grounded",
                    feedback_fail="C1 not grounded",
                )
            ],
        )
        grader = CircuitGrader()
        result = grader.grade(student, rubric)
        # C1 terminal 1 connects to GND in _build_rc_filter
        assert result.check_results[0].passed is True


class TestCircuitGraderComponentCount:
    def test_correct_count(self):
        student = _build_rc_filter()
        rubric = Rubric(
            title="Count Test",
            total_points=10,
            checks=[
                RubricCheck(
                    check_id="one_resistor",
                    check_type="component_count",
                    points=10,
                    params={"component_type": "Resistor", "expected_count": 1},
                    feedback_pass="OK",
                    feedback_fail="Wrong count",
                )
            ],
        )
        grader = CircuitGrader()
        result = grader.grade(student, rubric)
        assert result.check_results[0].passed is True

    def test_wrong_count(self):
        student = _build_rc_filter()
        rubric = Rubric(
            title="Count Test",
            total_points=10,
            checks=[
                RubricCheck(
                    check_id="two_resistors",
                    check_type="component_count",
                    points=10,
                    params={"component_type": "Resistor", "expected_count": 2},
                    feedback_pass="OK",
                    feedback_fail="Expected 2 resistors",
                )
            ],
        )
        grader = CircuitGrader()
        result = grader.grade(student, rubric)
        assert result.check_results[0].passed is False


class TestCircuitGraderExistsByType:
    def test_exists_by_type_min_count(self):
        student = _build_rc_filter()
        rubric = Rubric(
            title="Type Test",
            total_points=10,
            checks=[
                RubricCheck(
                    check_id="has_resistor",
                    check_type="component_exists",
                    points=10,
                    params={"component_type": "Resistor", "min_count": 1},
                    feedback_pass="OK",
                    feedback_fail="Missing",
                )
            ],
        )
        grader = CircuitGrader()
        result = grader.grade(student, rubric)
        assert result.check_results[0].passed is True


class TestGradingResult:
    def test_percentage_zero_total(self):
        result = GradingResult(
            student_file="",
            rubric_title="",
            total_points=0,
            earned_points=0,
        )
        assert result.percentage == 100.0

    def test_percentage_calculation(self):
        result = GradingResult(
            student_file="",
            rubric_title="",
            total_points=100,
            earned_points=75,
        )
        assert result.percentage == 75.0
