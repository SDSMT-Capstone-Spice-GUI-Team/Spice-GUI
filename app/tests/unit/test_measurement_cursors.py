"""
Unit tests for measurement_cursors.py — MeasurementCursors and CursorReadoutPanel.
"""

import numpy as np
import pytest
from GUI.measurement_cursors import CursorReadoutPanel, MeasurementCursors
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_axes_with_data():
    """Create a Figure/Canvas/Axes with sample data plotted."""
    fig = Figure(figsize=(4, 3))
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    ax.plot(x, y, label="sin")
    return fig, canvas, ax, x


# ---------------------------------------------------------------------------
# MeasurementCursors unit tests
# ---------------------------------------------------------------------------


class TestMeasurementCursors:
    def test_initial_state(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        assert mc.cursor_a_x is None
        assert mc.cursor_b_x is None

    def test_set_data(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        mc.set_data(x)
        assert mc._x_data is not None
        assert len(mc._x_data) == 100

    def test_snap_to_nearest(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        mc.set_data(x)
        # Should snap to nearest value in x
        snapped = mc._snap(5.01)
        assert abs(snapped - 5.0) < 0.2  # within one step

    def test_snap_without_data(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        # Without data, snap returns the input
        assert mc._snap(5.0) == 5.0

    def test_set_active_cursor(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        mc.set_active_cursor("b")
        assert mc._active_cursor == "b"
        mc.set_active_cursor("a")
        assert mc._active_cursor == "a"

    def test_get_y_values_at_returns_interpolated(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        y_vals = mc.get_y_values_at(0.0)
        assert "sin" in y_vals
        assert abs(y_vals["sin"] - np.sin(0.0)) < 0.01

    def test_get_y_values_at_none(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        assert mc.get_y_values_at(None) == {}

    def test_remove_does_not_crash(self):
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        mc.remove()  # should not raise

    def test_callback_called(self):
        fig, canvas, ax, x = _make_axes_with_data()
        calls = []
        mc = MeasurementCursors(
            ax, canvas, on_cursor_moved=lambda a, b: calls.append((a, b))
        )
        mc._notify()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# CursorReadoutPanel widget tests
# ---------------------------------------------------------------------------


class TestCursorReadoutPanel:
    def test_creates_without_crash(self, qtbot):
        panel = CursorReadoutPanel()
        qtbot.addWidget(panel)
        assert panel._label_a.text() == "Cursor A: —"
        assert panel._label_b.text() == "Cursor B: —"

    def test_set_cursors(self, qtbot):
        panel = CursorReadoutPanel()
        qtbot.addWidget(panel)
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        panel.set_cursors(mc)
        assert panel._cursors is mc

    def test_update_readout_no_cursors_placed(self, qtbot):
        panel = CursorReadoutPanel()
        qtbot.addWidget(panel)
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        panel.update_readout(mc)
        assert "—" in panel._label_a.text()

    def test_select_cursor_a(self, qtbot):
        panel = CursorReadoutPanel()
        qtbot.addWidget(panel)
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        panel.set_cursors(mc)
        panel._select_cursor("a")
        assert mc._active_cursor == "a"
        assert panel._btn_a.isChecked()
        assert not panel._btn_b.isChecked()

    def test_select_cursor_b(self, qtbot):
        panel = CursorReadoutPanel()
        qtbot.addWidget(panel)
        fig, canvas, ax, x = _make_axes_with_data()
        mc = MeasurementCursors(ax, canvas)
        panel.set_cursors(mc)
        panel._select_cursor("b")
        assert mc._active_cursor == "b"
        assert not panel._btn_a.isChecked()
        assert panel._btn_b.isChecked()


# ---------------------------------------------------------------------------
# Integration with plot dialogs
# ---------------------------------------------------------------------------


class TestDCSweepCursorIntegration:
    def test_dc_sweep_has_cursors(self, qtbot):
        from GUI.results_plot_dialog import DCSweepPlotDialog

        data = {
            "headers": ["Index", "v-sweep", "v(out)"],
            "data": [[0, 0.0, 0.0], [1, 1.0, 0.5], [2, 2.0, 1.0]],
        }
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert hasattr(dlg, "_cursors")
        assert dlg._cursors is not None
        assert hasattr(dlg, "_readout")

    def test_dc_sweep_cursor_data_set(self, qtbot):
        from GUI.results_plot_dialog import DCSweepPlotDialog

        data = {
            "headers": ["Index", "v-sweep", "v(out)"],
            "data": [[0, 0.0, 0.0], [1, 1.0, 0.5], [2, 2.0, 1.0]],
        }
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert dlg._cursors._x_data is not None


class TestACSweepCursorIntegration:
    def test_ac_sweep_has_cursors(self, qtbot):
        from GUI.results_plot_dialog import ACSweepPlotDialog

        data = {
            "frequencies": [100, 1000, 10000],
            "magnitude": {"out": [1.0, 0.7, 0.3]},
            "phase": {"out": [-10.0, -45.0, -80.0]},
        }
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert hasattr(dlg, "_cursors")
        assert dlg._cursors is not None

    def test_ac_sweep_cursor_data_set(self, qtbot):
        from GUI.results_plot_dialog import ACSweepPlotDialog

        data = {
            "frequencies": [100, 1000, 10000],
            "magnitude": {"out": [1.0, 0.7, 0.3]},
            "phase": {"out": [-10.0, -45.0, -80.0]},
        }
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert dlg._cursors._x_data is not None


class TestWaveformCursorIntegration:
    def test_waveform_has_cursors(self, qtbot):
        from GUI.waveform_dialog import WaveformDialog

        data = [
            {"time": 0.0, "v(out)": 0.0},
            {"time": 1e-6, "v(out)": 0.5},
            {"time": 2e-6, "v(out)": 1.0},
        ]
        dlg = WaveformDialog(data)
        qtbot.addWidget(dlg)
        assert hasattr(dlg, "_cursors")
        assert dlg._cursors is not None

    def test_waveform_cursor_data_set(self, qtbot):
        from GUI.waveform_dialog import WaveformDialog

        data = [
            {"time": 0.0, "v(out)": 0.0},
            {"time": 1e-6, "v(out)": 0.5},
            {"time": 2e-6, "v(out)": 1.0},
        ]
        dlg = WaveformDialog(data)
        qtbot.addWidget(dlg)
        assert dlg._cursors._x_data is not None
