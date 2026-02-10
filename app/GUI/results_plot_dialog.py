"""
results_plot_dialog.py — Matplotlib-based dialogs for DC Sweep and AC Sweep results.

Uses the same FigureCanvasQTAgg embedding pattern as waveform_dialog.py.
Includes measurement cursors for precise signal measurement.
"""

import logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout

from .measurement_cursors import MeasurementCursors, format_readout_html

matplotlib.use("QtAgg")

logger = logging.getLogger(__name__)


class DCSweepPlotDialog(QDialog):
    """Plot dialog for DC Sweep results (voltage vs. sweep variable)."""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DC Sweep Results")
        self.setMinimumSize(800, 550)

        layout = QVBoxLayout(self)

        fig = Figure(figsize=(8, 5), dpi=100)
        self._canvas = FigureCanvas(fig)
        layout.addWidget(self._canvas)

        ax = fig.add_subplot(111)
        self._plot_dc_sweep(ax, data)
        fig.tight_layout()

        # Cursor controls
        cursor_bar = QHBoxLayout()
        self._cursor_cb = QCheckBox("Enable Cursors")
        self._cursor_cb.setToolTip(
            "Left-click to place Cursor A, right-click for Cursor B"
        )
        cursor_bar.addWidget(self._cursor_cb)
        self._cursor_readout = QLabel("")
        self._cursor_readout.setWordWrap(True)
        cursor_bar.addWidget(self._cursor_readout, 1)
        layout.addLayout(cursor_bar)

        self._cursors = MeasurementCursors(self._canvas, ax)
        self._cursors.set_readout_callback(
            lambda d: self._cursor_readout.setText(
                format_readout_html(d, x_label="Sweep", y_label="Voltage")
            )
        )
        self._cursor_cb.toggled.connect(self._cursors.set_enabled)

    def _plot_dc_sweep(self, ax, data):
        headers = data.get("headers", [])
        rows = data.get("data", [])
        if not rows or len(headers) < 3:
            ax.text(0.5, 0.5, "No sweep data available", ha="center", va="center", transform=ax.transAxes)
            return

        # Column 0 = index, column 1 = sweep value, columns 2+ = node voltages
        sweep_vals = [row[1] for row in rows]
        cmap = plt.get_cmap("tab10")

        for col_idx in range(2, len(headers)):
            label = headers[col_idx]
            values = [row[col_idx] for row in rows]
            ax.plot(sweep_vals, values, label=label, color=cmap((col_idx - 2) % 10))

        ax.set_xlabel(headers[1] if len(headers) > 1 else "Sweep")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("DC Sweep")
        ax.legend(loc="best", fontsize="small")
        ax.grid(True, alpha=0.3)

    def closeEvent(self, event):
        self._cursors.disconnect()
        plt.close(self._canvas.figure)
        super().closeEvent(event)


class ACSweepPlotDialog(QDialog):
    """Bode plot dialog for AC Sweep results (magnitude + phase vs. frequency)."""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AC Sweep Results — Bode Plot")
        self.setMinimumSize(800, 650)

        layout = QVBoxLayout(self)

        fig = Figure(figsize=(8, 6), dpi=100)
        self._canvas = FigureCanvas(fig)
        layout.addWidget(self._canvas)

        ax_mag = fig.add_subplot(211)
        ax_phase = fig.add_subplot(212, sharex=ax_mag)
        self._plot_bode(ax_mag, ax_phase, data)
        fig.tight_layout()

        # Cursor controls — synchronized across both subplots
        cursor_bar = QHBoxLayout()
        self._cursor_cb = QCheckBox("Enable Cursors")
        self._cursor_cb.setToolTip(
            "Left-click to place Cursor A, right-click for Cursor B"
        )
        cursor_bar.addWidget(self._cursor_cb)
        self._cursor_readout = QLabel("")
        self._cursor_readout.setWordWrap(True)
        cursor_bar.addWidget(self._cursor_readout, 1)
        layout.addLayout(cursor_bar)

        self._cursors = MeasurementCursors(self._canvas, [ax_mag, ax_phase])
        self._cursors.set_readout_callback(
            lambda d: self._cursor_readout.setText(
                format_readout_html(d, x_label="Freq", y_label="Mag/Phase")
            )
        )
        self._cursor_cb.toggled.connect(self._cursors.set_enabled)

    def _plot_bode(self, ax_mag, ax_phase, data):
        frequencies = data.get("frequencies", [])
        magnitude = data.get("magnitude", {})
        phase = data.get("phase", {})

        if not frequencies or (not magnitude and not phase):
            ax_mag.text(0.5, 0.5, "No AC data available", ha="center", va="center", transform=ax_mag.transAxes)
            return

        cmap = plt.get_cmap("tab10")

        for i, (node, mag_vals) in enumerate(sorted(magnitude.items())):
            color = cmap(i % 10)
            ax_mag.semilogx(frequencies, mag_vals, label=node, color=color)
            if node in phase:
                ax_phase.semilogx(frequencies, phase[node], label=node, color=color)

        # Plot any phase-only signals not in magnitude
        for i, (node, ph_vals) in enumerate(sorted(phase.items())):
            if node not in magnitude:
                ax_phase.semilogx(frequencies, ph_vals, label=node, color=cmap((len(magnitude) + i) % 10))

        ax_mag.set_ylabel("Magnitude")
        ax_mag.set_title("Bode Plot")
        ax_mag.legend(loc="best", fontsize="small")
        ax_mag.grid(True, which="both", alpha=0.3)

        ax_phase.set_xlabel("Frequency (Hz)")
        ax_phase.set_ylabel("Phase (degrees)")
        ax_phase.legend(loc="best", fontsize="small")
        ax_phase.grid(True, which="both", alpha=0.3)

    def closeEvent(self, event):
        self._cursors.disconnect()
        plt.close(self._canvas.figure)
        super().closeEvent(event)
