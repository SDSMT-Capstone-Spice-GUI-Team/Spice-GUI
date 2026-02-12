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

    def _on_new_from_template(self):
        """Create a new circuit from an assignment template"""
        from controllers.template_controller import TEMPLATE_EXTENSION

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Assignment Template",
            "",
            f"Templates (*{TEMPLATE_EXTENSION});;All Files (*)",
        )
        if not filename:
            return

        # Warn if there's unsaved work
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
            from controllers.template_controller import TemplateController

            template_ctrl = TemplateController()
            template = template_ctrl.load_template(filename)
            model = template_ctrl.create_circuit_from_template(template)

            # Update current model in place
            self.model.clear()
            self.model.components = model.components
            self.model.wires = model.wires
            self.model.nodes = model.nodes
            self.model.terminal_to_node = model.terminal_to_node
            self.model.component_counter = model.component_counter
            self.model.analysis_type = model.analysis_type
            self.model.analysis_params = model.analysis_params
            self.model.annotations = model.annotations

            title = template.metadata.title or Path(filename).stem
            self.setWindowTitle(f"Circuit Design GUI - {title} (Template)")
            self.file_ctrl.current_file = None
            self._sync_analysis_menu()

            if self.circuit_ctrl:
                self.circuit_ctrl._notify("model_loaded", None)

            info = f"Template: {title}"
            if template.instructions:
                info += f"\n\nInstructions:\n{template.instructions}"
            QMessageBox.information(self, "Template Loaded", info)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load template:\n{e}")

    def _on_save_as_template(self):
        """Save current circuit as an assignment template"""
        from controllers.template_controller import TEMPLATE_EXTENSION

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save as Assignment Template",
            "",
            f"Templates (*{TEMPLATE_EXTENSION});;All Files (*)",
        )
        if not filename:
            return

        if not filename.endswith(TEMPLATE_EXTENSION):
            filename += TEMPLATE_EXTENSION

        try:
            from controllers.template_controller import TemplateController

            from .template_metadata_dialog import TemplateMetadataDialog

            dialog = TemplateMetadataDialog(self)
            if dialog.exec() != dialog.DialogCode.Accepted:
                return

            metadata = dialog.get_metadata()
            instructions = dialog.get_instructions()

            template_ctrl = TemplateController()
            template_ctrl.save_as_template(
                filepath=filename,
                metadata=metadata,
                starter_circuit=self.model,
                instructions=instructions,
            )

            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Template saved to {filename}", 3000)
        except (OSError, TypeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{e}")

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
