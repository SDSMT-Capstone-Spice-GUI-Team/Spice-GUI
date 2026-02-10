"""
results_plot_dialog.py — Matplotlib-based dialogs for DC Sweep and AC Sweep results.

Supports overlaying multiple simulation runs on the same plot.  Each run is
distinguished by line style (solid, dashed, dash-dot, dotted) while nodes
share consistent colors across runs.
"""

import logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

matplotlib.use("QtAgg")

logger = logging.getLogger(__name__)

# Line styles cycle to visually distinguish overlaid simulation runs.
_LINE_STYLES = ["-", "--", "-.", ":"]


class DCSweepPlotDialog(QDialog):
    """Plot dialog for DC Sweep results with multi-run overlay support.

    Accepts one or more result datasets.  Each run is plotted with a
    distinct line style; nodes share colours across runs so the same
    signal is easy to compare.
    """

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DC Sweep Results")
        self.setMinimumSize(900, 550)

        self._results: list[dict] = []
        self._run_counter = 0
        self._checkboxes: list[QCheckBox] = []

        # --- layout: sidebar | plot -----------------------------------------
        main_layout = QHBoxLayout(self)

        # Left sidebar
        sidebar = QVBoxLayout()

        self._toggle_group = QGroupBox("Simulation Runs")
        toggle_inner = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.addStretch()
        scroll.setWidget(self._scroll_content)
        toggle_inner.addWidget(scroll)
        self._toggle_group.setLayout(toggle_inner)
        sidebar.addWidget(self._toggle_group)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        sidebar.addWidget(clear_btn)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(200)
        main_layout.addWidget(sidebar_widget)

        # Right: matplotlib canvas
        self._fig = Figure(figsize=(8, 5), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        self._ax = self._fig.add_subplot(111)
        main_layout.addWidget(self._canvas, 3)

        # Backwards compat: if caller passes data directly, add it as Run 1.
        if data is not None:
            self.add_result(data)

    # -- public API ----------------------------------------------------------

    def add_result(self, data, label=None):
        """Add a new simulation run to the overlay."""
        self._run_counter += 1
        if label is None:
            label = f"Run {self._run_counter}"

        entry = {"label": label, "data": data, "visible": True}
        self._results.append(entry)

        cb = QCheckBox(label)
        cb.setChecked(True)
        idx = len(self._results) - 1
        cb.toggled.connect(lambda state, i=idx: self._set_visible(i, state))
        # Insert before the trailing stretch.
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, cb)
        self._checkboxes.append(cb)

        self._refresh_plot()

    def clear_all(self):
        """Remove all simulation runs and reset the plot."""
        self._results.clear()
        self._checkboxes.clear()
        while self._scroll_layout.count() > 1:  # keep the stretch
            item = self._scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._run_counter = 0
        self._refresh_plot()

    # -- internals -----------------------------------------------------------

    def _set_visible(self, index, visible):
        self._results[index]["visible"] = visible
        self._refresh_plot()

    def _refresh_plot(self):
        self._ax.clear()

        visible = [e for e in self._results if e["visible"]]
        if not visible:
            self._ax.text(
                0.5, 0.5, "No sweep data available",
                ha="center", va="center", transform=self._ax.transAxes,
            )
            self._canvas.draw()
            return

        cmap = plt.get_cmap("tab10")

        # Build a stable colour map: same node name → same colour.
        all_nodes: list[str] = []
        for entry in visible:
            for h in entry["data"].get("headers", [])[2:]:
                if h not in all_nodes:
                    all_nodes.append(h)
        node_colors = {node: cmap(i % 10) for i, node in enumerate(all_nodes)}

        multi = len(self._results) > 1

        for run_idx, entry in enumerate(self._results):
            if not entry["visible"]:
                continue

            data = entry["data"]
            headers = data.get("headers", [])
            rows = data.get("data", [])
            if not rows or len(headers) < 3:
                continue

            linestyle = _LINE_STYLES[run_idx % len(_LINE_STYLES)]
            sweep_vals = [row[1] for row in rows]

            for col_idx in range(2, len(headers)):
                node = headers[col_idx]
                values = [row[col_idx] for row in rows]
                color = node_colors.get(node, cmap(0))
                display = f"{entry['label']}: {node}" if multi else node
                self._ax.plot(
                    sweep_vals, values,
                    label=display, color=color, linestyle=linestyle,
                )

        xlabel = "Sweep"
        if visible and len(visible[0]["data"].get("headers", [])) > 1:
            xlabel = visible[0]["data"]["headers"][1]
        self._ax.set_xlabel(xlabel)
        self._ax.set_ylabel("Voltage (V)")
        self._ax.set_title("DC Sweep")
        if self._ax.get_legend_handles_labels()[1]:
            self._ax.legend(loc="best", fontsize="small")
        self._ax.grid(True, alpha=0.3)
        self._fig.tight_layout()
        self._canvas.draw()

    def closeEvent(self, event):
        plt.close(self._canvas.figure)
        super().closeEvent(event)


