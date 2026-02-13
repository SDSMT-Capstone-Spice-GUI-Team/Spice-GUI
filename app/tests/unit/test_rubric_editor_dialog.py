"""Tests for the rubric editor dialog."""

import json

import pytest
from grading.rubric import Rubric, RubricCheck
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox


@pytest.fixture
def dialog(qtbot):
    """Create a RubricEditorDialog instance."""
    from GUI.rubric_editor_dialog import RubricEditorDialog

    dlg = RubricEditorDialog()
    qtbot.addWidget(dlg)
    return dlg


@pytest.fixture
def sample_rubric():
    """Create a sample rubric for testing."""
    return Rubric(
        title="Test Rubric",
        total_points=15,
        checks=[
            RubricCheck(
                check_id="has_resistor",
                check_type="component_exists",
                points=5,
                params={"component_type": "Resistor"},
                feedback_pass="Resistor found",
                feedback_fail="Missing resistor",
            ),
            RubricCheck(
                check_id="r1_value",
                check_type="component_value",
                points=5,
                params={
                    "component_id": "R1",
                    "expected_value": "1k",
                    "tolerance_pct": 5.0,
                },
                feedback_pass="Correct value",
                feedback_fail="Wrong value",
            ),
            RubricCheck(
                check_id="has_ground",
                check_type="ground",
                points=5,
                params={},
                feedback_pass="Ground connected",
                feedback_fail="No ground",
            ),
        ],
    )


