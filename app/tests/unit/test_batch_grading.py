"""Tests for batch grading and CSV gradebook export."""

import csv
import json

import pytest
from grading.batch_grader import BatchGrader, BatchGradingResult
from grading.grade_exporter import export_gradebook_csv
from grading.rubric import Rubric, RubricCheck, save_rubric
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData


def _build_circuit(r_value="1k", c_value="100n"):
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
    """Save a circuit to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(circuit.to_dict(), f)


class TestBatchGrader:
    def test_grade_empty_folder(self, tmp_path):
        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)
        assert result.total_students == 0
        assert result.successful == 0
        assert result.failed == 0

    def test_grade_single_correct_student(self, tmp_path):
        circuit = _build_circuit()
        _save_circuit(circuit, tmp_path / "student1.json")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)

        assert result.total_students == 1
        assert result.successful == 1
        assert result.failed == 0
        assert len(result.results) == 1
        assert result.results[0].earned_points == 50

    def test_grade_multiple_students(self, tmp_path):
        # Correct student
        _save_circuit(_build_circuit(), tmp_path / "correct.json")
        # Wrong value student
        _save_circuit(_build_circuit(r_value="10k"), tmp_path / "wrong_value.json")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)

        assert result.total_students == 2
        assert result.successful == 2
        assert result.failed == 0
        scores = sorted(r.earned_points for r in result.results)
        assert scores == [25, 50]

    def test_grade_with_invalid_file(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "good.json")
        # Write invalid JSON
        (tmp_path / "bad.json").write_text("not valid json")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)

        assert result.total_students == 2
        assert result.successful == 1
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0][0] == "bad.json"

    def test_grade_ignores_non_circuit_files(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "student.json")
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "notes.md").write_text("also ignore")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)

        assert result.total_students == 1
        assert result.successful == 1

    def test_grade_with_template_files(self, tmp_path):
        circuit = _build_circuit()
        template_data = {
            "template_version": "1.0",
            "starter_circuit": circuit.to_dict(),
        }
        with open(tmp_path / "student.spice-template", "w") as f:
            json.dump(template_data, f)

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)

        assert result.total_students == 1
        assert result.successful == 1

    def test_progress_callback_invoked(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "s1.json")
        _save_circuit(_build_circuit(), tmp_path / "s2.json")

        calls = []

        def callback(current, total, filename):
            calls.append((current, total, filename))

        grader = BatchGrader()
        rubric = _build_rubric()
        grader.grade_folder(str(tmp_path), rubric, progress_callback=callback)

        assert len(calls) == 3  # 2 files + 1 "Done"
        assert calls[-1][2] == "Done"

    def test_grade_with_reference_circuit(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "student.json")
        reference = _build_circuit()

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric, reference_circuit=reference)

        assert result.successful == 1


class TestBatchGradingResultStats:
    def test_empty_results_stats(self):
        result = BatchGradingResult(
            rubric_title="Test",
            total_students=0,
            successful=0,
            failed=0,
        )
        assert result.mean_score == 0.0
        assert result.median_score == 0.0
        assert result.min_score == 0.0
        assert result.max_score == 0.0

    def test_stats_with_results(self, tmp_path):
        _save_circuit(_build_circuit(), tmp_path / "perfect.json")
        _save_circuit(_build_circuit(r_value="10k"), tmp_path / "partial.json")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(tmp_path), rubric)

        assert result.mean_score == pytest.approx(75.0)
        assert result.median_score == pytest.approx(75.0)
        assert result.min_score == pytest.approx(50.0)
        assert result.max_score == pytest.approx(100.0)


class TestGradeExporter:
    def test_export_gradebook_csv(self, tmp_path):
        submissions = tmp_path / "submissions"
        submissions.mkdir()
        _save_circuit(_build_circuit(), submissions / "alice.json")
        _save_circuit(_build_circuit(r_value="10k"), submissions / "bob.json")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(submissions), rubric)

        csv_path = tmp_path / "gradebook.csv"
        export_gradebook_csv(result, str(csv_path))

        assert csv_path.exists()
        content = csv_path.read_text()
        assert "Student File" in content
        assert "Total Score" in content
        assert "r1_exists" in content
        assert "r1_value" in content
        assert "alice.json" in content
        assert "bob.json" in content
        assert "Mean Score" in content

    def test_export_empty_results(self, tmp_path):
        result = BatchGradingResult(
            rubric_title="Test",
            total_students=0,
            successful=0,
            failed=0,
        )
        csv_path = tmp_path / "empty.csv"
        export_gradebook_csv(result, str(csv_path))

        assert csv_path.exists()
        content = csv_path.read_text()
        assert "No results" in content

    def test_export_includes_errors(self, tmp_path):
        submissions = tmp_path / "submissions"
        submissions.mkdir()
        _save_circuit(_build_circuit(), submissions / "good.json")
        (submissions / "bad.json").write_text("invalid")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(submissions), rubric)

        csv_path = tmp_path / "gradebook.csv"
        export_gradebook_csv(result, str(csv_path))

        content = csv_path.read_text()
        assert "Errors" in content
        assert "bad.json" in content

    def test_csv_has_correct_columns(self, tmp_path):
        submissions = tmp_path / "submissions"
        submissions.mkdir()
        _save_circuit(_build_circuit(), submissions / "student.json")

        grader = BatchGrader()
        rubric = _build_rubric()
        result = grader.grade_folder(str(submissions), rubric)

        csv_path = tmp_path / "gradebook.csv"
        export_gradebook_csv(result, str(csv_path))

        with open(csv_path) as f:
            reader = csv.reader(f)
            header = next(reader)

        assert header[0] == "Student File"
        assert header[1] == "Total Score"
        assert header[2] == "Percentage"
        assert "r1_exists (25pts)" in header
        assert "r1_value (25pts)" in header


class TestBatchGradingDialog:
    def test_dialog_creates(self, qtbot):
        from GUI.batch_grading_dialog import BatchGradingDialog

        dialog = BatchGradingDialog()
        qtbot.addWidget(dialog)

        assert dialog.folder_path is not None
        assert dialog.rubric_path is not None
        assert dialog.grade_btn is not None
        assert dialog.export_btn is not None
        assert dialog.progress_bar is not None

    def test_grade_button_initially_disabled(self, qtbot):
        from GUI.batch_grading_dialog import BatchGradingDialog

        dialog = BatchGradingDialog()
        qtbot.addWidget(dialog)
        assert not dialog.grade_btn.isEnabled()

    def test_export_button_initially_disabled(self, qtbot):
        from GUI.batch_grading_dialog import BatchGradingDialog

        dialog = BatchGradingDialog()
        qtbot.addWidget(dialog)
        assert not dialog.export_btn.isEnabled()

    def test_results_group_initially_hidden(self, qtbot):
        from GUI.batch_grading_dialog import BatchGradingDialog

        dialog = BatchGradingDialog()
        qtbot.addWidget(dialog)
        assert not dialog.results_group.isVisible()
