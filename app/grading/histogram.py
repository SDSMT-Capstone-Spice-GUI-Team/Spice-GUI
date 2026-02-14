"""Score distribution histogram generation for batch grading results.

Pure Python module — no Qt dependencies. Matplotlib is used only for
figure creation and is imported lazily.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grading.batch_grader import BatchGradingResult


def compute_score_bins(
    result: BatchGradingResult, num_bins: int = 10
) -> tuple[list[str], list[int]]:
    """Compute score distribution bins from batch grading results.

    Args:
        result: Batch grading result containing individual GradingResults.
        num_bins: Number of equal-width bins (default 10 for 10% intervals).

    Returns:
        Tuple of (bin_labels, counts) where bin_labels are strings like
        "0-10%" and counts are the number of students in each bin.
    """
    bin_width = 100.0 / num_bins
    counts = [0] * num_bins
    labels = []

    for i in range(num_bins):
        lo = int(i * bin_width)
        hi = int((i + 1) * bin_width)
        labels.append(f"{lo}-{hi}%")

    for gr in result.results:
        pct = gr.percentage
        # Clamp to [0, 100]
        pct = max(0.0, min(100.0, pct))
        idx = int(pct / bin_width)
        # 100% goes into the last bin
        if idx >= num_bins:
            idx = num_bins - 1
        counts[idx] += 1

    return labels, counts


def create_histogram_figure(result: BatchGradingResult, num_bins: int = 10):
    """Create a matplotlib Figure showing the score distribution histogram.

    Args:
        result: Batch grading result.
        num_bins: Number of bins.

    Returns:
        matplotlib.figure.Figure with the histogram plotted.
    """
    import matplotlib
    import matplotlib.figure as mpl_figure

    labels, counts = compute_score_bins(result, num_bins)

    fig = mpl_figure.Figure(figsize=(6, 3), dpi=100)
    ax = fig.add_subplot(111)

    x_positions = range(len(labels))
    ax.bar(x_positions, counts, color="#4CAF50", edgecolor="#388E3C", width=0.8)

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Score Range")
    ax.set_ylabel("Number of Students")
    ax.set_title("Score Distribution")

    # Integer y-axis ticks
    max_count = max(counts) if counts else 1
    ax.set_ylim(0, max_count + 1)
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))

    fig.tight_layout()
    return fig


def save_histogram_png(
    result: BatchGradingResult, filepath: str, num_bins: int = 10
) -> None:
    """Save score distribution histogram as a PNG image.

    Args:
        result: Batch grading result.
        filepath: Output PNG file path.
        num_bins: Number of bins.
    """
    fig = create_histogram_figure(result, num_bins)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
