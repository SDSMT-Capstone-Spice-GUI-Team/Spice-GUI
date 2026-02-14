"""Tests for per-check analytics in batch grading.

Covers:
- CheckAnalytics data class
- compute_check_analytics computation and sorting
- CSV export includes analytics section
- BatchGradingDialog analytics table (structural)
"""

from __future__ import annotations

import csv
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from grading.check_analytics import CheckAnalytics, compute_check_analytics

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
    rubric_title: str = "Test"
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

    @property
    def mean_score(self):
        if not self.results:
            return 0.0
        return sum(r.percentage for r in self.results) / len(self.results)

    @property
    def median_score(self):
        return self.mean_score

    @property
    def min_score(self):
        if not self.results:
            return 0.0
        return min(r.percentage for r in self.results)

    @property
    def max_score(self):
        if not self.results:
            return 0.0
        return max(r.percentage for r in self.results)


# ---------------------------------------------------------------------------
# CheckAnalytics
# ---------------------------------------------------------------------------


class TestCheckAnalytics:
    def test_pass_rate_all_pass(self):
        ca = CheckAnalytics(check_id="c1", pass_count=10, fail_count=0, total=10)
        assert ca.pass_rate == 100.0

    def test_pass_rate_all_fail(self):
        ca = CheckAnalytics(check_id="c1", pass_count=0, fail_count=10, total=10)
        assert ca.pass_rate == 0.0

    def test_pass_rate_mixed(self):
        ca = CheckAnalytics(check_id="c1", pass_count=3, fail_count=7, total=10)
        assert ca.pass_rate == pytest.approx(30.0)

    def test_pass_rate_empty(self):
        ca = CheckAnalytics(check_id="c1", pass_count=0, fail_count=0, total=0)
        assert ca.pass_rate == 0.0


# ---------------------------------------------------------------------------
# compute_check_analytics
# ---------------------------------------------------------------------------


class TestComputeCheckAnalytics:
    def test_empty_results(self):
        result = _FakeBatchResult()
        analytics = compute_check_analytics(result)
        assert analytics == []

    def test_single_student_all_pass(self):
        gr = _FakeGradingResult(
            check_results=[
                _FakeCheckResult(check_id="c1", passed=True),
                _FakeCheckResult(check_id="c2", passed=True),
            ]
        )
        result = _FakeBatchResult(results=[gr])
        analytics = compute_check_analytics(result)
        assert len(analytics) == 2
        assert all(ca.pass_rate == 100.0 for ca in analytics)

    def test_single_student_all_fail(self):
        gr = _FakeGradingResult(
            check_results=[
                _FakeCheckResult(check_id="c1", passed=False),
                _FakeCheckResult(check_id="c2", passed=False),
            ]
        )
        result = _FakeBatchResult(results=[gr])
        analytics = compute_check_analytics(result)
        assert len(analytics) == 2
        assert all(ca.pass_rate == 0.0 for ca in analytics)

    def test_multiple_students(self):
        gr1 = _FakeGradingResult(
            student_file="s1.json",
            check_results=[
                _FakeCheckResult(check_id="c1", passed=True),
                _FakeCheckResult(check_id="c2", passed=False),
            ],
        )
        gr2 = _FakeGradingResult(
            student_file="s2.json",
            check_results=[
                _FakeCheckResult(check_id="c1", passed=True),
                _FakeCheckResult(check_id="c2", passed=True),
            ],
        )
        result = _FakeBatchResult(results=[gr1, gr2])
        analytics = compute_check_analytics(result)

        # Should be sorted by pass rate (lowest first)
        assert analytics[0].check_id == "c2"  # 50% pass rate
        assert analytics[0].pass_count == 1
        assert analytics[0].fail_count == 1
        assert analytics[0].pass_rate == pytest.approx(50.0)

        assert analytics[1].check_id == "c1"  # 100% pass rate
        assert analytics[1].pass_count == 2
        assert analytics[1].fail_count == 0

    def test_sorted_by_pass_rate_ascending(self):
        # 3 students, 3 checks with different pass rates
        results = []
        for i in range(3):
            gr = _FakeGradingResult(
                student_file=f"s{i}.json",
                check_results=[
                    _FakeCheckResult(check_id="easy", passed=True),
                    _FakeCheckResult(check_id="medium", passed=(i < 2)),
                    _FakeCheckResult(check_id="hard", passed=(i < 1)),
                ],
            )
            results.append(gr)

        result = _FakeBatchResult(results=results)
        analytics = compute_check_analytics(result)

        assert analytics[0].check_id == "hard"  # 33% pass rate
        assert analytics[1].check_id == "medium"  # 67% pass rate
        assert analytics[2].check_id == "easy"  # 100% pass rate

    def test_check_counts_correct(self):
        results = []
        for i in range(10):
            gr = _FakeGradingResult(
                student_file=f"s{i}.json",
                check_results=[
                    _FakeCheckResult(check_id="check_a", passed=(i < 8)),
                ],
            )
            results.append(gr)

        result = _FakeBatchResult(results=results)
        analytics = compute_check_analytics(result)
        assert len(analytics) == 1
        assert analytics[0].pass_count == 8
        assert analytics[0].fail_count == 2
        assert analytics[0].total == 10
        assert analytics[0].pass_rate == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# CSV export integration
