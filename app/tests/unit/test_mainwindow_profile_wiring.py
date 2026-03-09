"""
Unit tests for MainWindow ↔ ProfileManager wiring (#703).

Tests profile-driven panel visibility, View > Course Profile menu item,
startup profile restoration, and settings persistence.
"""

from unittest.mock import MagicMock, patch

import pytest
from controllers.profile_manager import ProfileManager, profile_manager
from controllers.settings_service import settings as app_settings
from models.course_profile import BUILTIN_PROFILES


@pytest.fixture(autouse=True)
def _reset_profile_manager():
    """Reset ProfileManager to 'full' profile and clear observers."""
    profile_manager._profile = BUILTIN_PROFILES["full"]
    profile_manager._observers.clear()
    yield
    profile_manager._profile = BUILTIN_PROFILES["full"]
    profile_manager._observers.clear()


@pytest.fixture(autouse=True)
def _clear_course_setting():
    """Clear course profile setting between tests."""
    app_settings.set("course/profile_id", None)
    yield
    app_settings.set("course/profile_id", None)


# ---------------------------------------------------------------------------
# Helper: lightweight stand-in for MainWindow that mixes in ViewOperationsMixin
# without needing the full Qt MainWindow + all controllers.
# ---------------------------------------------------------------------------


def _make_stub_window():
    """Build a minimal stub with the attributes ViewOperationsMixin expects."""
    from GUI.main_window_analysis import AnalysisSettingsMixin
    from GUI.main_window_view import ViewOperationsMixin

    stub = type("StubWindow", (AnalysisSettingsMixin, ViewOperationsMixin), {})()

    # Minimal widget stand-ins
    stub.statistics_panel = MagicMock()
    stub.statistics_panel.isVisible.return_value = False
    stub.grading_panel = MagicMock()
    stub.grading_panel.isVisible.return_value = False
    stub.show_statistics_action = MagicMock()
    stub.show_statistics_action.isChecked.return_value = True

    stub.statusBar = MagicMock(return_value=MagicMock())
    stub.show_status_message = MagicMock()

    # Analysis menu mock actions (needed by AnalysisSettingsMixin)
    stub._analysis_action_map = {
        code: MagicMock() for code in ("op", "dc", "ac", "tran", "temp", "noise", "sweep", "mc")
    }
    stub.analysis_group = MagicMock()
    stub.analysis_group.checkedAction.return_value = None

    return stub


# ---------------------------------------------------------------------------
# Panel visibility
# ---------------------------------------------------------------------------


class TestProfilePanelVisibility:
    """Verify that _apply_profile_panels shows/hides panels correctly."""

    def test_full_profile_enables_advanced_panels(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["full"]
        stub._apply_profile_panels(profile)

        # show_advanced_panels is True for full
        stub.show_statistics_action.setEnabled.assert_called_with(True)

    def test_ee120_disables_advanced_panels(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["ee120"]
        stub._apply_profile_panels(profile)

        # show_advanced_panels is False for ee120
        stub.show_statistics_action.setEnabled.assert_called_with(False)
        stub.statistics_panel.setVisible.assert_called_with(False)

    def test_observer_callback_applies_panels(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["ee120"]
        stub._on_profile_changed(profile)

        stub.show_statistics_action.setEnabled.assert_called_with(False)
        stub.show_status_message.assert_called_once()

    def test_circuits2_enables_advanced(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["circuits2"]
        stub._apply_profile_panels(profile)

        stub.show_statistics_action.setEnabled.assert_called_with(True)


# ---------------------------------------------------------------------------
# Startup profile restoration
# ---------------------------------------------------------------------------


class TestStartupProfileRestore:
    """Verify _restore_course_profile reads from settings and activates."""

    def test_restores_saved_profile(self):
        stub = _make_stub_window()
        app_settings.set("course/profile_id", "ee120")
        stub._restore_course_profile()

        assert profile_manager.get_profile().id == "ee120"

    def test_keeps_default_when_no_saved_profile(self):
        stub = _make_stub_window()
        app_settings.set("course/profile_id", None)
        stub._restore_course_profile()

        assert profile_manager.get_profile().id == "full"

    def test_handles_unknown_profile_gracefully(self):
        stub = _make_stub_window()
        app_settings.set("course/profile_id", "nonexistent_profile")
        # Should not raise — falls back to current profile
        stub._restore_course_profile()
        assert profile_manager.get_profile().id == "full"


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------


class TestSettingsPersistence:
    """Verify _save_settings persists the active profile id."""

    def test_save_settings_persists_profile(self):
        from GUI.main_window_settings import SettingsMixin

        stub = type("S", (SettingsMixin,), {})()
        # Provide minimal attributes the mixin needs
        stub.saveGeometry = MagicMock(return_value=b"")
        stub.saveState = MagicMock(return_value=b"")
        stub.center_splitter = MagicMock()
        stub.center_splitter.sizes.return_value = [500, 200]
        stub.model = MagicMock()
        stub.model.analysis_type = "DC Operating Point"
        stub.canvas = MagicMock()
        stub.canvas.show_component_labels = True
        stub.canvas.show_component_values = True
        stub.canvas.show_node_labels = True
        stub.statistics_panel = MagicMock()
        stub.statistics_panel.isVisible.return_value = False

        profile_manager.set_profile("circuits1")
        stub._save_settings()

        assert app_settings.get_str("course/profile_id") == "circuits1"


# ---------------------------------------------------------------------------
# Menu item
# ---------------------------------------------------------------------------


class TestCourseProfileMenuItem:
    """Verify the View > Course Profile menu action exists."""

    def test_menu_action_triggers_dialog(self):
        stub = _make_stub_window()
        with patch("GUI.course_select_dialog.CourseSelectDialog") as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            stub._show_course_profile_dialog()
            mock_instance.exec.assert_called_once()


# ---------------------------------------------------------------------------
# Observer registration (integration-level)
# ---------------------------------------------------------------------------


class TestObserverRegistration:
    """Verify ProfileManager observer integration."""

    def test_observer_is_notified_on_set_profile(self):
        received = []
        profile_manager.register_observer(lambda p: received.append(p.id))
        profile_manager.set_profile("me301")
        assert received == ["me301"]

    def test_observer_not_notified_on_same_profile(self):
        profile_manager.set_profile("ee120")
        received = []
        profile_manager.register_observer(lambda p: received.append(p.id))
        profile_manager.set_profile("ee120")  # same profile
        assert received == []
