"""Tests for analysis dialog tooltips (issue #231).

Verifies that all input fields across the analysis dialogs have
descriptive tooltips to guide users.
"""

import pytest
from GUI.analysis_dialog import AnalysisDialog


class TestAnalysisConfigTooltips:
    """Every field in ANALYSIS_CONFIGS should have a corresponding tooltip."""

    def test_dc_sweep_fields_have_tooltips(self):
        """All DC Sweep fields should have tooltip entries."""
        config = AnalysisDialog.ANALYSIS_CONFIGS["DC Sweep"]
        tooltips = config["tooltips"]
        for field_config in config["fields"]:
            key = field_config[1]
            assert key in tooltips, f"DC Sweep field '{key}' missing tooltip"
            assert len(tooltips[key]) > 0

    def test_ac_sweep_fields_have_tooltips(self):
        """All AC Sweep fields should have tooltip entries."""
        config = AnalysisDialog.ANALYSIS_CONFIGS["AC Sweep"]
        tooltips = config["tooltips"]
        for field_config in config["fields"]:
            key = field_config[1]
            assert key in tooltips, f"AC Sweep field '{key}' missing tooltip"
            assert len(tooltips[key]) > 0

    def test_transient_fields_have_tooltips(self):
        """All Transient fields should have tooltip entries."""
        config = AnalysisDialog.ANALYSIS_CONFIGS["Transient"]
        tooltips = config["tooltips"]
        for field_config in config["fields"]:
            key = field_config[1]
            assert key in tooltips, f"Transient field '{key}' missing tooltip"
            assert len(tooltips[key]) > 0

    def test_temperature_sweep_fields_have_tooltips(self):
        """All Temperature Sweep fields should have tooltip entries."""
        config = AnalysisDialog.ANALYSIS_CONFIGS["Temperature Sweep"]
        tooltips = config["tooltips"]
        for field_config in config["fields"]:
            key = field_config[1]
            assert key in tooltips, f"Temperature Sweep field '{key}' missing tooltip"
            assert len(tooltips[key]) > 0

    def test_dc_operating_point_has_empty_tooltips(self):
        """DC Operating Point has no fields, so tooltips should be empty."""
        config = AnalysisDialog.ANALYSIS_CONFIGS["DC Operating Point"]
        assert config["tooltips"] == {}

    def test_all_configs_have_tooltips_key(self):
        """Every analysis config should have a 'tooltips' key."""
        for name, config in AnalysisDialog.ANALYSIS_CONFIGS.items():
            assert "tooltips" in config, f"Config '{name}' missing 'tooltips' key"

    def test_no_orphan_tooltip_keys(self):
        """Tooltip keys should match actual field keys (no stale entries)."""
        for name, config in AnalysisDialog.ANALYSIS_CONFIGS.items():
            field_keys = {fc[1] for fc in config["fields"]}
            tooltip_keys = set(config.get("tooltips", {}).keys())
            orphans = tooltip_keys - field_keys
            assert not orphans, f"Config '{name}' has orphan tooltip keys: {orphans}"


class TestAnalysisDialogWidgetTooltips:
    """Verify tooltips are applied to actual QWidget instances."""

    @pytest.fixture
    def dialog(self, qtbot):
        dlg = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dlg)
        return dlg

    def test_dc_sweep_source_widget_has_tooltip(self, dialog):
        """The 'source' QLineEdit should have a non-empty tooltip."""
        widget, _ = dialog.field_widgets["source"]
        assert widget.toolTip() != ""

    def test_dc_sweep_all_widgets_have_tooltips(self, dialog):
        """All DC Sweep field widgets should have tooltips."""
        for key, (widget, _) in dialog.field_widgets.items():
            assert widget.toolTip() != "", f"Widget for '{key}' has no tooltip"

    def test_ac_sweep_widgets_have_tooltips(self, qtbot):
        """All AC Sweep field widgets should have tooltips."""
        dlg = AnalysisDialog(analysis_type="AC Sweep")
        qtbot.addWidget(dlg)
        for key, (widget, _) in dlg.field_widgets.items():
            assert widget.toolTip() != "", f"Widget for '{key}' has no tooltip"

    def test_transient_widgets_have_tooltips(self, qtbot):
        """All Transient field widgets should have tooltips."""
        dlg = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dlg)
        for key, (widget, _) in dlg.field_widgets.items():
            assert widget.toolTip() != "", f"Widget for '{key}' has no tooltip"

    def test_temperature_sweep_widgets_have_tooltips(self, qtbot):
        """All Temperature Sweep field widgets should have tooltips."""
        dlg = AnalysisDialog(analysis_type="Temperature Sweep")
        qtbot.addWidget(dlg)
        for key, (widget, _) in dlg.field_widgets.items():
            assert widget.toolTip() != "", f"Widget for '{key}' has no tooltip"

    def test_type_combo_has_tooltip(self, qtbot):
        """The analysis type combo (when no type preset) should have a tooltip."""
        dlg = AnalysisDialog()
        qtbot.addWidget(dlg)
        assert dlg.type_combo.toolTip() != ""

    def test_preset_combo_has_tooltip(self, dialog):
        """The preset combo should have a tooltip."""
        assert dialog.preset_combo.toolTip() != ""

    def test_save_preset_button_has_tooltip(self, dialog):
        """The save preset button should have a tooltip."""
        assert dialog.save_preset_btn.toolTip() != ""

    def test_delete_preset_button_has_tooltip(self, dialog):
        """The delete preset button should have a tooltip."""
        assert dialog.delete_preset_btn.toolTip() != ""


