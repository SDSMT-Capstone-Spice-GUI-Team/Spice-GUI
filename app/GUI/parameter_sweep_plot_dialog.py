"""
Parameter Sweep Plot Dialog — Matplotlib-based overlay of simulation results
from sweeping a component parameter across a range of values.
"""

import logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QDialog, QVBoxLayout

matplotlib.use("QtAgg")

logger = logging.getLogger(__name__)


class ParameterSweepPlotDialog(QDialog):
    """Plot dialog for parameter sweep results.

    Routes to the appropriate plotting method based on the base analysis type.
    """

    def __init__(self, sweep_data, parent=None):
        super().__init__(parent)
        component_id = sweep_data["component_id"]
        base_type = sweep_data["base_analysis_type"]
        self.setWindowTitle(f"Parameter Sweep — {component_id} ({base_type})")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)

        fig = Figure(figsize=(9, 6), dpi=100)
        self._canvas = FigureCanvas(fig)
        layout.addWidget(self._canvas)

        if base_type == "DC Operating Point":
            self._plot_op_sweep(fig, sweep_data)
        elif base_type == "Transient":
            self._plot_transient_sweep(fig, sweep_data)
        elif base_type == "AC Sweep":
            self._plot_ac_sweep(fig, sweep_data)
        elif base_type == "DC Sweep":
            self._plot_dc_sweep(fig, sweep_data)
        else:
            ax = fig.add_subplot(111)
            ax.text(
                0.5, 0.5, f"No plot available for base analysis: {base_type}",
                ha="center", va="center", transform=ax.transAxes,
            )

        fig.tight_layout()

    # ------------------------------------------------------------------
    # DC Operating Point base: X = parameter value, Y = node voltages
    # ------------------------------------------------------------------
    def _plot_op_sweep(self, fig, sweep_data):
        ax = fig.add_subplot(111)

        sweep_values = sweep_data["sweep_values"]
        results = sweep_data["results"]
        component_id = sweep_data["component_id"]

        # Collect all node names
        all_nodes = set()
        for r in results:
            if r.success and r.data:
                all_nodes.update(r.data.keys())

        if not all_nodes:
            ax.text(0.5, 0.5, "No data available",
                    ha="center", va="center", transform=ax.transAxes)
            return

        cmap = plt.get_cmap("tab10")

        for idx, node in enumerate(sorted(all_nodes)):
            vals = []
            voltages = []
            for sv, r in zip(sweep_values, results):
                if r.success and r.data and node in r.data:
                    vals.append(sv)
                    voltages.append(r.data[node])
            if vals:
                ax.plot(vals, voltages, "o-", label=node,
                        color=cmap(idx % 10), markersize=4)

        ax.set_xlabel(f"{component_id} Value")
        ax.set_ylabel("Voltage (V)")
        ax.set_title(f"Parameter Sweep — {component_id}")
        ax.legend(loc="best", fontsize="small")
        ax.grid(True, alpha=0.3)

    # ------------------------------------------------------------------
    # Transient base: overlay time-domain waveforms per sweep step
    # ------------------------------------------------------------------
    def _plot_transient_sweep(self, fig, sweep_data):
        ax = fig.add_subplot(111)

        results = sweep_data["results"]
        sweep_labels = sweep_data.get("sweep_labels", [])
        component_id = sweep_data["component_id"]

        cmap = plt.get_cmap("viridis")
        n = len(results)

        for i, r in enumerate(results):
            if not r.success or not r.data:
                continue

            label = sweep_labels[i] if i < len(sweep_labels) else str(i)
            times = [pt["time"] for pt in r.data]
            nodes = [k for k in r.data[0].keys() if k != "time"]

            color = cmap(i / max(n - 1, 1))

            for node in nodes:
                values = [pt[node] for pt in r.data]
                ax.plot(times, values, color=color,
                        label=f"{node} ({component_id}={label})",
                        alpha=0.8, linewidth=1)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title(f"Transient Parameter Sweep — {component_id}")
        ax.legend(loc="best", fontsize="x-small", ncol=2)
        ax.grid(True, alpha=0.3)

    # ------------------------------------------------------------------
    # AC Sweep base: overlay Bode plots per sweep step
    # ------------------------------------------------------------------
    def _plot_ac_sweep(self, fig, sweep_data):
        ax_mag = fig.add_subplot(211)
        ax_phase = fig.add_subplot(212, sharex=ax_mag)

        results = sweep_data["results"]
        sweep_labels = sweep_data.get("sweep_labels", [])
        component_id = sweep_data["component_id"]

        cmap = plt.get_cmap("viridis")
        n = len(results)

        for i, r in enumerate(results):
            if not r.success or not r.data:
                continue

            label = sweep_labels[i] if i < len(sweep_labels) else str(i)
            freqs = r.data.get("frequencies", [])
            magnitude = r.data.get("magnitude", {})
            phase = r.data.get("phase", {})

            color = cmap(i / max(n - 1, 1))

            for node, mag_vals in sorted(magnitude.items()):
                ax_mag.semilogx(freqs, mag_vals, color=color,
                                label=f"{node} ({component_id}={label})",
                                alpha=0.8)
                if node in phase:
                    ax_phase.semilogx(freqs, phase[node], color=color,
                                      label=f"{node} ({component_id}={label})",
                                      alpha=0.8)

        ax_mag.set_ylabel("Magnitude")
        ax_mag.set_title(f"AC Parameter Sweep — {component_id}")
        ax_mag.legend(loc="best", fontsize="x-small")
        ax_mag.grid(True, which="both", alpha=0.3)

        ax_phase.set_xlabel("Frequency (Hz)")
        ax_phase.set_ylabel("Phase (degrees)")
        ax_phase.legend(loc="best", fontsize="x-small")
        ax_phase.grid(True, which="both", alpha=0.3)

    # ------------------------------------------------------------------
    # DC Sweep base: overlay DC sweep curves per parameter value
    # ------------------------------------------------------------------
    def _plot_dc_sweep(self, fig, sweep_data):
        ax = fig.add_subplot(111)

        results = sweep_data["results"]
        sweep_labels = sweep_data.get("sweep_labels", [])
        component_id = sweep_data["component_id"]

        cmap = plt.get_cmap("viridis")
        n = len(results)
        x_label = "Sweep"

        for i, r in enumerate(results):
            if not r.success or not r.data:
                continue

            label = sweep_labels[i] if i < len(sweep_labels) else str(i)
            headers = r.data.get("headers", [])
            rows = r.data.get("data", [])

            if not rows or len(headers) < 3:
                continue

            sweep_vals = [row[1] for row in rows]
            color = cmap(i / max(n - 1, 1))
            x_label = headers[1] if len(headers) > 1 else "Sweep"

            for col_idx in range(2, len(headers)):
                col_label = headers[col_idx]
                values = [row[col_idx] for row in rows]
                ax.plot(sweep_vals, values, color=color,
                        label=f"{col_label} ({component_id}={label})",
                        alpha=0.8)

        ax.set_xlabel(x_label)
        ax.set_ylabel("Voltage (V)")
        ax.set_title(f"DC Sweep with Parameter Sweep — {component_id}")
        ax.legend(loc="best", fontsize="x-small")
        ax.grid(True, alpha=0.3)

    def closeEvent(self, event):
        plt.close(self._canvas.figure)
        super().closeEvent(event)
