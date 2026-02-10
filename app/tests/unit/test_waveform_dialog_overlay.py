"""
Unit tests for WaveformDialog overlay functionality.
"""

import pytest
from GUI.waveform_dialog import WaveformDialog

# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------

TRAN_DATA_A = [
    {"time": 0.0, "v(out)": 0.0, "v(in)": 1.0},
    {"time": 1e-6, "v(out)": 0.5, "v(in)": 0.9},
    {"time": 2e-6, "v(out)": 1.0, "v(in)": 0.8},
]

TRAN_DATA_B = [
    {"time": 0.0, "v(out)": 0.1, "v(in)": 1.1},
    {"time": 1e-6, "v(out)": 0.6, "v(in)": 1.0},
    {"time": 2e-6, "v(out)": 1.1, "v(in)": 0.9},
]


class TestWaveformDialogOverlay:
    def test_analysis_type_attribute(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        assert dlg.analysis_type == "Transient"

    def test_initial_no_overlays(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        assert len(dlg._overlay_datasets) == 0

    def test_add_dataset(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(TRAN_DATA_B, "Run 2")
        assert len(dlg._overlay_datasets) == 1

    def test_add_multiple_datasets(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(TRAN_DATA_B, "Run 2")
        dlg.add_dataset(TRAN_DATA_A, "Run 3")
        assert len(dlg._overlay_datasets) == 2

    def test_add_dataset_default_label(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(TRAN_DATA_B)
        label, _ = dlg._overlay_datasets[0]
        assert label == "Run 1"

    def test_overlay_visibility_tracking(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(TRAN_DATA_B, "Run 2")
        # Each signal in the overlay should have a visibility entry
        assert "Run 2 — v(out)" in dlg._overlay_visibility
        assert "Run 2 — v(in)" in dlg._overlay_visibility
        assert dlg._overlay_visibility["Run 2 — v(out)"] is True

    def test_clear_overlays(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(TRAN_DATA_B, "Run 2")
        dlg.clear_overlays()
        assert len(dlg._overlay_datasets) == 0
        assert len(dlg._overlay_visibility) == 0

    def test_add_dataset_after_clear(self, qtbot):
        dlg = WaveformDialog(TRAN_DATA_A)
        qtbot.addWidget(dlg)
        dlg.add_dataset(TRAN_DATA_B, "Run 2")
        dlg.clear_overlays()
        dlg.add_dataset(TRAN_DATA_A, "Run 3")
        assert len(dlg._overlay_datasets) == 1
