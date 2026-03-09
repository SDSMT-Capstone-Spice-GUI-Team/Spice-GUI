"""Tests for CourseSelectDialog (#701).

Validates profile listing, selection, persistence via settings_service,
and activation via ProfileManager.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from controllers.profile_manager import ProfileManager
from models.course_profile import BUILTIN_PROFILES
from PyQt6.QtCore import Qt

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_profile_manager():
    """Reset singleton state between tests."""
    ProfileManager._instance = None
    yield
    ProfileManager._instance = None


@pytest.fixture()
def mock_settings():
    """Patch settings_service so nothing touches disk."""
    with patch("GUI.course_select_dialog.settings") as s:
        s.get_str.return_value = ""
        yield s


@pytest.fixture()
def dialog(qtbot, mock_settings):
    from GUI.course_select_dialog import CourseSelectDialog

    dlg = CourseSelectDialog()
    qtbot.addWidget(dlg)
    return dlg


# ── Construction / population ────────────────────────────────────────


class TestDialogConstruction:
    def test_window_title(self, dialog):
        assert dialog.windowTitle() == "Select Course Profile"

    def test_lists_all_builtin_profiles(self, dialog):
        assert dialog._list.count() == len(BUILTIN_PROFILES)

    def test_profile_names_displayed(self, dialog):
        names = {dialog._list.item(i).text() for i in range(dialog._list.count())}
        expected = {p.name for p in BUILTIN_PROFILES.values()}
        assert names == expected

    def test_profile_ids_stored_as_user_role(self, dialog):
        ids = {dialog._list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dialog._list.count())}
        expected = set(BUILTIN_PROFILES.keys())
        assert ids == expected

    def test_ok_button_enabled_after_preselection(self, dialog):
        """Current profile is pre-selected so OK starts enabled."""
        assert dialog._ok_button.isEnabled()


# ── Pre-selection ────────────────────────────────────────────────────


class TestPreSelection:
    def test_defaults_to_full_when_no_saved_setting(self, dialog):
        selected = dialog.selected_profile()
        assert selected is not None
        assert selected.id == "full"

    def test_restores_saved_profile_from_settings(self, qtbot, mock_settings):
        from GUI.course_select_dialog import CourseSelectDialog

        mock_settings.get_str.return_value = "ee120"
        dlg = CourseSelectDialog()
        qtbot.addWidget(dlg)

        selected = dlg.selected_profile()
        assert selected is not None
        assert selected.id == "ee120"

    def test_falls_back_to_active_profile_if_setting_empty(self, qtbot, mock_settings):
        from controllers.profile_manager import profile_manager
        from GUI.course_select_dialog import CourseSelectDialog

        profile_manager.set_profile("circuits1")
        mock_settings.get_str.return_value = ""

        dlg = CourseSelectDialog()
        qtbot.addWidget(dlg)

        selected = dlg.selected_profile()
        assert selected is not None
        assert selected.id == "circuits1"


# ── Selection behaviour ─────────────────────────────────────────────


class TestSelection:
    def test_description_updates_on_selection(self, dialog):
        dialog._list.setCurrentRow(0)
        profile = dialog._profiles[0]
        assert dialog._desc_label.text() == profile.description

    def test_ok_disabled_when_no_row(self, dialog):
        dialog._list.setCurrentRow(-1)
        assert not dialog._ok_button.isEnabled()

    def test_selected_profile_returns_none_for_no_selection(self, dialog):
        dialog._list.setCurrentRow(-1)
        assert dialog.selected_profile() is None

    def test_selected_profile_returns_correct_profile(self, dialog):
        for row in range(dialog._list.count()):
            dialog._list.setCurrentRow(row)
            profile = dialog.selected_profile()
            assert profile is dialog._profiles[row]


# ── Accept / apply ───────────────────────────────────────────────────


class TestAccept:
    def test_accept_sets_profile_on_manager(self, dialog, mock_settings):
        from controllers.profile_manager import profile_manager

        # Pick a profile that isn't the current one
        target = next(p for p in dialog._profiles if p.id == "ee120")
        row = dialog._profiles.index(target)
        dialog._list.setCurrentRow(row)

        dialog._on_accept()

        assert profile_manager.get_profile().id == "ee120"

    def test_accept_persists_to_settings(self, dialog, mock_settings):
        target = next(p for p in dialog._profiles if p.id == "circuits1")
        row = dialog._profiles.index(target)
        dialog._list.setCurrentRow(row)

        dialog._on_accept()

        mock_settings.set.assert_called_with("course/profile_id", "circuits1")

    def test_accept_noop_when_nothing_selected(self, dialog, mock_settings):
        dialog._list.setCurrentRow(-1)
        dialog._on_accept()
        mock_settings.set.assert_not_called()

    def test_double_click_accepts(self, dialog, mock_settings):
        from controllers.profile_manager import profile_manager

        target = next(p for p in dialog._profiles if p.id == "me301")
        row = dialog._profiles.index(target)
        dialog._list.setCurrentRow(row)

        item = dialog._list.item(row)
        dialog._on_double_click(item)

        assert profile_manager.get_profile().id == "me301"
        mock_settings.set.assert_called_with("course/profile_id", "me301")


# ── Full profile is always present ───────────────────────────────────


class TestFullProfile:
    def test_full_profile_present(self, dialog):
        ids = [dialog._list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dialog._list.count())]
        assert "full" in ids

    def test_full_profile_enables_everything(self):
        full = BUILTIN_PROFILES["full"]
        assert full.show_advanced_panels is True
        assert len(full.allowed_components) > 0
        assert len(full.allowed_analyses) > 0
