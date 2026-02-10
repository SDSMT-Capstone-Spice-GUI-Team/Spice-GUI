"""
Unit tests for results_plot_dialog.py — DC Sweep and AC Sweep plot dialogs
with multi-run overlay support.
"""

import pytest
from GUI.results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dc_data(node_count=1, rows=3):
    """Create sample DC sweep data with *node_count* signals."""
    headers = ["Index", "v-sweep"] + [f"v(node{i})" for i in range(node_count)]
    data = []
    for r in range(rows):
        row = [r, float(r)]
        for n in range(node_count):
            row.append(float(r) * 0.5 * (n + 1))
        data.append(row)
    return {"headers": headers, "data": data}


def _ac_data(node_count=1, freq_points=3):
    """Create sample AC sweep data with *node_count* signals."""
    freqs = [10 ** (i + 1) for i in range(freq_points)]
    magnitude = {f"node{i}": [1.0 / (j + 1) for j in range(freq_points)] for i in range(node_count)}
    phase = {f"node{i}": [-10.0 * (j + 1) for j in range(freq_points)] for i in range(node_count)}
    return {"frequencies": freqs, "magnitude": magnitude, "phase": phase}


# ---------------------------------------------------------------------------
# DC Sweep Plot — backwards compatibility
# ---------------------------------------------------------------------------


class TestDCSweepPlotDialog:
    def test_opens_with_valid_data(self, qtbot):
        data = _dc_data(1)
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "DC Sweep Results"

    def test_opens_with_empty_data(self, qtbot):
        data = {"headers": [], "data": []}
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)

    def test_opens_with_multiple_signals(self, qtbot):
        data = _dc_data(2)
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)


# ---------------------------------------------------------------------------
# DC Sweep Plot — overlay features
# ---------------------------------------------------------------------------


class TestDCSweepOverlay:
    def test_add_result_increases_run_count(self, qtbot):
        dlg = DCSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_dc_data(1))
        dlg.add_result(_dc_data(1))
        assert len(dlg._results) == 2
        assert dlg._run_counter == 2

    def test_add_result_with_custom_label(self, qtbot):
        dlg = DCSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_dc_data(1), label="R1=1k")
        assert dlg._results[0]["label"] == "R1=1k"

    def test_toggle_visibility(self, qtbot):
        dlg = DCSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_dc_data(1))
        dlg.add_result(_dc_data(1))
        dlg._set_visible(0, False)
        assert not dlg._results[0]["visible"]
        assert dlg._results[1]["visible"]

    def test_clear_all_removes_runs(self, qtbot):
        dlg = DCSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_dc_data(1))
        dlg.add_result(_dc_data(1))
        dlg.clear_all()
        assert len(dlg._results) == 0
        assert dlg._run_counter == 0

    def test_checkboxes_created_per_run(self, qtbot):
        dlg = DCSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_dc_data(1))
        dlg.add_result(_dc_data(1))
        assert len(dlg._checkboxes) == 2

    def test_checkbox_toggle_updates_visibility(self, qtbot):
        dlg = DCSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_dc_data(1))
        dlg._checkboxes[0].setChecked(False)
        assert not dlg._results[0]["visible"]


# ---------------------------------------------------------------------------
# AC Sweep Bode Plot — backwards compatibility
# ---------------------------------------------------------------------------


class TestACSweepPlotDialog:
    def test_opens_with_valid_data(self, qtbot):
        data = _ac_data(1)
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert "Bode" in dlg.windowTitle()

    def test_opens_with_empty_data(self, qtbot):
        data = {"frequencies": [], "magnitude": {}, "phase": {}}
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)

    def test_opens_with_multiple_signals(self, qtbot):
        data = _ac_data(2)
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)

    def test_phase_only_signal(self, qtbot):
        """Phase data for a node not in magnitude should still be plotted."""
        data = {
            "frequencies": [100, 1000],
            "magnitude": {"out": [1.0, 0.5]},
            "phase": {"out": [-45.0, -90.0], "extra": [-10.0, -20.0]},
        }
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)


# ---------------------------------------------------------------------------
# AC Sweep Bode Plot — overlay features
# ---------------------------------------------------------------------------


class TestACSweepOverlay:
    def test_add_result_increases_run_count(self, qtbot):
        dlg = ACSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_ac_data(1))
        dlg.add_result(_ac_data(1))
        assert len(dlg._results) == 2

    def test_toggle_visibility(self, qtbot):
        dlg = ACSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_ac_data(1))
        dlg.add_result(_ac_data(1))
        dlg._set_visible(1, False)
        assert dlg._results[0]["visible"]
        assert not dlg._results[1]["visible"]

    def test_clear_all(self, qtbot):
        dlg = ACSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_ac_data(1))
        dlg.clear_all()
        assert len(dlg._results) == 0

    def test_checkbox_toggle_updates_visibility(self, qtbot):
        dlg = ACSweepPlotDialog()
        qtbot.addWidget(dlg)
        dlg.add_result(_ac_data(1))
        dlg._checkboxes[0].setChecked(False)
        assert not dlg._results[0]["visible"]
