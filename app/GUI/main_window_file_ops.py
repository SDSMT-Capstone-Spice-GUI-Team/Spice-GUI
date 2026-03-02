"""File operations: new, open, save, load, import, examples, clipboard, undo/redo for MainWindow."""

import json
import logging
from pathlib import Path

from controllers.settings_service import settings as app_settings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)


class FileOperationsMixin:
    """Mixin providing file I/O, clipboard, undo/redo, and examples menu."""

    def _apply_default_zoom(self):
        """Apply the user's preferred default zoom level to the canvas."""
        zoom_percent = app_settings.get_int("view/default_zoom", 100)
        self.canvas.set_default_zoom(zoom_percent)

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
        self._apply_default_zoom()

    def copy_selected(self):
        """Copy selected components to internal clipboard."""
        ids = self.canvas.get_selected_component_ids()
        if ids:
            self.circuit_ctrl.copy_components(ids)
            n = len(ids)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Copied {n} component{'s' if n != 1 else ''}", 2000)

    def cut_selected(self):
        """Cut selected components to internal clipboard."""
        ids = self.canvas.get_selected_component_ids()
        if ids:
            self.circuit_ctrl.cut_components(ids)

    def paste_components(self):
        """Paste components from internal clipboard."""
        new_comps, new_wires = self.circuit_ctrl.paste_components()
        if new_comps:
            # Select newly pasted items on the canvas
            self.canvas.scene.clearSelection()
            for comp_data in new_comps:
                comp_item = self.canvas.components.get(comp_data.component_id)
                if comp_item is not None:
                    comp_item.setSelected(True)
            n = len(new_comps)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Pasted {n} component{'s' if n != 1 else ''}", 2000)

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
                self._apply_default_zoom()
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

            self.file_ctrl.load_from_model(model)
            self.file_ctrl.current_file = None

            title = template.metadata.title or Path(filename).stem
            self.setWindowTitle(f"Circuit Design GUI - {title} (Template)")
            self._sync_analysis_menu()

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

    def _on_export_bom(self):
        """Export a Bill of Materials (BOM) as CSV or Excel."""
        from simulation.bom_exporter import export_bom_csv, export_bom_excel, write_bom_csv

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
            circuit_name = ""
            if hasattr(self, "file_ctrl") and self.file_ctrl.current_file:
                circuit_name = self.file_ctrl.current_file.name

            if filename.lower().endswith(".xlsx") or "Excel" in selected_filter:
                if not filename.lower().endswith(".xlsx"):
                    filename += ".xlsx"
                export_bom_excel(self.model.components, filename, circuit_name=circuit_name)
            else:
                if not filename.lower().endswith(".csv"):
                    filename += ".csv"
                content = export_bom_csv(self.model.components, circuit_name=circuit_name)
                write_bom_csv(content, filename)

            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"BOM exported to {filename}", 3000)
        except (OSError, Exception) as e:
            QMessageBox.critical(self, "Error", f"Failed to export BOM: {e}")

    def _on_export_asc(self):
        """Export the circuit as an LTspice .asc schematic file."""
        from simulation.asc_exporter import export_asc, write_asc

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
            content = export_asc(self.model)
            write_asc(content, filename)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"LTspice schematic exported to {filename}", 3000)
        except (OSError, Exception) as e:
            QMessageBox.critical(self, "Error", f"Failed to export LTspice schematic: {e}")

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

    def _on_export_bundle(self):
        """Export all circuit artifacts as a ZIP bundle for lab submission."""
        import os
        import tempfile

        from simulation.bundle_exporter import create_bundle, suggest_bundle_name

        if not self.model.components:
            QMessageBox.information(self, "Export Bundle", "Nothing to export — the canvas is empty.")
            return

        circuit_name = ""
        if self.file_ctrl.current_file:
            circuit_name = self.file_ctrl.current_file.name

        suggested = suggest_bundle_name(circuit_name)
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

        try:
            # Circuit JSON
            circuit_json = self.model.to_dict()

            # Netlist
            netlist = None
            try:
                netlist = self.simulation_ctrl.generate_netlist()
            except Exception:
                pass

            # Schematic PNG (rendered at 2x via canvas)
            schematic_png = None
            try:
                tmp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp_img.close()
                self.canvas.export_image(tmp_img.name, include_grid=False)
                with open(tmp_img.name, "rb") as f:
                    schematic_png = f.read()
                os.unlink(tmp_img.name)
            except Exception:
                pass

            # Results CSV (only if simulation was run)
            results_csv = None
            if self._last_results is not None:
                try:
                    from simulation.csv_exporter import (
                        export_ac_results,
                        export_dc_sweep_results,
                        export_noise_results,
                        export_op_results,
                        export_transient_results,
                    )

                    cn = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
                    dispatch = {
                        "DC Operating Point": export_op_results,
                        "DC Sweep": export_dc_sweep_results,
                        "AC Sweep": export_ac_results,
                        "Transient": export_transient_results,
                        "Noise": export_noise_results,
                    }
                    func = dispatch.get(self._last_results_type)
                    if func:
                        results_csv = func(self._last_results, cn)
                except Exception:
                    pass

            # Results Excel (only if simulation was run)
            results_xlsx_path = None
            if self._last_results is not None:
                try:
                    from simulation.excel_exporter import export_to_excel

                    cn = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
                    tmp_xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
                    tmp_xlsx.close()
                    export_to_excel(self._last_results, self._last_results_type, tmp_xlsx.name, cn)
                    results_xlsx_path = tmp_xlsx.name
                except Exception:
                    pass

            included = create_bundle(
                filepath=filename,
                circuit_json=circuit_json,
                netlist=netlist,
                schematic_png=schematic_png,
                results_csv=results_csv,
                results_xlsx_path=results_xlsx_path,
                circuit_name=circuit_name,
            )

            # Clean up temp xlsx
            if results_xlsx_path:
                try:
                    os.unlink(results_xlsx_path)
                except OSError:
                    pass

            QMessageBox.information(
                self,
                "Bundle Exported",
                f"Lab bundle saved to {Path(filename).name}\n\nIncludes: {', '.join(included)}",
            )
        except (OSError, Exception) as e:
            QMessageBox.critical(self, "Error", f"Failed to export bundle: {e}")

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
        """Open the template browser dialog with preview."""
        from controllers.template_controller import TemplateController
        from controllers.template_manager import TemplateManager
        from GUI.template_dialog import NewFromTemplateDialog
        from GUI.template_preview_dialog import TemplatePreviewDialog

        if not hasattr(self, "_template_manager"):
            self._template_manager = TemplateManager()

        dialog = NewFromTemplateDialog(self._template_manager, self)
        if dialog.exec() == NewFromTemplateDialog.DialogCode.Accepted:
            template_info = dialog.get_selected_template()
            if template_info is None:
                return

            # Load full template data for preview
            try:
                template_ctrl = TemplateController()
                template_data = template_ctrl.load_template(template_info.filepath)
            except (OSError, ValueError):
                # If preview load fails, fall back to direct load
                self._open_template(template_info.filepath)
                return

            preview = TemplatePreviewDialog(template_data, self)
            if preview.exec() == TemplatePreviewDialog.DialogCode.Accepted:
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
            self._apply_default_zoom()
            # Don't set as current file (keep it as example, not saved)
            self.file_ctrl.current_file = None
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load example: {e}")

    # ------------------------------------------------------------------
    # Recent exports tracking and re-export
    # ------------------------------------------------------------------

    def _track_export(self, path, fmt, export_function):
        """Record a completed export for the Recent Exports menu."""
        from .recent_exports import add_recent_export

        add_recent_export(path, fmt, export_function)

    def _populate_recent_exports_menu(self):
        """Rebuild the Recent Exports submenu from QSettings."""
        from .recent_exports import get_recent_exports

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
        from .recent_exports import get_recent_exports

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
            if export_function == "export_netlist":
                netlist = self.simulation_ctrl.generate_netlist()
                with open(path, "w") as f:
                    f.write(netlist)
            elif export_function == "export_image":
                self.canvas.export_image(path, include_grid=False)
            elif export_function == "export_bom_csv":
                from simulation.bom_exporter import export_bom_csv, write_bom_csv

                circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
                content = export_bom_csv(self.model.components, circuit_name=circuit_name)
                write_bom_csv(content, path)
            elif export_function == "export_bom_excel":
                from simulation.bom_exporter import export_bom_excel

                circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
                export_bom_excel(self.model.components, path, circuit_name=circuit_name)
            elif export_function == "export_results_csv":
                self._re_export_results_csv(path)
            elif export_function == "export_results_excel":
                self._re_export_results_excel(path)
            elif export_function == "export_circuitikz":
                from simulation.circuitikz_exporter import generate

                content = generate(
                    self.model.components,
                    self.model.wires,
                    self.model.nodes,
                    self.model.terminal_to_node,
                )
                with open(path, "w") as f:
                    f.write(content)
            elif export_function == "export_asc":
                from simulation.asc_exporter import export_asc, write_asc

                content = export_asc(self.model)
                write_asc(content, path)
            elif export_function == "export_results_markdown":
                md = self._get_markdown_content()
                if md:
                    from simulation.markdown_exporter import write_markdown

                    write_markdown(md, path)
            else:
                QMessageBox.warning(self, "Re-export", f"Unknown export type: {export_function}")
                return

            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Re-exported to {Path(path).name}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Re-export Error", f"Failed to re-export:\n{e}")

    def _re_export_results_csv(self, path):
        """Re-export simulation results to CSV at the given path."""
        if self._last_results is None:
            return
        import os

        from simulation.csv_exporter import (
            export_ac_results,
            export_dc_sweep_results,
            export_noise_results,
            export_op_results,
            export_transient_results,
            write_csv,
        )

        circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
        dispatch = {
            "DC Operating Point": export_op_results,
            "DC Sweep": export_dc_sweep_results,
            "AC Sweep": export_ac_results,
            "Transient": export_transient_results,
            "Noise": export_noise_results,
        }
        func = dispatch.get(self._last_results_type)
        if func:
            write_csv(func(self._last_results, circuit_name), path)

    def _re_export_results_excel(self, path):
        """Re-export simulation results to Excel at the given path."""
        if self._last_results is None:
            return
        import os

        from simulation.excel_exporter import export_to_excel

        circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""
        export_to_excel(self._last_results, self._last_results_type, path, circuit_name)

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
                    f"Updated recommended components ({count} selected)" if count else "Cleared recommended components",
                    3000,
                )

    def _sync_palette_used_in_file(self):
        """Update the palette 'Used in File' section from the current model."""
        used_types = [comp.component_type for comp in self.model.components.values()]
        self.palette.update_used_in_file(used_types)

    def _sync_palette_recommendations(self):
        """Update the palette Recommended section from the current model."""
        self.palette.set_recommended_components(self.model.recommended_components)
