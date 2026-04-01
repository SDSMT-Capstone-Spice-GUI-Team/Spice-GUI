"""Instructor grading panel - displays rubric results with visual feedback."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from grading.component_mapper import extract_component_ids
from models.circuit import CircuitModel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .styles import theme_manager

if TYPE_CHECKING:
    from grading.grader import GradingResult
    from grading.rubric import Rubric

logger = logging.getLogger(__name__)


class GradingPanel(QWidget):
    """Panel for grading student circuits against rubrics.

    Shows rubric check results with pass/fail indicators, scores,
    and feedback. Supports loading student files and rubrics,
    running the grader, and exporting results.
    """

    def __init__(self, model: CircuitModel, parent=None, canvas=None):
        super().__init__(parent)
        self._model = model
        self._canvas = canvas
        self._grader = None  # Lazy-initialized to avoid circular import
        self._rubric: Optional[Rubric] = None
        self._student_circuit: Optional[CircuitModel] = None
        self._reference_circuit: Optional[CircuitModel] = None
        self._student_file: str = ""
        self._result: Optional[GradingResult] = None
        self._highlighted_components: list = []

        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(5, 5, 5, 5)

        title = QLabel("Instructor Grading")
        title.setStyleSheet(theme_manager.stylesheet("heading_medium"))
        outer.addWidget(title)

        # --- Action buttons ---
        btn_layout = QHBoxLayout()

        self.load_student_btn = QPushButton("Load Student...")
        self.load_student_btn.setToolTip("Load a student circuit file to grade")
        self.load_student_btn.clicked.connect(self._on_load_student)
        btn_layout.addWidget(self.load_student_btn)

        self.load_rubric_btn = QPushButton("Load Rubric...")
        self.load_rubric_btn.setToolTip("Load a grading rubric (.spice-rubric)")
        self.load_rubric_btn.clicked.connect(self._on_load_rubric)
        btn_layout.addWidget(self.load_rubric_btn)

        outer.addLayout(btn_layout)

        btn_layout2 = QHBoxLayout()

        self.grade_btn = QPushButton("Grade")
        self.grade_btn.setToolTip("Run the rubric against the loaded student circuit")
        self.grade_btn.setEnabled(False)
        self.grade_btn.clicked.connect(self._on_grade)
        btn_layout2.addWidget(self.grade_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setToolTip("Export grading results as CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_csv)
        btn_layout2.addWidget(self.export_btn)

        outer.addLayout(btn_layout2)

        # --- Status labels ---
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self.student_label = QLabel("Student: (none loaded)")
        status_layout.addWidget(self.student_label)

        self.rubric_label = QLabel("Rubric: (none loaded)")
        status_layout.addWidget(self.rubric_label)

        outer.addWidget(status_group)

        # --- Score display ---
        self.score_label = QLabel("")
        self.score_label.setStyleSheet(theme_manager.stylesheet("score_bold"))
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.score_label)

        # --- Check results list ---
        results_group = QGroupBox("Check Results")
        results_layout = QVBoxLayout(results_group)

        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        self.results_list.currentItemChanged.connect(self._on_check_selected)
        results_layout.addWidget(self.results_list)

        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setStyleSheet(theme_manager.stylesheet("label_padded"))
        results_layout.addWidget(self.feedback_label)

        outer.addWidget(results_group)

    # --- Load operations ---

    def _on_load_student(self):
        """Load a student circuit file and display it on the canvas."""
        from controllers.file_controller import validate_circuit_data

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Student Circuit",
            "",
            "Circuit Files (*.json);;Template Files (*.spice-template);;All Files (*)",
        )
        if not filename:
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)

            # Handle template files (extract starter_circuit)
            if "template_version" in data and "starter_circuit" in data:
                if data["starter_circuit"] is not None:
                    validate_circuit_data(data["starter_circuit"])
                    self._student_circuit = CircuitModel.from_dict(data["starter_circuit"])
                else:
                    self._student_circuit = CircuitModel()
            else:
                validate_circuit_data(data)
                self._student_circuit = CircuitModel.from_dict(data)

            # Snapshot the current (reference) circuit before replacing the canvas
            if self._reference_circuit is None:
                self._reference_circuit = CircuitModel.from_dict(self._model.to_dict())

            # Display student circuit on canvas so highlights target the correct components
            parent = self.parent()
            if parent is not None and hasattr(parent, "file_ctrl"):
                parent.file_ctrl.load_from_model(self._student_circuit)

            self._student_file = Path(filename).name
            self.student_label.setText(f"Student: {self._student_file}")
            self._update_grade_button()
        except (json.JSONDecodeError, ValueError, OSError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load student file:\n{e}")

    def _on_load_rubric(self):
        """Load a grading rubric."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Grading Rubric",
            "",
            "Rubric Files (*.spice-rubric);;All Files (*)",
        )
        if not filename:
            return

        try:
            from grading.rubric import load_rubric

            self._rubric = load_rubric(filename)
            self.rubric_label.setText(f"Rubric: {self._rubric.title}")
            self._update_grade_button()
        except (json.JSONDecodeError, ValueError, OSError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load rubric:\n{e}")

    def _update_grade_button(self):
        """Enable grade button when both student and rubric are loaded."""
        self.grade_btn.setEnabled(self._student_circuit is not None and self._rubric is not None)

    # --- Grading ---

    def _on_grade(self):
        """Run the grading engine and display results."""
        if self._student_circuit is None or self._rubric is None:
            return

        if self._grader is None:
            from grading.grader import CircuitGrader

            self._grader = CircuitGrader()

        reference = self._reference_circuit if self._reference_circuit is not None else self._model
        self._result = self._grader.grade(
            student_circuit=self._student_circuit,
            rubric=self._rubric,
            reference_circuit=reference,
            student_file=self._student_file,
        )

        self._display_results(self._result)
        self.export_btn.setEnabled(True)

    def _display_results(self, result: GradingResult):
        """Populate the results list with check outcomes."""
        self.results_list.clear()
        self._clear_highlights()

        # Score header
        pct = result.percentage
        self.score_label.setText(f"{result.earned_points}/{result.total_points} — {pct:.0f}%")
        if pct >= 90:
            self.score_label.setStyleSheet(theme_manager.stylesheet("score_success"))
        elif pct >= 70:
            self.score_label.setStyleSheet(theme_manager.stylesheet("score_warning"))
        else:
            self.score_label.setStyleSheet(theme_manager.stylesheet("score_error"))

        # Check results
        for cr in result.check_results:
            if cr.passed:
                icon = "\u2714"  # checkmark
                text = f"{icon} {cr.check_id}: +{cr.points_earned}/{cr.points_possible}"
            else:
                icon = "\u2718"  # X mark
                text = f"{icon} {cr.check_id}: 0/{cr.points_possible}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, cr)

            if cr.passed:
                item.setForeground(QColor("green"))
            else:
                item.setForeground(QColor("red"))

            self.results_list.addItem(item)

        self.feedback_label.setText("Click a check to see feedback")

    def _on_check_selected(self, current, previous):
        """Show feedback for the selected check and highlight affected components."""
        self._clear_highlights()

        if current is None:
            self.feedback_label.setText("")
            return

        cr = current.data(Qt.ItemDataRole.UserRole)
        if cr is None:
            return

        self.feedback_label.setText(cr.feedback)

        # Highlight components associated with this check
        comp_ids = extract_component_ids(cr.check_id)
        canvas = self._get_canvas()
        if canvas is None:
            return

        state = "passed" if cr.passed else "failed"
        for comp_id in comp_ids:
            comp_item = canvas.components.get(comp_id)
            if comp_item is not None:
                comp_item.set_grading_state(state, cr.feedback)
                self._highlighted_components.append(comp_id)

    # --- Highlight management ---

    def set_canvas(self, canvas):
        """Inject the circuit canvas reference for highlight management."""
        self._canvas = canvas

    def _get_canvas(self):
        """Return the injected circuit canvas, or None."""
        return self._canvas

    def _clear_highlights(self):
        """Remove all grading overlays from canvas components."""
        canvas = self._get_canvas()
        if canvas is not None:
            for comp_id in self._highlighted_components:
                comp_item = canvas.components.get(comp_id)
                if comp_item is not None:
                    comp_item.clear_grading_state()
        self._highlighted_components.clear()

    # --- Export ---

    def _on_export_csv(self):
        """Export grading results as CSV."""
        if self._result is None:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Grading Results",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not filename:
            return

        try:
            self._export_result_csv(self._result, filename)
            QMessageBox.information(self, "Exported", f"Results saved to {filename}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    @staticmethod
    def _export_result_csv(result: GradingResult, filepath: str):
        """Write a single student's grading result to CSV."""
        from grading.grade_exporter import export_single_result_csv

        export_single_result_csv(result, filepath)

    # --- Public API ---

    def clear_results(self):
        """Clear all grading results, overlays, and reset the panel."""
        self._clear_highlights()

        # Restore the reference (instructor) circuit on the canvas
        if self._reference_circuit is not None:
            parent = self.parent()
            if parent is not None and hasattr(parent, "file_ctrl"):
                parent.file_ctrl.load_from_model(self._reference_circuit)
            self._reference_circuit = None

        self._result = None
        self._student_circuit = None
        self._student_file = ""
        self._rubric = None
        self.results_list.clear()
        self.score_label.setText("")
        self.feedback_label.setText("")
        self.student_label.setText("Student: (none loaded)")
        self.rubric_label.setText("Rubric: (none loaded)")
        self.grade_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

    def get_result(self) -> Optional[GradingResult]:
        """Return the current grading result, or None."""
        return self._result
