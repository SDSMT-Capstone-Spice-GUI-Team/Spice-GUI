"""Tests for assignment_controller (save/load/validate/extract)."""

import json

import pytest
from controllers.assignment_controller import (
    extract_rubric,
    extract_template,
    load_assignment,
    save_assignment,
    validate_assignment_data,
)
from models.assignment import AssignmentBundle
from models.template import TemplateData, TemplateMetadata

# ---------------------------------------------------------------------------
# validate_assignment_data
# ---------------------------------------------------------------------------


class TestValidateAssignmentData:
    def test_rejects_non_dict(self):
        with pytest.raises(ValueError, match="JSON object"):
            validate_assignment_data([])

    def test_rejects_empty_dict(self):
        with pytest.raises(ValueError, match="template.*rubric"):
            validate_assignment_data({})

    def test_rejects_dict_without_template_or_rubric(self):
        with pytest.raises(ValueError, match="template.*rubric"):
            validate_assignment_data({"other": 1})

    def test_accepts_template_only(self):
        validate_assignment_data({"template": {}})

    def test_accepts_rubric_only(self):
        rubric = {
            "title": "T",
            "total_points": 10,
            "checks": [{"check_id": "c1", "check_type": "ground", "points": 10, "params": {}}],
        }
        validate_assignment_data({"rubric": rubric})

    def test_accepts_both_template_and_rubric(self):
        rubric = {
            "title": "T",
            "total_points": 5,
            "checks": [{"check_id": "c1", "check_type": "ground", "points": 5, "params": {}}],
        }
        validate_assignment_data({"template": {}, "rubric": rubric})

    def test_none_rubric_skips_rubric_validation(self):
        """A null rubric is explicitly allowed (no rubric bundled)."""
        validate_assignment_data({"template": {}, "rubric": None})


# ---------------------------------------------------------------------------
# save_assignment / load_assignment round-trip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundTrip:
    def _make_bundle(self) -> AssignmentBundle:
        meta = TemplateMetadata(title="Lab 1", author="Prof", tags=["RC"])
        template = TemplateData(metadata=meta, instructions="Build a circuit.")
        rubric = {
            "title": "Lab 1 Rubric",
            "total_points": 100,
            "checks": [{"check_id": "c1", "check_type": "ground", "points": 100, "params": {}}],
        }
        return AssignmentBundle(template=template, rubric=rubric)

    def test_save_creates_file(self, tmp_path):
        path = tmp_path / "lab.spice-assignment"
        bundle = self._make_bundle()
        save_assignment(bundle, path)
        assert path.exists()

    def test_save_writes_valid_json(self, tmp_path):
        path = tmp_path / "lab.spice-assignment"
        save_assignment(self._make_bundle(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_load_round_trip_preserves_template(self, tmp_path):
        path = tmp_path / "lab.spice-assignment"
        save_assignment(self._make_bundle(), path)
        loaded = load_assignment(path)
        assert loaded.template is not None
        assert loaded.template.metadata.title == "Lab 1"
        assert loaded.template.instructions == "Build a circuit."

    def test_load_round_trip_preserves_rubric(self, tmp_path):
        path = tmp_path / "lab.spice-assignment"
        save_assignment(self._make_bundle(), path)
        loaded = load_assignment(path)
        assert loaded.rubric is not None
        assert loaded.rubric["title"] == "Lab 1 Rubric"

    def test_load_rejects_invalid_json(self, tmp_path):
        path = tmp_path / "bad.spice-assignment"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_assignment(path)

    def test_load_rejects_missing_keys(self, tmp_path):
        path = tmp_path / "bad.spice-assignment"
        path.write_text(json.dumps({"other": 1}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_assignment(path)


# ---------------------------------------------------------------------------
# extract_template / extract_rubric
# ---------------------------------------------------------------------------


class TestExtractTemplate:
    def test_returns_bundled_template(self):
        template = TemplateData(instructions="hello")
        bundle = AssignmentBundle(template=template, rubric=None)
        result = extract_template(bundle)
        assert result.instructions == "hello"

    def test_returns_empty_template_when_none(self):
        bundle = AssignmentBundle(template=None, rubric=None)
        result = extract_template(bundle)
        assert isinstance(result, TemplateData)
        assert result.instructions == ""


class TestExtractRubric:
    def test_extracts_rubric(self):
        rubric_dict = {"title": "R", "total_points": 10, "checks": []}
        bundle = AssignmentBundle(template=None, rubric=rubric_dict)
        rubric = extract_rubric(bundle)
        assert rubric.title == "R"
        assert rubric.total_points == 10

    def test_raises_when_no_rubric(self):
        bundle = AssignmentBundle(template=None, rubric=None)
        with pytest.raises(ValueError, match="rubric"):
            extract_rubric(bundle)
