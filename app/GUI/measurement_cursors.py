"""
measurement_cursors.py — Reusable measurement cursor system for matplotlib plots.

Provides two draggable vertical cursors (A and B) with snap-to-data,
a readout panel showing X/Y values and deltas, and real-time updates.
"""

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class MeasurementCursors:
    """Two draggable vertical cursors on a matplotlib axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to attach cursors to.
    canvas : FigureCanvasQTAgg
        The canvas (needed for draw/event connection).
    on_cursor_moved : callable, optional
        Callback ``(cursor_a_x, cursor_b_x)`` called whenever a cursor moves.
    """

    CURSOR_A_COLOR = "#e74c3c"  # red
    CURSOR_B_COLOR = "#2980b9"  # blue

    def __init__(self, ax, canvas, on_cursor_moved=None):
        self._ax = ax
        self._canvas = canvas
        self._on_cursor_moved = on_cursor_moved

        # Data arrays for snap-to (set via set_data)
        self._x_data = None

        # Cursor positions (None = not placed)
        self._a_x = None
        self._b_x = None

        # Cursor line artists
        self._line_a = None
        self._line_b = None

        # Drag state
        self._dragging = None  # "a" or "b" or None
        self._active_cursor = "a"  # next click places this cursor

        # Connect events
        self._cid_press = canvas.mpl_connect("button_press_event", self._on_press)
        self._cid_release = canvas.mpl_connect("button_release_event", self._on_release)
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)

    def set_data(self, x_data):
        """Set the X data array for snap-to-nearest behaviour."""
        if x_data is not None and len(x_data) > 0:
            self._x_data = np.asarray(x_data, dtype=float)
        else:
            self._x_data = None

    def set_active_cursor(self, cursor):
        """Set which cursor the next click places: 'a' or 'b'."""
        self._active_cursor = cursor

    def _snap(self, x):
        """Snap *x* to the nearest value in the data array."""
        if self._x_data is None or len(self._x_data) == 0:
            return x
        idx = int(np.argmin(np.abs(self._x_data - x)))
        return float(self._x_data[idx])

    # ------ event handlers -----------------------------------------------

    def _on_press(self, event):
        if event.inaxes != self._ax or event.button != 1:
            return

        # Check if clicking near an existing cursor to drag it
        threshold = self._drag_threshold()

        if self._a_x is not None and abs(event.xdata - self._a_x) < threshold:
            self._dragging = "a"
            return
        if self._b_x is not None and abs(event.xdata - self._b_x) < threshold:
            self._dragging = "b"
            return

        # Place the active cursor
        x = self._snap(event.xdata)
        if self._active_cursor == "a":
            self._a_x = x
            self._draw_cursor_a()
        else:
            self._b_x = x
            self._draw_cursor_b()

        self._notify()
        self._canvas.draw_idle()

    def _on_motion(self, event):
        if self._dragging is None or event.inaxes != self._ax:
            return
        x = self._snap(event.xdata)
        if self._dragging == "a":
            self._a_x = x
            self._draw_cursor_a()
        else:
            self._b_x = x
            self._draw_cursor_b()
        self._notify()
        self._canvas.draw_idle()

    def _on_release(self, event):
        self._dragging = None

    def _drag_threshold(self):
        """Return a reasonable x-distance threshold for cursor grabbing."""
        xlim = self._ax.get_xlim()
        return (xlim[1] - xlim[0]) * 0.02

    # ------ drawing helpers -----------------------------------------------

    def _draw_cursor_a(self):
        if self._line_a is not None:
            self._line_a.remove()
        self._line_a = self._ax.axvline(
            self._a_x,
            color=self.CURSOR_A_COLOR,
            linewidth=1.5,
            linestyle="--",
            label="_cursor_a",
        )

    def _draw_cursor_b(self):
        if self._line_b is not None:
            self._line_b.remove()
        self._line_b = self._ax.axvline(
            self._b_x,
            color=self.CURSOR_B_COLOR,
            linewidth=1.5,
            linestyle="--",
            label="_cursor_b",
        )

    def _notify(self):
        if self._on_cursor_moved:
            self._on_cursor_moved(self._a_x, self._b_x)

    # ------ public queries -----------------------------------------------

    @property
    def cursor_a_x(self):
        return self._a_x

    @property
    def cursor_b_x(self):
        return self._b_x

    def get_y_values_at(self, x):
        """Return dict of {line_label: y_value} for all visible lines at *x*.

        Uses linear interpolation between the two nearest data points.
        """
        if x is None:
            return {}
        results = {}
        for line in self._ax.get_lines():
            label = line.get_label()
            if label.startswith("_") or not line.get_visible():
                continue
            xd = line.get_xdata()
            yd = line.get_ydata()
            if len(xd) < 2:
                continue
            y_interp = np.interp(x, xd, yd)
            results[label] = float(y_interp)
        return results

    def remove(self):
        """Disconnect events and remove cursor lines."""
        self._canvas.mpl_disconnect(self._cid_press)
        self._canvas.mpl_disconnect(self._cid_release)
        self._canvas.mpl_disconnect(self._cid_motion)
        if self._line_a is not None:
            self._line_a.remove()
        if self._line_b is not None:
            self._line_b.remove()


