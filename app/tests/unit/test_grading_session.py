"""Tests for grading session persistence (model, I/O, comparison)."""

import json

import pytest
from grading.batch_grader import BatchGradingResult
from grading.grader import CheckGradeResult, GradingResult
from grading.session_persistence import (
    GRADES_EXTENSION,
    batch_result_to_session,
    compare_sessions,
    dict_to_grading_result,
    grading_result_to_dict,
    load_grading_session,
    save_grading_session,
    validate_session_data,
)
from models.grading_session import GradingSessionData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_check_result(check_id="r1_exists", passed=True, earned=10, possible=10, feedback="OK"):
    return CheckGradeResult(
        check_id=check_id,
        passed=passed,
        points_earned=earned,
        points_possible=possible,
        feedback=feedback,
    )


def _make_grading_result(student="student1.json", title="Test Rubric", total=20, earned=15):
    return GradingResult(
        student_file=student,
        rubric_title=title,
        total_points=total,
        earned_points=earned,
        check_results=[
            _make_check_result("r1_exists", True, 10, 10, "R1 present"),
            _make_check_result("r1_value", False, 5, 10, "R1 wrong value"),
        ],
    )


def _make_batch_result():
    return BatchGradingResult(
        rubric_title="Test Rubric",
        total_students=3,
        successful=2,
        failed=1,
        results=[
            _make_grading_result("alice.json", earned=20),
            _make_grading_result("bob.json", earned=10),
        ],
        errors=[("charlie.json", "parse error")],
    )


def _make_session(**overrides):
    defaults = dict(
        session_version="1.0",
        timestamp="2026-01-15T12:00:00+00:00",
        rubric_title="Test Rubric",
        rubric_path="/path/to/rubric.spice-rubric",
        student_folder="/path/to/students",
        results=[
            grading_result_to_dict(_make_grading_result("alice.json", earned=20)),
            grading_result_to_dict(_make_grading_result("bob.json", earned=10)),
        ],
        errors=[("charlie.json", "parse error")],
    )
    defaults.update(overrides)
    return GradingSessionData(**defaults)


# ---------------------------------------------------------------------------
# GradingSessionData serialization
# ---------------------------------------------------------------------------


class TestGradingSessionDataSerialization:
    def test_to_dict_roundtrip(self):
        session = _make_session()
        d = session.to_dict()
        restored = GradingSessionData.from_dict(d)

        assert restored.session_version == session.session_version
        assert restored.timestamp == session.timestamp
        assert restored.rubric_title == session.rubric_title
        assert restored.rubric_path == session.rubric_path
        assert restored.student_folder == session.student_folder
        assert len(restored.results) == len(session.results)
        assert len(restored.errors) == len(session.errors)

    def test_to_dict_json_serializable(self):
        session = _make_session()
        d = session.to_dict()
        # Must not raise
        text = json.dumps(d)
        assert isinstance(text, str)

    def test_from_dict_defaults(self):
        session = GradingSessionData.from_dict({})
        assert session.session_version == "1.0"
        assert session.timestamp == ""
        assert session.rubric_title == ""
        assert session.results == []
        assert session.errors == []

    def test_errors_stored_as_tuples(self):
        session = _make_session()
        d = session.to_dict()
        # errors are stored as lists in JSON
        assert isinstance(d["errors"][0], list)
        restored = GradingSessionData.from_dict(d)
        # but restored as tuples
        assert isinstance(restored.errors[0], tuple)


# ---------------------------------------------------------------------------
# validate_session_data
# ---------------------------------------------------------------------------


