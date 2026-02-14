"""Tests for auto-save and crash recovery (Issue #123)."""

import json
from pathlib import Path

import pytest
from controllers.file_controller import FileController
from models.annotation import AnnotationData
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData


def _build_simple_circuit():
    """Build a simple V1-R1-GND circuit model."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5V",
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 0.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
    )
    model.wires = [
        WireData(start_component_id="V1", start_terminal=1, end_component_id="R1", end_terminal=0),
        WireData(start_component_id="R1", start_terminal=1, end_component_id="GND1", end_terminal=0),
        WireData(start_component_id="V1", start_terminal=0, end_component_id="GND1", end_terminal=0),
    ]
    model.component_counter = {"V": 1, "R": 1, "GND": 1}
    model.rebuild_nodes()
    return model


class TestAutoSave:
    def test_auto_save_creates_file(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()
        assert Path(autosave).exists()

    def test_auto_save_writes_valid_json(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()
        data = json.loads(Path(autosave).read_text())
        assert "components" in data
        assert "wires" in data

    def test_auto_save_includes_source_path(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        source = tmp_path / "my_circuit.json"
        ctrl.current_file = source
        ctrl.auto_save()
        data = json.loads(Path(autosave).read_text())
        assert data["_autosave_source"] == str(source)

    def test_auto_save_empty_source_when_no_file(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()
        data = json.loads(Path(autosave).read_text())
        assert data["_autosave_source"] == ""

    def test_auto_save_does_not_update_current_file(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        assert ctrl.current_file is None
        ctrl.auto_save()
        assert ctrl.current_file is None

    def test_auto_save_preserves_analysis_settings(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model = _build_simple_circuit()
        model.analysis_type = "Transient"
        model.analysis_params = {"duration": 0.01, "step": 1e-5}
        ctrl = FileController(model, autosave_file=autosave)
        ctrl.auto_save()
        data = json.loads(Path(autosave).read_text())
        assert data["analysis_type"] == "Transient"
        assert data["analysis_params"]["duration"] == 0.01


class TestHasAutoSave:
    def test_has_auto_save_false_initially(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(autosave_file=autosave)
        assert not ctrl.has_auto_save()

    def test_has_auto_save_true_after_save(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()
        assert ctrl.has_auto_save()


class TestClearAutoSave:
    def test_clear_removes_file(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()
        assert Path(autosave).exists()
        ctrl.clear_auto_save()
        assert not Path(autosave).exists()

    def test_clear_no_error_when_no_file(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(autosave_file=autosave)
        ctrl.clear_auto_save()  # Should not raise


class TestLoadAutoSave:
    def test_load_restores_components(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()

        # Load into fresh controller
        ctrl2 = FileController(autosave_file=autosave)
        source = ctrl2.load_auto_save()
        assert source is not None
        assert "V1" in ctrl2.model.components
        assert "R1" in ctrl2.model.components
        assert "GND1" in ctrl2.model.components

    def test_load_restores_wires(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        ctrl2.load_auto_save()
        assert len(ctrl2.model.wires) == 3

    def test_load_returns_source_path(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        source_file = tmp_path / "my_circuit.json"
        ctrl.current_file = source_file
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        source = ctrl2.load_auto_save()
        assert source == str(source_file)

    def test_load_returns_empty_string_for_unsaved(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        source = ctrl2.load_auto_save()
        assert source == ""

    def test_load_sets_current_file_from_source(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        source_file = tmp_path / "my_circuit.json"
        ctrl.current_file = source_file
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        ctrl2.load_auto_save()
        assert ctrl2.current_file == source_file

    def test_load_returns_none_when_no_file(self, tmp_path):
        autosave = str(tmp_path / "nonexistent.json")
        ctrl = FileController(autosave_file=autosave)
        assert ctrl.load_auto_save() is None

    def test_load_returns_none_for_corrupt_file(self, tmp_path):
        autosave = tmp_path / "recovery.json"
        autosave.write_text("not json")
        ctrl = FileController(autosave_file=str(autosave))
        assert ctrl.load_auto_save() is None

    def test_load_restores_analysis_settings(self, tmp_path):
        autosave = str(tmp_path / "recovery.json")
        model = _build_simple_circuit()
        model.analysis_type = "AC Sweep"
        model.analysis_params = {"fStart": 1, "fStop": 1e6}
        ctrl = FileController(model, autosave_file=autosave)
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        ctrl2.load_auto_save()
        assert ctrl2.model.analysis_type == "AC Sweep"
        assert ctrl2.model.analysis_params["fStart"] == 1

    def test_load_restores_annotations(self, tmp_path):
        """Regression test for #410: annotations lost on crash recovery."""
        autosave = str(tmp_path / "recovery.json")
        model = _build_simple_circuit()
        model.annotations = [
            AnnotationData(text="Input stage", x=50.0, y=25.0, font_size=12, bold=True, color="#FF0000"),
            AnnotationData(text="Output", x=200.0, y=75.0),
        ]
        ctrl = FileController(model, autosave_file=autosave)
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        ctrl2.load_auto_save()
        assert len(ctrl2.model.annotations) == 2
        assert ctrl2.model.annotations[0].text == "Input stage"
        assert ctrl2.model.annotations[0].x == 50.0
        assert ctrl2.model.annotations[0].bold is True
        assert ctrl2.model.annotations[0].color == "#FF0000"
        assert ctrl2.model.annotations[1].text == "Output"

    def test_load_notifies_observers(self, tmp_path):
        from unittest.mock import MagicMock

        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        mock_ctrl = MagicMock()
        ctrl2.circuit_ctrl = mock_ctrl
        ctrl2.load_auto_save()
        mock_ctrl._notify.assert_called_once_with("model_loaded", None)

    def test_autosave_source_not_in_model_data(self, tmp_path):
        """The _autosave_source metadata should not leak into the model."""
        autosave = str(tmp_path / "recovery.json")
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.current_file = tmp_path / "my_circuit.json"
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave)
        ctrl2.load_auto_save()
        # The model should not have _autosave_source in its serialized form
        model_data = ctrl2.model.to_dict()
        assert "_autosave_source" not in model_data


class TestAutoSaveIntegrationWithSave:
    """Test that auto-save is cleared on explicit save."""

    def test_save_does_not_affect_autosave_directly(self, tmp_path):
        """FileController.save_circuit does not touch auto-save file.
        Clearing is MainWindow's responsibility."""
        autosave = str(tmp_path / "recovery.json")
        circuit_file = tmp_path / "circuit.json"
        ctrl = FileController(_build_simple_circuit(), autosave_file=autosave)
        ctrl.auto_save()
        assert ctrl.has_auto_save()
        ctrl.save_circuit(circuit_file)
        # FileController save_circuit does NOT clear auto-save (that's MainWindow's job)
        assert ctrl.has_auto_save()
