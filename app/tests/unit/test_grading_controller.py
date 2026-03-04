"""Tests for controllers.grading_controller — batch grading orchestration."""

import json

import pytest
from controllers.grading_controller import GradingController
from grading.rubric import Rubric, RubricCheck
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

# ---------------------------------------------------------------------------
# Helpers (shared with test_batch_grading.py)
# ---------------------------------------------------------------------------


def _build_circuit(r_value="1k"):
    """Build a simple V1-R1-C1-GND circuit."""
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
        value="100n",
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
    model.analysis_type = "AC Sweep"
    model.rebuild_nodes()
    return model


def _build_rubric():
    return Rubric(
        title="RC Filter Test",
        total_points=50,
        checks=[
            RubricCheck(
                check_id="r1_exists",
                check_type="component_exists",
                points=25,
                params={"component_id": "R1", "component_type": "Resistor"},
                feedback_pass="R1 present",
                feedback_fail="R1 missing",
            ),
            RubricCheck(
                check_id="r1_value",
                check_type="component_value",
                points=25,
                params={"component_id": "R1", "expected_value": "1k", "tolerance_pct": 10},
                feedback_pass="R1 value OK",
                feedback_fail="R1 value wrong",
            ),
        ],
    )


def _save_circuit(circuit, filepath):
    with open(filepath, "w") as f:
        json.dump(circuit.to_dict(), f)


# ---------------------------------------------------------------------------
# GradingController tests
# ---------------------------------------------------------------------------


class TestGradingControllerGrading:
    """Tests for grade_folder() delegation."""

    def test_grade_folder_returns_result(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "student.json")
        ctrl = GradingController()
        rubric = _build_rubric()

        result = ctrl.grade_folder(str(tmp_path), rubric)

        assert result.total_students == 1
        assert result.successful == 1
        assert result.results[0].earned_points == 50

    def test_last_result_stored(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "student.json")
        ctrl = GradingController()
        rubric = _build_rubric()

        assert ctrl.last_result is None
        result = ctrl.grade_folder(str(tmp_path), rubric)
        assert ctrl.last_result is result

    def test_grade_empty_folder(self, tmp_path):
        ctrl = GradingController()
        rubric = _build_rubric()

        result = ctrl.grade_folder(str(tmp_path), rubric)
        assert result.total_students == 0

    def test_progress_callback_forwarded(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "a.json")
        _save_circuit(_build_circuit(), tmp_path / "b.json")

        calls = []
        ctrl = GradingController()
        rubric = _build_rubric()

        ctrl.grade_folder(str(tmp_path), rubric, progress_callback=lambda c, t, f: calls.append(f))

        assert len(calls) == 3  # 2 files + "Done"
        assert calls[-1] == "Done"

    def test_grade_with_reference_circuit(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "student.json")
        ctrl = GradingController()
        rubric = _build_rubric()
        reference = _build_circuit()

        result = ctrl.grade_folder(str(tmp_path), rubric, reference_circuit=reference)
        assert result.successful == 1


class TestGradingControllerExport:
    """Tests for export_csv() delegation."""

    def test_export_csv_creates_file(self, tmp_path):
        submissions = tmp_path / "submissions"
        submissions.mkdir()
        _save_circuit(_build_circuit(), submissions / "student.json")

        ctrl = GradingController()
        rubric = _build_rubric()
        result = ctrl.grade_folder(str(submissions), rubric)

        csv_path = tmp_path / "grades.csv"
        ctrl.export_csv(result, str(csv_path))

        assert csv_path.exists()
        content = csv_path.read_text()
        assert "Student File" in content
        assert "student.json" in content

    def test_export_csv_empty_result(self, tmp_path):
        from grading.batch_grader import BatchGradingResult

        result = BatchGradingResult(rubric_title="Empty", total_students=0, successful=0, failed=0)
        csv_path = tmp_path / "empty.csv"

        ctrl = GradingController()
        ctrl.export_csv(result, str(csv_path))

        assert csv_path.exists()
        assert "No results" in csv_path.read_text()
