"""File operations: new, open, save, load, import, examples, clipboard, undo/redo for MainWindow."""

import json
import logging
from pathlib import Path

from controllers.settings_service import settings as app_settings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .styles import STATUS_DURATION_DEFAULT, STATUS_DURATION_SHORT

logger = logging.getLogger(__name__)


class FileOperationsMixin:
    """Mixin providing file I/O, clipboard, undo/redo, and examples menu."""

    def _apply_default_zoom(self):
        """Apply the user's preferred default zoom level to the canvas."""
        zoom_percent = app_settings.get_int("view/default_zoom", 100)
        self.canvas.set_default_zoom(zoom_percent)

    def _on_new(self):
        """Create a new circuit"""
        if len(self.canvas.components) > 0 or self._dirty:
            if not self.dialogs.confirm("New Circuit", "Current circuit will be lost. Continue?"):
                return

        self.file_ctrl.new_circuit()
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.results_text.clear()
        self._apply_default_zoom()

    def copy_selected(self):
        """Copy selected components to internal clipboard."""
        ids = self.canvas.get_selected_component_ids()
        if ids:
            self.circuit_ctrl.copy_components(ids)
            n = len(ids)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(
                    f"Copied {n} component{'s' if n != 1 else ''}",
                    STATUS_DURATION_SHORT,
                )

    def cut_selected(self):
        """Cut selected components to internal clipboard (copy + undoable delete)."""
        ids = self.canvas.get_selected_component_ids()
        if ids:
            # Copy to clipboard first (non-destructive)
            self.circuit_ctrl.copy_components(ids)

            # Delete via command so it's undoable
            from controllers.commands import CompoundCommand, DeleteComponentCommand

            commands = [DeleteComponentCommand(self.circuit_ctrl, comp_id) for comp_id in ids]
            if len(commands) == 1:
                self.circuit_ctrl.execute_command(commands[0])
            else:
                compound = CompoundCommand(commands, f"Cut {len(commands)} components")
                self.circuit_ctrl.execute_command(compound)

    def paste_components(self):
        """Paste components from internal clipboard via undo/redo command."""
        if not self.circuit_ctrl.has_clipboard_content():
            return

        from controllers.commands import PasteCommand

        cmd = PasteCommand(self.circuit_ctrl)
        self.circuit_ctrl.execute_command(cmd)

        if cmd.pasted_component_ids:
            # Select newly pasted items on the canvas
            self.canvas.scene().clearSelection()
            for comp_id in cmd.pasted_component_ids:
                comp_item = self.canvas.components.get(comp_id)
                if comp_item is not None:
                    comp_item.setSelected(True)
            n = len(cmd.pasted_component_ids)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(
                    f"Pasted {n} component{'s' if n != 1 else ''}",
                    STATUS_DURATION_SHORT,
                )

    def copy_circuit_json(self):
        """Copy the entire circuit to system clipboard as JSON."""
        from PyQt6.QtWidgets import QApplication

        try:
            data = self.model.to_dict()
            json_str = json.dumps(data, indent=2)
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(json_str)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage("Circuit copied to clipboard as JSON", STATUS_DURATION_DEFAULT)
        except (TypeError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to copy circuit: {e}")

    def paste_circuit_json(self):
        """Paste a circuit from system clipboard JSON."""
        from controllers.file_controller import validate_circuit_data
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if not clipboard:
            return
        json_str = clipboard.text()
        if not json_str:
            QMessageBox.warning(self, "Paste Circuit", "Clipboard is empty.")
            return

        try:
            data = json.loads(json_str)
            validate_circuit_data(data)
        except (json.JSONDecodeError, ValueError) as e:
            QMessageBox.critical(
                self,
                "Invalid Circuit Data",
                f"Clipboard does not contain valid circuit JSON:\n{e}",
            )
            return

        if self.model.components:
            reply = QMessageBox.question(
                self,
                "Paste Circuit",
                "This will replace your current circuit. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            self.file_ctrl.load_from_dict(data)
            self._sync_analysis_menu()
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage("Circuit pasted from clipboard", STATUS_DURATION_DEFAULT)
        except (ValueError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Failed to paste circuit: {e}")

    def _on_undo(self):
        """Undo the last action."""
        if self.circuit_ctrl.undo():
            self._update_undo_redo_actions()

    def _on_redo(self):
        """Redo the last undone action."""
        if self.circuit_ctrl.redo():
            self._update_undo_redo_actions()

    def _update_undo_redo_actions(self):
        """Update the enabled state and text of undo/redo actions."""
        if hasattr(self, "undo_action"):
            can_undo = self.circuit_ctrl.can_undo()
            self.undo_action.setEnabled(can_undo)
            if can_undo:
                desc = self.circuit_ctrl.get_undo_description()
                self.undo_action.setText(f"&Undo {desc}" if desc else "&Undo")
            else:
                self.undo_action.setText("&Undo")

        if hasattr(self, "redo_action"):
            can_redo = self.circuit_ctrl.can_redo()
            self.redo_action.setEnabled(can_redo)
            if can_redo:
                desc = self.circuit_ctrl.get_redo_description()
                self.redo_action.setText(f"&Redo {desc}" if desc else "&Redo")
            else:
                self.redo_action.setText("&Redo")

    def _on_save(self):
        """Quick save to current file"""
        if self.file_ctrl.current_file:
            try:
                self.file_ctrl.save_circuit(self.file_ctrl.current_file)
                self.file_ctrl.clear_auto_save()
                self._set_dirty(False)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Saved to {self.file_ctrl.current_file}",
                        STATUS_DURATION_DEFAULT,
                    )
            except (OSError, TypeError) as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")
        else:
            self._on_save_as()

    def _on_save_as(self):
        """Save circuit to a new file"""
        path = self.dialogs.ask_save_file("Save Circuit", "JSON Files (*.json);;All Files (*)")
        if path:
            try:
                self.file_ctrl.save_circuit(path)
                self.file_ctrl.clear_auto_save()
                self._set_dirty(False)
                self.dialogs.show_info("Success", "Circuit saved successfully!")
            except (OSError, TypeError) as e:
                self.dialogs.show_error("Error", f"Failed to save: {e}")

    def _on_load(self):
        """Load circuit from file"""
        path = self.dialogs.ask_open_file("Load Circuit", "JSON Files (*.json);;All Files (*)")
        if path:
            try:
                self.file_ctrl.load_circuit(path)
                self.setWindowTitle(f"Circuit Design GUI - {path}")
                self._sync_analysis_menu()
                self._apply_default_zoom()
                self.dialogs.show_info("Success", "Circuit loaded successfully!")
            except (OSError, ValueError) as e:
                self.dialogs.show_error("Error", f"Failed to load: {e}")

    def _on_import_netlist(self):
        """Import a SPICE netlist file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import SPICE Netlist",
            "",
            "SPICE Netlists (*.cir *.spice *.sp *.net);;All Files (*)",
        )
        if filename:
            try:
                self.file_ctrl.import_netlist(filename)
                self.setWindowTitle(f"Circuit Design GUI - {Path(filename).name} (imported)")
                self._sync_analysis_menu()
                self._set_dirty(True)
                num_components = len(self.model.components)
                num_wires = len(self.model.wires)
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Imported {num_components} components and {num_wires} wires from {Path(filename).name}.",
                )
            except (OSError, ValueError) as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import netlist:\n{e}")

    def _on_import_asc(self):
        """Import an LTspice .asc schematic file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import LTspice Schematic",
            "",
            "LTspice Schematics (*.asc);;All Files (*)",
        )
        if filename:
            try:
                warnings = self.file_ctrl.import_asc(filename)
                self.setWindowTitle(f"Circuit Design GUI - {Path(filename).name} (imported)")
                self._sync_analysis_menu()
                self._set_dirty(True)
                num_components = len(self.model.components)
                num_wires = len(self.model.wires)
                msg = f"Imported {num_components} components and {num_wires} wires from {Path(filename).name}."
                if warnings:
                    msg += "\n\nWarnings:\n" + "\n".join(f"  - {w}" for w in warnings)
                QMessageBox.information(self, "Import Successful", msg)
            except (OSError, ValueError) as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import LTspice schematic:\n{e}")

    def _on_import_circuitikz(self):
        """Import a CircuiTikZ LaTeX file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import CircuiTikZ LaTeX",
            "",
            "LaTeX Files (*.tex);;All Files (*)",
        )
        if filename:
            try:
                warnings = self.file_ctrl.import_circuitikz(filename)
                self.setWindowTitle(f"Circuit Design GUI - {Path(filename).name} (imported)")
                self._sync_analysis_menu()
                self._set_dirty(True)
                num_components = len(self.model.components)
                num_wires = len(self.model.wires)
                msg = f"Imported {num_components} components and {num_wires} wires from {Path(filename).name}."
                if warnings:
                    msg += "\n\nWarnings:\n" + "\n".join(f"  - {w}" for w in warnings)
                QMessageBox.information(self, "Import Successful", msg)
            except (OSError, ValueError) as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import CircuiTikZ LaTeX:\n{e}")

    def _on_import_svg(self):
        """Import a shareable SVG file containing embedded circuit data."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Shareable SVG",
            "",
            "SVG Files (*.svg);;All Files (*)",
        )
        if filename:
            try:
                self.file_ctrl.import_svg(filename)
                self.setWindowTitle(f"Circuit Design GUI - {Path(filename).name} (imported)")
                self._sync_analysis_menu()
                self._set_dirty(True)
                num_components = len(self.model.components)
                num_wires = len(self.model.wires)
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Imported {num_components} components and {num_wires} wires from {Path(filename).name}.",
                )
            except (OSError, ValueError) as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import SVG:\n{e}")

    def _on_export_bom(self):
        """Export a Bill of Materials (BOM) as CSV or Excel."""
        if not self.model.components:
            QMessageBox.information(self, "Export BOM", "Nothing to export — the canvas is empty.")
            return

        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Bill of Materials",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)",
        )
        if not filename:
            return

        try:
            # Ensure correct extension based on selected filter
            if filename.lower().endswith(".xlsx") or "Excel" in selected_filter:
                if not filename.lower().endswith(".xlsx"):
                    filename += ".xlsx"
            else:
                if not filename.lower().endswith(".csv"):
                    filename += ".csv"

            circuit_name = ""
            if hasattr(self, "file_ctrl") and self.file_ctrl.current_file:
                circuit_name = self.file_ctrl.current_file.name

            self.file_ctrl.export_bom(filename, circuit_name=circuit_name)

            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"BOM exported to {filename}", STATUS_DURATION_DEFAULT)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to export BOM: {e}")

    def _on_export_asc(self):
        """Export the circuit as an LTspice .asc schematic file."""
        if not self.model.components:
            QMessageBox.information(self, "Export LTspice", "Nothing to export — the canvas is empty.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export as LTspice Schematic",
            "",
            "LTspice Schematics (*.asc);;All Files (*)",
        )
        if not filename:
            return

        try:
            self.file_ctrl.export_asc(filename)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"LTspice schematic exported to {filename}", STATUS_DURATION_DEFAULT)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to export LTspice schematic: {e}")

    def _on_generate_report(self):
        """Generate a comprehensive PDF circuit report."""
        from GUI.report_dialog import ReportDialog
        from GUI.report_renderer import PDFReportRenderer
        from services.report_generator import ReportDataBuilder

        # Determine circuit name from current file or default
        circuit_name = ""
        if self.file_ctrl.current_file:
            circuit_name = self.file_ctrl.current_file.stem

        has_results = getattr(self, "_last_results", None) is not None

        dialog = ReportDialog(self, circuit_name=circuit_name, has_results=has_results)
        if dialog.exec() != ReportDialog.DialogCode.Accepted:
            return

        config = dialog.get_config()

        filename, _ = QFileDialog.getSaveFileName(self, "Save Circuit Report", "", "PDF Files (*.pdf)")
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        # Gather data for the report
        netlist = ""
        if config.include_netlist:
            try:
                netlist = self.simulation_ctrl.generate_netlist()
            except (OSError, ValueError, RuntimeError):
                netlist = "(Netlist generation failed)"

        results_text = ""
        if config.include_results and hasattr(self, "results_text"):
            results_text = self.results_text.toPlainText()

        try:
            data = ReportDataBuilder.build(config, model=self.model, netlist=netlist, results_text=results_text)
            renderer = PDFReportRenderer()
            renderer.render(filepath=filename, data=data, scene=self.canvas.scene())
            QMessageBox.information(
                self,
                "Report Generated",
                f"Circuit report saved to:\n{filename}",
            )
        except (OSError, ValueError) as e:
            logger.error("Report generation failed", exc_info=True)
            QMessageBox.critical(self, "Report Error", f"Failed to generate report:\n{e}")

    def _on_export_bundle(self):
        """Export all circuit artifacts as a ZIP bundle for lab submission."""
        import os
        import tempfile

        if not self.model.components:
            QMessageBox.information(self, "Export Bundle", "Nothing to export — the canvas is empty.")
            return

        circuit_name = ""
        if self.file_ctrl.current_file:
            circuit_name = self.file_ctrl.current_file.name

        suggested = self.simulation_ctrl.suggest_bundle_name(circuit_name)
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Lab Bundle",
            suggested,
            "ZIP Files (*.zip);;All Files (*)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".zip"):
            filename += ".zip"

        tmp_img_path = None
        tmp_xlsx_path = None
        try:
            # Circuit JSON
            circuit_json = self.model.to_dict()

            # Netlist
            netlist = None
            try:
                netlist = self.simulation_ctrl.generate_netlist()
            except (OSError, ValueError, RuntimeError):
                logger.warning("Bundle export: netlist generation failed", exc_info=True)

            # Schematic PNG (rendered at 2x via canvas)
            schematic_png = None
            try:
                tmp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp_img.close()
                tmp_img_path = tmp_img.name
                self.canvas.export_image(tmp_img_path, include_grid=False)
                with open(tmp_img_path, "rb") as f:
                    schematic_png = f.read()
            except (OSError, ValueError, RuntimeError):
                logger.warning("Bundle export: schematic PNG export failed", exc_info=True)

            # Results CSV (only if simulation was run)
            results_csv = None
            if self._last_results is not None:
                try:
                    cn = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
                    results_csv = self.simulation_ctrl.generate_results_csv(
                        self._last_results, self._last_results_type, cn
                    )
                except (OSError, ValueError, RuntimeError):
                    logger.warning("Bundle export: CSV results export failed", exc_info=True)

            # Results Excel (only if simulation was run)
            results_xlsx_path = None
            if self._last_results is not None:
                try:
                    cn = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
                    tmp_xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
                    tmp_xlsx.close()
                    tmp_xlsx_path = tmp_xlsx.name
                    self.simulation_ctrl.export_results_excel(
                        self._last_results, self._last_results_type, tmp_xlsx_path, cn
                    )
                    results_xlsx_path = tmp_xlsx_path
                except (OSError, ValueError, RuntimeError):
                    logger.warning("Bundle export: Excel results export failed", exc_info=True)

            included = self.simulation_ctrl.create_bundle(
                filepath=filename,
                circuit_json=circuit_json,
                netlist=netlist,
                schematic_png=schematic_png,
                results_csv=results_csv,
                results_xlsx_path=results_xlsx_path,
                circuit_name=circuit_name,
            )

            QMessageBox.information(
                self,
                "Bundle Exported",
                f"Lab bundle saved to {Path(filename).name}\n\nIncludes: {', '.join(included)}",
            )
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Bundle export failed", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to export bundle:\n{e}")
        finally:
            for path in (tmp_img_path, tmp_xlsx_path):
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

    def _load_last_session(self):
        """Load last session using FileController"""
        last_file = self.file_ctrl.load_last_session()
        if last_file and last_file.exists():
            try:
                self.file_ctrl.load_circuit(last_file)
                self.setWindowTitle(f"Circuit Design GUI - {last_file}")
                self._sync_analysis_menu()
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error("Error loading last session: %s", e)

    def _populate_examples_menu(self):
        """Populate the Open Example submenu with example circuits"""
        # Get path to examples directory (relative to this file)
        examples_dir = Path(__file__).parent.parent / "examples"

        if not examples_dir.exists():
            no_examples_action = QAction("(No examples available)", self)
            no_examples_action.setEnabled(False)
            self.examples_menu.addAction(no_examples_action)
            return

        # Load and categorize examples
        examples_by_category = {}
        example_files = sorted(examples_dir.glob("*.json"))

        for example_file in example_files:
            try:
                from controllers.file_controller import check_file_size

                check_file_size(example_file)
                with open(example_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                name = data.get("name", example_file.stem)
                description = data.get("description", "")
                category = data.get("category", "Other")

                if category not in examples_by_category:
                    examples_by_category[category] = []

                examples_by_category[category].append(
                    {"name": name, "description": description, "filepath": example_file}
                )
            except (json.JSONDecodeError, OSError, ValueError) as e:
                logger.warning(f"Failed to load example {example_file}: {e}")

        # Create menu entries organized by category
        if not examples_by_category:
            no_examples_action = QAction("(No examples available)", self)
            no_examples_action.setEnabled(False)
            self.examples_menu.addAction(no_examples_action)
            return

        # Sort categories: Basic first, then alphabetically
        category_order = sorted(examples_by_category.keys(), key=lambda c: (c != "Basic", c))

        for i, category in enumerate(category_order):
            if i > 0:
                self.examples_menu.addSeparator()

            # Add category label
            category_label = QAction(f"─── {category} ───", self)
            category_label.setEnabled(False)
            self.examples_menu.addAction(category_label)

            # Add examples in this category
            for example in examples_by_category[category]:
                action = QAction(example["name"], self)
                action.setToolTip(example["description"])
                action.triggered.connect(lambda checked, path=example["filepath"]: self._open_example(path))
                self.examples_menu.addAction(action)

    def _populate_templates_menu(self):
        """Populate the New from Template submenu with available templates."""
        from controllers.template_manager import TemplateManager

        if not hasattr(self, "_template_manager"):
            self._template_manager = TemplateManager()

        self.templates_menu.clear()

        templates = self._template_manager.list_templates()
        if not templates:
            no_templates = QAction("(No templates available)", self)
            no_templates.setEnabled(False)
            self.templates_menu.addAction(no_templates)
            return

        # Group by category
        templates_by_category: dict[str, list] = {}
        for t in templates:
            templates_by_category.setdefault(t.category, []).append(t)

        category_order = sorted(templates_by_category.keys())
        for i, category in enumerate(category_order):
            if i > 0:
                self.templates_menu.addSeparator()

            category_label = QAction(f"--- {category} ---", self)
            category_label.setEnabled(False)
            self.templates_menu.addAction(category_label)

            for template in templates_by_category[category]:
                label = template.name
                if not template.is_builtin:
                    label += " (user)"
                action = QAction(label, self)
                action.setToolTip(template.description)
                action.triggered.connect(lambda checked, fp=template.filepath: self._open_template(fp))
                self.templates_menu.addAction(action)

        # Add separator and "Browse All..." option
        self.templates_menu.addSeparator()
        browse_action = QAction("Browse All...", self)
        browse_action.triggered.connect(self._on_new_from_template)
        self.templates_menu.addAction(browse_action)

    def _on_new_from_template(self):
        """Open the template browser dialog and load the selected template."""
        from controllers.template_manager import TemplateManager
        from GUI.template_dialog import NewFromTemplateDialog

        if not hasattr(self, "_template_manager"):
            self._template_manager = TemplateManager()

        templates = self._template_manager.list_templates()
        dialog = NewFromTemplateDialog(
            templates,
            delete_callback=self._template_manager.delete_template,
            parent=self,
        )
        if dialog.exec() == NewFromTemplateDialog.DialogCode.Accepted:
            template_info = dialog.get_selected_template()
            if template_info is None:
                return

            self._open_template(template_info.filepath)

    def _open_template(self, filepath: Path):
        """Load a circuit template, replacing the current circuit."""
        from controllers.template_manager import TemplateManager

        if not hasattr(self, "_template_manager"):
            self._template_manager = TemplateManager()

        if len(self.canvas.components) > 0:
            reply = QMessageBox.question(
                self,
                "New from Template",
                "Opening a template will replace your current circuit. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            new_model = self._template_manager.load_template(filepath)

            self.file_ctrl.load_from_model(new_model)
            self.file_ctrl.current_file = None

            self.setWindowTitle(f"Circuit Design GUI - {filepath.stem} (Template)")
            self._sync_analysis_menu()
            self._apply_default_zoom()
            self._set_dirty(True)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load template: {e}")

    def _on_save_as_template(self):
        """Save the current circuit as a reusable template."""
        from controllers.template_manager import TemplateManager
        from GUI.template_dialog import SaveAsTemplateDialog

        if not self.model.components:
            QMessageBox.information(self, "Save as Template", "Cannot save an empty circuit as a template.")
            return

        if not hasattr(self, "_template_manager"):
            self._template_manager = TemplateManager()

        dialog = SaveAsTemplateDialog(self)
        if dialog.exec() == SaveAsTemplateDialog.DialogCode.Accepted:
            name, description, category = dialog.get_values()
            try:
                self._template_manager.save_template(self.model, name, description, category)
                # Refresh the templates submenu
                self._populate_templates_menu()
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(f"Template saved: {name}", STATUS_DURATION_DEFAULT)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to save template: {e}")

    def _open_example(self, filepath: Path):
        """Open an example circuit file"""
        # Warn if there's unsaved work
        if len(self.canvas.components) > 0:
            reply = QMessageBox.question(
                self,
                "Open Example",
                "Opening an example will replace your current circuit. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            self.file_ctrl.load_circuit(filepath)
            self.setWindowTitle(f"Circuit Design GUI - {filepath.name} (Example)")
            self._sync_analysis_menu()
            self._apply_default_zoom()
            # Don't set as current file (keep it as example, not saved)
            self.file_ctrl.current_file = None
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load example: {e}")

    # ------------------------------------------------------------------
    # Recent files menu
    # ------------------------------------------------------------------

    def _populate_recent_files_menu(self):
        """Rebuild the Recent Files submenu from the file controller."""
        menu = self._recent_files_menu
        menu.clear()
        recent = self.file_ctrl.get_recent_files()

        if not recent:
            empty = menu.addAction("(no recent files)")
            empty.setEnabled(False)
            return

        for filepath_str in recent:
            label = Path(filepath_str).name
            action = menu.addAction(label)
            action.setToolTip(filepath_str)
            action.triggered.connect(lambda checked=False, p=filepath_str: self._open_recent_file(p))

        menu.addSeparator()
        clear_action = menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self._clear_recent_files)

    def _open_recent_file(self, filepath_str):
        """Open a file from the Recent Files menu."""
        path = Path(filepath_str)
        if not path.exists():
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file no longer exists:\n{filepath_str}",
            )
            return
        try:
            self.file_ctrl.load_circuit(path)
            self.setWindowTitle(f"Circuit Design GUI - {path}")
            self._sync_analysis_menu()
            self._apply_default_zoom()
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def _clear_recent_files(self):
        """Clear the recent files list."""
        self.file_ctrl.clear_recent_files()

    # ------------------------------------------------------------------
    # Recent exports tracking and re-export
    # ------------------------------------------------------------------

    def _track_export(self, path, fmt, export_function):
        """Record a completed export for the Recent Exports menu."""
        from controllers.recent_exports import add_recent_export

        add_recent_export(path, fmt, export_function)

    def _populate_recent_exports_menu(self):
        """Rebuild the Recent Exports submenu from QSettings."""
        from controllers.recent_exports import get_recent_exports

        menu = self._recent_exports_menu
        menu.clear()
        entries = get_recent_exports()

        if not entries:
            empty = menu.addAction("(no recent exports)")
            empty.setEnabled(False)
            return

        for entry in entries:
            label = f"[{entry['format']}] {Path(entry['path']).name}"
            action = menu.addAction(label)
            path = entry["path"]
            func_name = entry["export_function"]
            action.triggered.connect(lambda checked=False, p=path, f=func_name: self._re_export_to(p, f))

    def _on_re_export_last(self):
        """Re-export using the most recent export settings."""
        from controllers.recent_exports import get_recent_exports

        entries = get_recent_exports()
        if not entries:
            QMessageBox.information(self, "Re-export", "No recent exports to repeat.")
            return

        last = entries[0]
        self._re_export_to(last["path"], last["export_function"])

    def _re_export_to(self, path, export_function):
        """Repeat an export operation to the given path."""
        import os

        try:
            circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""

            if export_function == "export_netlist":
                self.simulation_ctrl.export_netlist(path)
            elif export_function == "export_image":
                self.canvas.export_image(path, include_grid=False)
            elif export_function in ("export_bom_csv", "export_bom_excel"):
                self.file_ctrl.export_bom(path, circuit_name=circuit_name)
            elif export_function == "export_results_csv":
                self._re_export_results_csv(path)
            elif export_function == "export_results_excel":
                self._re_export_results_excel(path)
            elif export_function == "export_circuitikz":
                from utils.atomic_write import atomic_write_text

                content = self.simulation_ctrl.generate_circuitikz()
                atomic_write_text(path, content)
            elif export_function == "export_asc":
                self.file_ctrl.export_asc(path)
            elif export_function == "export_results_markdown":
                if self._last_results is not None:
                    self.simulation_ctrl.export_results_markdown(
                        self._last_results, self._last_results_type, path, circuit_name
                    )
            else:
                QMessageBox.warning(self, "Re-export", f"Unknown export type: {export_function}")
                return

            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Re-exported to {Path(path).name}", STATUS_DURATION_DEFAULT)
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Re-export failed", exc_info=True)
            QMessageBox.critical(self, "Re-export Error", f"Failed to re-export:\n{e}")

    def _re_export_results_csv(self, path):
        """Re-export simulation results to CSV at the given path."""
        if self._last_results is None:
            return
        import os

        circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
        self.simulation_ctrl.export_results_csv(self._last_results, self._last_results_type, path, circuit_name)

    def _re_export_results_excel(self, path):
        """Re-export simulation results to Excel at the given path."""
        if self._last_results is None:
            return
        import os

        circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
        self.simulation_ctrl.export_results_excel(self._last_results, self._last_results_type, path, circuit_name)

    # --- Recommended / Used-in-File Components ---

    def _edit_recommended_components(self):
        """Open dialog to edit file-level recommended components."""
        from .recommended_components_dialog import RecommendedComponentsDialog

        dialog = RecommendedComponentsDialog(self.model.recommended_components, self)
        if dialog.exec() == RecommendedComponentsDialog.DialogCode.Accepted:
            new_recs = dialog.get_recommended()
            self.circuit_ctrl.set_recommended_components(new_recs)
            self.palette.set_recommended_components(new_recs)
            self._set_dirty(True)
            statusBar = self.statusBar()
            if statusBar:
                count = len(new_recs)
                statusBar.showMessage(
                    (
                        f"Updated recommended components ({count} selected)"
                        if count
                        else "Cleared recommended components"
                    ),
                    3000,
                )

    def _sync_palette_used_in_file(self):
        """Update the palette 'Used in File' section from the current model."""
        used_types = [comp.component_type for comp in self.model.components.values()]
        self.palette.update_used_in_file(used_types)

    def _sync_palette_recommendations(self):
        """Update the palette Recommended section from the current model."""
        self.palette.set_recommended_components(self.model.recommended_components)
