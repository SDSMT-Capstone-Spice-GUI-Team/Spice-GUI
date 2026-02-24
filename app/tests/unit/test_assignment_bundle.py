"""Tests for the .spice-assignment bundle format."""

import json

import pytest
from controllers.assignment_controller import (
    extract_rubric,
    extract_template,
    load_assignment,
    save_assignment,
    validate_assignment_data,
)
from grading.rubric import Rubric, RubricCheck
from models.assignment import AssignmentBundle
from models.template import TemplateData, TemplateMetadata


@pytest.fixture
def sample_rubric_dict():
    """Create a sample rubric dict."""
    rubric = Rubric(
        title="Test Rubric",
        total_points=10,
        checks=[
            RubricCheck(
                check_id="has_ground",
                check_type="ground",
                points=10,
                params={},
                feedback_pass="OK",
                feedback_fail="Missing ground",
            )
        ],
    )
    return rubric.to_dict()


@pytest.fixture
def sample_template():
    """Create a sample template."""
    return TemplateData(
        metadata=TemplateMetadata(title="Test Template", author="Tester"),
        instructions="Build the circuit.",
        starter_circuit={
            "components": [{"component_id": "R1", "component_type": "Resistor", "value": "1k", "position": [0, 0]}],
            "wires": [],
        },
    )


@pytest.fixture
def sample_bundle(sample_template, sample_rubric_dict):
    """Create a sample assignment bundle."""
    return AssignmentBundle(
        template=sample_template,
        rubric=sample_rubric_dict,
    )


class TestAssignmentBundleModel:
    """Tests for AssignmentBundle data model."""

    def test_to_dict(self, sample_bundle):
        """Bundle serializes to dict with both template and rubric."""
        d = sample_bundle.to_dict()
        assert d["assignment_version"] == "1.0"
        assert "template" in d
        assert "rubric" in d

    def test_from_dict_round_trip(self, sample_bundle):
        """Bundle survives serialization round-trip."""
        d = sample_bundle.to_dict()
        restored = AssignmentBundle.from_dict(d)
        assert restored.assignment_version == "1.0"
        assert restored.template is not None
        assert restored.template.metadata.title == "Test Template"
        assert restored.rubric is not None
        assert restored.rubric["title"] == "Test Rubric"

    def test_empty_bundle(self):
        """Empty bundle has no template or rubric."""
        bundle = AssignmentBundle()
        d = bundle.to_dict()
        assert "template" not in d
        assert "rubric" not in d

    def test_template_only(self, sample_template):
        """Bundle with only template, no rubric."""
        bundle = AssignmentBundle(template=sample_template)
        d = bundle.to_dict()
        assert "template" in d
        assert "rubric" not in d

    def test_rubric_only(self, sample_rubric_dict):
        """Bundle with only rubric, no template."""
        bundle = AssignmentBundle(rubric=sample_rubric_dict)
        d = bundle.to_dict()
        assert "rubric" in d
        assert "template" not in d


class TestValidateAssignmentData:
    """Tests for assignment data validation."""

    def test_valid_with_both(self, sample_bundle):
        """Valid bundle with template and rubric passes validation."""
        validate_assignment_data(sample_bundle.to_dict())

    def test_valid_rubric_only(self, sample_rubric_dict):
        """Rubric-only bundle passes validation."""
        validate_assignment_data({"rubric": sample_rubric_dict})

    def test_valid_template_only(self, sample_template):
        """Template-only bundle passes validation."""
        validate_assignment_data({"template": sample_template.to_dict()})

    def test_not_a_dict(self):
        """Non-dict raises ValueError."""
        with pytest.raises(ValueError, match="JSON object"):
            validate_assignment_data([])

    def test_empty_dict(self):
        """Empty dict (no template or rubric) raises ValueError."""
        with pytest.raises(ValueError, match="at least"):
            validate_assignment_data({})

    def test_invalid_rubric(self):
        """Invalid rubric structure raises ValueError."""
        with pytest.raises(ValueError):
            validate_assignment_data({"rubric": {"title": "", "total_points": 0, "checks": []}})


class TestSaveLoadAssignment:
    """Tests for save/load of assignment files."""

    def test_save_creates_file(self, sample_bundle, tmp_path):
        """Saving creates a .spice-assignment file."""
        filepath = tmp_path / "test.spice-assignment"
        save_assignment(sample_bundle, filepath)
        assert filepath.exists()

    def test_save_writes_valid_json(self, sample_bundle, tmp_path):
        """Saved file contains valid JSON."""
        filepath = tmp_path / "test.spice-assignment"
        save_assignment(sample_bundle, filepath)
        data = json.loads(filepath.read_text())
        assert "assignment_version" in data

    def test_round_trip(self, sample_bundle, tmp_path):
        """Save then load preserves all data."""
        filepath = tmp_path / "test.spice-assignment"
        save_assignment(sample_bundle, filepath)
        loaded = load_assignment(filepath)

        assert loaded.assignment_version == "1.0"
        assert loaded.template is not None
        assert loaded.template.metadata.title == "Test Template"
        assert loaded.rubric is not None
        assert loaded.rubric["title"] == "Test Rubric"

    def test_load_invalid_json(self, tmp_path):
        """Loading invalid JSON raises error."""
        filepath = tmp_path / "bad.spice-assignment"
        filepath.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            load_assignment(filepath)

    def test_load_invalid_structure(self, tmp_path):
        """Loading empty dict raises ValueError."""
        filepath = tmp_path / "bad.spice-assignment"
        filepath.write_text("{}")
        with pytest.raises(ValueError):
            load_assignment(filepath)

    def test_load_nonexistent_file(self, tmp_path):
        """Loading nonexistent file raises OSError."""
        with pytest.raises(OSError):
            load_assignment(tmp_path / "nope.spice-assignment")


class TestExtractFunctions:
    """Tests for extract_template and extract_rubric."""

    def test_extract_template(self, sample_bundle):
        """Extracts template from bundle."""
        template = extract_template(sample_bundle)
        assert template.metadata.title == "Test Template"

    def test_extract_template_empty(self):
        """Returns empty template when none present."""
        bundle = AssignmentBundle()
        template = extract_template(bundle)
        assert template.metadata.title == ""

    def test_extract_rubric(self, sample_bundle):
        """Extracts rubric from bundle."""
        rubric = extract_rubric(sample_bundle)
        assert rubric.title == "Test Rubric"
        assert len(rubric.checks) == 1

    def test_extract_rubric_missing(self):
        """Raises ValueError when no rubric present."""
        bundle = AssignmentBundle()
        with pytest.raises(ValueError, match="does not contain"):
            extract_rubric(bundle)
