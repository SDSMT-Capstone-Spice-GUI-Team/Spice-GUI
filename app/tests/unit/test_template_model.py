"""Tests for models.template (TemplateMetadata and TemplateData)."""

from models.template import TemplateData, TemplateMetadata


class TestTemplateMetadata:
    def test_defaults_are_empty_strings(self):
        meta = TemplateMetadata()
        assert meta.title == ""
        assert meta.description == ""
        assert meta.author == ""
        assert meta.created == ""
        assert meta.tags == []

    def test_to_dict_contains_all_fields(self):
        meta = TemplateMetadata(title="Lab", author="Prof", tags=["RC"])
        d = meta.to_dict()
        assert d["title"] == "Lab"
        assert d["author"] == "Prof"
        assert d["tags"] == ["RC"]

    def test_from_dict_round_trip(self):
        original = TemplateMetadata(title="Test", description="Desc", author="A", tags=["x"])
        restored = TemplateMetadata.from_dict(original.to_dict())
        assert restored.title == "Test"
        assert restored.description == "Desc"
        assert restored.author == "A"
        assert restored.tags == ["x"]

    def test_from_dict_with_empty_dict_uses_defaults(self):
        meta = TemplateMetadata.from_dict({})
        assert meta.title == ""
        assert meta.tags == []

    def test_tags_is_independent_copy(self):
        original = TemplateMetadata(tags=["a"])
        d = original.to_dict()
        d["tags"].append("b")
        assert original.tags == ["a"]


class TestTemplateData:
    def test_defaults(self):
        td = TemplateData()
        assert td.template_version == "1.0"
        assert td.instructions == ""
        assert td.starter_circuit is None
        assert td.reference_circuit is None
        assert td.required_analysis is None
        assert td.locked_components == []

    def test_to_dict_excludes_none_optionals(self):
        td = TemplateData()
        d = td.to_dict()
        assert "starter_circuit" not in d
        assert "reference_circuit" not in d
        assert "required_analysis" not in d

    def test_to_dict_includes_present_optionals(self):
        starter = {"components": [], "wires": []}
        reference = {"components": [{"id": "R1"}], "wires": []}
        td = TemplateData(starter_circuit=starter, reference_circuit=reference)
        d = td.to_dict()
        assert "starter_circuit" in d
        assert "reference_circuit" in d

    def test_to_dict_omits_reference_when_identical_to_starter(self):
        """Issue #530: identical circuits must not be duplicated in the bundle."""
        circuit = {"components": [], "wires": []}
        td = TemplateData(starter_circuit=circuit, reference_circuit=circuit)
        d = td.to_dict()
        assert "starter_circuit" in d
        assert "reference_circuit" not in d

    def test_from_dict_falls_back_reference_to_starter(self):
        """Issue #530: when reference_circuit is absent, fall back to starter."""
        circuit = {"components": [], "wires": []}
        td = TemplateData(starter_circuit=circuit)
        d = td.to_dict()
        restored = TemplateData.from_dict(d)
        assert restored.reference_circuit == circuit

    def test_to_dict_excludes_empty_locked_components(self):
        td = TemplateData()
        d = td.to_dict()
        assert "locked_components" not in d

    def test_to_dict_includes_nonempty_locked_components(self):
        td = TemplateData(locked_components=["R1", "C1"])
        d = td.to_dict()
        assert d["locked_components"] == ["R1", "C1"]

    def test_from_dict_round_trip(self):
        meta = TemplateMetadata(title="Lab 1")
        circuit = {"components": [{"id": "R1"}], "wires": []}
        original = TemplateData(
            metadata=meta,
            instructions="Build it.",
            starter_circuit=circuit,
            locked_components=["R1"],
        )
        restored = TemplateData.from_dict(original.to_dict())
        assert restored.metadata.title == "Lab 1"
        assert restored.instructions == "Build it."
        assert restored.starter_circuit == circuit
        assert restored.locked_components == ["R1"]
        # reference_circuit falls back to starter_circuit when absent
        assert restored.reference_circuit == circuit

    def test_from_dict_with_empty_dict_uses_defaults(self):
        td = TemplateData.from_dict({})
        assert td.template_version == "1.0"
        assert td.instructions == ""

    def test_metadata_field_default_is_template_metadata(self):
        td = TemplateData()
        assert isinstance(td.metadata, TemplateMetadata)
