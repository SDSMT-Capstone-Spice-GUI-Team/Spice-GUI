"""Tests for score distribution histogram generation.

Covers:
- compute_score_bins bin calculation logic
- create_histogram_figure produces a matplotlib Figure
- save_histogram_png writes a file
- BatchGradingDialog histogram integration (structural)
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from grading.histogram import compute_score_bins

# ---------------------------------------------------------------------------
# Lightweight stand-in so we don't need to import the full grading chain
# ---------------------------------------------------------------------------


@dataclass
class _FakeGradingResult:
    percentage: float = 0.0


@dataclass
class _FakeBatchResult:
    results: list = field(default_factory=list)
    total_students: int = 0
    successful: int = 0
    failed: int = 0
    rubric_title: str = "Test"

    @property
    def mean_score(self):
        if not self.results:
            return 0.0
        return sum(r.percentage for r in self.results) / len(self.results)


# ---------------------------------------------------------------------------
# compute_score_bins
# ---------------------------------------------------------------------------


class TestComputeScoreBins:
    """Tests for the pure-Python bin computation."""

    def test_empty_results(self):
        result = _FakeBatchResult()
        labels, counts = compute_score_bins(result)
        assert len(labels) == 10
        assert all(c == 0 for c in counts)

    def test_all_perfect_scores(self):
        result = _FakeBatchResult(results=[_FakeGradingResult(100.0) for _ in range(5)])
        labels, counts = compute_score_bins(result)
        # 100% should go into the last bin (90-100%)
        assert counts[-1] == 5
        assert sum(counts) == 5

    def test_all_zero_scores(self):
        result = _FakeBatchResult(results=[_FakeGradingResult(0.0) for _ in range(3)])
        labels, counts = compute_score_bins(result)
        assert counts[0] == 3
        assert sum(counts) == 3

    def test_spread_across_bins(self):
        scores = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
        result = _FakeBatchResult(results=[_FakeGradingResult(s) for s in scores])
        labels, counts = compute_score_bins(result)
        # Each bin should have exactly 1 student
        assert counts == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

    def test_boundary_values(self):
        """Test bin boundaries: 10 goes into 10-20%, 20 into 20-30%, etc."""
        result = _FakeBatchResult(
            results=[
                _FakeGradingResult(0.0),
                _FakeGradingResult(10.0),
                _FakeGradingResult(50.0),
                _FakeGradingResult(90.0),
                _FakeGradingResult(100.0),
            ]
        )
        labels, counts = compute_score_bins(result)
        assert counts[0] == 1  # 0%
        assert counts[1] == 1  # 10%
        assert counts[5] == 1  # 50%
        assert counts[9] == 2  # 90% and 100%

    def test_custom_num_bins(self):
        result = _FakeBatchResult(results=[_FakeGradingResult(50.0)])
        labels, counts = compute_score_bins(result, num_bins=5)
        assert len(labels) == 5
        assert len(counts) == 5
        # 50% in 5 bins of 20% each -> bin 2 (40-60%)
        assert counts[2] == 1

    def test_label_format(self):
        result = _FakeBatchResult()
        labels, _ = compute_score_bins(result)
        assert labels[0] == "0-10%"
        assert labels[4] == "40-50%"
        assert labels[9] == "90-100%"

    def test_clamps_negative_scores(self):
        result = _FakeBatchResult(results=[_FakeGradingResult(-5.0)])
        labels, counts = compute_score_bins(result)
        assert counts[0] == 1

    def test_clamps_over_100(self):
        result = _FakeBatchResult(results=[_FakeGradingResult(110.0)])
        labels, counts = compute_score_bins(result)
        assert counts[9] == 1

    def test_realistic_class_distribution(self):
        """Simulate a typical class with various scores."""
        scores = [42, 55, 67, 72, 75, 78, 80, 82, 85, 88, 90, 91, 95, 98, 100]
        result = _FakeBatchResult(results=[_FakeGradingResult(s) for s in scores])
        labels, counts = compute_score_bins(result)
        assert sum(counts) == 15
        # Check some bins
        assert counts[4] == 1  # 42
        assert counts[5] == 1  # 55
        assert counts[9] == 5  # 90, 91, 95, 98, 100


# ---------------------------------------------------------------------------
# create_histogram_figure (requires matplotlib)
# ---------------------------------------------------------------------------


class TestCreateHistogramFigure:
    """Tests for matplotlib figure generation."""

    def test_returns_figure(self):
        try:
            from grading.histogram import create_histogram_figure
        except ImportError:
            pytest.skip("matplotlib not available")

        result = _FakeBatchResult(
            results=[_FakeGradingResult(s) for s in [50, 60, 70, 80, 90]]
        )
        fig = create_histogram_figure(result)
        assert fig is not None
        # Should have one axes
        assert len(fig.axes) == 1

    def test_figure_has_correct_title(self):
        try:
            from grading.histogram import create_histogram_figure
        except ImportError:
            pytest.skip("matplotlib not available")

        result = _FakeBatchResult(results=[_FakeGradingResult(75.0)])
        fig = create_histogram_figure(result)
        ax = fig.axes[0]
        assert ax.get_title() == "Score Distribution"

    def test_figure_bar_count_matches_bins(self):
        try:
            from grading.histogram import create_histogram_figure
        except ImportError:
            pytest.skip("matplotlib not available")

        result = _FakeBatchResult(results=[_FakeGradingResult(50.0)])
        fig = create_histogram_figure(result, num_bins=10)
        ax = fig.axes[0]
        # Should have 10 bar patches
        assert len(ax.patches) == 10


# ---------------------------------------------------------------------------
# save_histogram_png
# ---------------------------------------------------------------------------


class TestSaveHistogramPng:
    """Tests for saving histogram to PNG file."""

    def test_saves_file(self):
        try:
            from grading.histogram import save_histogram_png
        except ImportError:
            pytest.skip("matplotlib not available")

        result = _FakeBatchResult(results=[_FakeGradingResult(s) for s in [50, 60, 70]])
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            filepath = Path(f.name)
        try:
            save_histogram_png(result, str(filepath))
            assert filepath.exists()
            assert filepath.stat().st_size > 0
        finally:
            filepath.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# BatchGradingDialog integration (structural)
# ---------------------------------------------------------------------------


class TestBatchGradingDialogHistogram:
    """Structural tests for histogram integration in the dialog."""

    def test_dialog_has_histogram_canvas_attr(self):
        """Verify the dialog stores a histogram canvas reference."""
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "_histogram_canvas" in text

    def test_dialog_has_show_histogram_method(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "def _show_histogram" in text

    def test_dialog_has_save_histogram_button(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "save_histogram_btn" in text
        assert "Save Histogram" in text

    def test_display_results_calls_show_histogram(self):
        source = Path(__file__).parents[2] / "GUI" / "batch_grading_dialog.py"
        text = source.read_text()
        assert "_show_histogram" in text
