"""CSV gradebook export for batch and single-student grading results.

Produces a spreadsheet-ready CSV with one row per student and columns
for each rubric check.

No Qt dependencies — pure Python module.
"""

import csv
import io
import os
import tempfile
from pathlib import Path

from grading.batch_grader import BatchGradingResult
from grading.grader import GradingResult


def export_gradebook_csv(result: BatchGradingResult, filepath: str) -> None:
    """Export batch grading results as a CSV gradebook.

    Format:
        Student File, Total Score, Percentage, check_1 (Npts), check_2 (Npts), ...

    Args:
        result: The batch grading result to export.
        filepath: Output CSV file path.
    """
    filepath = Path(filepath)
    buf = io.StringIO()
    writer = csv.writer(buf)

    if not result.results:
        writer.writerow(["No results to export"])
    else:
        # Collect all unique check IDs across all results (preserving first-seen order)
        check_columns: list[tuple[str, int]] = []  # (check_id, points_possible)
        seen_ids: set[str] = set()
        for gr in result.results:
            for cr in gr.check_results:
                if cr.check_id not in seen_ids:
                    seen_ids.add(cr.check_id)
                    check_columns.append((cr.check_id, cr.points_possible))

        check_headers = [f"{cid} ({pts}pts)" for cid, pts in check_columns]
        check_ids = [cid for cid, _ in check_columns]

        header = ["Student File", "Total Score", "Percentage"] + check_headers
        writer.writerow(header)

        for gr in result.results:
            row = [
                gr.student_file,
                f"{gr.earned_points}/{gr.total_points}",
                f"{gr.percentage:.1f}%",
            ]
            scores_by_id = {cr.check_id: cr.points_earned for cr in gr.check_results}
            for cid in check_ids:
                row.append(scores_by_id.get(cid, ""))
            writer.writerow(row)

        # Summary row
        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerow(["Total Students", result.total_students])
        writer.writerow(["Successfully Graded", result.successful])
        writer.writerow(["Failed", result.failed])
        if result.results:
            writer.writerow(["Mean Score", f"{result.mean_score:.1f}%"])
            writer.writerow(["Median Score", f"{result.median_score:.1f}%"])
            writer.writerow(["Min Score", f"{result.min_score:.1f}%"])
            writer.writerow(["Max Score", f"{result.max_score:.1f}%"])

        # Per-check analytics
        from grading.check_analytics import compute_check_analytics

        analytics = compute_check_analytics(result)
        if analytics:
            writer.writerow([])
            writer.writerow(["Per-Check Analytics (sorted by pass rate)"])
            writer.writerow(["Check ID", "Pass Count", "Fail Count", "Pass Rate"])
            for ca in analytics:
                writer.writerow(
                    [
                        ca.check_id,
                        ca.pass_count,
                        ca.fail_count,
                        f"{ca.pass_rate:.1f}%",
                    ]
                )

    # Errors
    if result.errors:
        writer.writerow([])
        writer.writerow(["Errors"])
        writer.writerow(["Filename", "Error"])
        for filename, error in result.errors:
            writer.writerow([filename, error])

    # Atomic write
    fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="") as f:
            f.write(buf.getvalue())
        os.replace(tmp, filepath)
    except BaseException:
        os.unlink(tmp)
        raise


def export_single_result_csv(result: GradingResult, filepath: str) -> None:
    """Export a single student's grading result to a CSV file.

    Args:
        result: The grading result to export.
        filepath: Output CSV file path.
    """
    filepath = Path(filepath)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Student File", "Rubric", "Score", "Percentage"])
    writer.writerow(
        [
            result.student_file,
            result.rubric_title,
            f"{result.earned_points}/{result.total_points}",
            f"{result.percentage:.1f}%",
        ]
    )
    writer.writerow([])
    writer.writerow(["Check ID", "Passed", "Points Earned", "Points Possible", "Feedback"])
    for cr in result.check_results:
        writer.writerow(
            [
                cr.check_id,
                "Yes" if cr.passed else "No",
                cr.points_earned,
                cr.points_possible,
                cr.feedback,
            ]
        )

    fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="") as f:
            f.write(buf.getvalue())
        os.replace(tmp, filepath)
    except BaseException:
        os.unlink(tmp)
        raise
