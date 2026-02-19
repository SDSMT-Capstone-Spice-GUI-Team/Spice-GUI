"""Tests for simulation result history and comparison (issue #232).

Covers: history storage, eviction, pinning, structural change detection,
and integration with SimulationController.
"""

from datetime import datetime, timedelta

import pytest
from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from models.simulation_history import SimulationHistoryManager, SimulationSnapshot

# ---------------------------------------------------------------------------
# SimulationSnapshot tests
# ---------------------------------------------------------------------------


class TestSimulationSnapshot:
    """Test the SimulationSnapshot dataclass."""

    def test_create_snapshot(self):
        snap = SimulationSnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0),
            label="Test Run",
            analysis_type="Transient",
            data={"time": [0, 1], "v(out)": [0, 5]},
        )
        assert snap.label == "Test Run"
        assert snap.analysis_type == "Transient"
        assert snap.pinned is False

    def test_snapshot_to_summary(self):
        snap = SimulationSnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0),
            label="Test Run",
            analysis_type="DC Operating Point",
            data={},
            pinned=True,
        )
        summary = snap.to_summary()
        assert summary["label"] == "Test Run"
        assert summary["analysis_type"] == "DC Operating Point"
        assert summary["pinned"] is True
        assert "timestamp" in summary


# ---------------------------------------------------------------------------
# SimulationHistoryManager tests
# ---------------------------------------------------------------------------


class TestHistoryManagerBasic:
    """Test basic history storage operations."""

    def test_empty_history(self):
        mgr = SimulationHistoryManager()
        assert mgr.count() == 0
        assert mgr.get_latest() is None
        assert mgr.get_all() == []

    def test_add_single_result(self):
        mgr = SimulationHistoryManager()
        snap = mgr.add(
            analysis_type="DC Operating Point",
            data={"v(1)": 5.0},
            label="Run 1",
        )
        assert mgr.count() == 1
        assert snap.label == "Run 1"
        assert snap.analysis_type == "DC Operating Point"

    def test_add_auto_label(self):
        mgr = SimulationHistoryManager()
        snap = mgr.add(analysis_type="Transient", data={})
        assert snap.label.startswith("Run ")

    def test_add_multiple_results(self):
        mgr = SimulationHistoryManager(max_size=5)
        for i in range(3):
            mgr.add(analysis_type="Transient", data={"run": i}, label=f"Run {i}")
        assert mgr.count() == 3

    def test_get_latest(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={"run": 0}, label="First")
        mgr.add(analysis_type="Transient", data={"run": 1}, label="Second")
        assert mgr.get_latest().label == "Second"

    def test_get_by_index(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="First")
        mgr.add(analysis_type="Transient", data={}, label="Second")
        assert mgr.get_by_index(0).label == "First"
        assert mgr.get_by_index(1).label == "Second"

    def test_get_by_index_out_of_range(self):
        mgr = SimulationHistoryManager()
        with pytest.raises(IndexError):
            mgr.get_by_index(0)

    def test_remove_by_index(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="First")
        mgr.add(analysis_type="Transient", data={}, label="Second")
        removed = mgr.remove(0)
        assert removed.label == "First"
        assert mgr.count() == 1
        assert mgr.get_by_index(0).label == "Second"

    def test_get_summaries(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="Run A")
        mgr.add(analysis_type="DC Sweep", data={}, label="Run B")
        summaries = mgr.get_summaries()
        assert len(summaries) == 2
        assert summaries[0]["label"] == "Run A"
        assert summaries[1]["analysis_type"] == "DC Sweep"


# ---------------------------------------------------------------------------
# Eviction tests
# ---------------------------------------------------------------------------


class TestHistoryEviction:
    """Test eviction behavior when history exceeds max_size."""

    def test_eviction_on_overflow(self):
        mgr = SimulationHistoryManager(max_size=3)
        for i in range(5):
            mgr.add(analysis_type="Transient", data={"run": i}, label=f"Run {i}")
        assert mgr.count() == 3
        # Oldest unpinned should be evicted
        assert mgr.get_by_index(0).label == "Run 2"

    def test_eviction_preserves_pinned(self):
        mgr = SimulationHistoryManager(max_size=3)
        mgr.add(analysis_type="Transient", data={}, label="Run 0")
        mgr.pin(0)  # Pin the first
        for i in range(1, 5):
            mgr.add(analysis_type="Transient", data={}, label=f"Run {i}")
        # Pinned Run 0 should still be there
        labels = [s.label for s in mgr.get_all()]
        assert "Run 0" in labels
        assert mgr.count() == 3

    def test_change_max_size(self):
        mgr = SimulationHistoryManager(max_size=5)
        for i in range(5):
            mgr.add(analysis_type="Transient", data={}, label=f"Run {i}")
        assert mgr.count() == 5
        mgr.max_size = 2
        assert mgr.count() == 2

    def test_max_size_validation(self):
        mgr = SimulationHistoryManager()
        with pytest.raises(ValueError, match="at least 1"):
            mgr.max_size = 0


# ---------------------------------------------------------------------------
# Pinning tests
# ---------------------------------------------------------------------------


class TestHistoryPinning:
    """Test snapshot pinning/unpinning."""

    def test_pin_snapshot(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="Run 0")
        mgr.pin(0)
        assert mgr.get_by_index(0).pinned is True

    def test_unpin_snapshot(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="Run 0")
        mgr.pin(0)
        mgr.unpin(0)
        assert mgr.get_by_index(0).pinned is False

    def test_pin_out_of_range(self):
        mgr = SimulationHistoryManager()
        with pytest.raises(IndexError):
            mgr.pin(0)