class TestRubricEditorDialog:
    """Tests for RubricEditorDialog."""

    def test_initial_state(self, dialog):
        """Dialog starts empty with no checks."""
        assert dialog.title_edit.text() == ""
        assert dialog.checks_list.count() == 0
        assert dialog.points_label.text() == "Total Points: 0"
        assert dialog.detail_widget.isEnabled() is False

    def test_add_check(self, dialog, qtbot):
        """Adding a check creates a list item and enables detail editor."""
        dialog.add_btn.click()

        assert dialog.checks_list.count() == 1
        assert dialog.detail_widget.isEnabled()
        assert dialog.check_id_edit.text() == "check_1"
        assert dialog.points_label.text() == "Total Points: 1"

    def test_add_multiple_checks_unique_ids(self, dialog, qtbot):
        """Each added check gets a unique auto-generated ID."""
        dialog.add_btn.click()
        dialog.add_btn.click()
        dialog.add_btn.click()

        assert dialog.checks_list.count() == 3
        ids = set()
        for i in range(3):
            item = dialog.checks_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            ids.add(data["check_id"])
        assert len(ids) == 3

    def test_remove_check(self, dialog, qtbot):
        """Removing a check decreases the list count."""
        dialog.add_btn.click()
        dialog.add_btn.click()
        assert dialog.checks_list.count() == 2

        dialog.checks_list.setCurrentRow(0)
        dialog.remove_btn.click()
        assert dialog.checks_list.count() == 1

    def test_move_up_down(self, dialog, qtbot):
        """Move up/down reorders checks."""
        dialog.add_btn.click()
        dialog.add_btn.click()
        dialog.checks_list.setCurrentRow(1)

        # Get second check's id
        second_data = dialog.checks_list.item(1).data(Qt.ItemDataRole.UserRole)
        second_id = second_data["check_id"]

        # Move up
        dialog.move_up_btn.click()
        first_data = dialog.checks_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert first_data["check_id"] == second_id

        # Move down
        dialog.checks_list.setCurrentRow(0)
        dialog.move_down_btn.click()
        last_data = dialog.checks_list.item(1).data(Qt.ItemDataRole.UserRole)
        assert last_data["check_id"] == second_id

    def test_edit_check_details(self, dialog, qtbot):
        """Editing detail fields updates the list item data."""
        dialog.add_btn.click()

        dialog.check_id_edit.setText("my_check")
        dialog.points_spin.setValue(10)
        dialog.feedback_pass_edit.setText("Good job")
        dialog.feedback_fail_edit.setText("Try again")

        item = dialog.checks_list.item(0)
        data = item.data(Qt.ItemDataRole.UserRole)
        assert data["check_id"] == "my_check"
        assert data["points"] == 10
        assert data["feedback_pass"] == "Good job"
        assert data["feedback_fail"] == "Try again"
        assert dialog.points_label.text() == "Total Points: 10"

    def test_check_type_changes_params(self, dialog, qtbot):
        """Changing check type rebuilds parameter widgets."""
        dialog.add_btn.click()

        # Default is component_exists (alphabetically first after sort)
        # Switch to topology
        dialog.check_type_combo.setCurrentText("topology")
        assert "component_a" in dialog._param_widgets
        assert "component_b" in dialog._param_widgets

        # Switch to analysis_type
        dialog.check_type_combo.setCurrentText("analysis_type")
        assert "expected_type" in dialog._param_widgets
        assert "component_a" not in dialog._param_widgets

    def test_param_values_collected(self, dialog, qtbot):
        """Parameter values are collected from widgets into check data."""
        dialog.add_btn.click()
        dialog.check_type_combo.setCurrentText("component_value")

        # Fill in params
        dialog._param_widgets["component_id"].setText("R1")
        dialog._param_widgets["expected_value"].setText("1k")
        dialog._param_widgets["tolerance_pct"].setValue(5.0)

        item = dialog.checks_list.item(0)
        data = item.data(Qt.ItemDataRole.UserRole)
        assert data["params"]["component_id"] == "R1"
        assert data["params"]["expected_value"] == "1k"
        assert data["params"]["tolerance_pct"] == 5.0

    def test_validation_empty_title(self, dialog, qtbot):
        """Validation catches empty title."""
        dialog.add_btn.click()
        errors = dialog._validate()
        assert any("title" in e.lower() for e in errors)

    def test_validation_no_checks(self, dialog, qtbot):
        """Validation catches zero checks."""
        dialog.title_edit.setText("Test")
        errors = dialog._validate()
        assert any("check" in e.lower() for e in errors)

    def test_validation_duplicate_ids(self, dialog, qtbot):
        """Validation catches duplicate check IDs."""
        dialog.title_edit.setText("Test")
        dialog.add_btn.click()
        dialog.add_btn.click()

        # Set both to the same ID
        dialog.checks_list.setCurrentRow(0)
        dialog.check_id_edit.setText("same_id")
        dialog.checks_list.setCurrentRow(1)
        dialog.check_id_edit.setText("same_id")

        errors = dialog._validate()
        assert any("duplicate" in e.lower() for e in errors)

    def test_validation_missing_required_params(self, dialog, qtbot):
        """Validation catches missing required params."""
        dialog.title_edit.setText("Test")
        dialog.add_btn.click()
        dialog.check_type_combo.setCurrentText("component_value")
        # Don't fill in required params

        errors = dialog._validate()
        assert any("component_id" in e for e in errors)

    def test_validation_passes_for_valid_rubric(self, dialog, qtbot):
        """Valid rubric has no validation errors."""
        dialog.title_edit.setText("Test Rubric")
        dialog.add_btn.click()
        dialog.check_id_edit.setText("has_ground")
        dialog.check_type_combo.setCurrentText("ground")
        dialog.points_spin.setValue(5)

        errors = dialog._validate()
        assert errors == []

    def test_load_rubric_into_ui(self, dialog, sample_rubric, qtbot):
        """Loading a rubric populates the UI correctly."""
        dialog._load_rubric_into_ui(sample_rubric)

        assert dialog.title_edit.text() == "Test Rubric"
        assert dialog.checks_list.count() == 3
        assert dialog.points_label.text() == "Total Points: 15"

        # Verify first check data
        first_data = dialog.checks_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert first_data["check_id"] == "has_resistor"
        assert first_data["check_type"] == "component_exists"
        assert first_data["points"] == 5

    def test_build_rubric_roundtrip(self, dialog, sample_rubric, qtbot):
        """Loading then building a rubric preserves the data."""
        dialog._load_rubric_into_ui(sample_rubric)
        built = dialog._build_rubric()

        assert built.title == sample_rubric.title
        assert built.total_points == sample_rubric.total_points
        assert len(built.checks) == len(sample_rubric.checks)

        for orig, rebuilt in zip(sample_rubric.checks, built.checks):
            assert rebuilt.check_id == orig.check_id
            assert rebuilt.check_type == orig.check_type
            assert rebuilt.points == orig.points

    def test_get_rubric_returns_none_without_accept(self, dialog, qtbot):
        """get_rubric() returns None if dialog was not accepted."""
        assert dialog.get_rubric() is None

    def test_save_load_file(self, dialog, sample_rubric, tmp_path, qtbot, monkeypatch):
        """Save and load rubric files through the dialog."""
        filepath = tmp_path / "test.spice-rubric"

        # Load sample rubric into dialog
        dialog._load_rubric_into_ui(sample_rubric)

        # Save directly (bypassing file dialog)
        rubric = dialog._build_rubric()
        from grading.rubric import load_rubric, save_rubric

        save_rubric(rubric, filepath)

        # Clear and reload
        dialog.checks_list.clear()
        dialog.title_edit.clear()
        loaded = load_rubric(filepath)
        dialog._load_rubric_into_ui(loaded)

        assert dialog.title_edit.text() == "Test Rubric"
        assert dialog.checks_list.count() == 3

    def test_points_auto_update(self, dialog, qtbot):
        """Total points updates as checks are added/modified/removed."""
        dialog.add_btn.click()
        dialog.points_spin.setValue(10)
        assert dialog.points_label.text() == "Total Points: 10"

        dialog.add_btn.click()
        dialog.points_spin.setValue(5)
        assert dialog.points_label.text() == "Total Points: 15"

        dialog.checks_list.setCurrentRow(0)
        dialog.remove_btn.click()
        assert dialog.points_label.text() == "Total Points: 5"

    def test_detail_editor_disabled_when_no_selection(self, dialog, qtbot):
        """Detail editor is disabled with no selection."""
        dialog.add_btn.click()
        assert dialog.detail_widget.isEnabled()

        dialog.checks_list.setCurrentRow(-1)
        assert dialog.detail_widget.isEnabled() is False

    def test_check_type_params_coverage(self):
        """All valid check types have parameter definitions."""
        from grading.rubric import VALID_CHECK_TYPES
        from GUI.rubric_editor_dialog import _CHECK_TYPE_PARAMS

        for ct in VALID_CHECK_TYPES:
            assert ct in _CHECK_TYPE_PARAMS, f"Missing params for check type: {ct}"
