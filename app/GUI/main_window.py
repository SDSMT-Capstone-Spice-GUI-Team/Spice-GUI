"""Main application window with MVC architecture"""

import json
import logging
import os
from pathlib import Path

from controllers.circuit_controller import CircuitController
from controllers.file_controller import FileController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .analysis_dialog import AnalysisDialog
from .circuit_canvas import CircuitCanvasView
from .component_palette import ComponentPalette
from .keybindings import KeybindingsRegistry
from .properties_panel import PropertiesPanel
from .results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog
from .styles import DEFAULT_SPLITTER_SIZES, DEFAULT_WINDOW_SIZE, theme_manager
from .waveform_dialog import WaveformDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with MVC architecture

    This class handles UI construction and coordinates between the model
    and various views. Business logic is delegated to controllers.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.setGeometry(100, 100, *DEFAULT_WINDOW_SIZE)

        # Keybindings registry (load before UI so shortcuts are applied)
        self.keybindings = KeybindingsRegistry()

        # Create model (single source of truth)
        self.model = CircuitModel()

        # Create controllers (Phase 5: wire them together)
        self.circuit_ctrl = CircuitController(self.model)
        self.file_ctrl = FileController(self.model, self.circuit_ctrl)
        self.simulation_ctrl = SimulationController(self.model, self.circuit_ctrl)

        # UI state
        self._last_results = None
        self._last_results_type = None
        self._waveform_dialog = None
        self._plot_dialog = None  # DC Sweep / AC Sweep plot dialog

        # Build UI
        self.init_ui()
        self.create_menu_bar()

        # Wire up connections
        self._connect_signals()

        # Restore state
        self._restore_settings()
        self._load_last_session()

    def _connect_signals(self):
        """Connect signals between UI components"""
        self.canvas.zoomChanged.connect(self._on_zoom_changed)
        self.canvas.componentRightClicked.connect(self.on_component_right_clicked)
        self.canvas.canvasClicked.connect(self.on_canvas_clicked)
        self.canvas.selectionChanged.connect(self._on_selection_changed)
        self.palette.componentDoubleClicked.connect(self.canvas.add_component_at_center)
        self.properties_panel.property_changed.connect(self.on_property_changed)

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel - Component palette
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Component Palette"))
        self.palette = ComponentPalette()
        left_panel.addWidget(self.palette)
        instructions = QLabel(
            "📦 Drag components from palette to canvas\n"
            "🔌 Left-click terminal → click another terminal to wire\n"
            "🖱️ Drag components to move (wires follow!)\n"
            "🔄 Press R to rotate selected\n"
            "🗑️ Right-click for context menu\n"
            "⌫ Delete key to remove selected\n"
            "\n"
            "Wires auto-route using IDA* path finding!"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(theme_manager.stylesheet("instructions_panel"))
        left_panel.addWidget(instructions)
        main_layout.addLayout(left_panel, 1)

        # Center - Canvas and results
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)

        # Canvas toolbar with zoom controls
        canvas_toolbar = QHBoxLayout()
        canvas_toolbar.addWidget(QLabel("Circuit Canvas"))
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedWidth(30)
        btn_zoom_in.setToolTip("Zoom In (Ctrl++)")
        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedWidth(30)
        btn_zoom_out.setToolTip("Zoom Out (Ctrl+-)")
        btn_zoom_fit = QPushButton("Fit")
        btn_zoom_fit.setToolTip("Fit to Circuit (Ctrl+0)")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(45)
        canvas_toolbar.addStretch()
        canvas_toolbar.addWidget(btn_zoom_out)
        canvas_toolbar.addWidget(self.zoom_label)
        canvas_toolbar.addWidget(btn_zoom_in)
        canvas_toolbar.addWidget(btn_zoom_fit)
        canvas_layout.addLayout(canvas_toolbar)

        # Phase 5: Pass controller to canvas for observer pattern
        self.canvas = CircuitCanvasView(self.circuit_ctrl)
        btn_zoom_in.clicked.connect(lambda: self.canvas.zoom_in())
        btn_zoom_out.clicked.connect(lambda: self.canvas.zoom_out())
        btn_zoom_fit.clicked.connect(lambda: self.canvas.zoom_fit())
        canvas_layout.addWidget(self.canvas)
        center_splitter.addWidget(canvas_widget)

        # Results panel
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Simulation Results"))
        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.setEnabled(False)
        self.btn_export_csv.clicked.connect(self.export_results_csv)
        results_header.addWidget(self.btn_export_csv)
        results_header.addStretch()
        results_layout.addLayout(results_header)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        center_splitter.addWidget(results_widget)
        center_splitter.setSizes(DEFAULT_SPLITTER_SIZES)
        self.center_splitter = center_splitter
        main_layout.addWidget(center_splitter, 3)

        # Right panel - Properties and Controls
        right_panel_layout = QVBoxLayout()

        # Properties stack (show/hide panel)
        self.properties_stack = QStackedWidget()
        self.properties_panel = PropertiesPanel()
        blank_widget = QWidget()
        self.properties_stack.addWidget(blank_widget)  # Index 0
        self.properties_stack.addWidget(self.properties_panel)  # Index 1
        right_panel_layout.addWidget(self.properties_stack)

        right_panel_layout.addStretch()
        right_panel_layout.addWidget(QLabel("Actions"))

        self.btn_save = QPushButton("Save Circuit")
        self.btn_save.clicked.connect(self._on_save_as)
        right_panel_layout.addWidget(self.btn_save)

        self.btn_load = QPushButton("Load Circuit")
        self.btn_load.clicked.connect(self._on_load)
        right_panel_layout.addWidget(self.btn_load)

        self.btn_clear = QPushButton("Clear Canvas")
        self.btn_clear.clicked.connect(self.clear_canvas)
        right_panel_layout.addWidget(self.btn_clear)

        right_panel_layout.addWidget(QLabel(""))  # Spacer

        self.btn_netlist = QPushButton("Generate Netlist")
        self.btn_netlist.clicked.connect(self.generate_netlist)
        right_panel_layout.addWidget(self.btn_netlist)

        self.btn_simulate = QPushButton("Run Simulation")
        self.btn_simulate.clicked.connect(self.run_simulation)
        right_panel_layout.addWidget(self.btn_simulate)

        main_layout.addLayout(right_panel_layout, 1)

    def create_menu_bar(self):
        """Create menu bar with File, Edit, View, Simulation, Analysis, and Settings menus"""
        menubar = self.menuBar()
        if menubar is None:
            return

        # File menu
        file_menu = menubar.addMenu("&File")
        if file_menu is None:
            return

        kb = self.keybindings

        new_action = QAction("&New", self)
        new_action.setShortcut(kb.get("file.new"))
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(kb.get("file.open"))
        open_action.triggered.connect(self._on_load)
        file_menu.addAction(open_action)

        # Open Example submenu
        self.examples_menu = file_menu.addMenu("Open &Example")
        self._populate_examples_menu()

        save_action = QAction("&Save", self)
        save_action.setShortcut(kb.get("file.save"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(kb.get("file.save_as"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_img_action = QAction("Export &Image...", self)
        export_img_action.setShortcut(kb.get("file.export_image"))
        export_img_action.triggered.connect(self.export_image)
        file_menu.addAction(export_img_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(kb.get("file.exit"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        if edit_menu is None:
            return

        # Undo/Redo actions
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(kb.get("edit.undo"))
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        self.undo_action = undo_action  # Store reference to update enabled state

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(kb.get("edit.redo"))
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)
        self.redo_action = redo_action  # Store reference to update enabled state

        edit_menu.addSeparator()

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(kb.get("edit.copy"))
        copy_action.triggered.connect(self.copy_selected)
        edit_menu.addAction(copy_action)

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(kb.get("edit.cut"))
        cut_action.triggered.connect(self.cut_selected)
        edit_menu.addAction(cut_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(kb.get("edit.paste"))
        paste_action.triggered.connect(self.paste_components)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(kb.get("edit.delete"))
        delete_action.triggered.connect(self.canvas.delete_selected)
        edit_menu.addAction(delete_action)

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(kb.get("edit.select_all"))
        select_all_action.triggered.connect(self.canvas.select_all)
        edit_menu.addAction(select_all_action)

        edit_menu.addSeparator()

        rotate_cw_action = QAction("Rotate Clockwise", self)
        rotate_cw_action.setShortcut(kb.get("edit.rotate_cw"))
        rotate_cw_action.triggered.connect(lambda: self.canvas.rotate_selected(True))
        edit_menu.addAction(rotate_cw_action)

        rotate_ccw_action = QAction("Rotate Counter-Clockwise", self)
        rotate_ccw_action.setShortcut(kb.get("edit.rotate_ccw"))
        rotate_ccw_action.triggered.connect(lambda: self.canvas.rotate_selected(False))
        edit_menu.addAction(rotate_ccw_action)

        flip_h_action = QAction("Flip Horizontal", self)
        flip_h_action.setShortcut(kb.get("edit.flip_h"))
        flip_h_action.triggered.connect(lambda: self.canvas.flip_selected(True))
        edit_menu.addAction(flip_h_action)

        flip_v_action = QAction("Flip Vertical", self)
        flip_v_action.setShortcut(kb.get("edit.flip_v"))
        flip_v_action.triggered.connect(lambda: self.canvas.flip_selected(False))
        edit_menu.addAction(flip_v_action)

        edit_menu.addSeparator()

        clear_action = QAction("&Clear Canvas", self)
        clear_action.setShortcut(kb.get("edit.clear"))
        clear_action.triggered.connect(self.clear_canvas)
        edit_menu.addAction(clear_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        if view_menu is None:
            return

        self.show_labels_action = QAction("Show Component &Labels", self)
        self.show_labels_action.setCheckable(True)
        self.show_labels_action.setChecked(True)
        self.show_labels_action.triggered.connect(self.toggle_component_labels)
        view_menu.addAction(self.show_labels_action)

        self.show_values_action = QAction("Show Component &Values", self)
        self.show_values_action.setCheckable(True)
        self.show_values_action.setChecked(True)
        self.show_values_action.triggered.connect(self.toggle_component_values)
        view_menu.addAction(self.show_values_action)

        self.show_nodes_action = QAction("Show &Node Labels", self)
        self.show_nodes_action.setCheckable(True)
        self.show_nodes_action.setChecked(True)
        self.show_nodes_action.triggered.connect(self.toggle_node_labels)
        view_menu.addAction(self.show_nodes_action)

        view_menu.addSeparator()

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(kb.get("view.zoom_in"))
        zoom_in_action.triggered.connect(lambda: self.canvas.zoom_in())
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(kb.get("view.zoom_out"))
        zoom_out_action.triggered.connect(lambda: self.canvas.zoom_out())
        view_menu.addAction(zoom_out_action)

        zoom_fit_action = QAction("&Fit to Circuit", self)
        zoom_fit_action.setShortcut(kb.get("view.zoom_fit"))
        zoom_fit_action.triggered.connect(lambda: self.canvas.zoom_fit())
        view_menu.addAction(zoom_fit_action)

        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut(kb.get("view.zoom_reset"))
        zoom_reset_action.triggered.connect(lambda: self.canvas.zoom_reset())
        view_menu.addAction(zoom_reset_action)

        # Simulation menu
        sim_menu = menubar.addMenu("&Simulation")
        if sim_menu is None:
            return

        netlist_action = QAction("Generate &Netlist", self)
        netlist_action.setShortcut(kb.get("sim.netlist"))
        netlist_action.triggered.connect(self.generate_netlist)
        sim_menu.addAction(netlist_action)

        run_action = QAction("&Run Simulation", self)
        run_action.setShortcut(kb.get("sim.run"))
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")
        if analysis_menu is None:
            return

        op_action = QAction("&DC Operating Point (.op)", self)
        op_action.setCheckable(True)
        op_action.setChecked(True)
        op_action.triggered.connect(self.set_analysis_op)
        analysis_menu.addAction(op_action)

        dc_action = QAction("&DC Sweep", self)
        dc_action.setCheckable(True)
        dc_action.triggered.connect(self.set_analysis_dc)
        analysis_menu.addAction(dc_action)

        ac_action = QAction("&AC Sweep", self)
        ac_action.setCheckable(True)
        ac_action.triggered.connect(self.set_analysis_ac)
        analysis_menu.addAction(ac_action)

        tran_action = QAction("&Transient", self)
        tran_action.setCheckable(True)
        tran_action.triggered.connect(self.set_analysis_transient)
        analysis_menu.addAction(tran_action)

        temp_action = QAction("Te&mperature Sweep", self)
        temp_action.setCheckable(True)
        temp_action.triggered.connect(self.set_analysis_temp_sweep)
        analysis_menu.addAction(temp_action)

        # Create action group for mutually exclusive analysis types
        self.analysis_group = QActionGroup(self)
        self.analysis_group.addAction(op_action)
        self.analysis_group.addAction(dc_action)
        self.analysis_group.addAction(ac_action)
        self.analysis_group.addAction(tran_action)
        self.analysis_group.addAction(temp_action)

        self.op_action = op_action
        self.dc_action = dc_action
        self.ac_action = ac_action
        self.tran_action = tran_action
        self.temp_action = temp_action

        # Store action references for keybinding re-application
        self._bound_actions = {
            "file.new": new_action,
            "file.open": open_action,
            "file.save": save_action,
            "file.save_as": save_as_action,
            "file.export_image": export_img_action,
            "file.exit": exit_action,
            "edit.undo": undo_action,
            "edit.redo": redo_action,
            "edit.copy": copy_action,
            "edit.cut": cut_action,
            "edit.paste": paste_action,
            "edit.delete": delete_action,
            "edit.select_all": select_all_action,
            "edit.rotate_cw": rotate_cw_action,
            "edit.rotate_ccw": rotate_ccw_action,
            "edit.flip_h": flip_h_action,
            "edit.flip_v": flip_v_action,
            "edit.clear": clear_action,
            "view.zoom_in": zoom_in_action,
            "view.zoom_out": zoom_out_action,
            "view.zoom_fit": zoom_fit_action,
            "view.zoom_reset": zoom_reset_action,
            "sim.netlist": netlist_action,
            "sim.run": run_action,
        }

        # Settings menu
        settings_menu = menubar.addMenu("Se&ttings")
        if settings_menu:
            keybindings_action = QAction("&Keybindings...", self)
            keybindings_action.triggered.connect(self._open_keybindings_dialog)
            settings_menu.addAction(keybindings_action)

    # File Operations (delegated to FileController)

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
                self.setWindowTitle(f"Circuit Design GUI - {filename}")
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

    # Simulation Operations (delegated to SimulationController)

    def generate_netlist(self):
        """Generate SPICE netlist"""
        try:
            # Phase 5: No sync needed - model always up to date
            netlist = self.simulation_ctrl.generate_netlist()
            self.results_text.setPlainText("SPICE Netlist:\n\n" + netlist)
        except (ValueError, KeyError, TypeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to generate netlist: {e}")

    def run_simulation(self):
        """Run SPICE simulation"""
        try:
            # Phase 5: No sync needed - model always up to date
            # Run simulation via controller
            result = self.simulation_ctrl.run_simulation()

            # Display results (view responsibility)
            self._display_simulation_results(result)

        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as e:
            logger.error("Simulation failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "Error", f"Simulation failed: {e}")

    def _display_simulation_results(self, result):
        """Display simulation results based on analysis type"""
        self._last_results = None
        self._last_results_type = self.model.analysis_type
        self.btn_export_csv.setEnabled(False)

        self.results_text.setPlainText("\n" + "=" * 70)
        self.results_text.append(f"SIMULATION COMPLETE - {self.model.analysis_type}")
        self.results_text.append("=" * 70)

        if not result.success:
            # Show validation / simulation errors in the results panel
            self.results_text.append("\nSIMULATION COULD NOT RUN")
            self.results_text.append("=" * 40)
            if result.errors:
                self.results_text.append("\nPlease fix the following issues:\n")
                for error in result.errors:
                    self.results_text.append(f"  - {error}")
            if result.warnings:
                self.results_text.append("\nAdditional notes:\n")
                for warning in result.warnings:
                    self.results_text.append(f"  - {warning}")
            if result.error and not result.errors:
                self.results_text.append(f"\n{result.error}")

            # Also show a popup so the user notices immediately
            popup_lines = list(result.errors or [])
            if result.warnings:
                popup_lines.append("")
                popup_lines.extend(result.warnings)
            if not popup_lines and result.error:
                popup_lines.append(result.error)
            QMessageBox.warning(
                self,
                "Circuit Validation",
                "\n\n".join(popup_lines),
            )
            return

        if self.model.analysis_type == "DC Operating Point":
            node_voltages = result.data if result.data else {}
            if node_voltages:
                self._last_results = node_voltages
                self.results_text.append("\nNODE VOLTAGES:")
                self.results_text.append("-" * 40)
                for node, voltage in sorted(node_voltages.items()):
                    self.results_text.append(f"  {node:15s} : {voltage:12.6f} V")
                self.canvas.set_node_voltages(node_voltages)
                self.results_text.append("-" * 40)
            else:
                self.results_text.append("\nNo node voltages found in output.")
                self.canvas.clear_node_voltages()

        elif self.model.analysis_type == "DC Sweep":
            sweep_data = result.data if result.data else None
            if sweep_data:
                self._last_results = sweep_data
                self.results_text.append("\nDC SWEEP RESULTS:")
                self.results_text.append("-" * 40)
                headers = sweep_data.get("headers", [])
                rows = sweep_data.get("data", [])
                if headers and rows:
                    self.results_text.append("  ".join(f"{h:>12}" for h in headers))
                    for row in rows[:20]:
                        self.results_text.append("  ".join(f"{v:12.6g}" for v in row))
                    if len(rows) > 20:
                        self.results_text.append(f"  ... ({len(rows)} total rows)")
                self.results_text.append("\nPlot opened in a new window.")
                self._show_plot_dialog(DCSweepPlotDialog(sweep_data, self))
            else:
                self.results_text.append("\nDC Sweep data - see raw output below")
            self.canvas.clear_node_voltages()

        elif self.model.analysis_type == "AC Sweep":
            ac_data = result.data if result.data else None
            if ac_data:
                self._last_results = ac_data
                self.results_text.append("\nAC SWEEP RESULTS:")
                self.results_text.append("-" * 40)
                freqs = ac_data.get("frequencies", [])
                mag = ac_data.get("magnitude", {})
                self.results_text.append(f"  Frequency points: {len(freqs)}")
                self.results_text.append(f"  Signals: {', '.join(sorted(mag.keys()))}")
                if freqs:
                    self.results_text.append(f"  Range: {freqs[0]:.4g} Hz — {freqs[-1]:.4g} Hz")
                self.results_text.append("\nBode plot opened in a new window.")
                self._show_plot_dialog(ACSweepPlotDialog(ac_data, self))
            else:
                self.results_text.append("\nAC Sweep data - see raw output below")
            self.canvas.clear_node_voltages()

        elif self.model.analysis_type == "Transient":
            tran_data = result.data if result.data else None

            if tran_data:
                self._last_results = tran_data
                self.results_text.append("\nTRANSIENT ANALYSIS RESULTS:")

                from simulation import ResultParser

                table_string = ResultParser.format_results_as_table(tran_data)
                self.results_text.append(table_string)

                self.results_text.append("\n" + "-" * 40)
                self.results_text.append("Waveform plot has also been generated in a new window.")

                # Clean up previous waveform dialog
                if self._waveform_dialog is not None:
                    self._waveform_dialog.close()
                    self._waveform_dialog.deleteLater()

                # Show waveform plot
                self._waveform_dialog = WaveformDialog(tran_data, self)
                self._waveform_dialog.show()
            else:
                self.results_text.append("\nNo transient data found in output.")
            self.canvas.clear_node_voltages()

        elif self.model.analysis_type == "Temperature Sweep":
            node_voltages = result.data if result.data else {}
            if node_voltages:
                self._last_results = node_voltages
                self.results_text.append("\nTEMPERATURE SWEEP RESULTS:")
                self.results_text.append("-" * 40)
                params = self.model.analysis_params
                self.results_text.append(
                    f"Temperature range: {params.get('tempStart', '?')}\u00b0C "
                    f"to {params.get('tempStop', '?')}\u00b0C "
                    f"(step {params.get('tempStep', '?')}\u00b0C)"
                )
                self.results_text.append("")
                for node, voltage in sorted(node_voltages.items()):
                    self.results_text.append(f"  {node:15s} : {voltage:12.6f} V")
                self.results_text.append("-" * 40)
                self.results_text.append("Note: values shown are from the final temperature step.")
            else:
                self.results_text.append("\nNo results found. Check raw output below.")
            self.canvas.clear_node_voltages()

        self.results_text.append("=" * 70)

        if self._last_results is not None:
            self.btn_export_csv.setEnabled(True)

    def _show_plot_dialog(self, dialog):
        """Show a plot dialog, closing any previous one."""
        if self._plot_dialog is not None:
            self._plot_dialog.close()
            self._plot_dialog.deleteLater()
        self._plot_dialog = dialog
        self._plot_dialog.show()

    def export_results_csv(self):
        """Export the last simulation results to a CSV file"""
        if self._last_results is None:
            return

        from simulation.csv_exporter import (
            export_ac_results,
            export_dc_sweep_results,
            export_op_results,
            export_transient_results,
            write_csv,
        )

        circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""

        if self._last_results_type == "DC Operating Point":
            csv_content = export_op_results(self._last_results, circuit_name)
        elif self._last_results_type == "DC Sweep":
            csv_content = export_dc_sweep_results(self._last_results, circuit_name)
        elif self._last_results_type == "AC Sweep":
            csv_content = export_ac_results(self._last_results, circuit_name)
        elif self._last_results_type == "Transient":
            csv_content = export_transient_results(self._last_results, circuit_name)
        else:
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export Results to CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filename:
            try:
                write_csv(csv_content, filename)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(f"Results exported to {filename}", 3000)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    # Analysis Settings

    def set_analysis_op(self):
        """Set analysis type to DC Operating Point"""
        self.simulation_ctrl.set_analysis("DC Operating Point", {})
        statusbar = self.statusBar()
        if statusbar:
            statusbar.showMessage("Analysis: DC Operating Point (.op)", 3000)

    def set_analysis_dc(self):
        """Set analysis type to DC Sweep with parameters"""
        dialog = AnalysisDialog("DC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("DC Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: DC Sweep (V: {params['min']}V to {params['max']}V, step {params['step']}V)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_ac(self):
        """Set analysis type to AC Sweep with parameters"""
        dialog = AnalysisDialog("AC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("AC Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: AC Sweep ({params['fStart']}Hz to {params['fStop']}Hz, {params['points']} pts/decade)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_transient(self):
        """Set analysis type to Transient with parameters"""
        dialog = AnalysisDialog("Transient", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Transient", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Transient (duration: {params['duration']}s, step: {params['step']}s)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_temp_sweep(self):
        """Set analysis type to Temperature Sweep with parameters"""
        dialog = AnalysisDialog("Temperature Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Temperature Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Temperature Sweep "
                        f"({params['tempStart']}\u00b0C to "
                        f"{params['tempStop']}\u00b0C, step "
                        f"{params['tempStep']}\u00b0C)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def _sync_analysis_menu(self):
        """Update Analysis menu checkboxes to match model state."""
        analysis_type = self.model.analysis_type
        if analysis_type == "DC Operating Point":
            self.op_action.setChecked(True)
        elif analysis_type == "DC Sweep":
            self.dc_action.setChecked(True)
        elif analysis_type == "AC Sweep":
            self.ac_action.setChecked(True)
        elif analysis_type == "Transient":
            self.tran_action.setChecked(True)
        elif analysis_type == "Temperature Sweep":
            self.temp_action.setChecked(True)

    # View Operations

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

    def clear_canvas(self):
        """Clear the canvas"""
        reply = QMessageBox.question(
            self,
            "Clear Canvas",
            "Are you sure you want to clear the canvas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_circuit()
            self.file_ctrl.new_circuit()
            # Phase 5: No sync needed - observer pattern handles canvas update

    # Properties Panel

    def on_component_right_clicked(self, component, event_pos):
        """Handle right-click on a component"""
        if component:
            self.properties_panel.show_component(component)
            self.properties_stack.setCurrentIndex(1)  # Show properties
        else:
            self.properties_stack.setCurrentIndex(0)  # Show blank

    def _on_selection_changed(self, selection):
        """Handle canvas selection changes — single component, list, or None."""
        if selection is None:
            self.properties_stack.setCurrentIndex(0)
            self.properties_panel.show_no_selection()
        elif isinstance(selection, list):
            self.properties_stack.setCurrentIndex(1)
            self.properties_panel.show_multi_selection(len(selection))
        else:
            self.properties_stack.setCurrentIndex(1)
            self.properties_panel.show_component(selection)

    def on_canvas_clicked(self):
        """Handle click on an empty canvas area"""
        self.properties_stack.setCurrentIndex(0)
        self.properties_panel.show_no_selection()

    def on_property_changed(self, component_id, property_name, new_value):
        """Handle property changes from properties panel"""
        component = self.canvas.components.get(component_id)
        if not component:
            return

        if property_name == "value":
            component.value = new_value
            component.update()
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Updated {component_id} value to {new_value}", 2000)

        elif property_name == "rotation":
            component.rotation_angle = new_value
            component.update_terminals()
            component.update()
            self.canvas.reroute_connected_wires(component)
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Rotated {component_id} to {new_value}°", 2000)
            self.properties_panel.show_component(component)

        elif property_name == "waveform":
            component.update()
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Updated {component_id} waveform configuration", 2000)

    # Keybindings

    def _open_keybindings_dialog(self):
        """Open the keybindings preferences dialog."""
        from .keybindings_dialog import KeybindingsDialog

        dialog = KeybindingsDialog(self.keybindings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Re-apply shortcuts to all menu actions
            self._apply_keybindings()

    def _apply_keybindings(self):
        """Re-apply shortcuts from the registry to stored actions."""
        kb = self.keybindings
        for action_name, qaction in self._bound_actions.items():
            qaction.setShortcut(kb.get(action_name))

    # Settings Persistence

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
            self.simulation_ctrl.set_analysis(analysis_type, self.model.analysis_params)
            # Update menu checkboxes
            if analysis_type == "DC Operating Point":
                self.op_action.setChecked(True)
            elif analysis_type == "DC Sweep":
                self.dc_action.setChecked(True)
            elif analysis_type == "AC Sweep":
                self.ac_action.setChecked(True)
            elif analysis_type == "Transient":
                self.tran_action.setChecked(True)

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

    def closeEvent(self, event):
        """Save settings before closing"""
        self._save_settings()
        super().closeEvent(event)
