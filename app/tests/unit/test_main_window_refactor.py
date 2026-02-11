"""Tests verifying the structural integrity of the MainWindow mixin decomposition.

These tests verify that:
- All mixin classes are importable
- MainWindow inherits from all mixins
- All expected methods exist on MainWindow
- MRO is correct (QMainWindow last)
- Mixins don't define __init__
- No circular imports between mixin files
- Simulation result handlers exist
"""

import ast
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow


class TestMixinClassesImportable:
    """Verify all 7 mixin classes can be imported."""

    def test_menu_bar_mixin(self):
        from GUI.main_window_menus import MenuBarMixin

        assert MenuBarMixin is not None

    def test_file_operations_mixin(self):
        from GUI.main_window_file_ops import FileOperationsMixin

        assert FileOperationsMixin is not None

    def test_simulation_mixin(self):
        from GUI.main_window_simulation import SimulationMixin

        assert SimulationMixin is not None

    def test_analysis_settings_mixin(self):
        from GUI.main_window_analysis import AnalysisSettingsMixin

        assert AnalysisSettingsMixin is not None

    def test_view_operations_mixin(self):
        from GUI.main_window_view import ViewOperationsMixin

        assert ViewOperationsMixin is not None

    def test_print_export_mixin(self):
        from GUI.main_window_print import PrintExportMixin

        assert PrintExportMixin is not None

    def test_settings_mixin(self):
        from GUI.main_window_settings import SettingsMixin

        assert SettingsMixin is not None


class TestMainWindowInheritsAllMixins:
    """Verify MainWindow inherits from all mixins and QMainWindow."""

    def test_inherits_menu_bar_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_menus import MenuBarMixin

        assert issubclass(MainWindow, MenuBarMixin)

    def test_inherits_file_operations_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_file_ops import FileOperationsMixin

        assert issubclass(MainWindow, FileOperationsMixin)

    def test_inherits_simulation_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_simulation import SimulationMixin

        assert issubclass(MainWindow, SimulationMixin)

    def test_inherits_analysis_settings_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_analysis import AnalysisSettingsMixin

        assert issubclass(MainWindow, AnalysisSettingsMixin)

    def test_inherits_view_operations_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_view import ViewOperationsMixin

        assert issubclass(MainWindow, ViewOperationsMixin)

    def test_inherits_print_export_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_print import PrintExportMixin

        assert issubclass(MainWindow, PrintExportMixin)

    def test_inherits_settings_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_settings import SettingsMixin

        assert issubclass(MainWindow, SettingsMixin)

    def test_inherits_qmainwindow(self):
        from GUI.main_window import MainWindow

        assert issubclass(MainWindow, QMainWindow)


class TestMainWindowHasAllExpectedMethods:
    """Verify every method from the original file exists on MainWindow."""

    def test_core_methods(self):
        from GUI.main_window import MainWindow

        for method in ["__init__", "init_ui", "_connect_signals"]:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_menu_methods(self):
        from GUI.main_window import MainWindow

        for method in ["create_menu_bar", "_open_keybindings_dialog", "_apply_keybindings"]:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_file_operation_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "_on_new",
            "copy_selected",
            "cut_selected",
            "paste_components",
            "_on_undo",
            "_on_redo",
            "_update_undo_redo_actions",
            "_on_save",
            "_on_save_as",
            "_on_load",
            "_on_import_netlist",
            "_load_last_session",
            "_populate_examples_menu",
            "_open_example",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_simulation_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "generate_netlist",
            "run_simulation",
            "_run_parameter_sweep",
            "_run_monte_carlo",
            "_display_simulation_results",
            "_calculate_power",
            "_show_plot_dialog",
            "_show_or_overlay_plot",
            "export_results_csv",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_analysis_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "set_analysis_op",
            "set_analysis_dc",
            "set_analysis_ac",
            "set_analysis_transient",
            "set_analysis_temp_sweep",
            "set_analysis_parameter_sweep",
            "set_analysis_monte_carlo",
            "_sync_analysis_menu",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_view_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "_set_theme",
            "_apply_theme",
            "_toggle_statistics_panel",
            "_on_dirty_change",
            "_set_dirty",
            "_update_title_bar",
            "toggle_component_labels",
            "toggle_component_values",
            "toggle_node_labels",
            "toggle_op_annotations",
            "_toggle_probe_mode",
            "_on_probe_requested",
            "_probe_open_waveform",
            "_probe_open_dc_sweep",
            "_probe_open_ac_sweep",
            "_on_zoom_changed",
            "export_image",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_print_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "_get_circuit_source_rect",
            "_render_to_printer",
            "_on_print",
            "_on_print_preview",
            "_on_export_pdf",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_settings_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "_save_settings",
            "_restore_settings",
            "closeEvent",
            "_start_autosave_timer",
            "_auto_save",
            "_check_auto_save_recovery",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"

    def test_canvas_callback_methods(self):
        from GUI.main_window import MainWindow

        methods = [
            "clear_canvas",
            "on_component_right_clicked",
            "_on_selection_changed",
            "on_canvas_clicked",
            "on_property_changed",
        ]
        for method in methods:
            assert hasattr(MainWindow, method), f"Missing: {method}"


