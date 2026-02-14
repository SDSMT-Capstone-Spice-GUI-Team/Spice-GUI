"""Batch grading dialog for processing folders of student submissions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QFileDialog, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QProgressBar,
                             QPushButton, QVBoxLayout)

if TYPE_CHECKING:
    from grading.batch_grader import BatchGradingResult

logger = logging.getLogger(__name__)


class BatchGradingDialog(QDialog):
    """Dialog for batch grading a folder of student submissions."""

    def __init__(self, reference_circuit=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Grade Student Submissions")
        self.setMinimumWidth(500)
        self._reference_circuit = reference_circuit
        self._rubric = None
        self._batch_result: Optional[BatchGradingResult] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Folder selection
        folder_group = QGroupBox("Student Submissions")
        folder_layout = QHBoxLayout(folder_group)
        self.folder_path = QLineEdit()
        self.folder_path.setPlaceholderText("Select folder containing student files...")
        self.folder_path.setReadOnly(True)
        folder_layout.addWidget(self.folder_path)
        self.browse_folder_btn = QPushButton("Browse...")
        self.browse_folder_btn.clicked.connect(self._on_browse_folder)
        folder_layout.addWidget(self.browse_folder_btn)
        layout.addWidget(folder_group)

        # Rubric selection
        rubric_group = QGroupBox("Grading Rubric")
        rubric_layout = QHBoxLayout(rubric_group)
        self.rubric_path = QLineEdit()
        self.rubric_path.setPlaceholderText("Select rubric file (.spice-rubric)...")
        self.rubric_path.setReadOnly(True)
        rubric_layout.addWidget(self.rubric_path)
        self.browse_rubric_btn = QPushButton("Browse...")
        self.browse_rubric_btn.clicked.connect(self._on_browse_rubric)
        rubric_layout.addWidget(self.browse_rubric_btn)
        layout.addWidget(rubric_group)

        # Reference circuit info
        if self._reference_circuit is not None:
            ref_label = QLabel("Reference circuit: current canvas circuit")
            ref_label.setStyleSheet("color: green;")
            layout.addWidget(ref_label)

        # Grade button
        btn_layout = QHBoxLayout()
        self.grade_btn = QPushButton("Grade All")
        self.grade_btn.setEnabled(False)
        self.grade_btn.clicked.connect(self._on_grade)
        btn_layout.addWidget(self.grade_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)

        self.save_histogram_btn = QPushButton("Save Histogram")
        self.save_histogram_btn.setEnabled(False)
        self.save_histogram_btn.clicked.connect(self._on_save_histogram)
        btn_layout.addWidget(self.save_histogram_btn)
        layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)

        # Results summary
        self.results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(self.results_group)
        self.results_label = QLabel("No results yet")
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        results_layout.addWidget(self.results_label)
        self.results_group.setVisible(False)
        layout.addWidget(self.results_group)

        # Histogram placeholder (populated after grading)
        self._histogram_canvas = None

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Student Submissions Folder"
        )
        if folder:
            self.folder_path.setText(folder)
            self._update_grade_button()

    def _on_browse_rubric(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Grading Rubric",
            "",
            "Rubric Files (*.spice-rubric);;All Files (*)",
        )
        if filename:
            try:
                from grading.rubric import load_rubric

                self._rubric = load_rubric(filename)
                self.rubric_path.setText(filename)
                self._update_grade_button()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load rubric:\n{e}")

    def _update_grade_button(self):
        self.grade_btn.setEnabled(
            bool(self.folder_path.text()) and self._rubric is not None
        )

    def _on_grade(self):
        from grading.batch_grader import BatchGrader

        folder = self.folder_path.text()
        if not folder or self._rubric is None:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.grade_btn.setEnabled(False)

        grader = BatchGrader()

        def progress_callback(current, total, filename):
            if total > 0:
                self.progress_bar.setMaximum(total)
                self.progress_bar.setValue(current)
            self.progress_label.setText(f"Grading: {filename}")

        self._batch_result = grader.grade_folder(
            folder_path=folder,
            rubric=self._rubric,
            reference_circuit=self._reference_circuit,
            progress_callback=progress_callback,
        )

        self._display_results(self._batch_result)
        self.grade_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.save_histogram_btn.setEnabled(bool(self._batch_result.results))
        self.progress_label.setText("Grading complete")

    def _display_results(self, result: BatchGradingResult):
        self.results_group.setVisible(True)

        lines = [
            f"Total students: {result.total_students}",
            f"Successfully graded: {result.successful}",
            f"Failed: {result.failed}",
        ]
        if result.results:
            lines.extend(
                [
                    "",
                    f"Mean score: {result.mean_score:.1f}%",
                    f"Median score: {result.median_score:.1f}%",
                    f"Min score: {result.min_score:.1f}%",
                    f"Max score: {result.max_score:.1f}%",
                ]
            )
        if result.errors:
            lines.append("")
            lines.append(f"Errors ({len(result.errors)}):")
            for filename, error in result.errors[:5]:
                lines.append(f"  {filename}: {error}")
            if len(result.errors) > 5:
                lines.append(f"  ... and {len(result.errors) - 5} more")

        self.results_label.setText("\n".join(lines))

        # Show histogram if there are results
        if result.results:
            self._show_histogram(result)

    def _show_histogram(self, result: BatchGradingResult):
        """Embed a matplotlib histogram in the results group."""
        try:
            from grading.histogram import create_histogram_figure
            from matplotlib.backends.backend_qtagg import \
                FigureCanvasQTAgg as FigureCanvas
        except ImportError:
            logger.warning("matplotlib not available for histogram")
            return

        # Remove previous histogram canvas if re-grading
        if self._histogram_canvas is not None:
            self.results_group.layout().removeWidget(self._histogram_canvas)
            self._histogram_canvas.deleteLater()
            self._histogram_canvas = None

        fig = create_histogram_figure(result)
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(250)
        self.results_group.layout().addWidget(canvas)
        self._histogram_canvas = canvas

        # Resize dialog to fit histogram
        self.setMinimumWidth(600)

    def _on_save_histogram(self):
        """Save the histogram as a PNG file."""
        if self._batch_result is None or not self._batch_result.results:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Histogram",
            "",
            "PNG Images (*.png);;All Files (*)",
        )
        if not filename:
            return

        try:
            from grading.histogram import save_histogram_png

            save_histogram_png(self._batch_result, filename)
            QMessageBox.information(self, "Saved", f"Histogram saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save histogram:\n{e}")

    def _on_export(self):
        if self._batch_result is None:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Gradebook CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not filename:
            return

        try:
            from grading.grade_exporter import export_gradebook_csv

            export_gradebook_csv(self._batch_result, filename)
            QMessageBox.information(self, "Exported", f"Gradebook saved to {filename}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def get_result(self) -> Optional[BatchGradingResult]:
        return self._batch_result
