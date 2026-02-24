"""Tests for the instructor grading panel."""

import csv
import json

import pytest
from grading.grader import CheckGradeResult, GradingResult
from grading.rubric import Rubric, RubricCheck, save_rubric
from GUI.grading_panel import GradingPanel
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from PyQt6.QtCore import Qt


def _build_rc_filter(r_value="1k", c_value="100n"):
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
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="R1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="C1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="C1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="GND1",
            end_terminal=0,
        ),
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
                params={
                    "component_id": "R1",
                    "expected_value": "1k",
                    "tolerance_pct": 10,
                },
                feedback_pass="R1 value OK",
                feedback_fail="R1 value wrong",
            ),
        ],
    )


class TestGradingPanelStructure:
    def test_creates_with_expected_widgets(self, qtbot):
        model = CircuitModel()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        assert panel.load_student_btn is not None
        assert panel.load_rubric_btn is not None
        assert panel.grade_btn is not None
        assert panel.export_btn is not None
        assert panel.results_list is not None
        assert panel.score_label is not None

    def test_grade_button_initially_disabled(self, qtbot):
        panel = GradingPanel(CircuitModel())
        qtbot.addWidget(panel)
        assert not panel.grade_btn.isEnabled()

    def test_export_button_initially_disabled(self, qtbot):
        panel = GradingPanel(CircuitModel())
        qtbot.addWidget(panel)
        assert not panel.export_btn.isEnabled()


class TestGradingPanelGrading:
    def test_grade_populates_results(self, qtbot):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter()
        panel._rubric = _build_rubric()
        panel._student_file = "test_student.json"
        panel._on_grade()

        assert panel.results_list.count() == 2
        assert panel._result is not None
        assert panel._result.earned_points == 50

    def test_grade_shows_score(self, qtbot):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter()
        panel._rubric = _build_rubric()
        panel._on_grade()

        assert "50/50" in panel.score_label.text()

    def test_grade_with_wrong_value(self, qtbot):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter(r_value="10k")
        panel._rubric = _build_rubric()
        panel._on_grade()

        assert panel._result.earned_points == 25  # Only existence check passes
        assert "25/50" in panel.score_label.text()

    def test_grade_enables_export(self, qtbot):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter()
        panel._rubric = _build_rubric()
        panel._on_grade()

        assert panel.export_btn.isEnabled()


class TestGradingPanelCheckSelection:
    def test_selecting_check_shows_feedback(self, qtbot):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter()
        panel._rubric = _build_rubric()
        panel._on_grade()

        # Select first item
        panel.results_list.setCurrentRow(0)
        assert panel.feedback_label.text() == "R1 present"


class TestGradingPanelClear:
    def test_clear_results(self, qtbot):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter()
        panel._rubric = _build_rubric()
        panel._on_grade()

        panel.clear_results()
        assert panel.results_list.count() == 0
        assert panel.score_label.text() == ""
        assert not panel.grade_btn.isEnabled()
        assert not panel.export_btn.isEnabled()


class TestGradingPanelExport:
    def test_export_csv(self, qtbot, tmp_path):
        model = _build_rc_filter()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        panel._student_circuit = _build_rc_filter()
        panel._rubric = _build_rubric()
        panel._student_file = "student1.json"
        panel._on_grade()

        filepath = tmp_path / "results.csv"
        panel._export_result_csv(panel._result, str(filepath))

        assert filepath.exists()
        content = filepath.read_text()
        assert "student1.json" in content
        assert "RC Filter Test" in content
        assert "r1_exists" in content


class TestGradingPanelLoadStudent:
    def test_load_student_json(self, qtbot, tmp_path):
        model = CircuitModel()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        # Create a circuit file
        circuit = _build_rc_filter()
        filepath = tmp_path / "student.json"
        with open(filepath, "w") as f:
            json.dump(circuit.to_dict(), f)

        # Simulate loading (bypass file dialog)
        from controllers.file_controller import validate_circuit_data

        with open(filepath, "r") as f:
            data = json.load(f)
        validate_circuit_data(data)
        panel._student_circuit = CircuitModel.from_dict(data)
        panel._student_file = "student.json"
        panel.student_label.setText("Student: student.json")

        assert panel._student_circuit is not None
        assert "R1" in panel._student_circuit.components


class TestGradingPanelLoadRubric:
    def test_load_rubric_file(self, qtbot, tmp_path):
        model = CircuitModel()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)

        rubric = _build_rubric()
        filepath = tmp_path / "test.spice-rubric"
        save_rubric(rubric, filepath)

        # Simulate loading (bypass file dialog)
        from grading.rubric import load_rubric

        panel._rubric = load_rubric(filepath)
        panel.rubric_label.setText(f"Rubric: {panel._rubric.title}")

        assert panel._rubric is not None
        assert panel._rubric.title == "RC Filter Test"