# ---------------------------------------------------------------------------
# Clear tests
# ---------------------------------------------------------------------------


class TestHistoryClear:
    """Test clearing behavior."""

    def test_clear_all(self):
        mgr = SimulationHistoryManager()
        for i in range(3):
            mgr.add(analysis_type="Transient", data={}, label=f"Run {i}")
        mgr.clear(keep_pinned=False)
        assert mgr.count() == 0

    def test_clear_keeps_pinned(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="Run 0")
        mgr.pin(0)
        mgr.add(analysis_type="Transient", data={}, label="Run 1")
        mgr.clear(keep_pinned=True)
        assert mgr.count() == 1
        assert mgr.get_by_index(0).label == "Run 0"

    def test_clear_default_keeps_pinned(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="Run 0")
        mgr.pin(0)
        mgr.add(analysis_type="Transient", data={}, label="Run 1")
        mgr.clear()
        assert mgr.count() == 1


# ---------------------------------------------------------------------------
# Structural change detection
# ---------------------------------------------------------------------------


class TestStructuralChangeDetection:
    """Test clearing on structural changes."""

    def test_clear_on_different_hash(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, component_hash="hash_v1")
        mgr.add(analysis_type="Transient", data={}, component_hash="hash_v1")
        assert mgr.count() == 2

        cleared = mgr.clear_on_structural_change("hash_v2")
        assert cleared is True
        assert mgr.count() == 0

    def test_no_clear_on_same_hash(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, component_hash="hash_v1")
        mgr.add(analysis_type="Transient", data={}, component_hash="hash_v1")

        cleared = mgr.clear_on_structural_change("hash_v1")
        assert cleared is False
        assert mgr.count() == 2

    def test_clear_on_change_preserves_pinned(self):
        mgr = SimulationHistoryManager()
        mgr.add(analysis_type="Transient", data={}, label="Pinned", component_hash="hash_v1")
        mgr.pin(0)
        mgr.add(
            analysis_type="Transient",
            data={},
            label="Not pinned",
            component_hash="hash_v1",
        )

        cleared = mgr.clear_on_structural_change("hash_v2")
        assert cleared is True
        assert mgr.count() == 1
        assert mgr.get_by_index(0).label == "Pinned"

    def test_no_clear_on_empty_history(self):
        mgr = SimulationHistoryManager()
        cleared = mgr.clear_on_structural_change("any_hash")
        assert cleared is False


# ---------------------------------------------------------------------------
# SimulationController integration
# ---------------------------------------------------------------------------


class TestControllerHistoryIntegration:
    """Test that SimulationController has history and component hash."""

    def test_controller_has_history(self):
        model = CircuitModel()
        ctrl = SimulationController(model)
        assert isinstance(ctrl.history, SimulationHistoryManager)
        assert ctrl.history.count() == 0

    def test_compute_component_hash_deterministic(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=cc)

        cc.add_component("Voltage Source", (0, 0))
        cc.add_component("Resistor", (100, 0))
        cc.add_component("Ground", (0, 100))
        cc.add_wire("V1", 0, "R1", 0)

        hash1 = sim._compute_component_hash()
        hash2 = sim._compute_component_hash()
        assert hash1 == hash2

    def test_component_hash_changes_on_add(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=cc)

        cc.add_component("Voltage Source", (0, 0))
        hash_before = sim._compute_component_hash()

        cc.add_component("Resistor", (100, 0))
        hash_after = sim._compute_component_hash()

        assert hash_before != hash_after

    def test_component_hash_stable_on_value_change(self):
        model = CircuitModel()
        cc = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=cc)

        r1 = cc.add_component("Resistor", (100, 0))
        hash_before = sim._compute_component_hash()

        r1.value = "10k"
        hash_after = sim._compute_component_hash()

        assert hash_before == hash_after

    def test_record_to_history(self):
        """Test _record_to_history adds successful results."""
        from controllers.simulation_controller import SimulationResult

        model = CircuitModel()
        cc = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=cc)

        cc.add_component("Voltage Source", (0, 0))
        cc.add_component("Resistor", (100, 0))
        gnd = cc.add_component("Ground", (0, 100))
        cc.add_wire("V1", 0, "R1", 0)
        cc.add_wire("R1", 1, gnd.component_id, 0)
        cc.add_wire("V1", 1, gnd.component_id, 0)

        result = SimulationResult(
            success=True,
            analysis_type="DC Operating Point",
            data={"v(1)": 5.0},
            netlist="test netlist",
        )
        sim._record_to_history(result)
        assert sim.history.count() == 1

    def test_record_skips_failed_results(self):
        """Failed results should not be stored in history."""
        from controllers.simulation_controller import SimulationResult

        model = CircuitModel()
        sim = SimulationController(model)

        result = SimulationResult(success=False, error="Failed")
        sim._record_to_history(result)
        assert sim.history.count() == 0

    def test_record_skips_null_data(self):
        """Results with no data should not be stored."""
        from controllers.simulation_controller import SimulationResult

        model = CircuitModel()
        sim = SimulationController(model)

        result = SimulationResult(success=True, analysis_type="DC Operating Point", data=None)
        sim._record_to_history(result)
        assert sim.history.count() == 0

    def test_history_default_max_size(self):
        """Default history size should be 5."""
        model = CircuitModel()
        sim = SimulationController(model)
        assert sim.history.max_size == 5
