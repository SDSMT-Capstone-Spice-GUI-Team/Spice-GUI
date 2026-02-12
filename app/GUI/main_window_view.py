"""View operations: theme, visibility toggles, probe tool, zoom, and image export for MainWindow."""

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog
from .styles import DarkTheme, LightTheme, theme_manager
from .waveform_dialog import WaveformDialog


class ViewOperationsMixin:
    """Mixin providing theme, visibility toggles, probe, zoom, and image export."""

    def _set_theme(self, theme_name: str):
        """Switch the application theme."""
        if theme_name == "dark":
            theme_manager.set_theme(DarkTheme())
            self.dark_theme_action.setChecked(True)
        else:
            theme_manager.set_theme(LightTheme())
            self.light_theme_action.setChecked(True)
        self._apply_theme()

    def _apply_theme(self):
        """Apply the current theme to all visual elements."""
        is_dark = theme_manager.current_theme.name == "Dark Theme"

        # Apply global widget stylesheet for dark mode
        if is_dark:
            dark_stylesheet = (
                "QMainWindow, QWidget { background-color: #1E1E1E; color: #D4D4D4; }"
                " QMenuBar { background-color: #2D2D2D; color: #D4D4D4; }"
                " QMenuBar::item:selected { background-color: #3D3D3D; }"
                " QMenu { background-color: #2D2D2D; color: #D4D4D4; }"
                " QMenu::item:selected { background-color: #3D3D3D; }"
                " QLabel { color: #D4D4D4; }"
                " QPushButton {"
                "   background-color: #3D3D3D; color: #D4D4D4;"
                "   border: 1px solid #555555; padding: 4px 12px; border-radius: 3px;"
                " }"
                " QPushButton:hover { background-color: #4D4D4D; }"
                " QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {"
                "   background-color: #2D2D2D; color: #D4D4D4;"
                "   border: 1px solid #555555;"
                " }"
                " QSplitter::handle { background-color: #3D3D3D; }"
                " QScrollBar { background-color: #2D2D2D; }"
                " QScrollBar::handle { background-color: #555555; }"
                " QGroupBox { color: #D4D4D4; border: 1px solid #555555; }"
                " QTableWidget { background-color: #2D2D2D; color: #D4D4D4;"
                "   gridline-color: #555555; }"
                " QHeaderView::section { background-color: #3D3D3D; color: #D4D4D4; }"
            )
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet("")

        # Refresh canvas (grid + components)
        self.canvas.refresh_theme()

    def _set_symbol_style(self, style: str):
        """Switch the component symbol drawing style."""
        theme_manager.set_symbol_style(style)
        if style == "iec":
            self.iec_style_action.setChecked(True)
        else:
            self.ieee_style_action.setChecked(True)
        self.canvas.scene.update()

    def _set_color_mode(self, mode: str):
        """Switch between per-type color and monochrome rendering."""
        theme_manager.set_color_mode(mode)
        if mode == "monochrome":
            self.monochrome_mode_action.setChecked(True)
        else:
            self.color_mode_action.setChecked(True)
        self.canvas.scene.update()

    def _toggle_statistics_panel(self, checked):
        """Toggle the circuit statistics panel visibility."""
        self.statistics_panel.setVisible(checked)
        if checked:
            self.statistics_panel.refresh()

    # Dirty flag (unsaved changes indicator)

    def _on_dirty_change(self, event: str, data) -> None:
        """Mark circuit as dirty on model-modifying events."""
        dirty_events = {
            "component_added",
            "component_removed",
            "component_moved",
            "component_rotated",
            "component_flipped",
            "component_value_changed",
            "wire_added",
            "wire_removed",
            "wire_routed",
            "net_name_changed",
        }
        if event in dirty_events:
            self._set_dirty(True)
        elif event in ("circuit_cleared", "model_loaded"):
            self._set_dirty(False)

    def _set_dirty(self, dirty: bool):
        """Update the dirty flag and refresh the title bar."""
        self._dirty = dirty
        self._update_title_bar()

    def _update_title_bar(self):
        """Update window title to show dirty indicator."""
        base = "Circuit Design GUI"
        if self.file_ctrl.current_file:
            base += f" - {self.file_ctrl.current_file}"
        else:
            base += " - Student Prototype"
        if self._dirty:
            base += " *"
        self.setWindowTitle(base)

    def toggle_component_labels(self, checked):
        """Toggle component label visibility"""
        self.canvas.show_component_labels = checked
        self.canvas.scene.update()

    def toggle_component_values(self, checked):
        """Toggle component value visibility"""
        self.canvas.show_component_values = checked
        self.canvas.scene.update()

    def toggle_node_labels(self, checked):
        """Toggle node label visibility"""
        self.canvas.show_node_labels = checked
        self.canvas.scene.update()

    def toggle_op_annotations(self, checked):
        """Toggle DC operating point annotation visibility."""
        self.canvas.show_op_annotations = checked
        self.canvas.scene.update()

    def _toggle_probe_mode(self, checked):
        """Toggle interactive probe mode on the canvas."""
        self.canvas.set_probe_mode(checked)
        if checked:
            if not self.canvas.node_voltages and self._last_results is None:
                self.statusBar().showMessage("Probe mode active. Run a simulation first to see values.", 3000)
            else:
                self.statusBar().showMessage(
                    "Probe mode active. Click nodes or components to see values. Press Escape to exit.",
                    3000,
                )
        else:
            self.canvas.clear_probes()
            self.statusBar().showMessage("Probe mode deactivated.", 2000)

    def _on_probe_requested(self, signal_name, probe_type):
        """Handle probe click for sweep/transient analyses (no OP data on canvas)."""
        if self._last_results is None:
            self.statusBar().showMessage("No simulation results available. Run a simulation first.", 3000)
            return

        analysis_type = self._last_results_type
        if analysis_type == "Transient":
            self._probe_open_waveform(signal_name, probe_type)
        elif analysis_type == "DC Sweep":
            self._probe_open_dc_sweep(signal_name, probe_type)
        elif analysis_type == "AC Sweep":
            self._probe_open_ac_sweep(signal_name, probe_type)
        else:
            self.statusBar().showMessage(f"Probe not supported for {analysis_type} analysis.", 3000)

    def _probe_open_waveform(self, signal_name, probe_type):
        """Open waveform dialog focused on the probed signal."""
        tran_data = self._last_results
        if not tran_data:
            return
        # Open or raise the waveform dialog
        if self._waveform_dialog is None or not self._waveform_dialog.isVisible():
            self._waveform_dialog = WaveformDialog(tran_data, self)
            self._waveform_dialog.show()
        self._waveform_dialog.raise_()
        self._waveform_dialog.activateWindow()
        self.statusBar().showMessage(f"Opened waveform plot for {signal_name}.", 2000)

    def _probe_open_dc_sweep(self, signal_name, probe_type):
        """Open DC sweep plot dialog for the probed signal."""
        sweep_data = self._last_results
        if not sweep_data:
            return
        if self._plot_dialog is None or not self._plot_dialog.isVisible():
            self._show_plot_dialog(DCSweepPlotDialog(sweep_data, self))
        self._plot_dialog.raise_()
        self._plot_dialog.activateWindow()
        self.statusBar().showMessage(f"Opened DC sweep plot for {signal_name}.", 2000)

    def _probe_open_ac_sweep(self, signal_name, probe_type):
        """Open AC sweep Bode plot dialog for the probed signal."""
        ac_data = self._last_results
        if not ac_data:
            return
        if self._plot_dialog is None or not self._plot_dialog.isVisible():
            self._show_plot_dialog(ACSweepPlotDialog(ac_data, self))
        self._plot_dialog.raise_()
        self._plot_dialog.activateWindow()
        self.statusBar().showMessage(f"Opened AC sweep plot for {signal_name}.", 2000)

    def _on_zoom_changed(self, level):
        """Update the zoom level display"""
        self.zoom_label.setText(f"{level * 100:.0f}%")

    def export_image(self):
        """Export the circuit diagram as a PNG or SVG image"""
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Image", "", "PNG Image (*.png);;SVG Image (*.svg)"
        )
        if not filename:
            return

        scene = self.canvas.scene

        # Compute bounding rect of circuit items (excluding grid)
        from .annotation_item import AnnotationItem
        from .component_item import ComponentGraphicsItem
        from .wire_item import WireGraphicsItem

        circuit_items = [
            item
            for item in scene.items()
            if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem, AnnotationItem))
        ]
        if not circuit_items:
            QMessageBox.information(self, "Export Image", "Nothing to export — the canvas is empty.")
            return

        source_rect = circuit_items[0].sceneBoundingRect()
        for item in circuit_items[1:]:
            source_rect = source_rect.united(item.sceneBoundingRect())

        # Add padding
        padding = 40
        source_rect.adjust(-padding, -padding, padding, padding)

        if filename.lower().endswith(".svg"):
            from PyQt6.QtCore import QSize
            from PyQt6.QtSvg import QSvgGenerator

            generator = QSvgGenerator()
            generator.setFileName(filename)
            generator.setSize(QSize(int(source_rect.width()), int(source_rect.height())))
            generator.setViewBox(source_rect)
            generator.setTitle("SDM Spice Circuit")

            from PyQt6.QtGui import QPainter

            painter = QPainter(generator)
            scene.render(painter, source=source_rect)
            painter.end()
        else:
            # PNG
            from PyQt6.QtCore import QRectF, Qt
            from PyQt6.QtGui import QImage, QPainter

            scale = 2  # 2x resolution for crisp output
            width = int(source_rect.width() * scale)
            height = int(source_rect.height() * scale)
            image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.white)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            target_rect = QRectF(0, 0, width, height)
            scene.render(painter, target=target_rect, source=source_rect)
            painter.end()
            image.save(filename)

        QMessageBox.information(self, "Export Image", f"Circuit exported to:\n{filename}")

    def export_circuitikz(self):
        """Export the circuit as a CircuiTikZ LaTeX file."""
        import os

        from simulation.circuitikz_exporter import generate

        from .circuitikz_options_dialog import CircuiTikZOptionsDialog

        model = self.circuit_ctrl.model
        if not model.components:
            QMessageBox.information(self, "Export LaTeX", "Nothing to export — the canvas is empty.")
            return

        # Show options dialog
        dialog = CircuiTikZOptionsDialog(self)
        if dialog.exec() != CircuiTikZOptionsDialog.DialogCode.Accepted:
            return
        opts = dialog.get_options()

        model.rebuild_nodes()

        try:
            tikz_code = generate(
                components=model.components,
                wires=model.wires,
                nodes=model.nodes,
                terminal_to_node=model.terminal_to_node,
                standalone=opts["standalone"],
                circuit_name=(os.path.basename(self.file_ctrl.current_file) if self.file_ctrl.current_file else ""),
                scale=opts["scale"],
                include_ids=opts["include_ids"],
                include_values=opts["include_values"],
                include_net_labels=opts["include_net_labels"],
                style=opts["style"],
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate CircuiTikZ: {e}")
            return

        default_name = ""
        if hasattr(self, "file_ctrl") and self.file_ctrl.current_file:
            base = os.path.splitext(os.path.basename(str(self.file_ctrl.current_file)))[0]
            default_name = base + ".tex"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export as CircuiTikZ",
            default_name,
            "LaTeX Files (*.tex);;All Files (*)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".tex"):
            filename += ".tex"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(tikz_code)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"CircuiTikZ exported to {filename}", 3000)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def copy_circuitikz(self):
        """Copy the CircuiTikZ environment block to the clipboard."""
        from simulation.circuitikz_exporter import generate

        model = self.circuit_ctrl.model
        if not model.components:
            self.statusBar().showMessage("Nothing to copy — the canvas is empty.", 3000)
            return

        model.rebuild_nodes()

        try:
            tikz_code = generate(
                components=model.components,
                wires=model.wires,
                nodes=model.nodes,
                terminal_to_node=model.terminal_to_node,
                standalone=False,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate CircuiTikZ: {e}")
            return

        QApplication.clipboard().setText(tikz_code)
        self.statusBar().showMessage("CircuiTikZ code copied to clipboard.", 3000)