class TestValidateSessionData:
    def test_valid_data(self):
        session = _make_session()
        # Must not raise
        validate_session_data(session.to_dict())

    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="JSON object"):
            validate_session_data("not a dict")

    def test_missing_session_version(self):
        d = _make_session().to_dict()
        del d["session_version"]
        with pytest.raises(ValueError, match="session_version"):
            validate_session_data(d)

    def test_missing_rubric_title(self):
        d = _make_session().to_dict()
        del d["rubric_title"]
        with pytest.raises(ValueError, match="rubric_title"):
            validate_session_data(d)

    def test_missing_results(self):
        d = _make_session().to_dict()
        del d["results"]
        with pytest.raises(ValueError, match="results"):
            validate_session_data(d)

    def test_results_not_a_list(self):
        d = _make_session().to_dict()
        d["results"] = "not a list"
        with pytest.raises(ValueError, match="results"):
            validate_session_data(d)

    def test_result_missing_required_field(self):
        d = _make_session().to_dict()
        del d["results"][0]["student_file"]
        with pytest.raises(ValueError, match="student_file"):
            validate_session_data(d)

    def test_result_not_a_dict(self):
        d = _make_session().to_dict()
        d["results"][0] = "not a dict"
        with pytest.raises(ValueError, match="JSON object"):
            validate_session_data(d)

    def test_errors_not_a_list(self):
        d = _make_session().to_dict()
        d["errors"] = "not a list"
        with pytest.raises(ValueError, match="errors"):
            validate_session_data(d)

    def test_empty_results_valid(self):
        d = _make_session(results=[], errors=[]).to_dict()
        # Must not raise
        validate_session_data(d)


# ---------------------------------------------------------------------------
# grading_result_to_dict / dict_to_grading_result
# ---------------------------------------------------------------------------


class TestGradingResultConversion:
    def test_roundtrip(self):
        original = _make_grading_result()
        d = grading_result_to_dict(original)
        restored = dict_to_grading_result(d)

        assert restored.student_file == original.student_file
        assert restored.rubric_title == original.rubric_title
        assert restored.total_points == original.total_points
        assert restored.earned_points == original.earned_points
        assert len(restored.check_results) == len(original.check_results)

    def test_check_results_roundtrip(self):
        original = _make_grading_result()
        d = grading_result_to_dict(original)
        restored = dict_to_grading_result(d)

        for orig_cr, rest_cr in zip(original.check_results, restored.check_results):
            assert rest_cr.check_id == orig_cr.check_id
            assert rest_cr.passed == orig_cr.passed
            assert rest_cr.points_earned == orig_cr.points_earned
            assert rest_cr.points_possible == orig_cr.points_possible
            assert rest_cr.feedback == orig_cr.feedback

    def test_percentage_preserved(self):
        original = _make_grading_result(total=20, earned=15)
        d = grading_result_to_dict(original)
        restored = dict_to_grading_result(d)
        assert restored.percentage == original.percentage

    def test_empty_check_results(self):
        result = GradingResult(
            student_file="empty.json",
            rubric_title="Empty",
            total_points=0,
            earned_points=0,
        )
        d = grading_result_to_dict(result)
        restored = dict_to_grading_result(d)
        assert restored.check_results == []


# ---------------------------------------------------------------------------
# batch_result_to_session
# ---------------------------------------------------------------------------


class TestBatchResultToSession:
    def test_conversion(self):
        batch = _make_batch_result()
        session = batch_result_to_session(batch, rubric_path="/r.spice-rubric", student_folder="/students")

        assert session.rubric_title == "Test Rubric"
        assert session.rubric_path == "/r.spice-rubric"
        assert session.student_folder == "/students"
        assert len(session.results) == 2
        assert len(session.errors) == 1
        assert session.session_version == "1.0"
        assert session.timestamp != ""  # auto-generated

    def test_results_are_dicts(self):
        batch = _make_batch_result()
        session = batch_result_to_session(batch)

        for r in session.results:
            assert isinstance(r, dict)
            assert "student_file" in r
            assert "check_results" in r

    def test_empty_batch(self):
        batch = BatchGradingResult(
            rubric_title="Empty",
            total_students=0,
            successful=0,
            failed=0,
        )
        session = batch_result_to_session(batch)
        assert session.results == []
        assert session.errors == []


