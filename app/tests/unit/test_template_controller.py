"""Tests for TemplateController and template data model."""

import json

import pytest
from controllers.template_controller import TemplateController, validate_template_data
from models.circuit import CircuitModel
from models.component import ComponentData
from models.template import TemplateData, TemplateMetadata
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
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="R1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
    ]
    model.component_counter = {"V": 1, "R": 1, "GND": 1}
    model.rebuild_nodes()
    return model


def _build_metadata(**overrides):
    """Build a TemplateMetadata with defaults."""
    defaults = {
        "title": "Test Template",
        "description": "A test assignment",
        "author": "Dr. Test",
        "created": "2026-02-11",
        "tags": ["test", "basic"],
    }
    defaults.update(overrides)
    return TemplateMetadata(**defaults)


class TestTemplateMetadata:
    def test_to_dict(self):
        meta = _build_metadata()
        d = meta.to_dict()
        assert d["title"] == "Test Template"
        assert d["author"] == "Dr. Test"
        assert d["tags"] == ["test", "basic"]

    def test_from_dict_round_trip(self):
        meta = _build_metadata()
        restored = TemplateMetadata.from_dict(meta.to_dict())
        assert restored.title == meta.title
        assert restored.description == meta.description
        assert restored.author == meta.author
        assert restored.created == meta.created
        assert restored.tags == meta.tags

    def test_from_dict_missing_fields(self):
        meta = TemplateMetadata.from_dict({})
        assert meta.title == ""
        assert meta.tags == []


class TestTemplateData:
    def test_to_dict_minimal(self):
        template = TemplateData(metadata=_build_metadata())
        d = template.to_dict()
        assert d["template_version"] == "1.0"
        assert d["metadata"]["title"] == "Test Template"
        assert "starter_circuit" not in d
        assert "reference_circuit" not in d

    def test_to_dict_with_circuits(self):
        circuit = _build_simple_circuit()
        template = TemplateData(
            metadata=_build_metadata(),
            starter_circuit=circuit.to_dict(),
            reference_circuit=circuit.to_dict(),
        )
        d = template.to_dict()
        assert "starter_circuit" in d
        assert "reference_circuit" in d
        assert "components" in d["starter_circuit"]

    def test_from_dict_round_trip(self):
        circuit = _build_simple_circuit()
        template = TemplateData(
            metadata=_build_metadata(),
            instructions="Build a voltage divider",
            starter_circuit=circuit.to_dict(),
            required_analysis={"type": "DC Operating Point", "params": {}},
        )
        restored = TemplateData.from_dict(template.to_dict())
        assert restored.metadata.title == "Test Template"
        assert restored.instructions == "Build a voltage divider"
        assert restored.starter_circuit is not None
        assert restored.reference_circuit is None
        assert restored.required_analysis["type"] == "DC Operating Point"

    def test_from_dict_missing_optional_fields(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": "Minimal"},
            "instructions": "",
        }
        template = TemplateData.from_dict(data)
        assert template.metadata.title == "Minimal"
        assert template.starter_circuit is None
        assert template.reference_circuit is None
        assert template.required_analysis is None


class TestValidateTemplateData:
    def test_valid_template(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": "Valid Template"},
        }
        validate_template_data(data)  # Should not raise

    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="valid template"):
            validate_template_data([])

    def test_missing_version(self):
        with pytest.raises(ValueError, match="template_version"):
            validate_template_data({"metadata": {"title": "No Version"}})

    def test_missing_metadata(self):
        with pytest.raises(ValueError, match="metadata"):
            validate_template_data({"template_version": "1.0"})

    def test_empty_title(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": ""},
        }
        with pytest.raises(ValueError, match="title"):
            validate_template_data(data)

    def test_invalid_starter_circuit(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": "Bad Circuit"},
            "starter_circuit": {"components": "not a list", "wires": []},
        }
        with pytest.raises(ValueError, match="components"):
            validate_template_data(data)

    def test_null_circuits_ok(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": "No Circuits"},
            "starter_circuit": None,
            "reference_circuit": None,
        }
        validate_template_data(data)  # Should not raise


