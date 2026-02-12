"""Settings persistence, autosave, crash recovery, and window lifecycle for MainWindow."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox

from .styles import theme_manager


class SettingsMixin:
    """Mixin providing QSettings persistence, autosave, and closeEvent."""

    def _save_settings(self):
        """Save user preferences via QSettings"""
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState())
        settings.setValue("splitter/sizes", self.center_splitter.sizes())
        settings.setValue("analysis/type", self.model.analysis_type)
        settings.setValue("view/show_labels", self.canvas.show_component_labels)
        settings.setValue("view/show_values", self.canvas.show_component_values)
        settings.setValue("view/show_nodes", self.canvas.show_node_labels)
        # Preserve auto-save defaults if not yet set
        if settings.value("autosave/interval") is None:
            settings.setValue("autosave/interval", 60)
        if settings.value("autosave/enabled") is None:
            settings.setValue("autosave/enabled", True)
        settings.setValue("view/show_statistics", self.statistics_panel.isVisible())
        settings.setValue("view/theme", theme_manager.current_theme.name)
        settings.setValue("view/symbol_style", theme_manager.symbol_style)
        settings.setValue("view/color_mode", theme_manager.color_mode)

    def _restore_settings(self):
        """Restore user preferences from QSettings"""
        settings = QSettings("SDSMT", "SDM Spice")

        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = settings.value("window/state")
        if state:
            self.restoreState(state)

        splitter_sizes = settings.value("splitter/sizes")
        if splitter_sizes:
            self.center_splitter.setSizes([int(s) for s in splitter_sizes])

        analysis_type = settings.value("analysis/type")
        if analysis_type:
            # Don't restore "Parameter Sweep" — it requires component selection
            if analysis_type == "Parameter Sweep":
                analysis_type = "DC Operating Point"
            self.simulation_ctrl.set_analysis(analysis_type, self.model.analysis_params)
            self._sync_analysis_menu()

        show_labels = settings.value("view/show_labels")
        if show_labels is not None:
            checked = show_labels == "true" or show_labels is True
            self.canvas.show_component_labels = checked
            self.show_labels_action.setChecked(checked)

        show_values = settings.value("view/show_values")
        if show_values is not None:
            checked = show_values == "true" or show_values is True
            self.canvas.show_component_values = checked
            self.show_values_action.setChecked(checked)

        show_nodes = settings.value("view/show_nodes")
        if show_nodes is not None:
            checked = show_nodes == "true" or show_nodes is True
            self.canvas.show_node_labels = checked
            self.show_nodes_action.setChecked(checked)

        show_stats = settings.value("view/show_statistics")
        if show_stats is not None:
            checked = show_stats == "true" or show_stats is True
            self.statistics_panel.setVisible(checked)
            self.show_statistics_action.setChecked(checked)

        saved_theme = settings.value("view/theme")
        if saved_theme == "Dark Theme":
            self._set_theme("dark")

        saved_symbol_style = settings.value("view/symbol_style")
        if saved_symbol_style in ("ieee", "iec"):
            self._set_symbol_style(saved_symbol_style)

        saved_color_mode = settings.value("view/color_mode")
        if saved_color_mode in ("color", "monochrome"):
            self._set_color_mode(saved_color_mode)

    def closeEvent(self, event):
        """Save settings before closing"""
        self._save_settings()
        self.file_ctrl.clear_auto_save()
        super().closeEvent(event)

    def _start_autosave_timer(self):
        """Start or restart the auto-save timer using the configured interval."""
        settings = QSettings("SDSMT", "SDM Spice")
        interval = int(settings.value("autosave/interval", 60))
        enabled = settings.value("autosave/enabled", True)
        if enabled == "false" or enabled is False:
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
