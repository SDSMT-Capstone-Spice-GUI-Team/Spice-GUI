"""Tests for first-launch tutorial auto-trigger (#486).

The guided tutorial should start automatically on the very first launch
(no existing settings). On subsequent launches it should not auto-start.

MainWindow cannot be instantiated in offscreen mode, so we test via
attribute checks on the mixin, mock-based behavioral tests, and settings
service integration.
"""

from unittest.mock import MagicMock, patch

from controllers.settings_service import SettingsService


class TestFirstLaunchTutorialStructure:
    """Behavioral tests for the first-launch tutorial trigger."""

    def test_settings_mixin_has_restore_settings(self):
        """SettingsMixin must expose a _restore_settings method."""
        from GUI.main_window_settings import SettingsMixin

        assert hasattr(SettingsMixin, "_restore_settings"), "SettingsMixin missing _restore_settings"

    def test_settings_mixin_has_start_tutorial(self):
        """SettingsMixin must expose a _start_tutorial attribute (provided by HelpMixin)."""
        from GUI.main_window_help import HelpMixin

        assert hasattr(HelpMixin, "_start_tutorial"), "HelpMixin missing _start_tutorial"

    def test_tutorial_triggered_on_first_launch(self):
        """_restore_settings sets tutorial/has_shown and schedules _start_tutorial on first run."""
        from GUI.main_window_settings import SettingsMixin

        # Build a minimal host object that satisfies every attribute _restore_settings touches.
        host = MagicMock()

        mock_svc = MagicMock()
        # All settings.get() calls return None except tutorial/has_shown check.
        mock_svc.get.return_value = None
        # First call to get_bool("tutorial/has_shown", False) → False (first launch).
        mock_svc.get_bool.return_value = False

        with (
            patch("GUI.main_window_settings.settings", mock_svc),
            patch("GUI.main_window_settings.QTimer") as mock_timer,
            patch("GUI.main_window_settings.theme_ctrl"),
            patch("GUI.main_window_settings.theme_manager"),
        ):
            SettingsMixin._restore_settings(host)

        # tutorial/has_shown must be set to True after first launch.
        mock_svc.set.assert_any_call("tutorial/has_shown", True)
        # _start_tutorial must be scheduled via QTimer.singleShot.
        mock_timer.singleShot.assert_called_once()
        timer_args = mock_timer.singleShot.call_args
        assert timer_args[0][1] == host._start_tutorial

    def test_tutorial_not_triggered_on_subsequent_launch(self):
        """_restore_settings must not schedule _start_tutorial when has_shown is True."""
        from GUI.main_window_settings import SettingsMixin

        host = MagicMock()

        mock_svc = MagicMock()
        mock_svc.get.return_value = None

        def get_bool_side_effect(key, default=False):
            if key == "tutorial/has_shown":
                return True
            return default

        mock_svc.get_bool.side_effect = get_bool_side_effect

        with (
            patch("GUI.main_window_settings.settings", mock_svc),
            patch("GUI.main_window_settings.QTimer") as mock_timer,
            patch("GUI.main_window_settings.theme_ctrl"),
            patch("GUI.main_window_settings.theme_manager"),
        ):
            SettingsMixin._restore_settings(host)

        # singleShot must NOT have been called.
        mock_timer.singleShot.assert_not_called()
        # has_shown must NOT be re-set.
        set_keys = [c.args[0] for c in mock_svc.set.call_args_list]
        assert "tutorial/has_shown" not in set_keys


class TestTutorialSettingsIntegration:
    """Integration tests with SettingsService for tutorial flag."""

    def test_fresh_settings_has_shown_is_false(self, tmp_path):
        """Fresh settings should return False for tutorial/has_shown."""
        svc = SettingsService(tmp_path / "test_settings.json")
        assert svc.get_bool("tutorial/has_shown", False) is False

    def test_after_set_has_shown_is_true(self, tmp_path):
        """After setting tutorial/has_shown to True, it should be True."""
        svc = SettingsService(tmp_path / "test_settings.json")
        svc.set("tutorial/has_shown", True)
        assert svc.get_bool("tutorial/has_shown", False) is True

    def test_flag_persists_across_instances(self, tmp_path):
        """Flag should persist across SettingsService instances (simulates restart)."""
        path = tmp_path / "test_settings.json"
        svc1 = SettingsService(path)
        svc1.set("tutorial/has_shown", True)
        svc2 = SettingsService(path)
        assert svc2.get_bool("tutorial/has_shown", False) is True
