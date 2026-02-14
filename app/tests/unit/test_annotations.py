"""Tests for text annotation CRUD, undo/redo, and persistence (issue #229).

Verifies that annotations can be added, deleted, edited through the
controller, persisted via CircuitModel, and undone/redone via commands.
"""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import (AddAnnotationCommand,
                                  DeleteAnnotationCommand,
                                  EditAnnotationCommand)
from models.annotation import AnnotationData
from models.circuit import CircuitModel


class TestAnnotationData:
    """Test AnnotationData model class."""

    def test_default_values(self):
        ann = AnnotationData()
        assert ann.text == "Annotation"
        assert ann.x == 0.0
        assert ann.y == 0.0
        assert ann.font_size == 10
        assert ann.bold is False
        assert ann.color == "#FFFFFF"

    def test_custom_values(self):
        ann = AnnotationData(
            text="Hello", x=100.0, y=200.0, font_size=14, bold=True, color="#FF0000"
        )
        assert ann.text == "Hello"
        assert ann.x == 100.0
        assert ann.y == 200.0
        assert ann.font_size == 14
        assert ann.bold is True
        assert ann.color == "#FF0000"

    def test_to_dict(self):
        ann = AnnotationData(text="Test", x=50.0, y=75.0)
        d = ann.to_dict()
        assert d["text"] == "Test"
        assert d["x"] == 50.0
        assert d["y"] == 75.0
        assert d["font_size"] == 10
        assert d["bold"] is False
        assert d["color"] == "#FFFFFF"

    def test_from_dict(self):
        d = {
            "text": "Loaded",
            "x": 10.0,
            "y": 20.0,
            "font_size": 12,
            "bold": True,
            "color": "#00FF00",
        }
        ann = AnnotationData.from_dict(d)
        assert ann.text == "Loaded"
        assert ann.x == 10.0
        assert ann.y == 20.0
        assert ann.font_size == 12
        assert ann.bold is True
        assert ann.color == "#00FF00"

    def test_from_dict_defaults(self):
        ann = AnnotationData.from_dict({})
        assert ann.text == "Annotation"
        assert ann.x == 0.0

    def test_roundtrip(self):
        original = AnnotationData(text="Roundtrip", x=42.0, y=84.0, bold=True)
        restored = AnnotationData.from_dict(original.to_dict())
        assert restored.text == original.text
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.bold == original.bold


class TestCircuitModelAnnotations:
    """Test annotations in CircuitModel."""

    def test_model_has_empty_annotations_by_default(self):
        model = CircuitModel()
        assert model.annotations == []

    def test_model_clear_clears_annotations(self):
        model = CircuitModel()
        model.annotations.append(AnnotationData(text="Test"))
        model.clear()
        assert model.annotations == []

    def test_model_to_dict_no_annotations(self):
        model = CircuitModel()
        d = model.to_dict()
        assert "annotations" not in d

    def test_model_to_dict_with_annotations(self):
        model = CircuitModel()
        model.annotations.append(AnnotationData(text="Note 1", x=10.0, y=20.0))
        d = model.to_dict()
        assert "annotations" in d
        assert len(d["annotations"]) == 1
        assert d["annotations"][0]["text"] == "Note 1"

    def test_model_from_dict_no_annotations(self):
        d = {"components": [], "wires": []}
        model = CircuitModel.from_dict(d)
        assert model.annotations == []

    def test_model_from_dict_with_annotations(self):
        d = {
            "components": [],
            "wires": [],
            "annotations": [
                {"text": "A", "x": 1.0, "y": 2.0},
                {"text": "B", "x": 3.0, "y": 4.0},
            ],
        }
        model = CircuitModel.from_dict(d)
        assert len(model.annotations) == 2
        assert model.annotations[0].text == "A"
        assert model.annotations[1].text == "B"

    def test_model_roundtrip_with_annotations(self):
        model = CircuitModel()
        model.annotations.append(
            AnnotationData(text="Persist", x=100.0, y=200.0, bold=True)
        )
        d = model.to_dict()
        restored = CircuitModel.from_dict(d)
        assert len(restored.annotations) == 1
        assert restored.annotations[0].text == "Persist"
        assert restored.annotations[0].x == 100.0
        assert restored.annotations[0].bold is True


