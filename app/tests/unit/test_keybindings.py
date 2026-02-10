"""
Unit tests for keybindings.py — KeybindingsRegistry.
"""

import json
from pathlib import Path

import pytest
from GUI.keybindings import ACTION_LABELS, DEFAULTS, KeybindingsRegistry


class TestKeybindingsRegistry:
    def test_defaults_loaded(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        assert reg.get("file.new") == "Ctrl+N"
        assert reg.get("sim.run") == "F5"

    def test_get_unknown_action(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        assert reg.get("nonexistent.action") == ""

    def test_set_updates_binding(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        reg.set("file.new", "Ctrl+Shift+N")
        assert reg.get("file.new") == "Ctrl+Shift+N"

    def test_get_all_returns_copy(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        all_bindings = reg.get_all()
        all_bindings["file.new"] = "MODIFIED"
        # Original should not be affected
        assert reg.get("file.new") == "Ctrl+N"

    def test_reset_defaults(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        reg.set("file.new", "Ctrl+Shift+N")
        reg.reset_defaults()
        assert reg.get("file.new") == "Ctrl+N"

    def test_save_and_load(self, tmp_path):
        config_path = tmp_path / "kb.json"
        reg = KeybindingsRegistry(config_path=config_path)
        reg.set("file.new", "Ctrl+Shift+N")
        reg.save()

        # Load in a new instance
        reg2 = KeybindingsRegistry(config_path=config_path)
        assert reg2.get("file.new") == "Ctrl+Shift+N"
        # Unchanged defaults should still be correct
        assert reg2.get("file.save") == "Ctrl+S"

    def test_save_only_overrides(self, tmp_path):
        config_path = tmp_path / "kb.json"
        reg = KeybindingsRegistry(config_path=config_path)
        reg.set("file.new", "Ctrl+Shift+N")
        reg.save()

        with open(config_path) as f:
            saved = json.load(f)
        # Only the override should be saved
        assert saved == {"file.new": "Ctrl+Shift+N"}

    def test_load_ignores_unknown_keys(self, tmp_path):
        config_path = tmp_path / "kb.json"
        config_path.write_text(json.dumps({"unknown.action": "Ctrl+Z"}))
        reg = KeybindingsRegistry(config_path=config_path)
        # Should not crash, unknown key is ignored
        assert reg.get("unknown.action") == ""

    def test_load_handles_corrupt_json(self, tmp_path):
        config_path = tmp_path / "kb.json"
        config_path.write_text("not valid json {{{")
        reg = KeybindingsRegistry(config_path=config_path)
        # Should fall back to defaults
        assert reg.get("file.new") == "Ctrl+N"

    def test_no_conflicts_in_defaults(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        conflicts = reg.get_conflicts()
        assert conflicts == [], f"Default keybindings have conflicts: {conflicts}"

    def test_conflict_detection(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        reg.set("file.save", "Ctrl+N")  # Conflicts with file.new
        conflicts = reg.get_conflicts()
        assert len(conflicts) == 1
        shortcut, actions = conflicts[0]
        assert shortcut == "ctrl+n"
        assert "file.new" in actions
        assert "file.save" in actions

    def test_empty_shortcuts_no_conflict(self, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        reg.set("edit.clear", "")
        reg.set("file.exit", "")
        conflicts = reg.get_conflicts()
        # Empty shortcuts should not be considered conflicts
        assert all(s != "" for s, _ in conflicts)


class TestActionLabels:
    def test_all_defaults_have_labels(self):
        for action in DEFAULTS:
            assert action in ACTION_LABELS, f"Missing label for action: {action}"

    def test_all_labels_have_defaults(self):
        for action in ACTION_LABELS:
            assert action in DEFAULTS, f"Label for non-existent action: {action}"
