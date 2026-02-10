"""Tests for MeasurementCursors — cursor placement, snapping, and readout."""

from unittest.mock import MagicMock

import numpy as np
import pytest
from matplotlib.figure import Figure

from GUI.measurement_cursors import MeasurementCursors, format_readout_html


def _make_figure_with_data():
    """Create a Figure with a single axes containing plotted data."""
    fig = Figure(figsize=(6, 4))
    ax = fig.add_subplot(111)
    x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    y = np.array([0.0, 2.0, 4.0, 6.0, 8.0])
    ax.plot(x, y, label="signal")
    return fig, ax


class FakeCanvas:
    """Minimal canvas mock that tracks mpl_connect calls."""

    def __init__(self, fig):
        self.figure = fig
        self._callbacks = {}
        self._next_cid = 0

    def mpl_connect(self, event, callback):
        cid = self._next_cid
        self._next_cid += 1
        self._callbacks.setdefault(event, []).append((cid, callback))
        return cid

    def mpl_disconnect(self, cid):
        for event in self._callbacks:
            self._callbacks[event] = [
                (c, cb) for c, cb in self._callbacks[event] if c != cid
            ]

    def draw_idle(self):
        pass

    def fire(self, event_name, **kwargs):
        """Simulate a matplotlib event."""
        event = MagicMock()
        for k, v in kwargs.items():
            setattr(event, k, v)
        for _, cb in self._callbacks.get(event_name, []):
            cb(event)


class TestMeasurementCursorsSnap:
    """Test data snapping logic."""

    def test_snap_to_exact_point(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)
        snapped = cursors._snap_to_data(2.0)
        assert snapped == 2.0

    def test_snap_to_nearest_point(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)
        snapped = cursors._snap_to_data(2.3)
        assert snapped == 2.0

    def test_snap_rounds_up(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)
        snapped = cursors._snap_to_data(2.8)
        assert snapped == 3.0

    def test_snap_ignores_underscore_labels(self):
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.axvline(1.5, label="_hidden")  # Should be ignored
        ax.plot([0, 1, 2], [0, 1, 2], label="data")
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        snapped = cursors._snap_to_data(0.9)
        assert snapped == 1.0  # Snaps to data, not axvline


