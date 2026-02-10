"""
Unit tests for keybindings_dialog.py — KeybindingsDialog.
"""

import pytest
from GUI.keybindings import KeybindingsRegistry
from GUI.keybindings_dialog import KeybindingsDialog


class TestKeybindingsDialog:
    def test_opens_without_crash(self, qtbot, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        dlg = KeybindingsDialog(reg)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Configure Keybindings"

    def test_table_populated(self, qtbot, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        dlg = KeybindingsDialog(reg)
        qtbot.addWidget(dlg)
        # Table should have rows for all actions
        assert dlg._table.rowCount() > 0
        assert dlg._table.columnCount() == 2

    def test_table_has_all_actions(self, qtbot, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        dlg = KeybindingsDialog(reg)
        qtbot.addWidget(dlg)
        all_bindings = reg.get_all()
        assert dlg._table.rowCount() == len(all_bindings)

    def test_registry_reset_reflected(self, qtbot, tmp_path):
        """Verify that resetting the registry restores defaults."""
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        reg.set("file.new", "Ctrl+Shift+N")
        assert reg.get("file.new") == "Ctrl+Shift+N"
        reg.reset_defaults()
        assert reg.get("file.new") == "Ctrl+N"
