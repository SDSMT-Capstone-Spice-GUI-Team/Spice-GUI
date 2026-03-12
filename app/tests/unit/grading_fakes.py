"""Shared lightweight test doubles for grading-related tests.

Provides fake dataclasses that mirror the grading result types without
importing the full grading chain.  Used by test_score_histogram.py,
test_feedback_exporter.py, and test_check_analytics.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeCheckResult:
    check_id: str = "check_1"
    passed: bool = True
    points_earned: int = 10
    points_possible: int = 10
    feedback: str = ""


@dataclass
class FakeGradingResult:
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
class FakeBatchResult:
    rubric_title: str = "Test"
    total_students: int = 0
    successful: int = 0
    failed: int = 0
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def mean_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.percentage for r in self.results) / len(self.results)

    @property
    def median_score(self) -> float:
        scores = sorted(r.percentage for r in self.results)
        n = len(scores)
        if n == 0:
            return 0.0
        mid = n // 2
        return (scores[mid - 1] + scores[mid]) / 2 if n % 2 == 0 else scores[mid]

    @property
    def min_score(self) -> float:
        if not self.results:
            return 0.0
        return min(r.percentage for r in self.results)

    @property
    def max_score(self) -> float:
        if not self.results:
            return 0.0
        return max(r.percentage for r in self.results)
