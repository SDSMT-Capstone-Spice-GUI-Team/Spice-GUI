"""
Unit tests for results_plot_dialog.py — DC Sweep and AC Sweep plot dialogs.
"""

import pytest
from GUI.results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

DC_DATA_A = {
    "headers": ["Index", "v-sweep", "v(nodeA)"],
    "data": [
        [0, 0.0, 0.0],
        [1, 1.0, 0.5],
        [2, 2.0, 1.0],
    ],
}

DC_DATA_B = {
    "headers": ["Index", "v-sweep", "v(nodeA)"],
    "data": [
        [0, 0.0, 0.1],
        [1, 1.0, 0.6],
        [2, 2.0, 1.1],
    ],
}

AC_DATA_A = {
    "frequencies": [100, 1000, 10000],
    "magnitude": {"out": [1.0, 0.7, 0.3]},
    "phase": {"out": [-10.0, -45.0, -80.0]},
}

AC_DATA_B = {
    "frequencies": [100, 1000, 10000],
    "magnitude": {"out": [0.9, 0.6, 0.2]},
    "phase": {"out": [-15.0, -50.0, -85.0]},
}


# ---------------------------------------------------------------------------
# DC Sweep Plot
# ---------------------------------------------------------------------------


class TestDCSweepPlotDialog:
    def test_opens_with_valid_data(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
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

    def test_analysis_type_attribute(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        assert dlg.analysis_type == "DC Sweep"

    def test_dataset_count_initial(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        assert dlg.dataset_count == 1

    def test_add_dataset_increments_count(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(DC_DATA_B, "Run 2")
        assert dlg.dataset_count == 2

    def test_add_multiple_datasets(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(DC_DATA_B, "Run 2")
        dlg.add_dataset(DC_DATA_A, "Run 3")
        assert dlg.dataset_count == 3

    def test_clear_all_resets_datasets(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(DC_DATA_B, "Run 2")
        dlg.clear_all()
        assert dlg.dataset_count == 0

    def test_add_dataset_after_clear(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.clear_all()
        dlg.add_dataset(DC_DATA_B, "Fresh")
        assert dlg.dataset_count == 1

    def test_add_dataset_with_default_label(self, qtbot):
        dlg = DCSweepPlotDialog(DC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(DC_DATA_B)
        # Should not crash; auto-labels as "Run 2"
        assert dlg.dataset_count == 2


# ---------------------------------------------------------------------------
# AC Sweep Bode Plot
# ---------------------------------------------------------------------------


class TestACSweepPlotDialog:
    def test_opens_with_valid_data(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
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

    def test_analysis_type_attribute(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        assert dlg.analysis_type == "AC Sweep"

    def test_dataset_count_initial(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        assert dlg.dataset_count == 1

    def test_add_dataset_increments_count(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(AC_DATA_B, "Run 2")
        assert dlg.dataset_count == 2

    def test_add_multiple_datasets(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(AC_DATA_B, "Run 2")
        dlg.add_dataset(AC_DATA_A, "Run 3")
        assert dlg.dataset_count == 3

    def test_clear_all_resets_datasets(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(AC_DATA_B, "Run 2")
        dlg.clear_all()
        assert dlg.dataset_count == 0

    def test_add_dataset_after_clear(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.clear_all()
        dlg.add_dataset(AC_DATA_B, "Fresh")
        assert dlg.dataset_count == 1

    def test_add_dataset_with_default_label(self, qtbot):
        dlg = ACSweepPlotDialog(AC_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(AC_DATA_B)
        assert dlg.dataset_count == 2
