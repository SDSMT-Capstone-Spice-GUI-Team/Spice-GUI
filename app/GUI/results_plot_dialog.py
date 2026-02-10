"""
results_plot_dialog.py — Matplotlib-based dialogs for DC Sweep and AC Sweep results.

Supports overlaying multiple simulation runs on the same plot with:
- Interactive legend click-to-toggle traces
- Distinct line styles per dataset
- Clear All button to reset
- Interactive measurement cursors for precise signal measurement
"""

import logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout

from .measurement_cursors import CursorReadoutPanel, MeasurementCursors

matplotlib.use("QtAgg")

logger = logging.getLogger(__name__)

# Line styles cycled per dataset for visual distinction
_LINE_STYLES = ["-", "--", "-.", ":"]


class DCSweepPlotDialog(QDialog):
    """Plot dialog for DC Sweep results (voltage vs. sweep variable).

    Supports overlaying multiple datasets from successive simulation runs.
    """

    analysis_type = "DC Sweep"

    def __init__(self, data, parent=None, label=None):
        super().__init__(parent)
        self.setWindowTitle("DC Sweep Results")
        self.setMinimumSize(900, 500)

        self._datasets = []
        self._lines = {}
        self._legend_line_map = {}

        main_layout = QHBoxLayout(self)

        # Left: toolbar + plot
        plot_layout = QVBoxLayout()

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear All")
        clear_btn.setToolTip("Remove all overlaid results and clear the plot")
        clear_btn.clicked.connect(self.clear_all)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)
        plot_layout.addLayout(toolbar)

        self._fig = Figure(figsize=(8, 5), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        plot_layout.addWidget(self._canvas)
        main_layout.addLayout(plot_layout, 3)

        # Right: cursor readout
        self._readout = CursorReadoutPanel()
        main_layout.addWidget(self._readout, 1)

        self._ax = self._fig.add_subplot(111)

        self._canvas.mpl_connect("pick_event", self._on_legend_pick)

        # Cursors (initialized after first plot)
        self._cursors = None

        if data:
            self.add_dataset(data, label)

    def add_dataset(self, data, label=None):
        """Add a new dataset to the overlay plot."""
        if label is None:
            label = f"Run {len(self._datasets) + 1}"
        self._datasets.append((label, data))
        self._replot()

    def _replot(self):
        """Redraw all datasets on the axes."""
        self._ax.clear()
        self._lines.clear()
        self._legend_line_map.clear()

        cmap = plt.get_cmap("tab10")
        sweep_vals_first = []

        for ds_idx, (ds_label, data) in enumerate(self._datasets):
            headers = data.get("headers", [])
            rows = data.get("data", [])
            if not rows or len(headers) < 3:
                continue

            sweep_vals = [row[1] for row in rows]
            if ds_idx == 0:
                sweep_vals_first = sweep_vals
            linestyle = _LINE_STYLES[ds_idx % len(_LINE_STYLES)]
            prefix = f"{ds_label} — " if len(self._datasets) > 1 else ""

            for col_idx in range(2, len(headers)):
                trace_label = f"{prefix}{headers[col_idx]}"
                values = [row[col_idx] for row in rows]
                (line,) = self._ax.plot(
                    sweep_vals,
                    values,
                    label=trace_label,
                    color=cmap((col_idx - 2) % 10),
                    linestyle=linestyle,
                )
                self._lines[trace_label] = line

        if not self._lines:
            self._ax.text(
                0.5,
                0.5,
                "No sweep data available",
                ha="center",
                va="center",
                transform=self._ax.transAxes,
            )
        else:
            first_headers = self._datasets[0][1].get("headers", [])
            self._ax.set_xlabel(first_headers[1] if len(first_headers) > 1 else "Sweep")

        self._ax.set_ylabel("Voltage (V)")
        self._ax.set_title("DC Sweep")
        self._ax.grid(True, alpha=0.3)

        if self._lines:
            legend = self._ax.legend(loc="best", fontsize="small")
            self._setup_legend_toggle(legend)

        self._fig.tight_layout()

        # Update cursors
        if self._cursors is not None:
            self._cursors.remove()
        self._cursors = MeasurementCursors(self._ax, self._canvas, on_cursor_moved=self._on_cursor_moved)
        self._readout.set_cursors(self._cursors)
        if sweep_vals_first:
            self._cursors.set_data(sweep_vals_first)

        self._canvas.draw()

    def _setup_legend_toggle(self, legend):
        """Wire up click-to-toggle on legend entries."""
        self._legend_line_map = {}
        for legend_line, legend_text in zip(legend.get_lines(), legend.get_texts()):
            legend_line.set_picker(5)
            label = legend_text.get_text()
            if label in self._lines:
                self._legend_line_map[legend_line] = (
                    self._lines[label],
                    legend_text,
                )

    def _on_legend_pick(self, event):
        legend_line = event.artist
        if legend_line not in self._legend_line_map:
            return
        orig_line, legend_text = self._legend_line_map[legend_line]
        visible = not orig_line.get_visible()
        orig_line.set_visible(visible)
        legend_line.set_alpha(1.0 if visible else 0.2)
        legend_text.set_alpha(1.0 if visible else 0.2)
        self._canvas.draw()

    def _on_cursor_moved(self, a_x, b_x):
        self._readout.update_readout(self._cursors)

    def clear_all(self):
        """Remove all datasets and clear the plot."""
        self._datasets.clear()
        self._lines.clear()
        self._legend_line_map.clear()
        self._ax.clear()
        self._ax.text(
            0.5,
            0.5,
            "All results cleared",
            ha="center",
            va="center",
            transform=self._ax.transAxes,
        )
        self._ax.set_title("DC Sweep")
        self._fig.tight_layout()
        self._canvas.draw()

    @property
    def dataset_count(self):
        return len(self._datasets)

    def closeEvent(self, event):
        if self._cursors is not None:
            self._cursors.remove()
        plt.close(self._canvas.figure)
        super().closeEvent(event)


class ACSweepPlotDialog(QDialog):
    """Bode plot dialog for AC Sweep results (magnitude + phase vs. frequency).

    Supports overlaying multiple datasets from successive simulation runs.
    """

    analysis_type = "AC Sweep"

    def __init__(self, data, parent=None, label=None):
        super().__init__(parent)
        self.setWindowTitle("AC Sweep Results — Bode Plot")
        self.setMinimumSize(900, 600)

        self._datasets = []
        self._lines = {}
        self._legend_line_map = {}

        main_layout = QHBoxLayout(self)

        # Left: toolbar + plot
        plot_layout = QVBoxLayout()

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear All")
        clear_btn.setToolTip("Remove all overlaid results and clear the plot")
        clear_btn.clicked.connect(self.clear_all)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)
        plot_layout.addLayout(toolbar)

        self._fig = Figure(figsize=(8, 6), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        plot_layout.addWidget(self._canvas)
        main_layout.addLayout(plot_layout, 3)

        # Right: cursor readout
        self._readout = CursorReadoutPanel()
        main_layout.addWidget(self._readout, 1)

        self._ax_mag = self._fig.add_subplot(211)
        self._ax_phase = self._fig.add_subplot(212, sharex=self._ax_mag)

        self._canvas.mpl_connect("pick_event", self._on_legend_pick)

        # Cursors (initialized after first plot)
        self._cursors = None

        if data:
            self.add_dataset(data, label)

    def add_dataset(self, data, label=None):
        """Add a new dataset to the overlay Bode plot."""
        if label is None:
            label = f"Run {len(self._datasets) + 1}"
        self._datasets.append((label, data))
        self._replot()

    def _replot(self):
        """Redraw all datasets on the Bode plot axes."""
        self._ax_mag.clear()
        self._ax_phase.clear()
        self._lines.clear()
        self._legend_line_map.clear()

        cmap = plt.get_cmap("tab10")
        frequencies_first = []

        for ds_idx, (ds_label, data) in enumerate(self._datasets):
            frequencies = data.get("frequencies", [])
            magnitude = data.get("magnitude", {})
            phase = data.get("phase", {})

            if not frequencies or (not magnitude and not phase):
                continue

            if ds_idx == 0:
                frequencies_first = frequencies

            linestyle = _LINE_STYLES[ds_idx % len(_LINE_STYLES)]
            prefix = f"{ds_label} — " if len(self._datasets) > 1 else ""

            for i, (node, mag_vals) in enumerate(sorted(magnitude.items())):
                color = cmap(i % 10)
                trace_label = f"{prefix}{node}"
                (line,) = self._ax_mag.semilogx(
                    frequencies,
                    mag_vals,
                    label=trace_label,
                    color=color,
                    linestyle=linestyle,
                )
                self._lines[trace_label] = line

                if node in phase:
                    phase_label = f"{prefix}{node} (phase)"
                    (pline,) = self._ax_phase.semilogx(
                        frequencies,
                        phase[node],
                        label=trace_label,
                        color=color,
                        linestyle=linestyle,
                    )
                    self._lines[phase_label] = pline

            for i, (node, ph_vals) in enumerate(sorted(phase.items())):
                if node not in magnitude:
                    color = cmap((len(magnitude) + i) % 10)
                    trace_label = f"{prefix}{node}"
                    (pline,) = self._ax_phase.semilogx(
                        frequencies,
                        ph_vals,
                        label=trace_label,
                        color=color,
                        linestyle=linestyle,
                    )
                    self._lines[f"{prefix}{node} (phase-only)"] = pline

        has_data = bool(self._lines)

        if not has_data:
            self._ax_mag.text(
                0.5,
                0.5,
                "No AC data available",
                ha="center",
                va="center",
                transform=self._ax_mag.transAxes,
            )

        self._ax_mag.set_ylabel("Magnitude")
        self._ax_mag.set_title("Bode Plot")
        self._ax_mag.grid(True, which="both", alpha=0.3)

        self._ax_phase.set_xlabel("Frequency (Hz)")
        self._ax_phase.set_ylabel("Phase (degrees)")
        self._ax_phase.grid(True, which="both", alpha=0.3)

        if has_data:
            mag_legend = self._ax_mag.legend(loc="best", fontsize="small")
            self._setup_legend_toggle(mag_legend, self._ax_mag)
            phase_legend = self._ax_phase.legend(loc="best", fontsize="small")
            self._setup_legend_toggle(phase_legend, self._ax_phase)

        self._fig.tight_layout()

        # Update cursors on magnitude axes (shared x with phase)
        if self._cursors is not None:
            self._cursors.remove()
        self._cursors = MeasurementCursors(self._ax_mag, self._canvas, on_cursor_moved=self._on_cursor_moved)
        self._readout.set_cursors(self._cursors)
        if frequencies_first:
            self._cursors.set_data(frequencies_first)

        self._canvas.draw()

    def _setup_legend_toggle(self, legend, ax):
        """Wire up click-to-toggle on legend entries for a given axes."""
        for legend_line, legend_text in zip(legend.get_lines(), legend.get_texts()):
            legend_line.set_picker(5)
            label = legend_text.get_text()
            # Find the matching line on this axes
            for line in ax.get_lines():
                if line.get_label() == label:
                    self._legend_line_map[legend_line] = (line, legend_text)
                    break

    def _on_legend_pick(self, event):
        legend_line = event.artist
        if legend_line not in self._legend_line_map:
            return
        orig_line, legend_text = self._legend_line_map[legend_line]
        visible = not orig_line.get_visible()
        orig_line.set_visible(visible)
        legend_line.set_alpha(1.0 if visible else 0.2)
        legend_text.set_alpha(1.0 if visible else 0.2)
        self._canvas.draw()

    def _on_cursor_moved(self, a_x, b_x):
        self._readout.update_readout(self._cursors)

    def clear_all(self):
        """Remove all datasets and clear the plot."""
        self._datasets.clear()
        self._lines.clear()
        self._legend_line_map.clear()
        self._ax_mag.clear()
        self._ax_phase.clear()
        self._ax_mag.text(
            0.5,
            0.5,
            "All results cleared",
            ha="center",
            va="center",
            transform=self._ax_mag.transAxes,
        )
        self._ax_mag.set_title("Bode Plot")
        self._fig.tight_layout()
        self._canvas.draw()

    @property
    def dataset_count(self):
        return len(self._datasets)

    def closeEvent(self, event):
        if self._cursors is not None:
            self._cursors.remove()
        plt.close(self._canvas.figure)
        super().closeEvent(event)
