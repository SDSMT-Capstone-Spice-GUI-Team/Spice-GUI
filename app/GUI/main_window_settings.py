"""Settings persistence, autosave, crash recovery, and window lifecycle for MainWindow."""

from controllers.settings_service import settings
from PyQt6.QtWidgets import QMessageBox

from .styles import theme_manager


class SettingsMixin:
    """Mixin providing settings persistence, autosave, and closeEvent."""

    def _save_settings(self):
        """Save user preferences via the centralized settings service."""
        settings.set("window/geometry", self.saveGeometry())
        settings.set("window/state", self.saveState())
        settings.set("splitter/sizes", self.center_splitter.sizes())
        settings.set("analysis/type", self.model.analysis_type)
        settings.set("view/show_labels", self.canvas.show_component_labels)
        settings.set("view/show_values", self.canvas.show_component_values)
        settings.set("view/show_nodes", self.canvas.show_node_labels)
        # Preserve auto-save defaults if not yet set
        if settings.get("autosave/interval") is None:
            settings.set("autosave/interval", 60)
        if settings.get("autosave/enabled") is None:
            settings.set("autosave/enabled", True)
        settings.set("view/show_statistics", self.statistics_panel.isVisible())
        # Preserve default zoom if not yet set
        if settings.get("view/default_zoom") is None:
            settings.set("view/default_zoom", 100)
        settings.set("view/theme_key", theme_manager.get_theme_key())
        settings.set("view/theme", theme_manager.current_theme.name)
        settings.set("view/symbol_style", theme_manager.symbol_style)
        settings.set("view/color_mode", theme_manager.color_mode)
        settings.set("view/wire_thickness", theme_manager.wire_thickness)
        settings.set("view/show_junction_dots", theme_manager.show_junction_dots)
        settings.set("view/routing_mode", theme_manager.routing_mode)

    def _restore_settings(self):
        """Restore user preferences from the centralized settings service."""
        geometry = settings.get("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = settings.get("window/state")
        if state:
            self.restoreState(state)

        splitter_sizes = settings.get("splitter/sizes")
        if splitter_sizes:
            self.center_splitter.setSizes([int(s) for s in splitter_sizes])

        analysis_type = settings.get("analysis/type")
        if analysis_type:
            # Don't restore "Parameter Sweep" — it requires component selection
            if analysis_type == "Parameter Sweep":
                analysis_type = "DC Operating Point"
            self.simulation_ctrl.set_analysis(analysis_type, self.model.analysis_params)
            self._sync_analysis_menu()

        show_labels = settings.get("view/show_labels")
        if show_labels is not None:
            checked = settings.get_bool("view/show_labels")
            self.canvas.show_component_labels = checked
            self.show_labels_action.setChecked(checked)

        show_values = settings.get("view/show_values")
        if show_values is not None:
            checked = settings.get_bool("view/show_values")
            self.canvas.show_component_values = checked
            self.show_values_action.setChecked(checked)

        show_nodes = settings.get("view/show_nodes")
        if show_nodes is not None:
            checked = settings.get_bool("view/show_nodes")
            self.canvas.show_node_labels = checked
            self.show_nodes_action.setChecked(checked)

        show_stats = settings.get("view/show_statistics")
        if show_stats is not None:
            checked = settings.get_bool("view/show_statistics")
            self.statistics_panel.setVisible(checked)
            self.show_statistics_action.setChecked(checked)

        default_zoom = settings.get("view/default_zoom")
        if default_zoom is not None:
            self.canvas.set_default_zoom(int(default_zoom))

        saved_theme_key = settings.get("view/theme_key")
        if saved_theme_key and saved_theme_key != "light":
            theme_manager.set_theme_by_key(saved_theme_key)
            self._apply_theme()
            if hasattr(self, "_refresh_theme_menu"):
                self._refresh_theme_menu()
        else:
            # Legacy fallback: check old theme name
            saved_theme = settings.get("view/theme")
            if saved_theme == "Dark Theme":
                self._set_theme("dark")

        saved_symbol_style = settings.get("view/symbol_style")
        if saved_symbol_style in ("ieee", "iec"):
            self._set_symbol_style(saved_symbol_style)

        saved_color_mode = settings.get("view/color_mode")
        if saved_color_mode in ("color", "monochrome"):
            self._set_color_mode(saved_color_mode)

        saved_wire_thickness = settings.get("view/wire_thickness")
        if saved_wire_thickness in ("thin", "normal", "thick"):
            self._set_wire_thickness(saved_wire_thickness)

        saved_junction_dots = settings.get("view/show_junction_dots")
        if saved_junction_dots is not None:
            self._set_show_junction_dots(settings.get_bool("view/show_junction_dots"))

        saved_routing_mode = settings.get("view/routing_mode")
        if saved_routing_mode in ("orthogonal", "diagonal"):
            self._set_routing_mode(saved_routing_mode)

    def closeEvent(self, event):
        """Save settings before closing"""
        self._save_settings()
        self.file_ctrl.clear_auto_save()
        super().closeEvent(event)

    def _start_autosave_timer(self):
        """Start or restart the auto-save timer using the configured interval."""
        interval = settings.get_int("autosave/interval", 60)
        enabled = settings.get_bool("autosave/enabled", True)
        if not enabled:
            self._autosave_timer.stop()
            return
        self._autosave_timer.start(interval * 1000)

    def _auto_save(self):
        """Periodic auto-save callback — saves to recovery file."""
        if not self.model.components:
            return
        self.file_ctrl.auto_save()

    def _check_auto_save_recovery(self):
        """On startup, check for auto-save file and offer recovery."""
        if not self.file_ctrl.has_auto_save():
            return
        reply = QMessageBox.question(
            self,
            "Recover Unsaved Changes",
            "An auto-save recovery file was found.\n\n"
            "This may contain unsaved work from a previous session "
            "that was not closed cleanly.\n\n"
            "Would you like to recover it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            source = self.file_ctrl.load_auto_save()
            if source is not None:
                title = f"Circuit Design GUI - {source}" if source else "Circuit Design GUI - (Recovered)"
                self.setWindowTitle(title)
                self._sync_analysis_menu()
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage("Auto-save recovered", 5000)
        self.file_ctrl.clear_auto_save()
