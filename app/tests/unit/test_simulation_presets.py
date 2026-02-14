"""Tests for simulation presets - PresetManager and AnalysisDialog integration."""

import json

import pytest
from simulation.preset_manager import BUILTIN_PRESETS, PresetManager


@pytest.fixture
def preset_file(tmp_path):
    """Return a temporary preset file path."""
    return tmp_path / "presets.json"


@pytest.fixture
def mgr(preset_file):
    """Create a PresetManager with a temp file."""
    return PresetManager(preset_file)


# --- PresetManager unit tests ---


class TestBuiltinPresets:
    def test_builtin_presets_available(self, mgr):
        presets = mgr.get_presets()
        assert len(presets) >= len(BUILTIN_PRESETS)

    def test_builtin_presets_have_required_fields(self, mgr):
        for p in BUILTIN_PRESETS:
            assert "name" in p
            assert "analysis_type" in p
            assert "params" in p

    def test_filter_by_analysis_type(self, mgr):
        ac_presets = mgr.get_presets("AC Sweep")
        assert all(p["analysis_type"] == "AC Sweep" for p in ac_presets)
        assert len(ac_presets) >= 2  # Audio + Wide

    def test_filter_transient(self, mgr):
        tran_presets = mgr.get_presets("Transient")
        assert len(tran_presets) >= 1  # Quick Transient

    def test_get_preset_by_name(self, mgr):
        p = mgr.get_preset_by_name("Quick Transient")
        assert p is not None
        assert p["analysis_type"] == "Transient"

    def test_get_preset_by_name_not_found(self, mgr):
        assert mgr.get_preset_by_name("Nonexistent") is None


class TestUserPresets:
    def test_save_user_preset(self, mgr):
        mgr.save_preset(
            "My Sweep", "DC Sweep", {"source": "V2", "min": 0, "max": 3, "step": 0.5}
        )
        p = mgr.get_preset_by_name("My Sweep", "DC Sweep")
        assert p is not None
        assert p["params"]["source"] == "V2"

    def test_save_overwrites_existing(self, mgr):
        mgr.save_preset(
            "My Sweep", "DC Sweep", {"source": "V1", "min": 0, "max": 5, "step": 0.1}
        )
        mgr.save_preset(
            "My Sweep", "DC Sweep", {"source": "V2", "min": 0, "max": 10, "step": 1}
        )
        presets = mgr.get_presets("DC Sweep")
        my_presets = [p for p in presets if p["name"] == "My Sweep"]
        assert len(my_presets) == 1
        assert my_presets[0]["params"]["source"] == "V2"

    def test_cannot_overwrite_builtin(self, mgr):
        with pytest.raises(ValueError, match="built-in"):
            mgr.save_preset(
                "Quick Transient",
                "Transient",
                {"duration": 1, "step": 0.001, "startTime": 0},
            )

    def test_delete_user_preset(self, mgr):
        mgr.save_preset(
            "Temp", "DC Sweep", {"source": "V1", "min": 0, "max": 5, "step": 0.1}
        )
        assert mgr.delete_preset("Temp", "DC Sweep") is True
        assert mgr.get_preset_by_name("Temp", "DC Sweep") is None

    def test_delete_nonexistent_returns_false(self, mgr):
        assert mgr.delete_preset("Nonexistent") is False

    def test_delete_builtin_returns_false(self, mgr):
        assert mgr.delete_preset("Quick Transient") is False


class TestPresetPersistence:
    def test_presets_persist_to_disk(self, preset_file):
        mgr1 = PresetManager(preset_file)
        mgr1.save_preset(
            "Saved", "Transient", {"duration": 0.1, "step": 1e-06, "startTime": 0}
        )

        mgr2 = PresetManager(preset_file)
        p = mgr2.get_preset_by_name("Saved", "Transient")
        assert p is not None
        assert p["params"]["duration"] == 0.1

    def test_corrupt_file_handled(self, preset_file):
        preset_file.write_text("not valid json{{{")
        mgr = PresetManager(preset_file)
        # Should fall back to empty user presets, builtins still work
        assert len(mgr.get_presets()) == len(BUILTIN_PRESETS)

    def test_missing_file_handled(self, tmp_path):
        mgr = PresetManager(tmp_path / "nonexistent" / "presets.json")
        assert len(mgr.get_presets()) == len(BUILTIN_PRESETS)

    def test_file_format_is_json(self, preset_file):
        mgr = PresetManager(preset_file)
        mgr.save_preset(
            "Test",
            "AC Sweep",
            {"fStart": 10, "fStop": 1000, "points": 50, "sweepType": "dec"},
        )
        data = json.loads(preset_file.read_text())
        assert "presets" in data
        assert len(data["presets"]) == 1


# --- AnalysisDialog + presets integration tests ---

pytest.importorskip("PyQt6")

from GUI.analysis_dialog import AnalysisDialog


class TestDialogPresetUI:
    def test_preset_combo_exists(self, qtbot, preset_file):
        mgr = PresetManager(preset_file)
        dialog = AnalysisDialog("AC Sweep", preset_manager=mgr)
        qtbot.addWidget(dialog)
        assert dialog.preset_combo is not None

    def test_preset_combo_lists_builtins(self, qtbot, preset_file):
        mgr = PresetManager(preset_file)
        dialog = AnalysisDialog("AC Sweep", preset_manager=mgr)
        qtbot.addWidget(dialog)
        items = [
            dialog.preset_combo.itemText(i) for i in range(dialog.preset_combo.count())
        ]
        assert any("Audio AC Sweep" in item for item in items)
        assert any("Wide AC Sweep" in item for item in items)

    def test_selecting_preset_populates_fields(self, qtbot, preset_file):
        mgr = PresetManager(preset_file)
        dialog = AnalysisDialog("AC Sweep", preset_manager=mgr)
        qtbot.addWidget(dialog)
        # Find the "Audio AC Sweep" preset index
        for i in range(dialog.preset_combo.count()):
            if dialog.preset_combo.itemData(i) == "Audio AC Sweep":
                dialog.preset_combo.setCurrentIndex(i)
                break
        # fStart should now be 20
        widget, _ = dialog.field_widgets["fStart"]
        assert widget.text() == "20"

    def test_delete_button_disabled_for_builtin(self, qtbot, preset_file):
        mgr = PresetManager(preset_file)
        dialog = AnalysisDialog("AC Sweep", preset_manager=mgr)
        qtbot.addWidget(dialog)
        # Select a built-in preset
        for i in range(dialog.preset_combo.count()):
            if dialog.preset_combo.itemData(i) == "Audio AC Sweep":
                dialog.preset_combo.setCurrentIndex(i)
                break
        assert not dialog.delete_preset_btn.isEnabled()

    def test_delete_button_disabled_for_none(self, qtbot, preset_file):
        mgr = PresetManager(preset_file)
        dialog = AnalysisDialog("Transient", preset_manager=mgr)
        qtbot.addWidget(dialog)
        dialog.preset_combo.setCurrentIndex(0)  # (none)
        assert not dialog.delete_preset_btn.isEnabled()

    def test_preset_combo_only_shows_matching_type(self, qtbot, preset_file):
        mgr = PresetManager(preset_file)
        dialog = AnalysisDialog("DC Sweep", preset_manager=mgr)
        qtbot.addWidget(dialog)
        items = [
            dialog.preset_combo.itemText(i) for i in range(dialog.preset_combo.count())
        ]
        # Should not show AC Sweep presets
        assert not any("Audio AC Sweep" in item for item in items)
        # Should show DC Sweep presets
        assert any("Fine DC Sweep" in item for item in items)
