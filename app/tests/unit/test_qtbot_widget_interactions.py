"""
Qtbot dialog and widget interaction tests.

Tests analysis dialogs, component palette, properties panel,
keybindings dialog, circuit statistics panel, and component
rendering structural assertions.

No MainWindow instantiation — all tests target individual widgets.

Issue: #282
"""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController
from GUI.analysis_dialog import AnalysisDialog
from GUI.component_palette import ComponentPalette
from GUI.keybindings import KeybindingsRegistry
from GUI.keybindings_dialog import KeybindingsDialog
from GUI.properties_panel import PropertiesPanel
from models.circuit import CircuitModel
from models.component import COMPONENT_TYPES, TERMINAL_COUNTS, ComponentData

pytest.importorskip("PyQt6")

from GUI.circuit_statistics_panel import CircuitStatisticsPanel
from PyQt6.QtWidgets import QComboBox, QLineEdit

# ===========================================================================
# Analysis Dialogs
# ===========================================================================


class TestAnalysisDialogInteractions:
    """Test analysis dialog widget interactions beyond basic field building."""

    @pytest.mark.parametrize(
        "analysis_type",
        ["DC Operating Point", "DC Sweep", "AC Sweep", "Transient", "Temperature Sweep", "Noise"],
    )
    def test_each_analysis_type_opens(self, qtbot, analysis_type):
        """Every analysis type dialog opens without error."""
        dialog = AnalysisDialog(analysis_type=analysis_type)
        qtbot.addWidget(dialog)
        assert dialog.analysis_type == analysis_type

    def test_type_combo_switching_updates_description(self, qtbot):
        """Switching analysis types updates the description label."""
        dialog = AnalysisDialog()
        qtbot.addWidget(dialog)

        dialog.type_combo.setCurrentText("Transient")
        expected = AnalysisDialog.ANALYSIS_CONFIGS["Transient"]["description"]
        assert dialog.desc_label.text() == expected

        dialog.type_combo.setCurrentText("DC Operating Point")
        expected_dc = AnalysisDialog.ANALYSIS_CONFIGS["DC Operating Point"]["description"]
        assert dialog.desc_label.text() == expected_dc

    def test_transient_fields_have_defaults(self, qtbot):
        """Transient dialog fields have default values."""
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        duration_widget, _ = dialog.field_widgets["duration"]
        step_widget, _ = dialog.field_widgets["step"]
        assert duration_widget.text() != ""
        assert step_widget.text() != ""

    def test_ac_sweep_combo_field_exists(self, qtbot):
        """AC Sweep has a combo box for sweep type."""
        dialog = AnalysisDialog(analysis_type="AC Sweep")
        qtbot.addWidget(dialog)
        sweep_widget, field_type = dialog.field_widgets["sweepType"]
        assert field_type == "combo"
        assert isinstance(sweep_widget, QComboBox)
        assert sweep_widget.currentText() == "dec"

    def test_noise_has_six_fields(self, qtbot):
        """Noise analysis has all 6 parameter fields."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        expected_keys = {"output_node", "source", "fStart", "fStop", "points", "sweepType"}
        assert set(dialog.field_widgets.keys()) == expected_keys

    def test_temp_sweep_command_generation(self, qtbot):
        """Temperature sweep generates correct ngspice command."""
        dialog = AnalysisDialog(analysis_type="Temperature Sweep")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert ".step temp" in cmd

    def test_field_tooltips_set(self, qtbot):
        """Fields with configured tooltips have tooltip text."""
        dialog = AnalysisDialog(analysis_type="DC Sweep")
        qtbot.addWidget(dialog)
        source_widget, _ = dialog.field_widgets["source"]
        assert source_widget.toolTip() != ""

    def test_preset_combo_exists(self, qtbot):
        """Dialog has a preset combo box."""
        dialog = AnalysisDialog(analysis_type="Transient")
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "preset_combo")
        assert isinstance(dialog.preset_combo, QComboBox)
        # Should have at least "(none)"
        assert dialog.preset_combo.count() >= 1


# ===========================================================================
# Component Palette
# ===========================================================================


class TestComponentPaletteInteractions:
    """Additional palette tests: search and category filtering."""

    @pytest.fixture
    def palette(self, qtbot):
        p = ComponentPalette()
        qtbot.addWidget(p)
        return p

    def test_search_for_op_amp(self, palette):
        """Searching 'op' shows Op-Amp."""
        palette.search_input.setText("op")
        visible = palette.get_visible_component_names()
        assert "Op-Amp" in visible

    def test_search_for_diode(self, palette):
        """Searching 'diode' shows Diode, LED, and Zener Diode."""
        palette.search_input.setText("diode")
        visible = palette.get_visible_component_names()
        assert "Diode" in visible
        assert "Zener Diode" in visible

    def test_search_cleared_restores_all(self, palette):
        """Clearing search shows all items again."""
        palette.search_input.setText("xyz_no_match")
        palette.search_input.clear()
        visible = palette.get_visible_component_names()
        assert len(visible) == len(palette.get_component_names())


# ===========================================================================
# Properties Panel
# ===========================================================================


class TestPropertiesPanelInteractions:
    """Test properties panel multi-select and component switching."""

    @pytest.fixture
    def panel(self, qtbot):
        p = PropertiesPanel()
        qtbot.addWidget(p)
        return p

    def test_multi_select_shows_count(self, panel):
        """Multi-select shows item count message."""
        panel.show_multi_selection(5)
        assert panel.current_component is None
        assert "5" in panel.id_label.text()

    def test_switching_components_updates_fields(self, panel):
        """Switching from one component to another updates fields."""
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        c1 = ComponentData("C1", "Capacitor", "10u", (100, 0))

        panel.show_component(r1)
        assert panel.id_label.text() == "R1"
        assert panel.value_input.text() == "1k"

        panel.show_component(c1)
        assert panel.id_label.text() == "C1"
        assert panel.value_input.text() == "10u"

    def test_opamp_shows_model_combo(self, panel):
        """Op-amp selection shows the model combo box."""
        oa = ComponentData("OA1", "Op-Amp", "Ideal", (0, 0))
        panel.show_component(oa)
        assert not panel.opamp_model_combo.isHidden()

    def test_waveform_shows_configure_button(self, panel):
        """Waveform source shows configure waveform button."""
        vw = ComponentData("VW1", "Waveform Source", "SIN(0 5 1k)", (0, 0))
        panel.show_component(vw)
        assert not panel.waveform_button.isHidden()
        assert panel.value_input.isReadOnly()

    def test_deselect_clears_panel(self, panel):
        """Deselection returns panel to empty state."""
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        panel.show_component(r1)
        panel.show_no_selection()
        assert panel.current_component is None
        assert panel.id_label.text() == "-"


# ===========================================================================
# Keybindings Dialog
# ===========================================================================


class TestKeybindingsDialogInteractions:
    """Test keybinding dialog table behavior."""

    @pytest.fixture
    def dialog(self, qtbot, tmp_path):
        reg = KeybindingsRegistry(config_path=tmp_path / "kb.json")
        dlg = KeybindingsDialog(reg)
        qtbot.addWidget(dlg)
        return dlg, reg

    def test_table_rows_match_action_count(self, dialog):
        dlg, reg = dialog
        assert dlg._table.rowCount() == len(reg.get_all())

    def test_table_columns_are_action_and_shortcut(self, dialog):
        dlg, _ = dialog
        assert dlg._table.columnCount() == 2

    def test_reset_defaults_restores_bindings(self, dialog):
        """Reset to defaults restores a modified binding."""
        dlg, reg = dialog
        original = reg.get("file.new")
        reg.set("file.new", "Ctrl+Shift+N")
        assert reg.get("file.new") == "Ctrl+Shift+N"
        reg.reset_defaults()
        assert reg.get("file.new") == original

    def test_conflict_detection(self, dialog):
        """Setting duplicate shortcut is detected."""
        _, reg = dialog
        undo_shortcut = reg.get("edit.undo")
        reg.set("file.new", undo_shortcut)
        conflicts = reg.get_conflicts()
        conflict_shortcuts = [c[0].lower() for c in conflicts]
        assert undo_shortcut.lower() in conflict_shortcuts


# ===========================================================================
# Circuit Statistics Panel
# ===========================================================================


class TestStatisticsPanelInteractions:
    """Test statistics panel updates via controller observer."""

    @pytest.fixture
    def panel_ctx(self, qtbot):
        model = CircuitModel()
        circuit_ctrl = CircuitController(model)
        sim_ctrl = SimulationController(model, circuit_ctrl)
        panel = CircuitStatisticsPanel(model, circuit_ctrl, sim_ctrl)
        qtbot.addWidget(panel)
        return panel, model, circuit_ctrl

    def test_wire_count_updates_on_add(self, panel_ctx):
        panel, _, ctrl = panel_ctx
        r1 = ctrl.add_component("Resistor", (0, 0))
        v1 = ctrl.add_component("Voltage Source", (100, 0))
        ctrl.add_wire(r1.component_id, 0, v1.component_id, 0)
        assert panel._wire_count_label.text() == "1"

    def test_wire_count_updates_on_remove(self, panel_ctx):
        panel, _, ctrl = panel_ctx
        r1 = ctrl.add_component("Resistor", (0, 0))
        v1 = ctrl.add_component("Voltage Source", (100, 0))
        ctrl.add_wire(r1.component_id, 0, v1.component_id, 0)
        ctrl.remove_wire(0)
        assert panel._wire_count_label.text() == "0"

    def test_circuit_clear_resets_all_stats(self, panel_ctx):
        panel, _, ctrl = panel_ctx
        ctrl.add_component("Resistor", (0, 0))
        ctrl.add_component("Capacitor", (100, 0))
        ctrl.clear_circuit()
        assert panel._total_components_label.text() == "0"
        assert panel._wire_count_label.text() == "0"


# ===========================================================================
# Component Rendering — Geometric/Structural Assertions
# ===========================================================================


class TestComponentTerminalGeometry:
    """Structural assertions about terminal positions without pixel rendering."""

    @pytest.mark.parametrize("comp_type", COMPONENT_TYPES)
    def test_terminal_count_matches_spec(self, comp_type):
        """Each component type has the expected number of terminals."""
        expected = TERMINAL_COUNTS.get(comp_type, 2)
        comp = ComponentData("X1", comp_type, "test", (100, 100))
        terminals = comp.get_terminal_positions()
        assert len(terminals) == expected

    @pytest.mark.parametrize("comp_type", COMPONENT_TYPES)
    def test_terminals_are_distinct(self, comp_type):
        """No two terminals overlap at the same position."""
        comp = ComponentData("X1", comp_type, "test", (100, 100))
        terminals = comp.get_terminal_positions()
        if len(terminals) > 1:
            positions = set(terminals)
            assert len(positions) == len(terminals), f"{comp_type} has overlapping terminals"

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_rotation_preserves_terminal_count(self, rotation):
        """All 4 rotations produce the correct number of terminals."""
        comp = ComponentData("R1", "Resistor", "1k", (100, 100), rotation=rotation)
        terminals = comp.get_terminal_positions()
        assert len(terminals) == 2

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_rotation_changes_terminal_positions(self, rotation):
        """Rotated terminals differ from non-rotated (except 0)."""
        comp_0 = ComponentData("R1", "Resistor", "1k", (100, 100), rotation=0)
        comp_r = ComponentData("R1", "Resistor", "1k", (100, 100), rotation=rotation)
        terms_0 = comp_0.get_terminal_positions()
        terms_r = comp_r.get_terminal_positions()
        if rotation == 0:
            assert terms_0 == terms_r
        else:
            assert terms_0 != terms_r

    def test_flip_h_transforms_terminals(self):
        """Horizontal flip changes terminal positions."""
        comp_normal = ComponentData("R1", "Resistor", "1k", (100, 100), flip_h=False)
        comp_flipped = ComponentData("R1", "Resistor", "1k", (100, 100), flip_h=True)
        terms_normal = comp_normal.get_terminal_positions()
        terms_flipped = comp_flipped.get_terminal_positions()
        # For symmetric 2-terminal components, flip_h swaps terminal order
        assert terms_normal[0] == terms_flipped[1]
        assert terms_normal[1] == terms_flipped[0]

    def test_flip_v_transforms_terminals(self):
        """Vertical flip changes terminal positions for non-horizontal components."""
        # Use Op-Amp which has terminals at different y positions
        comp_normal = ComponentData("OA1", "Op-Amp", "Ideal", (100, 100), flip_v=False)
        comp_flipped = ComponentData("OA1", "Op-Amp", "Ideal", (100, 100), flip_v=True)
        terms_normal = comp_normal.get_terminal_positions()
        terms_flipped = comp_flipped.get_terminal_positions()
        # The y-coordinates should differ
        assert terms_normal != terms_flipped

    def test_bounding_box_non_zero(self):
        """Terminal positions define a non-zero extent from center."""
        comp = ComponentData("R1", "Resistor", "1k", (0, 0))
        terminals = comp.get_terminal_positions()
        xs = [t[0] for t in terminals]
        assert max(xs) - min(xs) > 0

    @pytest.mark.parametrize(
        "comp_type",
        ["Op-Amp", "VCVS", "CCVS", "VCCS", "CCCS", "BJT NPN", "BJT PNP", "MOSFET NMOS", "MOSFET PMOS", "VC Switch"],
    )
    def test_multi_terminal_component_geometry(self, comp_type):
        """Multi-terminal components have correct terminal count and non-overlapping positions."""
        expected_count = TERMINAL_COUNTS[comp_type]
        comp = ComponentData("X1", comp_type, "test", (50, 50))
        terminals = comp.get_terminal_positions()
        assert len(terminals) == expected_count
        assert len(set(terminals)) == expected_count

    def test_ground_has_single_terminal(self):
        """Ground component has exactly 1 terminal."""
        comp = ComponentData("GND1", "Ground", "0V", (0, 0))
        terminals = comp.get_terminal_positions()
        assert len(terminals) == 1

    @pytest.mark.parametrize("comp_type", COMPONENT_TYPES)
    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_all_types_all_rotations_valid(self, comp_type, rotation):
        """Every component type at every rotation produces valid terminals."""
        expected = TERMINAL_COUNTS.get(comp_type, 2)
        comp = ComponentData("X1", comp_type, "test", (100, 100), rotation=rotation)
        terminals = comp.get_terminal_positions()
        assert len(terminals) == expected
        # All positions should be finite numbers
        for x, y in terminals:
            assert abs(x) < 10000
            assert abs(y) < 10000