class CursorReadoutPanel(QWidget):
    """Panel displaying cursor position readouts and delta values.

    Call ``update_readout(cursors)`` whenever cursor positions change.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cursors = None

        group = QGroupBox("Measurement Cursors")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)

        layout = QVBoxLayout(group)

        # Cursor selector buttons
        btn_row = QHBoxLayout()
        self._btn_a = QPushButton("Place Cursor A")
        self._btn_a.setStyleSheet(f"color: {MeasurementCursors.CURSOR_A_COLOR};")
        self._btn_a.setCheckable(True)
        self._btn_a.setChecked(True)
        self._btn_b = QPushButton("Place Cursor B")
        self._btn_b.setStyleSheet(f"color: {MeasurementCursors.CURSOR_B_COLOR};")
        self._btn_b.setCheckable(True)
        self._btn_a.clicked.connect(lambda: self._select_cursor("a"))
        self._btn_b.clicked.connect(lambda: self._select_cursor("b"))
        btn_row.addWidget(self._btn_a)
        btn_row.addWidget(self._btn_b)
        layout.addLayout(btn_row)

        # Readout labels
        self._label_a = QLabel("Cursor A: —")
        self._label_a.setStyleSheet(f"color: {MeasurementCursors.CURSOR_A_COLOR};")
        self._label_b = QLabel("Cursor B: —")
        self._label_b.setStyleSheet(f"color: {MeasurementCursors.CURSOR_B_COLOR};")
        self._label_delta = QLabel("Delta: —")
        self._label_delta.setStyleSheet("font-weight: bold;")

        layout.addWidget(self._label_a)
        layout.addWidget(self._label_b)
        layout.addWidget(self._label_delta)

        # Y-value readout area
        self._y_label = QLabel("")
        self._y_label.setWordWrap(True)
        self._y_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._y_label)

    def set_cursors(self, cursors):
        """Attach cursor object so button clicks can switch active cursor."""
        self._cursors = cursors

    def _select_cursor(self, which):
        if self._cursors:
            self._cursors.set_active_cursor(which)
        self._btn_a.setChecked(which == "a")
        self._btn_b.setChecked(which == "b")

    def update_readout(self, cursors):
        """Update the readout panel from cursor positions."""
        a_x = cursors.cursor_a_x
        b_x = cursors.cursor_b_x

        # Cursor A text
        if a_x is not None:
            y_vals_a = cursors.get_y_values_at(a_x)
            y_str_a = ", ".join(f"{k}={v:.4g}" for k, v in y_vals_a.items())
            self._label_a.setText(f"Cursor A: X={a_x:.6g}  |  {y_str_a}")
        else:
            self._label_a.setText("Cursor A: —")

        # Cursor B text
        if b_x is not None:
            y_vals_b = cursors.get_y_values_at(b_x)
            y_str_b = ", ".join(f"{k}={v:.4g}" for k, v in y_vals_b.items())
            self._label_b.setText(f"Cursor B: X={b_x:.6g}  |  {y_str_b}")
        else:
            self._label_b.setText("Cursor B: —")

        # Delta text
        if a_x is not None and b_x is not None:
            dx = b_x - a_x
            y_vals_a = cursors.get_y_values_at(a_x)
            y_vals_b = cursors.get_y_values_at(b_x)
            dy_parts = []
            for key in y_vals_a:
                if key in y_vals_b:
                    dy = y_vals_b[key] - y_vals_a[key]
                    dy_parts.append(f"Δ{key}={dy:.4g}")
            dy_str = ", ".join(dy_parts) if dy_parts else ""
            self._label_delta.setText(f"ΔX={dx:.6g}  |  {dy_str}")
        else:
            self._label_delta.setText("Delta: —")
