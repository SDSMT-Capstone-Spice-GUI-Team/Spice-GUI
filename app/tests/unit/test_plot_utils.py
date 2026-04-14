"""
Unit tests for GUI.plot_utils — shared matplotlib helpers.
"""

import numpy as np
from GUI.plot_utils import _LEGEND_BEST_MAX_POINTS, safe_legend
from matplotlib.figure import Figure


def _make_axes():
    """Return a fresh (Figure, Axes) pair."""
    fig = Figure(figsize=(4, 3))
    ax = fig.add_subplot(111)
    return fig, ax


class TestSafeLegend:
    """Tests for safe_legend() — threshold-based loc fallback."""

    def test_small_dataset_uses_best(self):
        """When total points are below threshold, loc='best' is preserved."""
        _, ax = _make_axes()
        x = np.linspace(0, 1, 100)
        ax.plot(x, x, label="line")
        legend = safe_legend(ax, fontsize="small")
        # matplotlib stores loc as an int code; "best" == 0
        assert legend._loc == 0

    def test_large_dataset_uses_upper_right(self):
        """When total points exceed threshold, loc falls back to 'upper right'."""
        _, ax = _make_axes()
        x = np.linspace(0, 1, _LEGEND_BEST_MAX_POINTS + 1)
        ax.plot(x, x, label="big")
        legend = safe_legend(ax, fontsize="small")
        # "upper right" == 1
        assert legend._loc == 1

    def test_explicit_fixed_loc_is_kept(self):
        """An explicit non-best loc should pass through unchanged."""
        _, ax = _make_axes()
        x = np.linspace(0, 1, _LEGEND_BEST_MAX_POINTS + 1)
        ax.plot(x, x, label="big")
        legend = safe_legend(ax, loc="lower left", fontsize="small")
        # "lower left" == 3
        assert legend._loc == 3

    def test_multiple_lines_summed(self):
        """Total points is the sum across all lines on the axes."""
        _, ax = _make_axes()
        n = _LEGEND_BEST_MAX_POINTS // 2 + 1
        ax.plot(range(n), range(n), label="a")
        ax.plot(range(n), range(n), label="b")
        # Combined > threshold
        legend = safe_legend(ax)
        assert legend._loc == 1  # "upper right"

    def test_no_lines_uses_best(self):
        """With zero data points, loc='best' is fine."""
        _, ax = _make_axes()
        legend = safe_legend(ax)
        assert legend._loc == 0

    def test_kwargs_forwarded(self):
        """Extra kwargs (fontsize, ncol, etc.) are forwarded to ax.legend()."""
        _, ax = _make_axes()
        ax.plot([0, 1], [0, 1], label="line")
        legend = safe_legend(ax, fontsize="x-small", ncol=2)
        assert legend._ncols == 2
