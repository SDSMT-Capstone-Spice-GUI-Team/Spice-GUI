"""
Unit tests for WaveformDialog multi-run overlay support.
"""

import pytest
from GUI.waveform_dialog import WaveformDialog


def _tran_data(node_count=1, points=5, offset=0.0):
    """Create sample transient data."""
    data = []
    nodes = [f"node{i}" for i in range(node_count)]
    for p in range(points):
        row = {"time": p * 0.001}
        for i, n in enumerate(nodes):
            row[n] = (p + offset) * 0.1 * (i + 1)
        data.append(row)
    return data


class TestWaveformOverlay:
    def test_add_run_stashes_current_data(self, qtbot):
        data1 = _tran_data(1)
        dlg = WaveformDialog(data1)
        qtbot.addWidget(dlg)

        data2 = _tran_data(1, offset=1.0)
        dlg.add_run(data2)

        assert len(dlg._overlay_runs) == 1
        assert dlg._overlay_runs[0]["data"] is data1
        assert dlg.full_data is data2

    def test_add_run_increments_counter(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        assert dlg._run_counter == 1
        dlg.add_run(_tran_data(1))
        assert dlg._run_counter == 2

    def test_overlay_run_visible_by_default(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        dlg.add_run(_tran_data(1))
        assert dlg._overlay_runs[0]["visible"] is True

    def test_toggle_overlay_visibility(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        dlg.add_run(_tran_data(1))
        dlg._set_overlay_visible(0, False)
        assert dlg._overlay_runs[0]["visible"] is False

    def test_clear_overlay_runs(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        dlg.add_run(_tran_data(1))
        dlg.add_run(_tran_data(1))
        assert len(dlg._overlay_runs) == 2
        dlg._clear_overlay_runs()
        assert len(dlg._overlay_runs) == 0

    def test_runs_group_hidden_initially(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        assert dlg._runs_group.isHidden()

    def test_runs_group_visible_after_add_run(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        dlg.add_run(_tran_data(1))
        assert not dlg._runs_group.isHidden()

    def test_runs_group_hidden_after_clear(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        dlg.add_run(_tran_data(1))
        dlg._clear_overlay_runs()
        assert dlg._runs_group.isHidden()

    def test_add_run_with_custom_label(self, qtbot):
        dlg = WaveformDialog(_tran_data(1))
        qtbot.addWidget(dlg)
        dlg.add_run(_tran_data(1), label="R1=1k")
        assert dlg._overlay_runs[0]["label"] == "R1=1k"

    def test_multiple_runs_preserve_order(self, qtbot):
        data1 = _tran_data(1)
        data2 = _tran_data(1, offset=1.0)
        data3 = _tran_data(1, offset=2.0)
        dlg = WaveformDialog(data1)
        qtbot.addWidget(dlg)
        dlg.add_run(data2)
        dlg.add_run(data3)

        assert dlg._overlay_runs[0]["data"] is data1
        assert dlg._overlay_runs[1]["data"] is data2
        assert dlg.full_data is data3
