"""File operations: new, open, save, load, import, examples, clipboard, undo/redo for MainWindow."""

import json
import logging
from pathlib import Path

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)


class FileOperationsMixin:
    """Mixin providing file I/O, clipboard, undo/redo, and examples menu."""

    def _on_new(self):
        """Create a new circuit"""
        if len(self.canvas.components) > 0:
            reply = QMessageBox.question(
                self,
                "New Circuit",
                "Current circuit will be lost. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.file_ctrl.new_circuit()
        # Phase 5: No sync needed - observer pattern handles canvas update
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.results_text.clear()

    def copy_selected(self):
        """Copy selected components to internal clipboard."""
        ids = self.canvas.get_selected_component_ids()
        if ids:
            self.canvas.copy_selected_components(ids)

    def cut_selected(self):
        """Cut selected components to internal clipboard."""
        ids = self.canvas.get_selected_component_ids()
        if ids:
            self.canvas.cut_selected_components(ids)

    def paste_components(self):
        """Paste components from internal clipboard."""
        self.canvas.paste_components()

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
                statusBar.showMessage("Circuit copied to clipboard as JSON", 3000)
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
            QMessageBox.critical(self, "Invalid Circuit Data", f"Clipboard does not contain valid circuit JSON:\n{e}")
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
                statusBar.showMessage("Circuit pasted from clipboard", 3000)
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
                # Phase 5: No sync needed - model always up to date
                self.file_ctrl.save_circuit(self.file_ctrl.current_file)
                self.file_ctrl.clear_auto_save()
                self._set_dirty(False)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(f"Saved to {self.file_ctrl.current_file}", 3000)
            except (OSError, TypeError) as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")
        else:
            self._on_save_as()

    def _on_save_as(self):
        """Save circuit to a new file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Circuit", "", "JSON Files (*.json);;All Files (*)")
        if filename:
            try:
                # Phase 5: No sync needed - model always up to date
                self.file_ctrl.save_circuit(filename)
                self.file_ctrl.clear_auto_save()
                self._set_dirty(False)
                QMessageBox.information(self, "Success", "Circuit saved successfully!")
            except (OSError, TypeError) as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _on_load(self):
        """Load circuit from file"""
        filename, _ = QFileDialog.getOpenFileName(self, "Load Circuit", "", "JSON Files (*.json);;All Files (*)")
        if filename:
            try:
                self.file_ctrl.load_circuit(filename)
                # Phase 5: No sync needed - observer pattern rebuilds canvas
                self.setWindowTitle(f"Circuit Design GUI - {filename}")
                self._sync_analysis_menu()
                QMessageBox.information(self, "Success", "Circuit loaded successfully!")
            except (OSError, ValueError) as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")

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

    def _on_generate_report(self):
        """Generate a comprehensive PDF circuit report."""
        from GUI.report_dialog import ReportDialog
        from GUI.report_generator import ReportGenerator

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
            except Exception:
                netlist = "(Netlist generation failed)"

        results_text = ""
        if config.include_results and hasattr(self, "results_text"):
            results_text = self.results_text.toPlainText()

        try:
            generator = ReportGenerator(config)
            generator.generate(
                filepath=filename,
                scene=self.canvas.scene,
                model=self.model,
                netlist=netlist,
                results_text=results_text,
            )
            QMessageBox.information(
                self,
                "Report Generated",
                f"Circuit report saved to:\n{filename}",
            )
        except (OSError, Exception) as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report:\n{e}")

    def _load_last_session(self):
        """Load last session using FileController"""
        last_file = self.file_ctrl.load_last_session()
        if last_file and last_file.exists():
            try:
                self.file_ctrl.load_circuit(last_file)
                # Phase 5: No sync needed - observer pattern rebuilds canvas
                self.setWindowTitle(f"Circuit Design GUI - {last_file}")
                self._sync_analysis_menu()
            except Exception as e:
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
                with open(example_file, "r") as f:
                    data = json.load(f)

                name = data.get("name", example_file.stem)
                description = data.get("description", "")
                category = data.get("category", "Other")

                if category not in examples_by_category:
                    examples_by_category[category] = []

                examples_by_category[category].append(
                    {"name": name, "description": description, "filepath": example_file}
                )
            except (json.JSONDecodeError, OSError) as e:
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
        """Open the template browser dialog."""
        from controllers.template_manager import TemplateManager
        from GUI.template_dialog import NewFromTemplateDialog

        if not hasattr(self, "_template_manager"):
            self._template_manager = TemplateManager()

        dialog = NewFromTemplateDialog(self._template_manager, self)
        if dialog.exec() == NewFromTemplateDialog.DialogCode.Accepted:
            template = dialog.get_selected_template()
            if template:
                self._open_template(template.filepath)

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

            self.model.clear()
            self.model.components = new_model.components
            self.model.wires = new_model.wires
            self.model.nodes = new_model.nodes
            self.model.terminal_to_node = new_model.terminal_to_node
            self.model.component_counter = new_model.component_counter
            self.model.analysis_type = new_model.analysis_type
            self.model.analysis_params = new_model.analysis_params
            self.model.annotations = new_model.annotations

            # Notify observers to rebuild canvas
            if self.circuit_ctrl:
                self.circuit_ctrl._notify("model_loaded", None)

            self.setWindowTitle(f"Circuit Design GUI - {filepath.stem} (Template)")
            self._sync_analysis_menu()
            self.file_ctrl.current_file = None
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
                    statusBar.showMessage(f"Template saved: {name}", 3000)
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
            # Don't set as current file (keep it as example, not saved)
            self.file_ctrl.current_file = None
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load example: {e}")
