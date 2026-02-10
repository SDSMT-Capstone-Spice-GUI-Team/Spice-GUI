"""
Monte Carlo Results Dialog — Display overlaid simulation runs with
statistical summary and histogram view.
"""

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout
from simulation.monte_carlo import compute_mc_statistics

from .styles import theme_manager

matplotlib.use("QtAgg")


def _apply_mpl_theme(fig):
    """Apply the current application theme colors to a matplotlib figure."""
    is_dark = theme_manager.current_theme.name == "Dark Theme"
    if is_dark:
        bg = "#1E1E1E"
        fg = "#D4D4D4"
        fig.patch.set_facecolor(bg)
        for ax in fig.axes:
            ax.set_facecolor("#2D2D2D")
            ax.tick_params(colors=fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.title.set_color(fg)
            for spine in ax.spines.values():
                spine.set_edgecolor("#555555")


class MonteCarloResultsDialog(QDialog):
    """Dialog displaying Monte Carlo simulation results.

    Shows overlaid traces from all runs, statistical summary, and
    a histogram of a selected output metric.
    """

    analysis_type = "Monte Carlo"

    def __init__(self, mc_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monte Carlo Results")
        self.setMinimumSize(1000, 700)

        self._mc_data = mc_data
        self._base_type = mc_data.get("base_analysis_type", "")

        layout = QVBoxLayout(self)

        # Top: metric selector
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Histogram metric:"))
        self._metric_combo = QComboBox()
        self._metric_combo.currentTextChanged.connect(self._update_histogram)
        top_layout.addWidget(self._metric_combo)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Middle: plots side by side
        plots_layout = QHBoxLayout()

        # Left: overlay plot
        self._overlay_fig = Figure(figsize=(5, 4), dpi=100)
        self._overlay_canvas = FigureCanvas(self._overlay_fig)
        plots_layout.addWidget(self._overlay_canvas, 1)

        # Right: histogram
        self._hist_fig = Figure(figsize=(4, 4), dpi=100)
        self._hist_canvas = FigureCanvas(self._hist_fig)
        plots_layout.addWidget(self._hist_canvas, 1)

        layout.addLayout(plots_layout, 3)

        # Bottom: statistics summary
        self._summary = QTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setMaximumHeight(180)
        layout.addWidget(self._summary, 1)

        # Extract metrics from results
        self._metrics = self._extract_metrics()
        self._populate_combo()
        self._plot_overlay()
        self._update_histogram()

    def _extract_metrics(self):
        """Extract scalar metrics from each successful run result.

        Returns dict[metric_name -> list of float values].
        """
        metrics = {}
        results = self._mc_data.get("results", [])

        for run_result in results:
            if not run_result.success:
                continue
            data = run_result.data
            if data is None:
                continue

            if self._base_type == "DC Operating Point":
                voltages = data.get("node_voltages", {}) if isinstance(data, dict) else data
                if isinstance(voltages, dict):
                    for node, val in voltages.items():
                        key = f"V({node})"
                        metrics.setdefault(key, []).append(val)

            elif self._base_type == "Transient":
                if isinstance(data, list) and data:
                    # Extract final values
                    last_row = data[-1]
                    for key, val in last_row.items():
                        if key.lower() not in ("time", "index"):
                            metric_key = f"V({key}) final"
                            metrics.setdefault(metric_key, []).append(val)

            elif self._base_type == "DC Sweep":
                rows = data.get("data", []) if isinstance(data, dict) else []
                headers = data.get("headers", []) if isinstance(data, dict) else []
                if rows and len(headers) >= 3:
                    # Use mid-point value of each signal
                    mid = len(rows) // 2
                    for col_idx in range(2, len(headers)):
                        metric_key = f"{headers[col_idx]} @mid"
                        metrics.setdefault(metric_key, []).append(rows[mid][col_idx])

            elif self._base_type == "AC Sweep":
                if isinstance(data, dict):
                    freqs = data.get("frequencies", [])
                    mag = data.get("magnitude", {})
                    if freqs and mag:
                        mid = len(freqs) // 2
                        for node, vals in mag.items():
                            if mid < len(vals):
                                metric_key = f"|{node}| @{freqs[mid]:.4g}Hz"
                                metrics.setdefault(metric_key, []).append(vals[mid])

        return metrics

    def _populate_combo(self):
        self._metric_combo.blockSignals(True)
        self._metric_combo.clear()
        for key in sorted(self._metrics.keys()):
            self._metric_combo.addItem(key)
        self._metric_combo.blockSignals(False)

    def _plot_overlay(self):
        """Plot all simulation runs overlaid."""
        ax = self._overlay_fig.add_subplot(111)
        results = self._mc_data.get("results", [])
        cmap = plt.get_cmap("tab10")

        if self._base_type == "DC Operating Point":
            # Bar chart of node voltages for each run
            ok_results = [r for r in results if r.success and r.data]
            if ok_results:
                first_data = ok_results[0].data
                if isinstance(first_data, dict) and "node_voltages" in first_data:
                    nodes = sorted(first_data.get("node_voltages", {}).keys())
                elif isinstance(first_data, dict):
                    nodes = sorted(first_data.keys())
                else:
                    nodes = []
                for i, r in enumerate(ok_results):
                    if isinstance(r.data, dict) and "node_voltages" in r.data:
                        voltages = r.data.get("node_voltages", {})
                    else:
                        voltages = r.data
                    if isinstance(voltages, dict):
                        vals = [voltages.get(n, 0) for n in nodes]
                        ax.scatter(
                            nodes,
                            vals,
                            alpha=0.3,
                            s=10,
                            color=cmap(0),
                            zorder=2,
                        )
                ax.set_ylabel("Voltage (V)")
                ax.set_title("DC OP — All Runs")

        elif self._base_type == "Transient":
            ok_results = [r for r in results if r.success and r.data]
            for i, r in enumerate(ok_results):
                data = r.data
                if not isinstance(data, list) or not data:
                    continue
                time_vals = [row.get("time", 0) for row in data]
                signal_keys = sorted(k for k in data[0].keys() if k.lower() not in ("time", "index"))
                for j, key in enumerate(signal_keys):
                    vals = [row.get(key, 0) for row in data]
                    ax.plot(time_vals, vals, alpha=0.2, color=cmap(j % 10), linewidth=0.5)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Voltage (V)")
            ax.set_title("Transient — All Runs")

        elif self._base_type == "DC Sweep":
            ok_results = [r for r in results if r.success and r.data]
            for i, r in enumerate(ok_results):
                data = r.data
                if not isinstance(data, dict):
                    continue
                rows = data.get("data", [])
                headers = data.get("headers", [])
                if rows and len(headers) >= 3:
                    sweep_vals = [row[1] for row in rows]
                    for col_idx in range(2, len(headers)):
                        vals = [row[col_idx] for row in rows]
                        ax.plot(
                            sweep_vals,
                            vals,
                            alpha=0.2,
                            color=cmap((col_idx - 2) % 10),
                            linewidth=0.5,
                        )
            ax.set_xlabel("Sweep Value")
            ax.set_ylabel("Voltage (V)")
            ax.set_title("DC Sweep — All Runs")

        elif self._base_type == "AC Sweep":
            ok_results = [r for r in results if r.success and r.data]
            for i, r in enumerate(ok_results):
                data = r.data
                if not isinstance(data, dict):
                    continue
                freqs = data.get("frequencies", [])
                mag = data.get("magnitude", {})
                for j, (node, vals) in enumerate(sorted(mag.items())):
                    ax.semilogx(freqs, vals, alpha=0.2, color=cmap(j % 10), linewidth=0.5)
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("Magnitude")
            ax.set_title("AC Sweep — All Runs")

        ax.grid(True, alpha=0.3)
        _apply_mpl_theme(self._overlay_fig)
        self._overlay_fig.tight_layout()
        self._overlay_canvas.draw()

    def _update_histogram(self):
        """Update histogram and statistics for the selected metric."""
        self._hist_fig.clear()
        ax = self._hist_fig.add_subplot(111)

        metric = self._metric_combo.currentText()
        values = self._metrics.get(metric, [])

        if not values:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            self._summary.setPlainText("No metric data available.")
        else:
            ax.hist(values, bins=min(30, max(5, len(values) // 3)), edgecolor="black", alpha=0.7)
            ax.set_xlabel(metric)
            ax.set_ylabel("Count")
            ax.set_title(f"Distribution — {metric}")
            ax.grid(True, alpha=0.3)

            stats = compute_mc_statistics(values)
            lines = [
                f"Metric: {metric}",
                f"Runs:   {stats['count']}",
                f"Mean:   {stats['mean']:.6g}",
                f"Std:    {stats['std']:.6g}",
                f"Min:    {stats['min']:.6g}",
                f"Max:    {stats['max']:.6g}",
                f"Median: {stats['median']:.6g}",
                (
                    f"Spread: {stats['max'] - stats['min']:.6g} "
                    f"({(stats['max'] - stats['min']) / abs(stats['mean']) * 100:.1f}% of mean)"
                    if stats["mean"] != 0
                    else f"Spread: {stats['max'] - stats['min']:.6g}"
                ),
            ]
            self._summary.setPlainText("\n".join(lines))

        _apply_mpl_theme(self._hist_fig)
        self._hist_fig.tight_layout()
        self._hist_canvas.draw()

    def closeEvent(self, event):
        plt.close(self._overlay_fig)
        plt.close(self._hist_fig)
        super().closeEvent(event)
