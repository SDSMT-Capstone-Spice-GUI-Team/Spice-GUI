"""
Unit tests for results_plot_dialog.py — DC Sweep and AC Sweep plot dialogs.
"""

import pytest
from GUI.results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog

# ---------------------------------------------------------------------------
# DC Sweep Plot
# ---------------------------------------------------------------------------


class TestDCSweepPlotDialog:
    def test_opens_with_valid_data(self, qtbot):
        data = {
            "headers": ["Index", "v-sweep", "v(nodeA)"],
            "data": [
                [0, 0.0, 0.0],
                [1, 1.0, 0.5],
                [2, 2.0, 1.0],
            ],
        }
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "DC Sweep Results"

    def test_opens_with_empty_data(self, qtbot):
        data = {"headers": [], "data": []}
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        # Should not crash — shows placeholder text

    def test_opens_with_multiple_signals(self, qtbot):
        data = {
            "headers": ["Index", "v-sweep", "v(nodeA)", "v(nodeB)"],
            "data": [
                [0, 0.0, 0.0, 0.0],
                [1, 1.0, 0.5, 0.3],
            ],
        }
        dlg = DCSweepPlotDialog(data)
        qtbot.addWidget(dlg)


# ---------------------------------------------------------------------------
# AC Sweep Bode Plot
# ---------------------------------------------------------------------------


class TestACSweepPlotDialog:
    def test_opens_with_valid_data(self, qtbot):
        data = {
            "frequencies": [100, 1000, 10000],
            "magnitude": {"out": [1.0, 0.7, 0.3]},
            "phase": {"out": [-10.0, -45.0, -80.0]},
        }
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)
        assert "Bode" in dlg.windowTitle()

    def test_opens_with_empty_data(self, qtbot):
        data = {"frequencies": [], "magnitude": {}, "phase": {}}
        dlg = ACSweepPlotDialog(data)
        qtbot.addWidget(dlg)

    def test_opens_with_multiple_signals(self, qtbot):
        data = {
            "frequencies": [100, 1000],
            "magnitude": {"out": [1.0, 0.5], "node2": [0.8, 0.4]},
            "phase": {"out": [-45.0, -90.0], "node2": [-30.0, -60.0]},
        }
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