class TestControllerAnnotations:
    """Test annotation operations through CircuitController."""

    def test_add_annotation(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ann = AnnotationData(text="Test", x=50.0, y=60.0)
        idx = ctrl.add_annotation(ann)
        assert idx == 0
        assert len(model.annotations) == 1
        assert model.annotations[0].text == "Test"

    def test_add_annotation_fires_event(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        events = []
        ctrl.add_observer(lambda e, d: events.append(e))
        ctrl.add_annotation(AnnotationData(text="Event"))
        assert "annotation_added" in events

    def test_remove_annotation(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="ToDelete"))
        assert len(model.annotations) == 1
        ctrl.remove_annotation(0)
        assert len(model.annotations) == 0

    def test_remove_annotation_fires_event(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="ToDelete"))
        events = []
        ctrl.add_observer(lambda e, d: events.append(e))
        ctrl.remove_annotation(0)
        assert "annotation_removed" in events

    def test_update_annotation_text(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="Original"))
        ctrl.update_annotation_text(0, "Updated")
        assert model.annotations[0].text == "Updated"

    def test_update_annotation_fires_event(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="Original"))
        events = []
        ctrl.add_observer(lambda e, d: events.append(e))
        ctrl.update_annotation_text(0, "Updated")
        assert "annotation_updated" in events

    def test_remove_invalid_index_is_noop(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.remove_annotation(5)  # should not crash
        assert len(model.annotations) == 0

    def test_update_invalid_index_is_noop(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.update_annotation_text(5, "noop")  # should not crash


class TestAnnotationCommands:
    """Test undo/redo commands for annotations."""

    def test_add_annotation_command_execute(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Cmd"))
        cmd.execute()
        assert len(model.annotations) == 1
        assert model.annotations[0].text == "Cmd"

    def test_add_annotation_command_undo(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Cmd"))
        cmd.execute()
        cmd.undo()
        assert len(model.annotations) == 0

    def test_add_annotation_command_redo(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Cmd"))
        cmd.execute()
        cmd.undo()
        cmd.execute()
        assert len(model.annotations) == 1

    def test_delete_annotation_command_execute(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="ToDelete"))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert len(model.annotations) == 0

    def test_delete_annotation_command_undo(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="ToRestore"))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        cmd.execute()
        assert len(model.annotations) == 0
        cmd.undo()
        assert len(model.annotations) == 1
        assert model.annotations[0].text == "ToRestore"

    def test_edit_annotation_command_execute(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="Before"))
        cmd = EditAnnotationCommand(ctrl, 0, "After")
        cmd.execute()
        assert model.annotations[0].text == "After"

    def test_edit_annotation_command_undo(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="Before"))
        cmd = EditAnnotationCommand(ctrl, 0, "After")
        cmd.execute()
        cmd.undo()
        assert model.annotations[0].text == "Before"

    def test_edit_annotation_command_redo(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="Before"))
        cmd = EditAnnotationCommand(ctrl, 0, "After")
        cmd.execute()
        cmd.undo()
        cmd.execute()
        assert model.annotations[0].text == "After"

    def test_add_command_via_undo_manager(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        cmd = AddAnnotationCommand(ctrl, AnnotationData(text="Managed"))
        ctrl.execute_command(cmd)
        assert len(model.annotations) == 1
        ctrl.undo()
        assert len(model.annotations) == 0
        ctrl.redo()
        assert len(model.annotations) == 1

    def test_delete_command_via_undo_manager(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        ctrl.add_annotation(AnnotationData(text="Managed"))
        cmd = DeleteAnnotationCommand(ctrl, 0)
        ctrl.execute_command(cmd)
        assert len(model.annotations) == 0
        ctrl.undo()
        assert len(model.annotations) == 1

    def test_command_descriptions(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        add_cmd = AddAnnotationCommand(ctrl, AnnotationData())
        del_cmd = DeleteAnnotationCommand(ctrl, 0)
        edit_cmd = EditAnnotationCommand(ctrl, 0, "x")
        assert "annotation" in add_cmd.get_description().lower()
        assert "annotation" in del_cmd.get_description().lower()
        assert "annotation" in edit_cmd.get_description().lower()


class TestAnnotationPersistence:
    """Test that annotations survive save/load round-trips via the model."""

    def test_save_load_preserves_annotations(self):
        model = CircuitModel()
        model.annotations.append(AnnotationData(text="Saved", x=10.0, y=20.0))
        model.annotations.append(
            AnnotationData(text="Also Saved", x=30.0, y=40.0, bold=True)
        )

        data = model.to_dict()
        restored = CircuitModel.from_dict(data)

        assert len(restored.annotations) == 2
        assert restored.annotations[0].text == "Saved"
        assert restored.annotations[1].text == "Also Saved"
        assert restored.annotations[1].bold is True

    def test_save_without_annotations(self):
        model = CircuitModel()
        data = model.to_dict()
        assert "annotations" not in data

    def test_load_old_format_without_annotations(self):
        data = {"components": [], "wires": []}
        model = CircuitModel.from_dict(data)
        assert model.annotations == []
