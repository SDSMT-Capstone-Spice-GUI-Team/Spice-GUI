"""View operations: theme, visibility toggles, probe tool, zoom, and image export for MainWindow."""

from controllers.theme_controller import theme_ctrl
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog
from .styles import STATUS_DURATION_DEFAULT, STATUS_DURATION_SHORT, theme_manager
from .waveform_dialog import WaveformDialog


class ViewOperationsMixin:
    """Mixin providing theme, visibility toggles, probe, zoom, and image export."""

    def _set_theme(self, theme_name: str):
        """Switch the application theme (legacy: 'light' or 'dark' only)."""
        if theme_name == "dark":
            theme_ctrl.set_theme_by_key("dark")
            self.dark_theme_action.setChecked(True)
        else:
            theme_ctrl.set_theme_by_key("light")
            self.light_theme_action.setChecked(True)
        self.apply_theme()
        if hasattr(self, "refresh_theme_menu"):
            self.refresh_theme_menu()

    def apply_theme(self):
        """Apply the current theme to all visual elements.

        QSS ``setStyleSheet()`` triggers an immediate repaint of every widget,
        including the ``QGraphicsView``.  During that repaint Qt may
        invalidate/delete the C++ objects backing ``QGraphicsItem`` instances
        in the scene, leading to a segfault when we later touch those items
        (see #860).

        The fix: swap the live scene for a temporary empty one *before*
        applying the stylesheet so the repaint has nothing to destroy, then
        rebuild the real scene from the model afterwards.
        """
        theme = theme_manager.current_theme

        # 1. Park an empty scene on the view so the QSS repaint is harmless.
        self.canvas.detach_scene()

        # 2. Apply the new stylesheet — repaint hits only the empty scene.
        self.setStyleSheet(theme.generate_stylesheet())

        # 3. Rebuild the real scene with correct theme colors and reattach.
        self.canvas.rebuild_scene()

    def set_symbol_style(self, style: str):
        """Switch the component symbol drawing style."""
        theme_ctrl.set_symbol_style(style)
        if style == "iec":
            self.iec_style_action.setChecked(True)
        else:
            self.ieee_style_action.setChecked(True)
        self.canvas.scene().update()

    def set_color_mode(self, mode: str):
        """Switch between per-type color and monochrome rendering."""
        theme_ctrl.set_color_mode(mode)
        if mode == "monochrome":
            self.monochrome_mode_action.setChecked(True)
        else:
            self.color_mode_action.setChecked(True)
        self.canvas.scene().update()

    def set_wire_thickness(self, thickness: str):
        """Switch wire rendering thickness."""
        theme_ctrl.set_wire_thickness(thickness)
        if hasattr(self, "wire_thickness_actions"):
            for t, action in self.wire_thickness_actions.items():
                action.setChecked(t == thickness)
        self.canvas.scene().update()

    def set_show_junction_dots(self, show: bool):
        """Toggle junction dot visibility at wire intersections."""
        theme_ctrl.set_show_junction_dots(show)
        if hasattr(self, "show_junction_dots_action"):
            self.show_junction_dots_action.setChecked(show)
        self.canvas.scene().update()

    def set_routing_mode(self, mode: str):
        """Switch wire routing mode between orthogonal and diagonal."""
        theme_ctrl.set_routing_mode(mode)
        if hasattr(self, "routing_mode_actions"):
            for m, action in self.routing_mode_actions.items():
                action.setChecked(m == mode)
        self.canvas.scene().update()

    def _toggle_statistics_panel(self, checked):
        """Toggle the circuit statistics panel visibility."""
        self.statistics_panel.setVisible(checked)
        if checked:
            self.statistics_panel.refresh()

    def _toggle_grading_panel(self):
        """Toggle the instructor grading panel visibility."""
        visible = not self.grading_panel.isVisible()
        self.grading_panel.setVisible(visible)

    def _on_batch_grade(self):
        """Open the batch grading dialog."""
        from .batch_grading_dialog import BatchGradingDialog

        dialog = BatchGradingDialog(reference_circuit=self.model, parent=self)
        dialog.exec()

    def _on_create_rubric(self):
        """Open the rubric editor dialog."""
        from .rubric_editor_dialog import RubricEditorDialog

        dialog = RubricEditorDialog(parent=self)
        dialog.exec()

    def _on_generate_rubric(self):
        """Auto-generate a rubric from the current circuit and open it in the editor."""
        from grading.rubric_generator import generate_rubric_from_circuit

        from .rubric_editor_dialog import RubricEditorDialog

        model = self.circuit_ctrl.model
        if not model.components:
            QMessageBox.information(
                self,
                "Generate Rubric",
                "The canvas is empty. Build a reference circuit first.",
            )
            return

        rubric = generate_rubric_from_circuit(model)
        dialog = RubricEditorDialog(rubric=rubric, parent=self)
        dialog.exec()

    def _on_open_assignment(self):
        """Open a .spice-assignment bundle file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Assignment",
            "",
            "Assignment Files (*.spice-assignment);;All Files (*)",
        )
        if not filename:
            return

        try:
            from controllers.assignment_controller import extract_rubric, load_assignment

            bundle = load_assignment(filename)

            # Load template circuit if present
            if bundle.template is not None:
                from controllers.template_controller import TemplateController

                model = TemplateController().create_circuit_from_template(bundle.template)
                self.file_ctrl.load_from_model(model)

            # Load rubric into grading panel if present
            if bundle.rubric is not None:
                rubric = extract_rubric(bundle)
                self.grading_panel._rubric = rubric
                self.grading_panel.rubric_label.setText(f"Rubric: {rubric.title}")
                self.grading_panel._update_grade_button()
                self.grading_panel.setVisible(True)

            if bar := self.statusBar():
                bar.showMessage(f"Assignment loaded: {filename}", STATUS_DURATION_DEFAULT)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load assignment:\n{e}")

    def _on_save_assignment(self):
        """Save current circuit + rubric as a .spice-assignment bundle."""
        if not self.model.components:
            QMessageBox.information(
                self,
                "Save Assignment",
                "The canvas is empty. Build a circuit first.",
            )
            return

        # Get rubric file
        rubric_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Rubric for Assignment",
            "",
            "Rubric Files (*.spice-rubric);;All Files (*)",
        )
        if not rubric_path:
            return

        try:
            from grading.rubric import load_rubric

            rubric = load_rubric(rubric_path)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load rubric:\n{e}")
            return

        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Assignment Bundle",
            "",
            "Assignment Files (*.spice-assignment);;All Files (*)",
        )
        if not save_path:
            return
        if not save_path.endswith(".spice-assignment"):
            save_path += ".spice-assignment"

        try:
            from controllers.assignment_controller import save_assignment
            from models.assignment import AssignmentBundle
            from models.template import TemplateData, TemplateMetadata

            circuit_data = self.model.to_dict()
            template = TemplateData(
                metadata=TemplateMetadata(title=rubric.title),
                starter_circuit=circuit_data,
                reference_circuit=circuit_data,
            )
            bundle = AssignmentBundle(
                template=template,
                rubric=rubric.to_dict(),
            )
            save_assignment(bundle, save_path)
            if bar := self.statusBar():
                bar.showMessage(f"Assignment saved: {save_path}", STATUS_DURATION_DEFAULT)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to save assignment:\n{e}")

    # Dirty flag (unsaved changes indicator)

    def _on_dirty_change(self, event: str, data) -> None:
        """Mark circuit as dirty on model-modifying events and refresh undo/redo menu."""
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

        if event == "undo_state_changed":
            self._update_undo_redo_actions()

        # Sync palette "Used in File" when components change
        if event in (
            "component_added",
            "component_removed",
            "circuit_cleared",
            "model_loaded",
        ):
            self._sync_palette_used_in_file()
        if event == "model_loaded":
            self._sync_palette_recommendations()

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
        self.canvas.scene().update()

    def toggle_component_values(self, checked):
        """Toggle component value visibility"""
        self.canvas.show_component_values = checked
        self.canvas.scene().update()

    def toggle_node_labels(self, checked):
        """Toggle node label visibility"""
        self.canvas.show_node_labels = checked
        self.canvas.scene().update()

    def toggle_op_annotations(self, checked):
        """Toggle DC operating point annotation visibility."""
        self.canvas.show_op_annotations = checked
        self.canvas.scene().update()

    def _toggle_probe_mode(self, checked):
        """Toggle interactive probe mode on the canvas."""
        self.canvas.set_probe_mode(checked)
        if checked:
            if bar := self.statusBar():
                if not self.canvas.node_voltages and self._last_results is None:
                    bar.showMessage("Probe mode active. Run a simulation first to see values.", STATUS_DURATION_DEFAULT)
                else:
                    bar.showMessage(
                        "Probe mode active. Click nodes or components to see values. Press Escape to exit.",
                        3000,
                    )
        else:
            self.canvas.clear_probes()
            if bar := self.statusBar():
                bar.showMessage("Probe mode deactivated.", STATUS_DURATION_SHORT)

    def _on_probe_requested(self, signal_name, probe_type):
        """Handle probe click for sweep/transient analyses (no OP data on canvas)."""
        if self._last_results is None:
            if bar := self.statusBar():
                bar.showMessage("No simulation results available. Run a simulation first.", STATUS_DURATION_DEFAULT)
            return

        analysis_type = self._last_results_type
        if analysis_type == "Transient":
            self._probe_open_waveform(signal_name, probe_type)
        elif analysis_type == "DC Sweep":
            self._probe_open_dc_sweep(signal_name, probe_type)
        elif analysis_type == "AC Sweep":
            self._probe_open_ac_sweep(signal_name, probe_type)
        else:
            if bar := self.statusBar():
                bar.showMessage(f"Probe not supported for {analysis_type} analysis.", STATUS_DURATION_DEFAULT)

    def _probe_open_waveform(self, signal_name, probe_type):
        """Open waveform dialog focused on the probed signal."""
        tran_data = self._last_results
        if not tran_data:
            return
        # Open or raise the waveform dialog
        if self._waveform_dialog is None or not self._waveform_dialog.isVisible():
            self._waveform_dialog = WaveformDialog(tran_data, self, sim_ctrl=self.simulation_ctrl)
            self._waveform_dialog.show()
        self._waveform_dialog.raise_()
        self._waveform_dialog.activateWindow()
        if bar := self.statusBar():
            bar.showMessage(f"Opened waveform plot for {signal_name}.", STATUS_DURATION_SHORT)

    def _probe_open_dc_sweep(self, signal_name, probe_type):
        """Open DC sweep plot dialog for the probed signal."""
        sweep_data = self._last_results
        if not sweep_data:
            return
        if self._plot_dialog is None or not self._plot_dialog.isVisible():
            self._show_plot_dialog(DCSweepPlotDialog(sweep_data, self))
        self._plot_dialog.raise_()
        self._plot_dialog.activateWindow()
        if bar := self.statusBar():
            bar.showMessage(f"Opened DC sweep plot for {signal_name}.", STATUS_DURATION_SHORT)

    def _probe_open_ac_sweep(self, signal_name, probe_type):
        """Open AC sweep Bode plot dialog for the probed signal."""
        ac_data = self._last_results
        if not ac_data:
            return
        if self._plot_dialog is None or not self._plot_dialog.isVisible():
            self._show_plot_dialog(ACSweepPlotDialog(ac_data, self, sim_ctrl=self.simulation_ctrl))
        self._plot_dialog.raise_()
        self._plot_dialog.activateWindow()
        if bar := self.statusBar():
            bar.showMessage(f"Opened AC sweep plot for {signal_name}.", STATUS_DURATION_SHORT)

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

        scene = self.canvas.scene()

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
            from PyQt6.QtCore import QRect, QRectF, QSize
            from PyQt6.QtSvg import QSvgGenerator

            width = int(source_rect.width())
            height = int(source_rect.height())

            generator = QSvgGenerator()
            generator.setFileName(filename)
            generator.setSize(QSize(width, height))
            generator.setViewBox(QRect(0, 0, width, height))
            generator.setTitle("SDM Spice Circuit")

            from PyQt6.QtGui import QPainter

            painter = QPainter(generator)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Override scene background to white so dark-mode theme doesn't leak
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QBrush

            original_brush = scene.backgroundBrush()
            scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
            scene.render(painter, QRectF(0, 0, width, height), source_rect)
            scene.setBackgroundBrush(original_brush)
            painter.end()

            # Embed circuit data in the SVG for shareable round-trip import
            from simulation.svg_shareable import embed_circuit_data

            embed_circuit_data(filename, self.model)
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
            # Override scene background to white so dark-mode theme doesn't leak
            from PyQt6.QtGui import QBrush

            original_brush = scene.backgroundBrush()
            scene.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
            scene.render(painter, target=target_rect, source=source_rect)
            scene.setBackgroundBrush(original_brush)
            painter.end()
            image.save(filename)

        QMessageBox.information(self, "Export Image", f"Circuit exported to:\n{filename}")

    def export_circuitikz(self):
        """Export the circuit as a CircuiTikZ LaTeX file."""
        import os

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

        try:
            tikz_code = self.simulation_ctrl.generate_circuitikz(
                standalone=opts["standalone"],
                circuit_name=(os.path.basename(self.file_ctrl.current_file) if self.file_ctrl.current_file else ""),
                scale=opts["scale"],
                include_ids=opts["include_ids"],
                include_values=opts["include_values"],
                include_net_labels=opts["include_net_labels"],
                style=opts["style"],
            )
        except (ValueError, KeyError, TypeError) as e:
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
            from utils.atomic_write import atomic_write_text

            atomic_write_text(filename, tikz_code)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"CircuiTikZ exported to {filename}", STATUS_DURATION_DEFAULT)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def copy_circuitikz(self):
        """Copy the CircuiTikZ environment block to the clipboard."""
        model = self.circuit_ctrl.model
        if not model.components:
            if bar := self.statusBar():
                bar.showMessage("Nothing to copy — the canvas is empty.", STATUS_DURATION_DEFAULT)
            return

        try:
            tikz_code = self.simulation_ctrl.generate_circuitikz(standalone=False)
        except (ValueError, KeyError, TypeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to generate CircuiTikZ: {e}")
            return

        QApplication.clipboard().setText(tikz_code)
        if bar := self.statusBar():
            bar.showMessage("CircuiTikZ code copied to clipboard.", STATUS_DURATION_DEFAULT)
