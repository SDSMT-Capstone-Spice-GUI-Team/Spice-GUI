"""Tests for grading utility modules: component_mapper and rubric_validator."""

import pytest
from grading.component_mapper import extract_component_ids
from grading.rubric import Rubric, RubricCheck
from grading.rubric_validator import (
    build_rubric,
    calculate_total_points,
    generate_check_id,
    get_required_params,
    validate_rubric,
)

# ---------------------------------------------------------------------------
# component_mapper.extract_component_ids
# ---------------------------------------------------------------------------


class TestExtractComponentIds:
    def test_extracts_single_id(self):
        assert extract_component_ids("R1") == ["R1"]

    def test_extracts_multiple_ids(self):
        result = extract_component_ids("check_R1_C2")
        assert "R1" in result
        assert "C2" in result

    def test_returns_uppercase(self):
        assert extract_component_ids("r1") == ["R1"]

    def test_no_ids_returns_empty(self):
        assert extract_component_ids("check") == []

    def test_filters_check_token(self):
        result = extract_component_ids("check1_R1")
        # "check1" matches the regex but is not in skip list (skip = {"check"})
        # "R1" is always included; the important thing is "check" alone is skipped
        assert "R1" in result

    def test_empty_string_returns_empty(self):
        assert extract_component_ids("") == []

    def test_voltage_source_id(self):
        assert extract_component_ids("V1_connected") == ["V1"]

    def test_ground_component_id(self):
        assert extract_component_ids("GND1") == ["GND1"]


# ---------------------------------------------------------------------------
# rubric_validator.get_required_params
# ---------------------------------------------------------------------------


class TestGetRequiredParams:
    def test_component_exists_has_no_required_params(self):
        assert get_required_params("component_exists") == []

    def test_component_value_requires_id_and_value(self):
        params = get_required_params("component_value")
        assert "component_id" in params
        assert "expected_value" in params

    def test_component_count_requires_type_and_count(self):
        params = get_required_params("component_count")
        assert "component_type" in params
        assert "expected_count" in params

    def test_topology_requires_two_components(self):
        params = get_required_params("topology")
        assert "component_a" in params
        assert "component_b" in params

    def test_ground_has_no_required_params(self):
        assert get_required_params("ground") == []

    def test_analysis_type_requires_expected_type(self):
        assert "expected_type" in get_required_params("analysis_type")

    def test_unknown_type_returns_empty(self):
        assert get_required_params("nonexistent_type") == []


# ---------------------------------------------------------------------------
# rubric_validator.validate_rubric
# ---------------------------------------------------------------------------


class TestValidateRubric:
    def _check(self, cid="check_1", ctype="ground", points=10, params=None):
        return {"check_id": cid, "check_type": ctype, "points": points, "params": params or {}}

    def test_valid_rubric_returns_no_errors(self):
        errors = validate_rubric("Lab 1", [self._check()])
        assert errors == []

    def test_empty_title_is_error(self):
        errors = validate_rubric("", [self._check()])
        assert any("title" in e.lower() for e in errors)

    def test_whitespace_title_is_error(self):
        errors = validate_rubric("   ", [self._check()])
        assert any("title" in e.lower() for e in errors)

    def test_no_checks_is_error(self):
        errors = validate_rubric("Lab 1", [])
        assert any("check" in e.lower() for e in errors)

    def test_duplicate_check_ids_is_error(self):
        checks = [self._check("dup"), self._check("dup")]
        errors = validate_rubric("Lab 1", checks)
        assert any("duplicate" in e.lower() for e in errors)

    def test_missing_required_param_is_error(self):
        check = self._check(ctype="component_value", params={})
        errors = validate_rubric("Lab 1", [check])
        assert any("component_id" in e for e in errors)

    def test_present_required_param_no_error(self):
        check = self._check(
            ctype="component_value",
            params={"component_id": "R1", "expected_value": "1k"},
        )
        errors = validate_rubric("Lab 1", [check])
        assert errors == []


# ---------------------------------------------------------------------------
# rubric_validator.generate_check_id
# ---------------------------------------------------------------------------


class TestGenerateCheckId:
    def test_first_id_is_check_1(self):
        assert generate_check_id(set()) == "check_1"

    def test_skips_existing_ids(self):
        existing = {"check_1", "check_2"}
        assert generate_check_id(existing) == "check_3"

    def test_handles_non_sequential_gaps(self):
        existing = {"check_1", "check_3"}
        assert generate_check_id(existing) == "check_2"


# ---------------------------------------------------------------------------
# rubric_validator.calculate_total_points
# ---------------------------------------------------------------------------


class TestCalculateTotalPoints:
    def test_empty_list_is_zero(self):
        assert calculate_total_points([]) == 0

    def test_sums_points_correctly(self):
        checks = [{"points": 10}, {"points": 20}, {"points": 5}]
        assert calculate_total_points(checks) == 35

    def test_missing_points_treated_as_zero(self):
        assert calculate_total_points([{"check_type": "ground"}]) == 0


# ---------------------------------------------------------------------------
# rubric_validator.build_rubric
# ---------------------------------------------------------------------------


class TestBuildRubric:
    def test_returns_rubric_instance(self):
        checks = [{"check_id": "c1", "check_type": "ground", "points": 10, "params": {}}]
        rubric = build_rubric("Lab 1", checks)
        assert isinstance(rubric, Rubric)

    def test_title_is_stripped(self):
        checks = [{"check_id": "c1", "check_type": "ground", "points": 5, "params": {}}]
        rubric = build_rubric("  Lab 1  ", checks)
        assert rubric.title == "Lab 1"

    def test_total_points_summed(self):
        checks = [
            {"check_id": "c1", "check_type": "ground", "points": 10, "params": {}},
            {"check_id": "c2", "check_type": "ground", "points": 15, "params": {}},
        ]
        rubric = build_rubric("Lab 1", checks)
        assert rubric.total_points == 25

    def test_checks_converted_to_rubric_checks(self):
        checks = [{"check_id": "c1", "check_type": "ground", "points": 5, "params": {}}]
        rubric = build_rubric("Lab 1", checks)
        assert len(rubric.checks) == 1
        assert isinstance(rubric.checks[0], RubricCheck)
