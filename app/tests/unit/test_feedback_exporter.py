"""Tests for student feedback report export.

Covers:
- HTML report generation for a single student
- Bulk export of reports to a folder
- BatchGradingDialog integration (structural)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from grading.feedback_exporter import export_student_reports, generate_student_report_html
from tests.unit.grading_fakes import FakeBatchResult, FakeCheckResult, FakeGradingResult

# ---------------------------------------------------------------------------
# generate_student_report_html
# ---------------------------------------------------------------------------


class TestGenerateStudentReportHtml:
    def test_basic_report(self):
        result = FakeGradingResult(
            student_file="alice.json",
            rubric_title="Lab 1",
            total_points=100,
            earned_points=85,
            check_results=[
                FakeCheckResult(check_id="R1_exists", passed=True, feedback="Found R1"),
                FakeCheckResult(
                    check_id="R1_value",
                    passed=False,
                    points_earned=0,
                    feedback="Expected 1k, got 2k",
                ),
            ],
        )
        html = generate_student_report_html(result)
        assert "alice.json" in html
        assert "Lab 1" in html
        assert "85/100" in html
        assert "85.0%" in html
        assert "R1_exists" in html
        assert "R1_value" in html
        assert "Found R1" in html
        assert "Expected 1k, got 2k" in html

    def test_html_structure(self):
        result = FakeGradingResult()
        html = generate_student_report_html(result)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<table>" in html

    def test_pass_fail_classes(self):
        result = FakeGradingResult(
            check_results=[
                FakeCheckResult(check_id="c1", passed=True),
                FakeCheckResult(check_id="c2", passed=False),
            ]
        )
        html = generate_student_report_html(result)
        assert 'class="pass"' in html
        assert 'class="fail"' in html
        assert ">Pass<" in html
        assert ">Fail<" in html

    def test_html_escapes_special_chars(self):
        result = FakeGradingResult(
            student_file='<script>alert("xss")</script>.json',
            check_results=[
                FakeCheckResult(check_id="check_1", feedback='Value is <b>"wrong"</b> & bad'),
            ],
        )
        html = generate_student_report_html(result)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "&amp;" in html

    def test_empty_check_results(self):
        result = FakeGradingResult(check_results=[])
        html = generate_student_report_html(result)
        assert "student.json" in html
        assert "<tbody>" in html

    def test_zero_total_points(self):
        result = FakeGradingResult(total_points=0, earned_points=0)
        html = generate_student_report_html(result)
        assert "0/0" in html
        assert "0.0%" in html

    def test_empty_feedback(self):
        result = FakeGradingResult(check_results=[FakeCheckResult(check_id="c1", feedback="")])
        html = generate_student_report_html(result)
        assert "c1" in html


# ---------------------------------------------------------------------------
# export_student_reports
# ---------------------------------------------------------------------------


class TestExportStudentReports:
    def test_creates_files(self):
        results = [
            FakeGradingResult(
                student_file="alice.json",
                check_results=[FakeCheckResult(check_id="c1")],
            ),
            FakeGradingResult(
                student_file="bob.json",
                check_results=[FakeCheckResult(check_id="c1")],
            ),
        ]
        batch = FakeBatchResult(results=results)

        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_student_reports(batch, tmpdir)
            assert len(created) == 2
            assert Path(created[0]).exists()
            assert Path(created[1]).exists()
            # Check filenames
            names = {Path(f).name for f in created}
            assert "alice_report.html" in names
            assert "bob_report.html" in names

    def test_report_content(self):
        results = [
            FakeGradingResult(
                student_file="charlie.json",
                rubric_title="Final",
                total_points=50,
                earned_points=40,
                check_results=[
                    FakeCheckResult(check_id="c1", passed=True, feedback="OK"),
                ],
            ),
        ]
        batch = FakeBatchResult(results=results)

        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_student_reports(batch, tmpdir)
            content = Path(created[0]).read_text(encoding="utf-8")
            assert "charlie.json" in content
            assert "Final" in content
            assert "40/50" in content

    def test_empty_results(self):
        batch = FakeBatchResult(results=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_student_reports(batch, tmpdir)
            assert created == []

    def test_creates_output_dir(self):
        results = [
            FakeGradingResult(
                student_file="test.json",
                check_results=[FakeCheckResult()],
            ),
        ]
        batch = FakeBatchResult(results=results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "reports" / "subdir"
            created = export_student_reports(batch, str(output_dir))
            assert len(created) == 1
            assert output_dir.exists()

    def test_handles_student_file_with_path(self):
        results = [
            FakeGradingResult(
                student_file="submissions/student1.json",
                check_results=[FakeCheckResult()],
            ),
        ]
        batch = FakeBatchResult(results=results)

        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_student_reports(batch, tmpdir)
            assert "student1_report.html" in Path(created[0]).name


# ---------------------------------------------------------------------------
# BatchGradingDialog integration (structural)
# ---------------------------------------------------------------------------


class TestBatchGradingDialogFeedbackExport:
    def test_dialog_has_export_reports_button(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "export_reports_btn" in text
        assert "Export Student Reports" in text

    def test_dialog_has_export_reports_handler(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "def _on_export_reports" in text

    def test_handler_imports_feedback_exporter(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "feedback_exporter" in text
        assert "export_student_reports" in text