class TestMeasurementCursorsInterpolation:
    """Test Y-value interpolation at cursor positions."""

    def test_interpolation_at_exact_point(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        y_vals = cursors._get_y_at_x(ax, 2.0)
        assert "signal" in y_vals
        assert abs(y_vals["signal"] - 4.0) < 1e-10

    def test_interpolation_between_points(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        y_vals = cursors._get_y_at_x(ax, 1.5)
        assert "signal" in y_vals
        assert abs(y_vals["signal"] - 3.0) < 1e-10

    def test_interpolation_at_start(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        y_vals = cursors._get_y_at_x(ax, 0.0)
        assert abs(y_vals["signal"] - 0.0) < 1e-10

    def test_interpolation_beyond_end(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        y_vals = cursors._get_y_at_x(ax, 10.0)
        assert abs(y_vals["signal"] - 8.0) < 1e-10


class TestMeasurementCursorsPlacement:
    """Test cursor placement and readout data."""

    def test_place_cursor_a(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)

        cursors._place("a", 2.0)
        data = cursors.get_readout_data()
        assert "a" in data
        assert data["a"]["x"] == 2.0
        assert abs(data["a"]["y"]["signal"] - 4.0) < 1e-10

    def test_place_both_cursors_gives_delta(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)

        cursors._place("a", 1.0)
        cursors._place("b", 3.0)
        data = cursors.get_readout_data()
        assert "a" in data
        assert "b" in data
        assert "delta" in data
        assert abs(data["delta"]["dx"] - 2.0) < 1e-10
        assert abs(data["delta"]["dy"]["signal"] - 4.0) < 1e-10

    def test_disable_removes_cursors(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)
        cursors._place("a", 1.0)
        cursors._place("b", 3.0)

        cursors.set_enabled(False)
        data = cursors.get_readout_data()
        assert data == {}

    def test_readout_callback_fires(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)
        received = []
        cursors.set_readout_callback(lambda d: received.append(d))
        cursors._place("a", 2.0)
        assert len(received) == 1
        assert "a" in received[0]


class TestMeasurementCursorsRefresh:
    """Test cursor recreation after axes.clear()."""

    def test_refresh_recreates_lines(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)
        cursors._place("a", 1.0)
        cursors._place("b", 3.0)

        # Simulate replot: clear and replot data
        ax.clear()
        ax.plot([0, 1, 2, 3, 4], [0, 2, 4, 6, 8], label="signal")
        cursors.refresh()

        # Cursor positions should be preserved
        data = cursors.get_readout_data()
        assert "a" in data
        assert "b" in data
        assert data["a"]["x"] == 1.0
        assert data["b"]["x"] == 3.0


class TestMeasurementCursorsMultiAxes:
    """Test cursor synchronization across multiple axes."""

    def test_cursors_appear_on_all_axes(self):
        fig = Figure()
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        ax1.plot([0, 1, 2], [0, 1, 2], label="mag")
        ax2.plot([0, 1, 2], [0, -45, -90], label="phase")

        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, [ax1, ax2])
        cursors.set_enabled(True)
        cursors._place("a", 1.0)

        data = cursors.get_readout_data()
        assert "mag" in data["a"]["y"]
        assert "phase" in data["a"]["y"]
        assert abs(data["a"]["y"]["mag"] - 1.0) < 1e-10
        assert abs(data["a"]["y"]["phase"] - (-45.0)) < 1e-10


class TestMeasurementCursorsDisconnect:
    """Test cleanup."""

    def test_disconnect_clears_cids(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        assert len(cursors._cids) == 3
        cursors.disconnect()
        assert len(cursors._cids) == 0


class TestFormatReadoutHtml:
    """Test HTML readout formatting."""

    def test_empty_data(self):
        html = format_readout_html({})
        assert "Left-click" in html

    def test_cursor_a_only(self):
        data = {"a": {"x": 1.5, "y": {"signal": 3.0}}}
        html = format_readout_html(data, x_label="Time")
        assert "Cursor A" in html
        assert "1.5" in html
        assert "signal" in html
        assert "Cursor B" not in html
        assert "Delta" not in html

    def test_both_cursors_with_delta(self):
        data = {
            "a": {"x": 1.0, "y": {"s1": 2.0}},
            "b": {"x": 3.0, "y": {"s1": 6.0}},
            "delta": {"dx": 2.0, "dy": {"s1": 4.0}},
        }
        html = format_readout_html(data)
        assert "Cursor A" in html
        assert "Cursor B" in html
        assert "Delta" in html
        assert "4" in html  # delta value


class TestMouseInteraction:
    """Test mouse event handling for cursor placement."""

    def test_left_click_places_cursor_a(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)

        canvas.fire("button_press_event", button=1, xdata=2.0, inaxes=ax)
        canvas.fire("button_release_event", button=1, xdata=2.0, inaxes=ax)

        data = cursors.get_readout_data()
        assert "a" in data
        assert data["a"]["x"] == 2.0

    def test_right_click_places_cursor_b(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)

        canvas.fire("button_press_event", button=3, xdata=3.0, inaxes=ax)
        canvas.fire("button_release_event", button=3, xdata=3.0, inaxes=ax)

        data = cursors.get_readout_data()
        assert "b" in data
        assert data["b"]["x"] == 3.0

    def test_click_when_disabled_does_nothing(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        # Not enabled

        canvas.fire("button_press_event", button=1, xdata=2.0, inaxes=ax)
        data = cursors.get_readout_data()
        assert data == {}

    def test_click_outside_axes_does_nothing(self):
        fig, ax = _make_figure_with_data()
        canvas = FakeCanvas(fig)
        cursors = MeasurementCursors(canvas, ax)
        cursors.set_enabled(True)

        other_ax = MagicMock()
        canvas.fire("button_press_event", button=1, xdata=2.0, inaxes=other_ax)
        data = cursors.get_readout_data()
        assert data == {}
