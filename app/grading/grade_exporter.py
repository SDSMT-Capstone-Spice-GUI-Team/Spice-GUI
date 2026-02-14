"""CSV gradebook export for batch grading results.

Produces a spreadsheet-ready CSV with one row per student and columns
for each rubric check.

No Qt dependencies — pure Python module.
"""

import csv
from pathlib import Path

from grading.batch_grader import BatchGradingResult


def export_gradebook_csv(result: BatchGradingResult, filepath: str) -> None:
    """Export batch grading results as a CSV gradebook.

    Format:
        Student File, Total Score, Percentage, check_1 (Npts), check_2 (Npts), ...

    Args:
        result: The batch grading result to export.
        filepath: Output CSV file path.
    """
    filepath = Path(filepath)

    if not result.results:
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["No results to export"])
        return

    # Build header from first result's check IDs
    first = result.results[0]
    check_headers = [
        f"{cr.check_id} ({cr.points_possible}pts)" for cr in first.check_results
    ]

    header = ["Student File", "Total Score", "Percentage"] + check_headers

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for gr in result.results:
            row = [
                gr.student_file,
                f"{gr.earned_points}/{gr.total_points}",
                f"{gr.percentage:.1f}%",
            ]
            for cr in gr.check_results:
                row.append(cr.points_earned)
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

    # Append per-check analytics
    if result.results:
        from grading.check_analytics import compute_check_analytics

        analytics = compute_check_analytics(result)
        if analytics:
            with open(filepath, "a", newline="") as f:
                writer = csv.writer(f)
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

    # Append errors if any
    if result.errors:
        with open(filepath, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([])
            writer.writerow(["Errors"])
            writer.writerow(["Filename", "Error"])
            for filename, error in result.errors:
                writer.writerow([filename, error])
