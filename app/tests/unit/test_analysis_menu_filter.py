"""
Unit tests for analysis menu filtering by course profile (#704).

Tests that analysis menu actions are shown/hidden based on the active
profile's allowed_analyses list, and that switching profiles falls back
to an allowed analysis when the current selection becomes hidden.
"""

from unittest.mock import MagicMock

import pytest
from controllers.profile_manager import profile_manager
from GUI.main_window_analysis import _CODE_TO_ANALYSIS_TYPE, AnalysisSettingsMixin
from models.course_profile import BUILTIN_PROFILES, CourseProfile


@pytest.fixture(autouse=True)
def _reset_profile_manager():
    """Reset ProfileManager to 'full' profile and clear observers."""
    profile_manager._profile = BUILTIN_PROFILES["full"]
    profile_manager._observers.clear()
    yield
    profile_manager._profile = BUILTIN_PROFILES["full"]
    profile_manager._observers.clear()


# ---------------------------------------------------------------------------
# Helper: lightweight stub that provides the attributes AnalysisSettingsMixin
# and ViewOperationsMixin expect without a full MainWindow.
# ---------------------------------------------------------------------------

_ALL_CODES = ("op", "dc", "ac", "tran", "temp", "noise", "sweep", "mc")


def _make_action(name: str, *, visible: bool = True, checked: bool = False) -> MagicMock:
    """Create a mock QAction with realistic visibility/checked state."""
    action = MagicMock(name=name)
    action._visible = visible
    action._checked = checked

    def _set_visible(v):
        action._visible = v

    def _is_visible():
        return action._visible

    def _set_checked(c):
        action._checked = c
        # If checked, it becomes the group's checked action
        if c and hasattr(action, "_group"):
            action._group._checked = action

    def _is_checked():
        return action._checked

    action.setVisible = MagicMock(side_effect=_set_visible)
    action.isVisible = MagicMock(side_effect=_is_visible)
    action.setChecked = MagicMock(side_effect=_set_checked)
    action.isChecked = MagicMock(side_effect=_is_checked)
    action.trigger = MagicMock()
    return action


def _make_stub_window():
    """Build a minimal stub with the attributes AnalysisSettingsMixin expects."""
    from GUI.main_window_view import ViewOperationsMixin

    stub = type("StubWindow", (AnalysisSettingsMixin, ViewOperationsMixin), {})()

    # Create mock actions for each analysis type
    actions = {}
    for code in _ALL_CODES:
        actions[code] = _make_action(code, visible=True, checked=(code == "op"))

    stub.op_action = actions["op"]
    stub.dc_action = actions["dc"]
    stub.ac_action = actions["ac"]
    stub.tran_action = actions["tran"]
    stub.temp_action = actions["temp"]
    stub.noise_action = actions["noise"]
    stub.sweep_action = actions["sweep"]
    stub.mc_action = actions["mc"]

    stub._analysis_action_map = actions

    # Mock analysis_group with checkedAction
    group = MagicMock()
    group._checked = actions["op"]
    group.checkedAction = MagicMock(side_effect=lambda: group._checked)
    stub.analysis_group = group

    # Give each action a back-reference to the group
    for a in actions.values():
        a._group = group

    # Model mock (for _sync_analysis_menu / set_analysis calls)
    stub.model = MagicMock()
    stub.model.analysis_type = "DC Operating Point"
    stub.simulation_ctrl = MagicMock()

    # Panel mocks expected by ViewOperationsMixin
    stub.statistics_panel = MagicMock()
    stub.statistics_panel.isVisible.return_value = False
    stub.grading_panel = MagicMock()
    stub.grading_panel.isVisible.return_value = False
    stub.show_statistics_action = MagicMock()
    stub.show_statistics_action.isChecked.return_value = True
    stub.statusBar = MagicMock(return_value=MagicMock())
    stub.show_status_message = MagicMock()

    return stub


# ---------------------------------------------------------------------------
# Basic visibility tests
# ---------------------------------------------------------------------------