class TestTemplateControllerSaveLoad:
    def test_save_creates_file(self, tmp_path):
        ctrl = TemplateController()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
        )
        assert filepath.exists()

    def test_save_writes_valid_json(self, tmp_path):
        ctrl = TemplateController()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
        )
        data = json.loads(filepath.read_text())
        assert data["template_version"] == "1.0"
        assert data["metadata"]["title"] == "Test Template"

    def test_save_with_circuits(self, tmp_path):
        ctrl = TemplateController()
        circuit = _build_simple_circuit()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
            starter_circuit=circuit,
            reference_circuit=circuit,
            instructions="Follow the steps.",
        )
        data = json.loads(filepath.read_text())
        assert "starter_circuit" in data
        assert "reference_circuit" in data
        assert data["instructions"] == "Follow the steps."

    def test_load_returns_template_data(self, tmp_path):
        ctrl = TemplateController()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
            instructions="Do this",
        )
        template = ctrl.load_template(filepath)
        assert isinstance(template, TemplateData)
        assert template.metadata.title == "Test Template"
        assert template.instructions == "Do this"

    def test_round_trip_preserves_data(self, tmp_path):
        ctrl = TemplateController()
        circuit = _build_simple_circuit()
        meta = _build_metadata(
            title="Round Trip Test",
            tags=["round", "trip"],
        )
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=meta,
            starter_circuit=circuit,
            reference_circuit=circuit,
            instructions="Step 1: Build it\nStep 2: Test it",
            required_analysis={"type": "AC Sweep", "params": {"fStart": 20}},
        )

        template = ctrl.load_template(filepath)
        assert template.metadata.title == "Round Trip Test"
        assert template.metadata.tags == ["round", "trip"]
        assert template.instructions == "Step 1: Build it\nStep 2: Test it"
        assert template.starter_circuit is not None
        assert template.reference_circuit is not None
        assert template.required_analysis["type"] == "AC Sweep"

    def test_load_invalid_json_raises(self, tmp_path):
        filepath = tmp_path / "bad.spice-template"
        filepath.write_text("not json")
        ctrl = TemplateController()
        with pytest.raises(json.JSONDecodeError):
            ctrl.load_template(filepath)

    def test_load_missing_title_raises(self, tmp_path):
        filepath = tmp_path / "bad.spice-template"
        filepath.write_text(json.dumps({"template_version": "1.0", "metadata": {"title": ""}}))
        ctrl = TemplateController()
        with pytest.raises(ValueError, match="title"):
            ctrl.load_template(filepath)

    def test_load_nonexistent_file_raises(self):
        ctrl = TemplateController()
        with pytest.raises(OSError):
            ctrl.load_template("/nonexistent/path/file.spice-template")


class TestCreateCircuitFromTemplate:
    def test_creates_model_from_starter(self, tmp_path):
        ctrl = TemplateController()
        circuit = _build_simple_circuit()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
            starter_circuit=circuit,
        )
        template = ctrl.load_template(filepath)
        model = ctrl.create_circuit_from_template(template)

        assert isinstance(model, CircuitModel)
        assert "V1" in model.components
        assert "R1" in model.components
        assert len(model.wires) == 2

    def test_creates_empty_model_when_no_starter(self):
        ctrl = TemplateController()
        template = TemplateData(metadata=_build_metadata())
        model = ctrl.create_circuit_from_template(template)
        assert isinstance(model, CircuitModel)
        assert len(model.components) == 0

    def test_applies_required_analysis(self):
        ctrl = TemplateController()
        template = TemplateData(
            metadata=_build_metadata(),
            required_analysis={
                "type": "AC Sweep",
                "params": {"fStart": 20, "fStop": 20000},
            },
        )
        model = ctrl.create_circuit_from_template(template)
        assert model.analysis_type == "AC Sweep"
        assert model.analysis_params["fStart"] == 20

    def test_applies_analysis_to_starter_circuit(self, tmp_path):
        ctrl = TemplateController()
        circuit = _build_simple_circuit()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
            starter_circuit=circuit,
            required_analysis={"type": "Transient", "params": {"duration": 0.01}},
        )
        template = ctrl.load_template(filepath)
        model = ctrl.create_circuit_from_template(template)
        assert model.analysis_type == "Transient"
        assert model.analysis_params["duration"] == 0.01
        assert "V1" in model.components


class TestGetReferenceCircuit:
    def test_returns_model_when_present(self, tmp_path):
        ctrl = TemplateController()
        circuit = _build_simple_circuit()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(),
            reference_circuit=circuit,
        )
        template = ctrl.load_template(filepath)
        ref = ctrl.get_reference_circuit(template)
        assert ref is not None
        assert "V1" in ref.components
        assert "R1" in ref.components

    def test_returns_none_when_absent(self):
        ctrl = TemplateController()
        template = TemplateData(metadata=_build_metadata())
        assert ctrl.get_reference_circuit(template) is None


class TestGetTemplateMetadata:
    def test_returns_metadata_only(self, tmp_path):
        ctrl = TemplateController()
        circuit = _build_simple_circuit()
        filepath = tmp_path / "test.spice-template"
        ctrl.save_as_template(
            filepath=filepath,
            metadata=_build_metadata(title="Metadata Only Test"),
            starter_circuit=circuit,
        )
        meta = ctrl.get_template_metadata(filepath)
        assert isinstance(meta, TemplateMetadata)
        assert meta.title == "Metadata Only Test"
        assert meta.author == "Dr. Test"

    def test_raises_on_invalid_file(self, tmp_path):
        filepath = tmp_path / "bad.spice-template"
        filepath.write_text("[]")
        ctrl = TemplateController()
        with pytest.raises(ValueError, match="valid template"):
            ctrl.get_template_metadata(filepath)

    def test_raises_on_empty_title(self, tmp_path):
        filepath = tmp_path / "bad.spice-template"
        filepath.write_text(json.dumps({"metadata": {"title": ""}}))
        ctrl = TemplateController()
        with pytest.raises(ValueError, match="title"):
            ctrl.get_template_metadata(filepath)
