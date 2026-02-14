"""Tests for simulation.result_history — SimulationHistory and HistoryEntry."""

import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Import result_history directly to bypass simulation/__init__.py which
# pulls in NgspiceRunner -> GUI -> matplotlib.use("QtAgg") in headless envs.
_mod_path = Path(__file__).resolve().parent.parent.parent / "simulation" / "result_history.py"
_spec = importlib.util.spec_from_file_location("simulation.result_history", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("simulation.result_history", _mod)
_spec.loader.exec_module(_mod)

DEFAULT_MAX_HISTORY = _mod.DEFAULT_MAX_HISTORY
HistoryEntry = _mod.HistoryEntry
SimulationHistory = _mod.SimulationHistory


# ---------------------------------------------------------------------------
# HistoryEntry
# ---------------------------------------------------------------------------


class TestHistoryEntry:
    def test_summary_success(self):
        entry = HistoryEntry(
            timestamp=datetime(2025, 6, 15, 10, 30, 0),
            analysis_type="DC Operating Point",
            success=True,
        )
        assert "DC Operating Point" in entry.summary
        assert "OK" in entry.summary
        assert "2025-06-15 10:30:00" in entry.summary

    def test_summary_failure(self):
        entry = HistoryEntry(
            timestamp=datetime(2025, 6, 15, 10, 30, 0),
            analysis_type="AC Sweep",
            success=False,
        )
        assert "FAIL" in entry.summary

    def test_summary_with_label(self):
        entry = HistoryEntry(
            timestamp=datetime(2025, 6, 15, 10, 30, 0),
            analysis_type="Transient",
            success=True,
            label="baseline run",
        )
        assert "(baseline run)" in entry.summary


# ---------------------------------------------------------------------------
# SimulationHistory — basic operations
# ---------------------------------------------------------------------------


class TestSimulationHistoryBasic:
    def test_empty_by_default(self):
        h = SimulationHistory()
        assert len(h) == 0
        assert not h
        assert h.latest() is None

    def test_add_and_latest(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True, data={"node_voltages": {"v1": 5.0}})
        assert len(h) == 1
        assert h
        assert h.latest().analysis_type == "DC Operating Point"

    def test_newest_first_ordering(self):
        h = SimulationHistory()
        t1 = datetime(2025, 1, 1, 10, 0)
        t2 = datetime(2025, 1, 1, 11, 0)
        h.add("DC Operating Point", True, timestamp=t1)
        h.add("AC Sweep", True, timestamp=t2)
        assert h[0].analysis_type == "AC Sweep"  # newest
        assert h[1].analysis_type == "DC Operating Point"

    def test_entries_returns_copy(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True)
        entries = h.entries
        entries.clear()
        assert len(h) == 1  # internal list unaffected

    def test_getitem(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True)
        assert h[0].analysis_type == "DC Operating Point"

    def test_getitem_out_of_range(self):
        h = SimulationHistory()
        with pytest.raises(IndexError):
            h[0]


# ---------------------------------------------------------------------------
# Capacity / eviction
# ---------------------------------------------------------------------------


class TestSimulationHistoryCapacity:
    def test_default_max(self):
        h = SimulationHistory()
        assert h.max_entries == DEFAULT_MAX_HISTORY

    def test_custom_max(self):
        h = SimulationHistory(max_entries=3)
        assert h.max_entries == 3

    def test_min_max_is_one(self):
        h = SimulationHistory(max_entries=0)
        assert h.max_entries == 1

    def test_eviction_drops_oldest(self):
        h = SimulationHistory(max_entries=3)
        for i in range(5):
            h.add("DC Operating Point", True, label=f"run-{i}")
        assert len(h) == 3
        labels = [e.label for e in h.entries]
        assert labels == ["run-4", "run-3", "run-2"]


# ---------------------------------------------------------------------------
# Mutators
# ---------------------------------------------------------------------------


class TestSimulationHistoryMutators:
    def test_clear(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True)
        h.add("AC Sweep", True)
        h.clear()
        assert len(h) == 0

    def test_remove(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True, label="a")
        h.add("AC Sweep", True, label="b")
        removed = h.remove(0)
        assert removed.label == "b"
        assert len(h) == 1
        assert h[0].label == "a"

    def test_set_label(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True)
        h.set_label(0, "golden reference")
        assert h[0].label == "golden reference"


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


class TestSimulationHistoryFilters:
    def test_filter_by_type(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True)
        h.add("AC Sweep", True)
        h.add("DC Operating Point", False)
        results = h.filter_by_type("DC Operating Point")
        assert len(results) == 2
        assert all(e.analysis_type == "DC Operating Point" for e in results)

    def test_successful(self):
        h = SimulationHistory()
        h.add("DC Operating Point", True)
        h.add("AC Sweep", False)
        h.add("Transient", True)
        results = h.successful()
        assert len(results) == 2
        assert all(e.success for e in results)


# ---------------------------------------------------------------------------
# Comparison — DC Operating Point
# ---------------------------------------------------------------------------


class TestCompareOPResults:
    def _make_op_entry(self, voltages, currents=None, label=""):
        data = {"node_voltages": voltages}
        if currents:
            data["branch_currents"] = currents
        return HistoryEntry(
            timestamp=datetime.now(),
            analysis_type="DC Operating Point",
            success=True,
            data=data,
            label=label,
        )

    def test_basic_comparison(self):
        a = self._make_op_entry({"v1": 5.0, "v2": 3.3})
        b = self._make_op_entry({"v1": 5.1, "v2": 3.3})
        diff = SimulationHistory.compare_op_results(a, b)
        assert "node_voltages:v1" in diff
        assert diff["node_voltages:v1"]["delta"] == pytest.approx(0.1)
        assert diff["node_voltages:v2"]["delta"] == pytest.approx(0.0)

    def test_comparison_with_currents(self):
        a = self._make_op_entry({"v1": 5.0}, currents={"i(v1)": 0.001})
        b = self._make_op_entry({"v1": 5.0}, currents={"i(v1)": 0.002})
        diff = SimulationHistory.compare_op_results(a, b)
        assert "branch_currents:i(v1)" in diff
        assert diff["branch_currents:i(v1)"]["delta"] == pytest.approx(0.001)

    def test_comparison_missing_in_one(self):
        a = self._make_op_entry({"v1": 5.0, "v2": 3.3})
        b = self._make_op_entry({"v1": 5.0})
        diff = SimulationHistory.compare_op_results(a, b)
        assert diff["node_voltages:v2"]["b"] is None
        assert diff["node_voltages:v2"]["delta"] is None

    def test_comparison_bad_data_raises(self):
        a = HistoryEntry(
            timestamp=datetime.now(),
            analysis_type="DC Operating Point",
            success=True,
            data="not a dict",
        )
        b = self._make_op_entry({"v1": 5.0})
        with pytest.raises(ValueError):
            SimulationHistory.compare_op_results(a, b)


# ---------------------------------------------------------------------------
# Comparison — DC Sweep
# ---------------------------------------------------------------------------


class TestCompareDCSweep:
    def _make_sweep_entry(self, headers, data):
        return HistoryEntry(
            timestamp=datetime.now(),
            analysis_type="DC Sweep",
            success=True,
            data={"headers": headers, "data": data},
        )

    def test_same_structure(self):
        a = self._make_sweep_entry(["V1", "v(out)"], [[0, 1], [1, 2]])
        b = self._make_sweep_entry(["V1", "v(out)"], [[0, 1.1], [1, 2.1]])
        diff = SimulationHistory.compare_dc_sweep_results(a, b)
        assert diff["shared_headers"] == ["V1", "v(out)"]
        assert diff["same_length"] is True
        assert diff["only_in_a"] == []
        assert diff["only_in_b"] == []

    def test_different_headers(self):
        a = self._make_sweep_entry(["V1", "v(out)"], [[0, 1]])
        b = self._make_sweep_entry(["V1", "v(in)"], [[0, 2]])
        diff = SimulationHistory.compare_dc_sweep_results(a, b)
        assert "v(out)" in diff["only_in_a"]
        assert "v(in)" in diff["only_in_b"]

    def test_different_lengths(self):
        a = self._make_sweep_entry(["V1"], [[0], [1]])
        b = self._make_sweep_entry(["V1"], [[0], [1], [2]])
        diff = SimulationHistory.compare_dc_sweep_results(a, b)
        assert diff["same_length"] is False
        assert diff["rows_a"] == 2
        assert diff["rows_b"] == 3

    def test_bad_data_raises(self):
        a = HistoryEntry(
            timestamp=datetime.now(),
            analysis_type="DC Sweep",
            success=True,
            data="not sweep data",
        )
        b = self._make_sweep_entry(["V1"], [[0]])
        with pytest.raises(ValueError):
            SimulationHistory.compare_dc_sweep_results(a, b)


# ---------------------------------------------------------------------------
# Integration with SimulationController
# ---------------------------------------------------------------------------


class TestControllerHistoryIntegration:
    def test_controller_has_history(self):
        from controllers.simulation_controller import SimulationController

        ctrl = SimulationController()
        assert ctrl.history is not None
        assert len(ctrl.history) == 0

    def test_history_is_lazily_created(self):
        from controllers.simulation_controller import SimulationController

        ctrl = SimulationController()
        assert ctrl._history is None
        _ = ctrl.history
        assert ctrl._history is not None

    def test_record_result(self):
        from controllers.simulation_controller import SimulationController, SimulationResult

        ctrl = SimulationController()
        result = SimulationResult(
            success=True,
            analysis_type="DC Operating Point",
            data={"node_voltages": {"v1": 5.0}},
            netlist="* test",
        )
        ctrl._record_result(result)
        assert len(ctrl.history) == 1
        assert ctrl.history[0].analysis_type == "DC Operating Point"
        assert ctrl.history[0].data == {"node_voltages": {"v1": 5.0}}