class TestParameterSweepDialogTooltips:
    """Verify tooltips on ParameterSweepDialog widgets."""

    @pytest.fixture
    def dialog(self, qtbot):
        from GUI.parameter_sweep_dialog import ParameterSweepDialog
        from models.component import ComponentData

        components = {
            "R1": ComponentData(
                component_id="R1",
                component_type="Resistor",
                value="1k",
                position=(0, 0),
            ),
        }
        dlg = ParameterSweepDialog(components)
        qtbot.addWidget(dlg)
        return dlg

    def test_component_combo_has_tooltip(self, dialog):
        assert dialog.component_combo.toolTip() != ""

    def test_start_edit_has_tooltip(self, dialog):
        assert dialog.start_edit.toolTip() != ""

    def test_stop_edit_has_tooltip(self, dialog):
        assert dialog.stop_edit.toolTip() != ""

    def test_steps_spin_has_tooltip(self, dialog):
        assert dialog.steps_spin.toolTip() != ""

    def test_analysis_combo_has_tooltip(self, dialog):
        assert dialog.analysis_combo.toolTip() != ""

    def test_base_form_fields_get_tooltips_on_type_change(self, dialog):
        """Changing base analysis type should apply tooltips to new fields."""
        dialog.analysis_combo.setCurrentText("Transient")
        for key, (widget, _) in dialog._base_field_widgets.items():
            assert widget.toolTip() != "", f"Base field '{key}' has no tooltip"


class TestMonteCarloDialogTooltips:
    """Verify tooltips on MonteCarloDialog widgets."""

    @pytest.fixture
    def dialog(self, qtbot):
        from GUI.monte_carlo_dialog import MonteCarloDialog
        from models.component import ComponentData

        components = {
            "R1": ComponentData(
                component_id="R1",
                component_type="Resistor",
                value="1k",
                position=(0, 0),
            ),
        }
        dlg = MonteCarloDialog(components)
        qtbot.addWidget(dlg)
        return dlg

    def test_num_runs_spin_has_tooltip(self, dialog):
        assert dialog.num_runs_spin.toolTip() != ""

    def test_analysis_combo_has_tooltip(self, dialog):
        assert dialog.analysis_combo.toolTip() != ""

    def test_tolerance_table_has_tooltip(self, dialog):
        assert dialog.tol_table is not None
        assert dialog.tol_table.toolTip() != ""

    def test_tolerance_spin_has_tooltip(self, dialog):
        """Each tolerance spin box should have a tooltip."""
        assert dialog.tol_table is not None
        for row in range(dialog.tol_table.rowCount()):
            tol_spin = dialog.tol_table.cellWidget(row, 2)
            assert tol_spin.toolTip() != "", f"Row {row} tolerance spin has no tooltip"

    def test_distribution_combo_has_tooltip(self, dialog):
        """Each distribution combo should have a tooltip."""
        assert dialog.tol_table is not None
        for row in range(dialog.tol_table.rowCount()):
            dist_combo = dialog.tol_table.cellWidget(row, 3)
            assert dist_combo.toolTip() != "", f"Row {row} dist combo has no tooltip"

    def test_base_form_fields_get_tooltips(self, dialog):
        """Changing base analysis type should apply tooltips to base fields."""
        dialog.analysis_combo.setCurrentText("AC Sweep")
        for key, (widget, _) in dialog._base_field_widgets.items():
            assert widget.toolTip() != "", f"Base field '{key}' has no tooltip"
