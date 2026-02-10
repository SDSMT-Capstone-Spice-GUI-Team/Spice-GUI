"""
Measurement Cursors — Interactive dual vertical cursors for matplotlib plots.

Provides two draggable cursors (A and B) that snap to nearest data points and
display X/Y values and delta measurements in a readout panel.

Usage:
    cursors = MeasurementCursors(canvas, [ax1, ax2])
    cursors.set_readout_callback(lambda data: label.setText(format_readout_html(data)))
    cursors.set_enabled(True)

    # After replotting (axes.clear() + replot), call:
    cursors.refresh()
"""

import numpy as np

# Cursor colors (red-ish for A, blue-ish for B)
CURSOR_A_COLOR = "#E74C3C"
CURSOR_B_COLOR = "#3498DB"


class MeasurementCursors:
    """Manages two vertical measurement cursors on one or more matplotlib axes.

    Left-click places/drags Cursor A. Right-click places/drags Cursor B.
    Cursors snap to the nearest X data point for accuracy.
    """

    def __init__(self, canvas, axes):
        """
        Args:
            canvas: FigureCanvasQTAgg instance
            axes: a single Axes or list of Axes to synchronize cursors across
        """
        self.canvas = canvas
        self.axes = axes if isinstance(axes, list) else [axes]

        self._cursor_a_x = None
        self._cursor_b_x = None
        self._cursor_a_lines = []
        self._cursor_b_lines = []
        self._enabled = False
        self._dragging = None
        self._readout_callback = None

        self._cids = [
            canvas.mpl_connect("button_press_event", self._on_press),
            canvas.mpl_connect("button_release_event", self._on_release),
            canvas.mpl_connect("motion_notify_event", self._on_motion),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_readout_callback(self, callback):
        """Set a callback invoked with readout data dict whenever cursors change."""
        self._readout_callback = callback

    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self._remove_all()
        self._fire_readout()

    @property
    def enabled(self):
        return self._enabled

    def refresh(self):
        """Recreate cursor lines after the axes have been cleared and replotted."""
        self._cursor_a_lines.clear()
        self._cursor_b_lines.clear()
        if self._enabled:
            if self._cursor_a_x is not None:
                self._create_lines("a", self._cursor_a_x)
            if self._cursor_b_x is not None:
                self._create_lines("b", self._cursor_b_x)
            self._fire_readout()
            self.canvas.draw_idle()

    def get_readout_data(self):
        """Return structured readout data for both cursors and their delta.

        Returns dict that may contain keys 'a', 'b', 'delta'.
        Each cursor entry has 'x' and 'y' (dict of label -> value).
        Delta has 'dx' and 'dy' (dict of label -> value).
        """
        data = {}
        if self._cursor_a_x is not None:
            y_vals = {}
            for ax in self.axes:
                y_vals.update(self._get_y_at_x(ax, self._cursor_a_x))
            data["a"] = {"x": self._cursor_a_x, "y": y_vals}

        if self._cursor_b_x is not None:
            y_vals = {}
            for ax in self.axes:
                y_vals.update(self._get_y_at_x(ax, self._cursor_b_x))
            data["b"] = {"x": self._cursor_b_x, "y": y_vals}

        if "a" in data and "b" in data:
            dx = data["b"]["x"] - data["a"]["x"]
            dy = {}
            for label in data["a"]["y"]:
                if label in data["b"]["y"]:
                    dy[label] = data["b"]["y"][label] - data["a"]["y"][label]
            data["delta"] = {"dx": dx, "dy": dy}

        return data

    def disconnect(self):
        """Disconnect all matplotlib event handlers."""
        for cid in self._cids:
            self.canvas.mpl_disconnect(cid)
        self._cids.clear()

    # ------------------------------------------------------------------
    # Mouse event handlers
    # ------------------------------------------------------------------

    def _on_press(self, event):
        if not self._enabled or event.inaxes not in self.axes:
            return
        x = event.xdata
        if x is None:
            return

        thresh = self._drag_threshold()

        # Check if clicking near an existing cursor to start dragging
        if self._cursor_a_x is not None and abs(x - self._cursor_a_x) < thresh:
            self._dragging = "a"
            return
        if self._cursor_b_x is not None and abs(x - self._cursor_b_x) < thresh:
            self._dragging = "b"
            return

        # Place cursor: left-click = A, right-click = B
        if event.button == 1:
            self._place("a", x)
        elif event.button == 3:
            self._place("b", x)

    def _on_motion(self, event):
        if self._dragging and event.inaxes in self.axes and event.xdata is not None:
            self._place(self._dragging, event.xdata)

    def _on_release(self, event):
        self._dragging = None

    # ------------------------------------------------------------------
    # Cursor placement
    # ------------------------------------------------------------------

    def _place(self, which, x):
        snapped = self._snap_to_data(x)
        if snapped is not None:
            x = snapped

        if which == "a":
            self._cursor_a_x = x
            self._update_lines("a", x)
        else:
            self._cursor_b_x = x
            self._update_lines("b", x)

        self._fire_readout()
        self.canvas.draw_idle()

    def _update_lines(self, which, x):
        lines = self._cursor_a_lines if which == "a" else self._cursor_b_lines
        if lines:
            for line in lines:
                line.set_xdata([x, x])
        else:
            self._create_lines(which, x)

    def _create_lines(self, which, x):
        color = CURSOR_A_COLOR if which == "a" else CURSOR_B_COLOR
        lines = []
        for ax in self.axes:
            line = ax.axvline(x, color=color, linestyle="--", linewidth=1.5, alpha=0.8)
            line.set_label(f"_Cursor {which.upper()}")
            lines.append(line)
        if which == "a":
            self._cursor_a_lines = lines
        else:
            self._cursor_b_lines = lines

    def _remove_all(self):
        for line in self._cursor_a_lines + self._cursor_b_lines:
            try:
                line.remove()
            except ValueError:
                pass
        self._cursor_a_lines.clear()
        self._cursor_b_lines.clear()
        self._cursor_a_x = None
        self._cursor_b_x = None
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Data snapping and interpolation
    # ------------------------------------------------------------------

    def _drag_threshold(self):
        """Return 2% of the X-axis range for cursor proximity detection."""
        xlim = self.axes[0].get_xlim()
        return (xlim[1] - xlim[0]) * 0.02

    def _snap_to_data(self, x):
        """Snap to the nearest X data point across all plotted lines."""
        best_x = None
        best_dist = float("inf")

        for ax in self.axes:
            for line in ax.get_lines():
                if line.get_label().startswith("_"):
                    continue
                xdata = np.asarray(line.get_xdata(), dtype=float)
                if len(xdata) == 0:
                    continue
                idx = int(np.searchsorted(xdata, x))
                for i in [max(0, idx - 1), min(len(xdata) - 1, idx)]:
                    dist = abs(xdata[i] - x)
                    if dist < best_dist:
                        best_dist = dist
                        best_x = float(xdata[i])

        return best_x

    def _get_y_at_x(self, ax, x):
        """Interpolate Y values at X for each data line on the given axes."""
        result = {}
        for line in ax.get_lines():
            label = line.get_label()
            if label.startswith("_"):
                continue
            xdata = np.asarray(line.get_xdata(), dtype=float)
            ydata = np.asarray(line.get_ydata(), dtype=float)
            if len(xdata) < 1:
                continue

            idx = int(np.searchsorted(xdata, x))
            if idx == 0:
                result[label] = float(ydata[0])
            elif idx >= len(xdata):
                result[label] = float(ydata[-1])
            else:
                x0, x1 = xdata[idx - 1], xdata[idx]
                y0, y1 = ydata[idx - 1], ydata[idx]
                if x1 != x0:
                    t = (x - x0) / (x1 - x0)
                    result[label] = float(y0 + t * (y1 - y0))
                else:
                    result[label] = float(y0)
        return result

    def _fire_readout(self):
        if self._readout_callback:
            self._readout_callback(self.get_readout_data())


def format_readout_html(data, x_label="X", y_label="Y"):
    """Format cursor readout data as HTML for display in a QLabel.

    Args:
        data: dict from MeasurementCursors.get_readout_data()
        x_label: label for X axis (e.g. "Time", "Frequency")
        y_label: label for Y axis (e.g. "Voltage", "Magnitude")
    """
    if not data:
        return (
            "<i>Left-click to place Cursor A, right-click for Cursor B</i>"
        )

    parts = []

    if "a" in data:
        a = data["a"]
        parts.append(
            f"<b style='color:{CURSOR_A_COLOR}'>Cursor A</b> "
            f"&mdash; {x_label}: {a['x']:.6g}"
        )
        for label, y in a["y"].items():
            parts.append(f"&nbsp;&nbsp;{label}: {y:.6g}")

    if "b" in data:
        b = data["b"]
        parts.append(
            f"<b style='color:{CURSOR_B_COLOR}'>Cursor B</b> "
            f"&mdash; {x_label}: {b['x']:.6g}"
        )
        for label, y in b["y"].items():
            parts.append(f"&nbsp;&nbsp;{label}: {y:.6g}")

    if "delta" in data:
        d = data["delta"]
        parts.append(f"<b>Delta</b> &mdash; \u0394{x_label}: {d['dx']:.6g}")
        for label, dy in d["dy"].items():
            parts.append(f"&nbsp;&nbsp;\u0394{label}: {dy:.6g}")

    return "<br>".join(parts)