# ---------------------------------------------------------------------------
# save / load file I/O
# ---------------------------------------------------------------------------


class TestSaveLoadSession:
    def test_save_and_load_roundtrip(self, tmp_path):
        session = _make_session()
        filepath = tmp_path / f"test{GRADES_EXTENSION}"
        save_grading_session(filepath, session)

        loaded = load_grading_session(filepath)
        assert loaded.rubric_title == session.rubric_title
        assert loaded.timestamp == session.timestamp
        assert len(loaded.results) == len(session.results)
        assert len(loaded.errors) == len(session.errors)

    def test_file_is_valid_json(self, tmp_path):
        session = _make_session()
        filepath = tmp_path / f"test{GRADES_EXTENSION}"
        save_grading_session(filepath, session)

        with open(filepath) as f:
            data = json.load(f)
        assert data["rubric_title"] == "Test Rubric"

    def test_load_nonexistent_file(self, tmp_path):
        with pytest.raises(OSError):
            load_grading_session(tmp_path / "nonexistent.spice-grades")

    def test_load_invalid_json(self, tmp_path):
        filepath = tmp_path / "bad.spice-grades"
        filepath.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            load_grading_session(filepath)

    def test_load_invalid_structure(self, tmp_path):
        filepath = tmp_path / "bad.spice-grades"
        filepath.write_text(json.dumps({"rubric_title": 42}))
        with pytest.raises(ValueError):
            load_grading_session(filepath)

    def test_roundtrip_preserves_grading_results(self, tmp_path):
        batch = _make_batch_result()
        session = batch_result_to_session(batch)
        filepath = tmp_path / f"test{GRADES_EXTENSION}"
        save_grading_session(filepath, session)

        loaded = load_grading_session(filepath)
        for orig, restored in zip(session.results, loaded.results):
            restored_result = dict_to_grading_result(restored)
            orig_result = dict_to_grading_result(orig)
            assert restored_result.student_file == orig_result.student_file
            assert restored_result.earned_points == orig_result.earned_points
            assert restored_result.total_points == orig_result.total_points

    def test_paths_stored_as_relative_in_file(self, tmp_path):
        """Issue #535: paths on disk must be relative, not absolute."""
        rubric = tmp_path / "rubric.spice-rubric"
        students = tmp_path / "students"
        session = _make_session(
            rubric_path=str(rubric),
            student_folder=str(students),
        )
        filepath = tmp_path / f"test{GRADES_EXTENSION}"
        save_grading_session(filepath, session)

        with open(filepath) as f:
            data = json.load(f)
        # Stored paths must be relative to the session file directory
        assert data["rubric_path"] == "rubric.spice-rubric"
        assert data["student_folder"] == "students"

    def test_relative_paths_resolved_on_load(self, tmp_path):
        """Issue #535: relative paths are resolved back to absolute on load."""
        rubric = tmp_path / "rubric.spice-rubric"
        students = tmp_path / "students"
        session = _make_session(
            rubric_path=str(rubric),
            student_folder=str(students),
        )
        filepath = tmp_path / f"test{GRADES_EXTENSION}"
        save_grading_session(filepath, session)

        loaded = load_grading_session(filepath)
        assert loaded.rubric_path == str(rubric.resolve())
        assert loaded.student_folder == str(students.resolve())

    def test_empty_paths_preserved(self, tmp_path):
        """Empty paths must stay empty through save/load."""
        session = _make_session(rubric_path="", student_folder="")
        filepath = tmp_path / f"test{GRADES_EXTENSION}"
        save_grading_session(filepath, session)

        loaded = load_grading_session(filepath)
        assert loaded.rubric_path == ""
        assert loaded.student_folder == ""


# ---------------------------------------------------------------------------
# compare_sessions
# ---------------------------------------------------------------------------