class TestFullProfileShowsAll:
    """With the 'full' profile every analysis action should be visible."""

    def test_all_actions_visible(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["full"]
        stub._apply_analysis_profile_filter(profile)

        for code in _ALL_CODES:
            action = stub._analysis_action_map[code]
            action.setVisible.assert_called_with(True)

    def test_full_profile_via_observer(self):
        stub = _make_stub_window()
        stub._on_profile_changed(BUILTIN_PROFILES["full"])

        for code in _ALL_CODES:
            assert stub._analysis_action_map[code]._visible is True


# ---------------------------------------------------------------------------
# Restricted profile visibility
# ---------------------------------------------------------------------------


class TestRestrictedProfileHidesAnalyses:
    """Profiles with limited allowed_analyses should hide disallowed items."""

    def test_ee120_only_op_visible(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["ee120"]
        stub._apply_analysis_profile_filter(profile)

        assert stub._analysis_action_map["op"]._visible is True
        assert stub._analysis_action_map["dc"]._visible is False
        assert stub._analysis_action_map["ac"]._visible is False
        assert stub._analysis_action_map["tran"]._visible is False
        assert stub._analysis_action_map["temp"]._visible is False
        assert stub._analysis_action_map["noise"]._visible is False
        assert stub._analysis_action_map["sweep"]._visible is False
        assert stub._analysis_action_map["mc"]._visible is False

    def test_circuits1_shows_op_ac_tran(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["circuits1"]
        stub._apply_analysis_profile_filter(profile)

        assert stub._analysis_action_map["op"]._visible is True
        assert stub._analysis_action_map["ac"]._visible is True
        assert stub._analysis_action_map["tran"]._visible is True
        assert stub._analysis_action_map["dc"]._visible is False

    def test_circuits2_shows_op_ac_tran_dc(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["circuits2"]
        stub._apply_analysis_profile_filter(profile)

        assert stub._analysis_action_map["op"]._visible is True
        assert stub._analysis_action_map["ac"]._visible is True
        assert stub._analysis_action_map["tran"]._visible is True
        assert stub._analysis_action_map["dc"]._visible is True
        # Advanced analyses not in circuits2
        assert stub._analysis_action_map["temp"]._visible is False
        assert stub._analysis_action_map["noise"]._visible is False

    def test_me301_shows_op_tran(self):
        stub = _make_stub_window()
        profile = BUILTIN_PROFILES["me301"]
        stub._apply_analysis_profile_filter(profile)

        assert stub._analysis_action_map["op"]._visible is True
        assert stub._analysis_action_map["tran"]._visible is True
        assert stub._analysis_action_map["ac"]._visible is False
        assert stub._analysis_action_map["dc"]._visible is False


# ---------------------------------------------------------------------------
# Fallback when current analysis becomes hidden
# ---------------------------------------------------------------------------


class TestAnalysisFallback:
    """When the selected analysis is hidden by a profile switch, fall back."""

    def test_fallback_to_op_when_dc_hidden(self):
        stub = _make_stub_window()
        # Simulate DC Sweep being the checked action
        stub._analysis_action_map["dc"]._checked = True
        stub.analysis_group._checked = stub._analysis_action_map["dc"]
        stub._analysis_action_map["op"]._checked = False

        # Switch to ee120 which only allows "op"
        profile = BUILTIN_PROFILES["ee120"]
        stub._apply_analysis_profile_filter(profile)

        # op should have been triggered as fallback
        stub._analysis_action_map["op"].trigger.assert_called_once()

    def test_no_fallback_when_current_is_allowed(self):
        stub = _make_stub_window()
        # op is checked and allowed in all profiles
        profile = BUILTIN_PROFILES["ee120"]
        stub._apply_analysis_profile_filter(profile)

        # op should NOT have trigger called (it's already selected and visible)
        stub._analysis_action_map["op"].trigger.assert_not_called()

    def test_fallback_when_ac_hidden_on_me301(self):
        stub = _make_stub_window()
        # Simulate AC Sweep being checked
        stub._analysis_action_map["ac"]._checked = True
        stub.analysis_group._checked = stub._analysis_action_map["ac"]
        stub._analysis_action_map["op"]._checked = False

        profile = BUILTIN_PROFILES["me301"]  # allows op, tran
        stub._apply_analysis_profile_filter(profile)

        # Should fall back to op (preferred fallback)
        stub._analysis_action_map["op"].trigger.assert_called_once()


# ---------------------------------------------------------------------------
# Switching profiles back and forth
# ---------------------------------------------------------------------------


class TestProfileSwitching:
    """Switching from restricted back to full should restore all analyses."""

    def test_restricted_then_full_restores_all(self):
        stub = _make_stub_window()

        # Restrict
        stub._apply_analysis_profile_filter(BUILTIN_PROFILES["ee120"])
        assert stub._analysis_action_map["dc"]._visible is False

        # Restore
        stub._apply_analysis_profile_filter(BUILTIN_PROFILES["full"])
        assert stub._analysis_action_map["dc"]._visible is True
        assert stub._analysis_action_map["mc"]._visible is True

    def test_switch_between_restricted_profiles(self):
        stub = _make_stub_window()

        # ee120: only op
        stub._apply_analysis_profile_filter(BUILTIN_PROFILES["ee120"])
        assert stub._analysis_action_map["tran"]._visible is False

        # circuits1: op, ac, tran
        stub._apply_analysis_profile_filter(BUILTIN_PROFILES["circuits1"])
        assert stub._analysis_action_map["tran"]._visible is True
        assert stub._analysis_action_map["dc"]._visible is False


# ---------------------------------------------------------------------------
# Observer integration
# ---------------------------------------------------------------------------


class TestObserverIntegration:
    """Verify the observer callback updates analysis menu visibility."""

    def test_observer_callback_filters_analyses(self):
        stub = _make_stub_window()
        stub._on_profile_changed(BUILTIN_PROFILES["ee120"])

        assert stub._analysis_action_map["dc"]._visible is False
        assert stub._analysis_action_map["op"]._visible is True

    def test_profile_manager_notifies_analysis_filter(self):
        stub = _make_stub_window()
        profile_manager.register_observer(stub._on_profile_changed)
        profile_manager.set_profile("ee120")

        assert stub._analysis_action_map["dc"]._visible is False
        assert stub._analysis_action_map["op"]._visible is True

    def test_startup_restore_applies_filter(self):
        """_restore_course_profile should apply analysis filtering."""
        from controllers.settings_service import settings as app_settings

        stub = _make_stub_window()
        app_settings.set("course/profile_id", "me301")
        stub._restore_course_profile()

        assert stub._analysis_action_map["ac"]._visible is False
        assert stub._analysis_action_map["tran"]._visible is True

        # Cleanup
        app_settings.set("course/profile_id", None)


# ---------------------------------------------------------------------------
# Code-to-analysis-type mapping
# ---------------------------------------------------------------------------


class TestCodeToAnalysisTypeMapping:
    """Verify the _CODE_TO_ANALYSIS_TYPE mapping is complete."""

    def test_all_codes_mapped(self):
        for code in _ALL_CODES:
            assert code in _CODE_TO_ANALYSIS_TYPE

    def test_mapping_values(self):
        assert _CODE_TO_ANALYSIS_TYPE["op"] == "DC Operating Point"
        assert _CODE_TO_ANALYSIS_TYPE["dc"] == "DC Sweep"
        assert _CODE_TO_ANALYSIS_TYPE["ac"] == "AC Sweep"
        assert _CODE_TO_ANALYSIS_TYPE["tran"] == "Transient"
        assert _CODE_TO_ANALYSIS_TYPE["temp"] == "Temperature Sweep"
        assert _CODE_TO_ANALYSIS_TYPE["noise"] == "Noise"
        assert _CODE_TO_ANALYSIS_TYPE["sweep"] == "Parameter Sweep"
        assert _CODE_TO_ANALYSIS_TYPE["mc"] == "Monte Carlo"
