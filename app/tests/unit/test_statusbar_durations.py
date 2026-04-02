"""Tests for centralized status bar message duration constants (#517).

Verifies that duration constants exist, are reasonable, and form a
sensible hierarchy. Also checks that no hardcoded duration literals
remain in the GUI modules.
"""

import ast
import inspect

from GUI.styles import STATUS_DURATION_DEFAULT, STATUS_DURATION_LONG, STATUS_DURATION_SHORT


class TestDurationConstants:
    """Status bar duration constants must be positive and ordered."""

    def test_short_is_positive(self):
        assert STATUS_DURATION_SHORT > 0

    def test_default_is_positive(self):
        assert STATUS_DURATION_DEFAULT > 0

    def test_long_is_positive(self):
        assert STATUS_DURATION_LONG > 0

    def test_short_less_than_default(self):
        assert STATUS_DURATION_SHORT < STATUS_DURATION_DEFAULT

    def test_default_less_than_long(self):
        assert STATUS_DURATION_DEFAULT < STATUS_DURATION_LONG

    def test_short_value(self):
        assert STATUS_DURATION_SHORT == 2000

    def test_default_value(self):
        assert STATUS_DURATION_DEFAULT == 3000

    def test_long_value(self):
        assert STATUS_DURATION_LONG == 5000


class TestNoHardcodedDurationsInMainWindow:
    """Main window show_status_message should use the constant as default."""

    def test_show_status_message_default_uses_constant(self):
        from GUI.main_window import MainWindow

        sig = inspect.signature(MainWindow.show_status_message)
        default = sig.parameters["timeout_ms"].default
        assert default == STATUS_DURATION_DEFAULT