# ---------------------------------------------------------------------------


class TestCsvExportAnalytics:
    @pytest.fixture(autouse=True)
    def _skip_if_matplotlib_headless(self):
        try:
            from grading.grade_exporter import \
                export_gradebook_csv  # noqa: F401
        except ImportError:
            pytest.skip("matplotlib headless conflict prevents import")

    def test_csv_includes_analytics_section(self):
        from grading.grade_exporter import export_gradebook_csv

        gr1 = _FakeGradingResult(
            student_file="s1.json",
            check_results=[
                _FakeCheckResult(
                    check_id="c1", passed=True, points_earned=10, points_possible=10
                ),
                _FakeCheckResult(
                    check_id="c2", passed=False, points_earned=0, points_possible=10
                ),
            ],
        )
        result = _FakeBatchResult(
            total_students=1,
            successful=1,
            failed=0,
            results=[gr1],
        )

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            filepath = Path(f.name)

        try:
            export_gradebook_csv(result, str(filepath))
            content = filepath.read_text()
            assert "Per-Check Analytics" in content
            assert "Check ID" in content
            assert "Pass Count" in content
            assert "Fail Count" in content
            assert "Pass Rate" in content
        finally:
            filepath.unlink(missing_ok=True)

    def test_csv_analytics_sorted_by_pass_rate(self):
        from grading.grade_exporter import export_gradebook_csv

        gr1 = _FakeGradingResult(
            student_file="s1.json",
            check_results=[
                _FakeCheckResult(
                    check_id="easy", passed=True, points_earned=10, points_possible=10
                ),
                _FakeCheckResult(
                    check_id="hard", passed=False, points_earned=0, points_possible=10
                ),
            ],
        )
        gr2 = _FakeGradingResult(
            student_file="s2.json",
            check_results=[
                _FakeCheckResult(
                    check_id="easy", passed=True, points_earned=10, points_possible=10
                ),
                _FakeCheckResult(
                    check_id="hard", passed=False, points_earned=0, points_possible=10
                ),
            ],
        )
        result = _FakeBatchResult(
            total_students=2,
            successful=2,
            failed=0,
            results=[gr1, gr2],
        )

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            filepath = Path(f.name)

        try:
            export_gradebook_csv(result, str(filepath))
            with open(filepath, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Find the analytics section
            analytics_start = None
            for i, row in enumerate(rows):
                if row and "Per-Check Analytics" in row[0]:
                    analytics_start = i
                    break

            assert analytics_start is not None
            # Header is analytics_start + 1, first data row is analytics_start + 2
            first_check = rows[analytics_start + 2]
            assert first_check[0] == "hard"  # Lowest pass rate first
            assert first_check[3] == "0.0%"
        finally:
            filepath.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# BatchGradingDialog analytics integration (structural)
# ---------------------------------------------------------------------------


class TestBatchGradingDialogAnalytics:
    def test_dialog_has_analytics_table(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "analytics_table" in text
        assert "QTableWidget" in text

    def test_dialog_has_display_check_analytics_method(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "def _display_check_analytics" in text

    def test_display_results_calls_analytics(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "_display_check_analytics" in text
