"""Unit tests for Monte Carlo configuration and results dialogs.

Tests MonteCarloDialog (app/GUI/monte_carlo_dialog.py) and
MonteCarloResultsDialog (app/GUI/monte_carlo_results_dialog.py).
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from GUI.monte_carlo_dialog import MC_BASE_ANALYSIS_TYPES, MonteCarloDialog
from GUI.monte_carlo_results_dialog import MonteCarloResultsDialog
from models.component import ComponentData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_components(*specs):
    """Build a components dict from (id, type, value) tuples."""
    return {
        cid: ComponentData(
            component_id=cid,
            component_type=ctype,
            value=val,
            position=(0.0, 0.0),
        )
        for cid, ctype, val in specs
    }


@dataclass
class FakeSimResult:
    """Minimal stand-in for SimulationResult."""

    success: bool = True
    data: Any = None


# ---------------------------------------------------------------------------
# MonteCarloDialog — initialization
# ---------------------------------------------------------------------------


class TestMonteCarloDialogInit:
    def test_opens_without_crash(self, qtbot):
        comps = _make_components(("R1", "Resistor", "1k"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)

    def test_window_title(self, qtbot):
        dlg = MonteCarloDialog(_make_components(("R1", "Resistor", "1k")))
        qtbot.addWidget(dlg)
        assert "Monte Carlo" in dlg.windowTitle()

    def test_default_num_runs(self, qtbot):
        dlg = MonteCarloDialog(_make_components(("R1", "Resistor", "1k")))
        qtbot.addWidget(dlg)
        assert dlg.num_runs_spin.value() == 20

    def test_num_runs_range(self, qtbot):
        dlg = MonteCarloDialog(_make_components(("R1", "Resistor", "1k")))
        qtbot.addWidget(dlg)
        assert dlg.num_runs_spin.minimum() == 2
        assert dlg.num_runs_spin.maximum() == 1000

    def test_analysis_combo_has_four_types(self, qtbot):
        dlg = MonteCarloDialog(_make_components(("R1", "Resistor", "1k")))
        qtbot.addWidget(dlg)
        items = [dlg.analysis_combo.itemText(i) for i in range(dlg.analysis_combo.count())]
        assert items == MC_BASE_ANALYSIS_TYPES

    def test_tolerance_table_row_count_matches_eligible(self, qtbot):
        comps = _make_components(
            ("R1", "Resistor", "1k"),
            ("C1", "Capacitor", "100n"),
            ("V1", "Voltage Source", "5V"),
        )
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)
        assert dlg.tol_table is not None
        assert dlg.tol_table.rowCount() == 3

    def test_empty_circuit_shows_no_eligible_label(self, qtbot):
        # Only a Diode — not in MC_ELIGIBLE_TYPES
        comps = _make_components(("D1", "Diode", "1N4148"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)
        assert dlg.tol_table is None

    def test_default_tolerances_match_constants(self, qtbot):
        from simulation.monte_carlo import DEFAULT_TOLERANCES

        comps = _make_components(("R1", "Resistor", "1k"), ("C1", "Capacitor", "10u"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)

        for row in range(dlg.tol_table.rowCount()):
            comp_type = dlg.tol_table.item(row, 1).text()
            tol_spin = dlg.tol_table.cellWidget(row, 2)
            expected = DEFAULT_TOLERANCES.get(comp_type, 5.0)
            assert tol_spin.value() == pytest.approx(expected)


# ---------------------------------------------------------------------------
# MonteCarloDialog — analysis type switching
# ---------------------------------------------------------------------------


class TestMonteCarloDialogAnalysisSwitch:
    def test_switching_type_rebuilds_base_form(self, qtbot):
        dlg = MonteCarloDialog(_make_components(("R1", "Resistor", "1k")))
        qtbot.addWidget(dlg)

        # Start at DC OP (no extra fields)
        dlg.analysis_combo.setCurrentText("DC Operating Point")
        count_dcop = dlg._base_form.count()

        # Switch to Transient (has fields)
        dlg.analysis_combo.setCurrentText("Transient")
        count_tran = dlg._base_form.count()
        assert count_tran > count_dcop


# ---------------------------------------------------------------------------
# MonteCarloDialog — get_parameters
# ---------------------------------------------------------------------------


class TestMonteCarloDialogGetParameters:
    def test_returns_correct_structure(self, qtbot):
        comps = _make_components(("R1", "Resistor", "1k"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)

        params = dlg.get_parameters()
        assert params is not None
        assert "num_runs" in params
        assert "base_analysis_type" in params
        assert "base_params" in params
        assert "tolerances" in params
        assert params["num_runs"] == 20

    def test_returns_none_when_all_tolerances_zero(self, qtbot):
        comps = _make_components(("R1", "Resistor", "1k"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)

        # Set all tolerances to 0
        for row in range(dlg.tol_table.rowCount()):
            dlg.tol_table.cellWidget(row, 2).setValue(0.0)

        assert dlg.get_parameters() is None

    def test_tolerances_contain_component_ids(self, qtbot):
        comps = _make_components(("R1", "Resistor", "1k"), ("C1", "Capacitor", "10u"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)

        params = dlg.get_parameters()
        assert params is not None
        for cid in params["tolerances"]:
            assert cid in comps

    def test_tolerance_has_pct_and_distribution(self, qtbot):
        comps = _make_components(("R1", "Resistor", "1k"))
        dlg = MonteCarloDialog(comps)
        qtbot.addWidget(dlg)

        params = dlg.get_parameters()
        tol = list(params["tolerances"].values())[0]
        assert "tolerance_pct" in tol
        assert "distribution" in tol
        assert tol["distribution"] in ("gaussian", "uniform")


# ---------------------------------------------------------------------------
# MonteCarloResultsDialog
# ---------------------------------------------------------------------------


def _dc_op_mc_data(n_runs=5):
    """Build fake MC data for DC Operating Point analysis."""
    results = []
    for i in range(n_runs):
        results.append(
            FakeSimResult(
                success=True,
                data={"node_voltages": {"out": 4.9 + i * 0.05, "in": 5.0}},
            )
        )
    return {
        "base_analysis_type": "DC Operating Point",
        "results": results,
    }


def _transient_mc_data(n_runs=3):
    """Build fake MC data for Transient analysis."""
    results = []
    for i in range(n_runs):
        results.append(
            FakeSimResult(
                success=True,
                data=[
                    {"time": 0.0, "out": 0.0},
                    {"time": 0.5e-3, "out": 2.5 + i * 0.1},
                    {"time": 1e-3, "out": 5.0 + i * 0.2},
                ],
            )
        )
    return {
        "base_analysis_type": "Transient",
        "results": results,
    }


class TestMonteCarloResultsDialog:
    def test_opens_with_dc_op_data(self, qtbot):
        dlg = MonteCarloResultsDialog(_dc_op_mc_data())
        qtbot.addWidget(dlg)
        assert "Monte Carlo" in dlg.windowTitle()

    def test_metric_combo_populated(self, qtbot):
        dlg = MonteCarloResultsDialog(_dc_op_mc_data())
        qtbot.addWidget(dlg)
        assert dlg._metric_combo.count() >= 1

    def test_summary_contains_statistics(self, qtbot):
        dlg = MonteCarloResultsDialog(_dc_op_mc_data())
        qtbot.addWidget(dlg)
        text = dlg._summary.toPlainText()
        assert "Mean" in text
        assert "Std" in text

    def test_histogram_updates_on_metric_change(self, qtbot):
        dlg = MonteCarloResultsDialog(_dc_op_mc_data())
        qtbot.addWidget(dlg)

        if dlg._metric_combo.count() >= 2:
            dlg._metric_combo.setCurrentIndex(1)
            text = dlg._summary.toPlainText()
            assert "Mean" in text

    def test_opens_with_transient_data(self, qtbot):
        dlg = MonteCarloResultsDialog(_transient_mc_data())
        qtbot.addWidget(dlg)
        assert dlg._metric_combo.count() >= 1

    def test_empty_results_handled(self, qtbot):
        mc_data = {"base_analysis_type": "DC Operating Point", "results": []}
        dlg = MonteCarloResultsDialog(mc_data)
        qtbot.addWidget(dlg)
        assert dlg._metric_combo.count() == 0
        assert "No metric data" in dlg._summary.toPlainText()

    def test_failed_results_skipped(self, qtbot):
        results = [FakeSimResult(success=False, data=None) for _ in range(3)]
        mc_data = {"base_analysis_type": "DC Operating Point", "results": results}
        dlg = MonteCarloResultsDialog(mc_data)
        qtbot.addWidget(dlg)
        assert dlg._metric_combo.count() == 0

    def test_close_event_cleans_up_figures(self, qtbot):
        dlg = MonteCarloResultsDialog(_dc_op_mc_data())
        qtbot.addWidget(dlg)

        import matplotlib.pyplot as plt

        with patch.object(plt, "close") as mock_close:
            dlg.close()
            assert mock_close.call_count >= 2

    def test_dc_sweep_mc_data(self, qtbot):
        results = []
        for i in range(3):
            results.append(
                FakeSimResult(
                    success=True,
                    data={
                        "headers": ["idx", "v-sweep", "V(out)"],
                        "data": [
                            [0, 0.0, 0.0 + i * 0.1],
                            [1, 5.0, 2.5 + i * 0.1],
                            [2, 10.0, 5.0 + i * 0.1],
                        ],
                    },
                )
            )
        mc_data = {"base_analysis_type": "DC Sweep", "results": results}
        dlg = MonteCarloResultsDialog(mc_data)
        qtbot.addWidget(dlg)
        assert dlg._metric_combo.count() >= 1

    def test_ac_sweep_mc_data(self, qtbot):
        results = []
        for i in range(3):
            results.append(
                FakeSimResult(
                    success=True,
                    data={
                        "frequencies": [100.0, 1000.0, 10000.0],
                        "magnitude": {"out": [1.0, 0.7 + i * 0.01, 0.3]},
                    },
                )
            )
        mc_data = {"base_analysis_type": "AC Sweep", "results": results}
        dlg = MonteCarloResultsDialog(mc_data)
        qtbot.addWidget(dlg)
        assert dlg._metric_combo.count() >= 1
