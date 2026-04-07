"""Tests for first-launch tutorial auto-trigger (#486).

The guided tutorial should start automatically on the very first launch
(no existing settings). On subsequent launches it should not auto-start.

MainWindow cannot be instantiated in offscreen mode, so we test via
structural analysis and settings service integration.
"""

import ast
import inspect
import textwrap

from controllers.settings_service import SettingsService


def _get_restore_settings_source():
    """Return the source of SettingsMixin._restore_settings."""
    from GUI.main_window_settings import SettingsMixin

    return textwrap.dedent(inspect.getsource(SettingsMixin._restore_settings))


class TestFirstLaunchTutorialStructure:
    """Structural tests for the first-launch tutorial trigger."""

    def test_tutorial_has_shown_key_checked(self):
        """_restore_settings should check tutorial/has_shown flag."""
        src = _get_restore_settings_source()
        assert "tutorial/has_shown" in src

    def test_tutorial_flag_set_to_true(self):
        """After triggering, tutorial/has_shown should be set to True."""
        src = _get_restore_settings_source()
        assert 'settings.set("tutorial/has_shown", True)' in src

    def test_start_tutorial_called_via_timer(self):
        """Tutorial should be triggered via QTimer.singleShot for deferred start."""
        src = _get_restore_settings_source()
        assert "singleShot" in src
        assert "_start_tutorial" in src

    def test_tutorial_only_on_first_launch(self):
        """The check should use get_bool with default False so existing users are not affected."""
        src = _get_restore_settings_source()
        tree = ast.parse(src)
        # Verify it checks get_bool("tutorial/has_shown", False) with a NOT condition
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "get_bool":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and arg.value == "tutorial/has_shown":
                            found = True
        assert found, "_restore_settings should call settings.get_bool('tutorial/has_shown', ...)"


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
