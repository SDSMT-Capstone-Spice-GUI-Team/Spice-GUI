"""Batch grading dialog for processing folders of student submissions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from grading.batch_grader import BatchGradingResult
    from grading.rubric import Rubric
    from models.circuit import CircuitModel
    from models.grading_session import GradingSessionData

logger = logging.getLogger(__name__)


class _GradingWorker(QThread):
    """Background thread that runs batch grading without freezing the UI."""

    progress = pyqtSignal(int, int, str)
    finished_grading = pyqtSignal(object)

    def __init__(
        self,
        folder: str,
        rubric: Rubric,
        reference_circuit: Optional[CircuitModel] = None,
    ):
        super().__init__()
        self._folder = folder
        self._rubric = rubric
        self._reference_circuit = reference_circuit

    def run(self):
        from controllers.grading_controller import create_batch_grader

        grader = create_batch_grader()

        def progress_callback(current, total, filename):
            self.progress.emit(current, total, filename)

        result = grader.grade_folder(
            folder_path=self._folder,
            rubric=self._rubric,
            reference_circuit=self._reference_circuit,
            progress_callback=progress_callback,
        )
        self.finished_grading.emit(result)


class BatchGradingDialog(QDialog):
    """Dialog for batch grading a folder of student submissions."""

    def __init__(self, reference_circuit=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Grade Student Submissions")
        self.setMinimumWidth(500)
        self._reference_circuit = reference_circuit
        self._rubric = None
        self._batch_result: Optional[BatchGradingResult] = None
        self._loaded_session: Optional[GradingSessionData] = None
        self._worker: Optional[_GradingWorker] = None
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

        self.export_reports_btn = QPushButton("Export Student Reports...")
        self.export_reports_btn.setEnabled(False)
        self.export_reports_btn.clicked.connect(self._on_export_reports)
        btn_layout.addWidget(self.export_reports_btn)
        self.save_histogram_btn = QPushButton("Save Histogram")
        self.save_histogram_btn.setEnabled(False)
        self.save_histogram_btn.clicked.connect(self._on_save_histogram)
        btn_layout.addWidget(self.save_histogram_btn)
        layout.addLayout(btn_layout)

        # Session persistence buttons
        session_layout = QHBoxLayout()
        self.save_grades_btn = QPushButton("Save Grades...")
        self.save_grades_btn.setToolTip("Save grading results as a .spice-grades session file")
        self.save_grades_btn.setEnabled(False)
        self.save_grades_btn.clicked.connect(self._on_save_grades)
        session_layout.addWidget(self.save_grades_btn)

        self.load_grades_btn = QPushButton("Load Grades...")
        self.load_grades_btn.setToolTip("Load a previous grading session (.spice-grades)")
        self.load_grades_btn.clicked.connect(self._on_load_grades)
        session_layout.addWidget(self.load_grades_btn)
        layout.addLayout(session_layout)

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
        self.comparison_label = QLabel("")
        self.comparison_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.comparison_label.setVisible(False)
        results_layout.addWidget(self.comparison_label)
        self.results_group.setVisible(False)
        layout.addWidget(self.results_group)

        # Per-check analytics table
        self.analytics_group = QGroupBox("Per-Check Analytics (sorted by pass rate)")
        analytics_layout = QVBoxLayout(self.analytics_group)
        self.analytics_table = QTableWidget()
        self.analytics_table.setColumnCount(4)
        self.analytics_table.setHorizontalHeaderLabels(["Check ID", "Pass", "Fail", "Pass Rate"])
        self.analytics_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.analytics_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.analytics_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        analytics_layout.addWidget(self.analytics_table)
        self.analytics_group.setVisible(False)
        layout.addWidget(self.analytics_group)
        # Histogram placeholder (populated after grading)
        self._histogram_canvas = None

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Student Submissions Folder")
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
                from controllers.grading_controller import load_rubric

                self._rubric = load_rubric(filename)
                self.rubric_path.setText(filename)
                self._update_grade_button()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load rubric:\n{e}")

    def _update_grade_button(self):
        self.grade_btn.setEnabled(bool(self.folder_path.text()) and self._rubric is not None)

    def _on_grade(self):
        folder = self.folder_path.text()
        if not folder or self._rubric is None:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.grade_btn.setEnabled(False)

        self._worker = _GradingWorker(folder, self._rubric, self._reference_circuit)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished_grading.connect(self._on_grading_finished)
        self._worker.start()

    def _on_worker_progress(self, current: int, total: int, filename: str):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        self.progress_label.setText(f"Grading: {filename}")

    def _on_grading_finished(self, result):
        self._worker = None
        self._batch_result = result

        self._display_results(self._batch_result)
        self.grade_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.save_grades_btn.setEnabled(True)
        self.export_reports_btn.setEnabled(bool(self._batch_result.results))
        self.save_histogram_btn.setEnabled(bool(self._batch_result.results))
        self.progress_label.setText("Grading complete")

        # Show comparison if a previous session was loaded
        if self._loaded_session is not None:
            self._show_comparison(self._loaded_session)

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

    def _on_save_grades(self):
        """Save current grading results as a .spice-grades session file."""
        if self._batch_result is None:
            return

        from controllers.grading_controller import GRADES_EXTENSION, batch_result_to_session, save_grading_session

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Grading Session",
            "",
            f"Grade Files (*{GRADES_EXTENSION});;All Files (*)",
        )
        if not filename:
            return

        try:
            session = batch_result_to_session(
                self._batch_result,
                rubric_path=self.rubric_path.text(),
                student_folder=self.folder_path.text(),
            )
            save_grading_session(filename, session)
            QMessageBox.information(self, "Saved", f"Grading session saved to {filename}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to save grading session:\n{e}")

    def _on_load_grades(self):
        """Load a previous grading session from a .spice-grades file."""
        from controllers.grading_controller import GRADES_EXTENSION, load_grading_session, session_to_batch_result

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Grading Session",
            "",
            f"Grade Files (*{GRADES_EXTENSION});;All Files (*)",
        )
        if not filename:
            return

        try:
            session = load_grading_session(filename)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load grading session:\n{e}")
            return

        self._loaded_session = session
        loaded_result = session_to_batch_result(session)
        self._batch_result = loaded_result
        self._display_results(loaded_result)
        self.export_btn.setEnabled(True)
        self.save_grades_btn.setEnabled(True)
        self.progress_label.setText(f"Loaded session: {session.rubric_title} ({session.timestamp})")

    def _show_comparison(self, old_session: GradingSessionData):
        """Display a comparison between the loaded session and current results."""
        if self._batch_result is None:
            return

        from controllers.grading_controller import batch_result_to_session, compare_sessions

        new_session = batch_result_to_session(self._batch_result)
        comparisons = compare_sessions(old_session, new_session)

        if not comparisons:
            return

        lines = ["", "Comparison with previous session:"]
        for c in comparisons:
            if c["delta"] is not None:
                sign = "+" if c["delta"] >= 0 else ""
                lines.append(
                    f"  {c['student_file']}: {c['old_pct']:.1f}% -> {c['new_pct']:.1f}% ({sign}{c['delta']:.1f}%)"
                )
            elif c["old_pct"] is None:
                lines.append(f"  {c['student_file']}: (new) {c['new_pct']:.1f}%")
            else:
                lines.append(f"  {c['student_file']}: {c['old_pct']:.1f}% (removed)")

        self.comparison_label.setText("\n".join(lines))
        self.comparison_label.setVisible(True)
        # Show per-check analytics table
        if self._batch_result.results:
            self._display_check_analytics(self._batch_result)

    def _display_check_analytics(self, result: BatchGradingResult):
        """Populate the per-check analytics table."""
        from controllers.grading_controller import compute_check_analytics

        analytics = compute_check_analytics(result)
        if not analytics:
            return

        self.analytics_group.setVisible(True)
        self.analytics_table.setRowCount(len(analytics))

        for row, ca in enumerate(analytics):
            self.analytics_table.setItem(row, 0, QTableWidgetItem(ca.check_id))
            self.analytics_table.setItem(row, 1, QTableWidgetItem(str(ca.pass_count)))
            self.analytics_table.setItem(row, 2, QTableWidgetItem(str(ca.fail_count)))

            rate_item = QTableWidgetItem(f"{ca.pass_rate:.1f}%")
            # Color-code: red for low pass rates, green for high
            if ca.pass_rate < 50:
                rate_item.setForeground(Qt.GlobalColor.red)
            elif ca.pass_rate >= 80:
                rate_item.setForeground(Qt.GlobalColor.darkGreen)
            self.analytics_table.setItem(row, 3, rate_item)
        # Show histogram if there are results
        if result.results:
            self._show_histogram(result)

    def _show_histogram(self, result: BatchGradingResult):
        """Embed a matplotlib histogram in the results group."""
        try:
            from controllers.grading_controller import create_histogram_figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
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
            from controllers.grading_controller import save_histogram_png

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
            from controllers.grading_controller import export_gradebook_csv

            export_gradebook_csv(self._batch_result, filename)
            QMessageBox.information(self, "Exported", f"Gradebook saved to {filename}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def _on_export_reports(self):
        """Export individual HTML feedback reports for each student."""
        if self._batch_result is None or not self._batch_result.results:
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder for Student Reports")
        if not folder:
            return

        try:
            from controllers.grading_controller import export_student_reports

            created = export_student_reports(self._batch_result, folder)
            QMessageBox.information(
                self,
                "Reports Exported",
                f"Created {len(created)} student report(s) in:\n{folder}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export reports:\n{e}")

    def get_result(self) -> Optional[BatchGradingResult]:
        return self._batch_result
