"""Integration tests for auto-save and crash recovery (Issue #357).

Verifies the full round-trip lifecycle through FileController:
  auto_save -> has_auto_save -> load_auto_save -> clear_auto_save

Covers:
- auto_save() creates recovery file with correct content
- load_auto_save() restores model state (components, wires, analysis)
- _autosave_source metadata is preserved and returned
- has_auto_save() returns True/False correctly
- clear_auto_save() removes the file
- auto_save() after modifications -> load_auto_save() reflects latest state
- Error handling: corrupted auto-save file returns None
- Cross-controller visibility through shared model
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from controllers.circuit_controller import CircuitController
from controllers.file_controller import FileController
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_circuit_via_controller():
    """Build a V1-R1-GND circuit using CircuitController (integration path)."""
    model = CircuitModel()
    cc = CircuitController(model)
    fc = FileController(model, circuit_ctrl=cc)

    v1 = cc.add_component("Voltage Source", (0, 0))
    r1 = cc.add_component("Resistor", (100, 0))
    gnd = cc.add_component("Ground", (100, 100))
    cc.add_wire(v1.component_id, 0, r1.component_id, 0)
    cc.add_wire(r1.component_id, 1, gnd.component_id, 0)
    cc.add_wire(v1.component_id, 1, gnd.component_id, 0)

    return model, cc, fc


class EventLog:
    """Simple observer that records (event, data) tuples."""

    def __init__(self):
        self.events = []

    def __call__(self, event, data):
        self.events.append((event, data))

    def count(self, event_name):
        return sum(1 for e, _ in self.events if e == event_name)


# ---------------------------------------------------------------------------
# Full lifecycle: save -> detect -> load -> verify -> clear
# ---------------------------------------------------------------------------


class TestAutoSaveFullLifecycle:
    """End-to-end auto-save lifecycle through real controllers."""

    def test_full_lifecycle(self, tmp_path):
        """save -> has_auto_save -> load -> verify state -> clear."""
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        # Step 1: No auto-save initially
        assert not fc.has_auto_save()

        # Step 2: auto_save creates file
        fc.auto_save()
        assert fc.has_auto_save()
        assert Path(autosave).exists()

        # Step 3: Load into fresh controller
        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        source = fc2.load_auto_save()
        assert source is not None

        # Step 4: Verify restored state
        assert len(model2.components) == 3
        assert len(model2.wires) == 3
        comp_types = {c.component_type for c in model2.components.values()}
        assert "Voltage Source" in comp_types
        assert "Resistor" in comp_types
        assert "Ground" in comp_types

        # Step 5: Clear auto-save
        fc2.clear_auto_save()
        assert not fc2.has_auto_save()
        assert not Path(autosave).exists()

    def test_auto_save_does_not_alter_controller_state(self, tmp_path):
        """auto_save must not change current_file or other state."""
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        assert fc.current_file is None
        fc.auto_save()
        assert fc.current_file is None

    def test_auto_save_with_source_file(self, tmp_path):
        """auto_save stores current_file path and load returns it."""
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        circuit_path = tmp_path / "my_circuit.json"
        fc.current_file = circuit_path
        fc.auto_save()

        # Verify on disk
        raw = json.loads(Path(autosave).read_text())
        assert raw["_autosave_source"] == str(circuit_path)

        # Load and verify returned path
        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        source = fc2.load_auto_save()
        assert source == str(circuit_path)
        assert fc2.current_file == circuit_path

    def test_auto_save_unsaved_circuit_returns_empty_source(self, tmp_path):
        """When no current_file, auto_save stores empty string."""
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        source = fc2.load_auto_save()
        assert source == ""


# ---------------------------------------------------------------------------
# State verification after restore
# ---------------------------------------------------------------------------


class TestAutoSaveStateRestore:
    """Verify that load_auto_save correctly restores all model attributes."""

    def test_restores_components_with_correct_values(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        # Modify a value before saving
        v_ids = [cid for cid, c in model.components.items() if c.component_type == "Voltage Source"]
        cc.update_component_value(v_ids[0], "12V")

        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        restored_v = model2.components[v_ids[0]]
        assert restored_v.value == "12V"
        assert restored_v.component_type == "Voltage Source"

    def test_restores_wire_connections(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert len(model2.wires) == 3
        # Verify wire terminal references are valid component IDs
        comp_ids = set(model2.components.keys())
        for wire in model2.wires:
            assert wire.start_component_id in comp_ids
            assert wire.end_component_id in comp_ids

    def test_restores_analysis_settings(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        model.analysis_type = "Transient"
        model.analysis_params = {"duration": "1ms", "step": "1us"}
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert model2.analysis_type == "Transient"
        assert model2.analysis_params["duration"] == "1ms"
        assert model2.analysis_params["step"] == "1us"

    def test_restores_component_counter(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert model2.component_counter == model.component_counter

    def test_restores_node_graph(self, tmp_path):
        """Nodes and terminal_to_node should be rebuilt on load."""
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert len(model2.nodes) > 0
        assert len(model2.terminal_to_node) > 0

    def test_restores_rotation_and_flip(self, tmp_path):
        """Component rotation and flip state should survive auto-save."""
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        # Rotate and flip a component
        r_ids = [cid for cid, c in model.components.items() if c.component_type == "Resistor"]
        cc.rotate_component(r_ids[0])
        cc.flip_component(r_ids[0], horizontal=True)
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        restored = model2.components[r_ids[0]]
        assert restored.rotation == 90
        assert restored.flip_h is True


# ---------------------------------------------------------------------------
# _autosave_source metadata handling
# ---------------------------------------------------------------------------


class TestAutoSaveMetadata:
    """Verify _autosave_source does not leak into restored model."""

    def test_autosave_source_not_in_restored_model(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.current_file = tmp_path / "original.json"
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        # _autosave_source must not appear in model serialization
        data = model2.to_dict()
        assert "_autosave_source" not in data

    def test_autosave_source_present_on_disk(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.current_file = tmp_path / "circuit.json"
        fc.auto_save()

        raw = json.loads(Path(autosave).read_text())
        assert "_autosave_source" in raw
        assert raw["_autosave_source"] == str(tmp_path / "circuit.json")


# ---------------------------------------------------------------------------
# Modification then re-save
# ---------------------------------------------------------------------------


class TestAutoSaveAfterModification:
    """auto_save after circuit changes should reflect the latest state."""

    def test_modification_reflected_after_resave(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        # Add another component
        c_new = cc.add_component("Capacitor", (200, 0))
        fc.auto_save()  # overwrite with updated state

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert len(model2.components) == 4
        assert c_new.component_id in model2.components
        assert model2.components[c_new.component_id].component_type == "Capacitor"

    def test_value_change_reflected_after_resave(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        r_ids = [cid for cid, c in model.components.items() if c.component_type == "Resistor"]
        cc.update_component_value(r_ids[0], "47k")
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert model2.components[r_ids[0]].value == "47k"

    def test_wire_removal_reflected_after_resave(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc.auto_save()

        # Remove a wire (index 0)
        cc.remove_wire(0)
        fc.auto_save()

        model2 = CircuitModel()
        fc2 = FileController(model2, autosave_file=autosave)
        fc2.load_auto_save()

        assert len(model2.wires) == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestAutoSaveErrorHandling:
    """Graceful handling of corrupted or missing auto-save files."""

    def test_corrupt_json_returns_none(self, tmp_path):
        autosave = tmp_path / "recovery.json"
        autosave.write_text("{not valid json!!!")
        fc = FileController(autosave_file=str(autosave))
        assert fc.load_auto_save() is None

    def test_invalid_structure_returns_none(self, tmp_path):
        """Valid JSON but missing required circuit fields."""
        autosave = tmp_path / "recovery.json"
        autosave.write_text(json.dumps({"foo": "bar"}))
        fc = FileController(autosave_file=str(autosave))
        assert fc.load_auto_save() is None

    def test_missing_file_returns_none(self, tmp_path):
        autosave = str(tmp_path / "nonexistent.json")
        fc = FileController(autosave_file=autosave)
        assert fc.load_auto_save() is None

    def test_empty_file_returns_none(self, tmp_path):
        autosave = tmp_path / "recovery.json"
        autosave.write_text("")
        fc = FileController(autosave_file=str(autosave))
        assert fc.load_auto_save() is None

    def test_missing_components_returns_none(self, tmp_path):
        """JSON with wires but no components should fail validation."""
        autosave = tmp_path / "recovery.json"
        autosave.write_text(json.dumps({"wires": [], "_autosave_source": ""}))
        fc = FileController(autosave_file=str(autosave))
        assert fc.load_auto_save() is None

    def test_clear_auto_save_no_error_when_missing(self, tmp_path):
        autosave = str(tmp_path / "nonexistent.json")
        fc = FileController(autosave_file=autosave)
        fc.clear_auto_save()  # Should not raise

    def test_has_auto_save_false_after_corrupt_load(self, tmp_path):
        """has_auto_save returns True even if file is corrupt (it checks existence)."""
        autosave = tmp_path / "recovery.json"
        autosave.write_text("corrupt")
        fc = FileController(autosave_file=str(autosave))
        assert fc.has_auto_save() is True
        assert fc.load_auto_save() is None
        # File still exists after failed load
        assert fc.has_auto_save() is True


# ---------------------------------------------------------------------------
# Cross-controller visibility
# ---------------------------------------------------------------------------


class TestAutoSaveCrossController:
    """Auto-save written by one controller should be loadable by another."""

    def test_second_controller_sees_auto_save(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model1, cc1, fc1 = _build_circuit_via_controller()
        fc1._autosave_file = Path(autosave)
        fc1.auto_save()

        # Second independent controller pair
        model2 = CircuitModel()
        cc2 = CircuitController(model2)
        fc2 = FileController(model2, circuit_ctrl=cc2, autosave_file=autosave)

        assert fc2.has_auto_save()
        source = fc2.load_auto_save()
        assert source is not None
        assert len(model2.components) == len(model1.components)
        assert len(model2.wires) == len(model1.wires)

    def test_load_auto_save_fires_observer_event(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model1, cc1, fc1 = _build_circuit_via_controller()
        fc1._autosave_file = Path(autosave)
        fc1.auto_save()

        model2 = CircuitModel()
        cc2 = CircuitController(model2)
        fc2 = FileController(model2, circuit_ctrl=cc2, autosave_file=autosave)

        log = EventLog()
        cc2.add_observer(log)
        fc2.load_auto_save()

        assert log.count("model_loaded") == 1

    def test_auto_save_isolation_from_normal_save(self, tmp_path):
        """auto_save should not affect normal save/load paths."""
        autosave = str(tmp_path / "recovery.json")
        circuit_file = tmp_path / "circuit.json"

        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)

        # Save normally
        fc.save_circuit(circuit_file)
        assert fc.current_file == circuit_file

        # Auto-save should not change current_file
        fc.auto_save()
        assert fc.current_file == circuit_file

        # Normal load should still work
        model2 = CircuitModel()
        fc2 = FileController(model2)
        fc2.load_circuit(circuit_file)
        assert len(model2.components) == 3

    def test_auto_save_does_not_update_session(self, tmp_path):
        """auto_save must not write to session file."""
        autosave = str(tmp_path / "recovery.json")
        session = str(tmp_path / "session.txt")
        model, cc, fc = _build_circuit_via_controller()
        fc._autosave_file = Path(autosave)
        fc._session_file = session

        fc.auto_save()

        # Session file should not exist (auto_save never calls _save_session)
        assert not Path(session).exists()