class ACSweepPlotDialog(QDialog):
    """Bode plot dialog for AC Sweep results with multi-run overlay support."""

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AC Sweep Results \u2014 Bode Plot")
        self.setMinimumSize(900, 650)

        self._results: list[dict] = []
        self._run_counter = 0
        self._checkboxes: list[QCheckBox] = []

        # --- layout: sidebar | plot -----------------------------------------
        main_layout = QHBoxLayout(self)

        # Left sidebar
        sidebar = QVBoxLayout()

        self._toggle_group = QGroupBox("Simulation Runs")
        toggle_inner = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.addStretch()
        scroll.setWidget(self._scroll_content)
        toggle_inner.addWidget(scroll)
        self._toggle_group.setLayout(toggle_inner)
        sidebar.addWidget(self._toggle_group)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        sidebar.addWidget(clear_btn)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(200)
        main_layout.addWidget(sidebar_widget)

        # Right: matplotlib canvas with two subplots
        self._fig = Figure(figsize=(8, 6), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        self._ax_mag = self._fig.add_subplot(211)
        self._ax_phase = self._fig.add_subplot(212, sharex=self._ax_mag)
        main_layout.addWidget(self._canvas, 3)

        if data is not None:
            self.add_result(data)

    # -- public API ----------------------------------------------------------

    def add_result(self, data, label=None):
        """Add a new simulation run to the overlay."""
        self._run_counter += 1
        if label is None:
            label = f"Run {self._run_counter}"

        entry = {"label": label, "data": data, "visible": True}
        self._results.append(entry)

        cb = QCheckBox(label)
        cb.setChecked(True)
        idx = len(self._results) - 1
        cb.toggled.connect(lambda state, i=idx: self._set_visible(i, state))
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, cb)
        self._checkboxes.append(cb)

        self._refresh_plot()

    def clear_all(self):
        """Remove all simulation runs and reset the plot."""
        self._results.clear()
        self._checkboxes.clear()
        while self._scroll_layout.count() > 1:
            item = self._scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._run_counter = 0
        self._refresh_plot()

    # -- internals -----------------------------------------------------------

    def _set_visible(self, index, visible):
        self._results[index]["visible"] = visible
        self._refresh_plot()

    def _refresh_plot(self):
        self._ax_mag.clear()
        self._ax_phase.clear()

        visible = [e for e in self._results if e["visible"]]
        if not visible:
            self._ax_mag.text(
                0.5, 0.5, "No AC data available",
                ha="center", va="center", transform=self._ax_mag.transAxes,
            )
            self._canvas.draw()
            return

        cmap = plt.get_cmap("tab10")

        # Stable colour map across runs.
        all_nodes: list[str] = []
        for entry in visible:
            for node in sorted(entry["data"].get("magnitude", {}).keys()):
                if node not in all_nodes:
                    all_nodes.append(node)
            for node in sorted(entry["data"].get("phase", {}).keys()):
                if node not in all_nodes:
                    all_nodes.append(node)
        node_colors = {node: cmap(i % 10) for i, node in enumerate(all_nodes)}

        multi = len(self._results) > 1

        for run_idx, entry in enumerate(self._results):
            if not entry["visible"]:
                continue

            data = entry["data"]
            frequencies = data.get("frequencies", [])
            magnitude = data.get("magnitude", {})
            phase = data.get("phase", {})
            if not frequencies or (not magnitude and not phase):
                continue

            linestyle = _LINE_STYLES[run_idx % len(_LINE_STYLES)]

            for node, mag_vals in sorted(magnitude.items()):
                color = node_colors.get(node, cmap(0))
                display = f"{entry['label']}: {node}" if multi else node
                self._ax_mag.semilogx(
                    frequencies, mag_vals,
                    label=display, color=color, linestyle=linestyle,
                )
                if node in phase:
                    self._ax_phase.semilogx(
                        frequencies, phase[node],
                        label=display, color=color, linestyle=linestyle,
                    )

            # Phase-only signals
            for node, ph_vals in sorted(phase.items()):
                if node not in magnitude:
                    color = node_colors.get(node, cmap(0))
                    display = f"{entry['label']}: {node}" if multi else node
                    self._ax_phase.semilogx(
                        frequencies, ph_vals,
                        label=display, color=color, linestyle=linestyle,
                    )

        self._ax_mag.set_ylabel("Magnitude")
        self._ax_mag.set_title("Bode Plot")
        if self._ax_mag.get_legend_handles_labels()[1]:
            self._ax_mag.legend(loc="best", fontsize="small")
        self._ax_mag.grid(True, which="both", alpha=0.3)

        self._ax_phase.set_xlabel("Frequency (Hz)")
        self._ax_phase.set_ylabel("Phase (degrees)")
        if self._ax_phase.get_legend_handles_labels()[1]:
            self._ax_phase.legend(loc="best", fontsize="small")
        self._ax_phase.grid(True, which="both", alpha=0.3)

        self._fig.tight_layout()
        self._canvas.draw()

    def closeEvent(self, event):
        plt.close(self._canvas.figure)
        super().closeEvent(event)