class TestCompareSessions:
    def test_same_students(self):
        old = _make_session()
        new = _make_session()
        # Modify new scores
        new.results[0]["earned_points"] = 18  # alice: was 20 -> 18
        new.results[1]["earned_points"] = 15  # bob: was 10 -> 15

        comparisons = compare_sessions(old, new)

        assert len(comparisons) == 2
        alice = next(c for c in comparisons if c["student_file"] == "alice.json")
        assert alice["old_pct"] == 100.0  # 20/20
        assert alice["new_pct"] == 90.0  # 18/20
        assert alice["delta"] == -10.0

        bob = next(c for c in comparisons if c["student_file"] == "bob.json")
        assert bob["old_pct"] == pytest.approx(50.0)  # 10/20
        assert bob["new_pct"] == 75.0  # 15/20
        assert bob["delta"] == pytest.approx(25.0)

    def test_new_student_in_new_session(self):
        old = _make_session(results=[grading_result_to_dict(_make_grading_result("alice.json", earned=20))])
        new_result = grading_result_to_dict(_make_grading_result("alice.json", earned=20))
        dave_result = grading_result_to_dict(_make_grading_result("dave.json", earned=15))
        new = _make_session(results=[new_result, dave_result])

        comparisons = compare_sessions(old, new)
        dave = next(c for c in comparisons if c["student_file"] == "dave.json")
        assert dave["old_score"] is None
        assert dave["old_pct"] is None
        assert dave["new_pct"] == 75.0
        assert dave["delta"] is None

    def test_student_removed_in_new_session(self):
        alice_result = grading_result_to_dict(_make_grading_result("alice.json", earned=20))
        bob_result = grading_result_to_dict(_make_grading_result("bob.json", earned=10))
        old = _make_session(results=[alice_result, bob_result])
        new = _make_session(results=[alice_result])

        comparisons = compare_sessions(old, new)
        bob = next(c for c in comparisons if c["student_file"] == "bob.json")
        assert bob["new_score"] is None
        assert bob["new_pct"] is None
        assert bob["delta"] is None

    def test_empty_sessions(self):
        old = _make_session(results=[])
        new = _make_session(results=[])
        comparisons = compare_sessions(old, new)
        assert comparisons == []

    def test_zero_total_points(self):
        result = {
            "student_file": "zero.json",
            "rubric_title": "Zero",
            "total_points": 0,
            "earned_points": 0,
            "check_results": [],
        }
        old = _make_session(results=[result])
        new = _make_session(results=[result])

        comparisons = compare_sessions(old, new)
        assert len(comparisons) == 1
        assert comparisons[0]["old_pct"] == 100.0  # 0/0 => 100%
        assert comparisons[0]["delta"] == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_session_with_no_results_no_errors(self):
        session = GradingSessionData(
            rubric_title="Empty",
            timestamp="2026-01-15T12:00:00+00:00",
        )
        d = session.to_dict()
        assert d["results"] == []
        assert d["errors"] == []
        restored = GradingSessionData.from_dict(d)
        assert restored.results == []

    def test_missing_optional_fields_in_from_dict(self):
        minimal = {
            "session_version": "1.0",
            "rubric_title": "Minimal",
            "results": [],
        }
        validate_session_data(minimal)
        session = GradingSessionData.from_dict(minimal)
        assert session.rubric_path == ""
        assert session.student_folder == ""
        assert session.errors == []

    def test_grades_extension_value(self):
        assert GRADES_EXTENSION == ".spice-grades"

    def test_dict_to_grading_result_missing_feedback(self):
        """Check results with no feedback field default to empty string."""
        data = {
            "student_file": "test.json",
            "rubric_title": "Test",
            "total_points": 10,
            "earned_points": 10,
            "check_results": [
                {
                    "check_id": "c1",
                    "passed": True,
                    "points_earned": 10,
                    "points_possible": 10,
                    # no "feedback" key
                }
            ],
        }
        result = dict_to_grading_result(data)
        assert result.check_results[0].feedback == ""