class TestQMainWindowIsLastInMRO:
    """Verify QMainWindow comes after all mixins in MRO for correct super() chains."""

    def test_qmainwindow_after_all_mixins(self):
        from GUI.main_window import MainWindow

        mro = MainWindow.__mro__
        mixin_indices = []
        qmw_index = None
        for i, cls in enumerate(mro):
            if cls.__name__.endswith("Mixin"):
                mixin_indices.append(i)
            if cls is QMainWindow:
                qmw_index = i
        assert qmw_index is not None, "QMainWindow not in MRO"
        for mi in mixin_indices:
            assert mi < qmw_index, f"Mixin at index {mi} should come before QMainWindow at {qmw_index}"


class TestSimulationResultHandlersExist:
    """Verify the per-analysis-type display methods exist on SimulationMixin."""

    def test_handler_methods(self):
        from GUI.main_window_simulation import SimulationMixin

        handlers = [
            "_display_op_results",
            "_display_dc_sweep_results",
            "_display_ac_sweep_results",
            "_display_transient_results",
            "_display_temp_sweep_results",
            "_display_param_sweep_results",
            "_display_monte_carlo_results",
            "_display_simulation_errors",
        ]
        for method in handlers:
            assert hasattr(SimulationMixin, method), f"Missing handler: {method}"


class TestMixinClassesHaveNoInit:
    """Verify mixins do not define __init__ (which would interfere with QMainWindow's __init__)."""

    def test_no_init_on_mixins(self):
        from GUI.main_window_analysis import AnalysisSettingsMixin
        from GUI.main_window_file_ops import FileOperationsMixin
        from GUI.main_window_menus import MenuBarMixin
        from GUI.main_window_print import PrintExportMixin
        from GUI.main_window_settings import SettingsMixin
        from GUI.main_window_simulation import SimulationMixin
        from GUI.main_window_view import ViewOperationsMixin

        for mixin_cls in [
            MenuBarMixin,
            FileOperationsMixin,
            SimulationMixin,
            AnalysisSettingsMixin,
            ViewOperationsMixin,
            PrintExportMixin,
            SettingsMixin,
        ]:
            assert "__init__" not in mixin_cls.__dict__, f"{mixin_cls.__name__} should not define __init__"


class TestNoCircularImportsBetweenMixins:
    """Verify mixin files do not import from each other."""

    def test_no_cross_mixin_imports(self):
        gui_dir = Path(__file__).parent.parent.parent / "GUI"
        mixin_modules = {
            "main_window_menus",
            "main_window_file_ops",
            "main_window_simulation",
            "main_window_analysis",
            "main_window_view",
            "main_window_print",
            "main_window_settings",
        }
        for mod_name in mixin_modules:
            source = (gui_dir / f"{mod_name}.py").read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported = node.module.split(".")[-1]
                    msg = f"{mod_name}.py imports {imported} — mixins must not import each other"
                    assert imported not in mixin_modules, msg
