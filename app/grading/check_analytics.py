"""Per-check analytics for batch grading results.

Computes pass/fail rates per rubric check across all student
submissions to identify common mistakes.

No Qt dependencies - pure Python module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grading.batch_grader import BatchGradingResult


@dataclass
class CheckAnalytics:
    """Analytics for a single rubric check across all students."""

    check_id: str
    pass_count: int
    fail_count: int
    total: int

    @property
    def pass_rate(self) -> float:
        """Pass rate as a percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return (self.pass_count / self.total) * 100.0


def compute_check_analytics(result: BatchGradingResult) -> list[CheckAnalytics]:
    """Compute per-check pass/fail analytics from batch grading results.

    Args:
        result: Batch grading result containing individual GradingResults.

    Returns:
        List of CheckAnalytics sorted by pass rate (lowest first) to
        surface the checks students struggled with most.
    """
    if not result.results:
        return []

    # Collect stats per check_id
    stats: dict[str, dict[str, int]] = {}

    for gr in result.results:
        for cr in gr.check_results:
            if cr.check_id not in stats:
                stats[cr.check_id] = {"pass": 0, "fail": 0}
            if cr.passed:
                stats[cr.check_id]["pass"] += 1
            else:
                stats[cr.check_id]["fail"] += 1

    analytics = []
    for check_id, counts in stats.items():
        total = counts["pass"] + counts["fail"]
        analytics.append(
            CheckAnalytics(
                check_id=check_id,
                pass_count=counts["pass"],
                fail_count=counts["fail"],
                total=total,
            )
        )

    # Sort by pass rate ascending (lowest first = most problematic)
    analytics.sort(key=lambda a: a.pass_rate)
    return analytics
