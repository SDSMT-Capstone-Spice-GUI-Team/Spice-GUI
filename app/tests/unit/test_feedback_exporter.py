"""Tests for student feedback report export.

Covers:
- HTML report generation for a single student
- Bulk export of reports to a folder
- BatchGradingDialog integration (structural)
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from grading.feedback_exporter import (export_student_reports,
                                       generate_student_report_html)

# ---------------------------------------------------------------------------
# Lightweight test doubles
# ---------------------------------------------------------------------------


@dataclass
class _FakeCheckResult:
    check_id: str = "check_1"
    passed: bool = True
    points_earned: int = 10
    points_possible: int = 10
    feedback: str = ""


@dataclass
class _FakeGradingResult:
    student_file: str = "student.json"
    rubric_title: str = "Test Rubric"
    total_points: int = 100
    earned_points: int = 80
    check_results: list = field(default_factory=list)

    @property
    def percentage(self) -> float:
        if self.total_points == 0:
            return 0.0
        return (self.earned_points / self.total_points) * 100.0


@dataclass
class _FakeBatchResult:
    rubric_title: str = "Test"
    total_students: int = 0
    successful: int = 0
    failed: int = 0
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# generate_student_report_html
# ---------------------------------------------------------------------------


class TestGenerateStudentReportHtml:
    def test_basic_report(self):
        result = _FakeGradingResult(
            student_file="alice.json",
            rubric_title="Lab 1",
            total_points=100,
            earned_points=85,
            check_results=[
                _FakeCheckResult(
                    check_id="R1_exists", passed=True, feedback="Found R1"
                ),
                _FakeCheckResult(
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
        result = _FakeGradingResult()
        html = generate_student_report_html(result)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<table>" in html

    def test_pass_fail_classes(self):
        result = _FakeGradingResult(
            check_results=[
                _FakeCheckResult(check_id="c1", passed=True),
                _FakeCheckResult(check_id="c2", passed=False),
            ]
        )
        html = generate_student_report_html(result)
        assert 'class="pass"' in html
        assert 'class="fail"' in html
        assert ">Pass<" in html
        assert ">Fail<" in html

    def test_html_escapes_special_chars(self):
        result = _FakeGradingResult(
            student_file='<script>alert("xss")</script>.json',
            check_results=[
                _FakeCheckResult(
                    check_id="check_1", feedback='Value is <b>"wrong"</b> & bad'
                ),
            ],
        )
        html = generate_student_report_html(result)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "&amp;" in html

    def test_empty_check_results(self):
        result = _FakeGradingResult(check_results=[])
        html = generate_student_report_html(result)
        assert "student.json" in html
        assert "<tbody>" in html

    def test_zero_total_points(self):
        result = _FakeGradingResult(total_points=0, earned_points=0)
        html = generate_student_report_html(result)
        assert "0/0" in html
        assert "0.0%" in html

    def test_empty_feedback(self):
        result = _FakeGradingResult(
            check_results=[_FakeCheckResult(check_id="c1", feedback="")]
        )
        html = generate_student_report_html(result)
        assert "c1" in html


# ---------------------------------------------------------------------------
# export_student_reports
# ---------------------------------------------------------------------------


class TestExportStudentReports:
    def test_creates_files(self):
        results = [
            _FakeGradingResult(
                student_file="alice.json",
                check_results=[_FakeCheckResult(check_id="c1")],
            ),
            _FakeGradingResult(
                student_file="bob.json",
                check_results=[_FakeCheckResult(check_id="c1")],
            ),
        ]
        batch = _FakeBatchResult(results=results)

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
            _FakeGradingResult(
                student_file="charlie.json",
                rubric_title="Final",
                total_points=50,
                earned_points=40,
                check_results=[
                    _FakeCheckResult(check_id="c1", passed=True, feedback="OK"),
                ],
            ),
        ]
        batch = _FakeBatchResult(results=results)

        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_student_reports(batch, tmpdir)
            content = Path(created[0]).read_text(encoding="utf-8")
            assert "charlie.json" in content
            assert "Final" in content
            assert "40/50" in content

    def test_empty_results(self):
        batch = _FakeBatchResult(results=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_student_reports(batch, tmpdir)
            assert created == []

    def test_creates_output_dir(self):
        results = [
            _FakeGradingResult(
                student_file="test.json",
                check_results=[_FakeCheckResult()],
            ),
        ]
        batch = _FakeBatchResult(results=results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "reports" / "subdir"
            created = export_student_reports(batch, str(output_dir))
            assert len(created) == 1
            assert output_dir.exists()

    def test_handles_student_file_with_path(self):
        results = [
            _FakeGradingResult(
                student_file="submissions/student1.json",
                check_results=[_FakeCheckResult()],
            ),
        ]
        batch = _FakeBatchResult(results=results)

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
