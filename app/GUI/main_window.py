"""Main application window with MVC architecture"""

import json
import logging
import os
from pathlib import Path

from controllers.circuit_controller import CircuitController
from controllers.file_controller import FileController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .analysis_dialog import AnalysisDialog
from .circuit_canvas import CircuitCanvasView
from .circuit_statistics_panel import CircuitStatisticsPanel
from .component_palette import ComponentPalette
from .keybindings import KeybindingsRegistry
from .parameter_sweep_dialog import ParameterSweepDialog
from .parameter_sweep_plot_dialog import ParameterSweepPlotDialog
from .properties_panel import PropertiesPanel
from .results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog
from .styles import DEFAULT_SPLITTER_SIZES, DEFAULT_WINDOW_SIZE, DarkTheme, LightTheme, theme_manager
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
        self._dirty = False  # Unsaved changes flag

        # Build UI
        self.init_ui()
        self.create_menu_bar()

        # Wire up connections
        self._connect_signals()

        # Restore state
        self._restore_settings()
        self._check_auto_save_recovery()
        self._load_last_session()

        # Auto-save timer
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._auto_save)
        self._start_autosave_timer()

    def _connect_signals(self):
        """Connect signals between UI components"""
        self.canvas.zoomChanged.connect(self._on_zoom_changed)
        self.canvas.componentRightClicked.connect(self.on_component_right_clicked)
        self.canvas.canvasClicked.connect(self.on_canvas_clicked)
        self.canvas.selectionChanged.connect(self._on_selection_changed)
        self.canvas.probeRequested.connect(self._on_probe_requested)
        self.palette.componentDoubleClicked.connect(self.canvas.add_component_at_center)
        self.properties_panel.property_changed.connect(self.on_property_changed)
        self.circuit_ctrl.add_observer(self._on_dirty_change)

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

        # Circuit statistics panel
        self.statistics_panel = CircuitStatisticsPanel(self.model, self.circuit_ctrl, self.simulation_ctrl)
        self.statistics_panel.setVisible(False)
        right_panel_layout.addWidget(self.statistics_panel)

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

        # Focus policies for keyboard navigation
        self.palette.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.results_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.btn_load.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.btn_clear.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.btn_netlist.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.btn_simulate.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        # Tab order: Palette -> Canvas -> Properties -> Action buttons
        self.setTabOrder(self.palette, self.canvas)
        self.setTabOrder(self.canvas, self.properties_panel.value_input)
        self.setTabOrder(self.properties_panel.value_input, self.properties_panel.apply_button)
        self.setTabOrder(self.properties_panel.apply_button, self.btn_save)
        self.setTabOrder(self.btn_save, self.btn_load)
        self.setTabOrder(self.btn_load, self.btn_clear)
        self.setTabOrder(self.btn_clear, self.btn_netlist)
        self.setTabOrder(self.btn_netlist, self.btn_simulate)
        self.setTabOrder(self.btn_simulate, self.results_text)

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

        self.show_op_annotations_action = QAction("Show &OP Annotations", self)
        self.show_op_annotations_action.setCheckable(True)
        self.show_op_annotations_action.setChecked(True)
        self.show_op_annotations_action.triggered.connect(self.toggle_op_annotations)
        view_menu.addAction(self.show_op_annotations_action)

        view_menu.addSeparator()

        self.probe_action = QAction("&Probe Tool", self)
        self.probe_action.setCheckable(True)
        self.probe_action.setShortcut(kb.get("tools.probe"))
        self.probe_action.setToolTip("Click nodes or components to see voltage/current values")
        self.probe_action.triggered.connect(self._toggle_probe_mode)
        view_menu.addAction(self.probe_action)

        view_menu.addSeparator()

        self.show_statistics_action = QAction("Circuit &Statistics", self)
        self.show_statistics_action.setCheckable(True)
        self.show_statistics_action.setChecked(False)
        self.show_statistics_action.triggered.connect(self._toggle_statistics_panel)
        view_menu.addAction(self.show_statistics_action)

        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")
        self.light_theme_action = QAction("&Light", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.setChecked(True)
        self.light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(self.light_theme_action)

        self.dark_theme_action = QAction("&Dark", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(self.dark_theme_action)

        self.theme_group = QActionGroup(self)
        self.theme_group.addAction(self.light_theme_action)
        self.theme_group.addAction(self.dark_theme_action)

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

        analysis_menu.addSeparator()

        sweep_action = QAction("&Parameter Sweep...", self)
        sweep_action.setCheckable(True)
        sweep_action.setToolTip(
            "Sweep a component parameter across a range of values and overlay results from each step"
        )
        sweep_action.triggered.connect(self.set_analysis_parameter_sweep)
        analysis_menu.addAction(sweep_action)

        # Create action group for mutually exclusive analysis types
        self.analysis_group = QActionGroup(self)
        self.analysis_group.addAction(op_action)
        self.analysis_group.addAction(dc_action)
        self.analysis_group.addAction(ac_action)
        self.analysis_group.addAction(tran_action)
        self.analysis_group.addAction(temp_action)
        self.analysis_group.addAction(sweep_action)

        self.op_action = op_action
        self.dc_action = dc_action
        self.ac_action = ac_action
        self.tran_action = tran_action
        self.temp_action = temp_action
        self.sweep_action = sweep_action

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
            "tools.probe": self.probe_action,
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
            if self.model.analysis_type == "Parameter Sweep":
                result = self._run_parameter_sweep()
            else:
                # Phase 5: No sync needed - model always up to date
                result = self.simulation_ctrl.run_simulation()

            # Display results (view responsibility)
            self._display_simulation_results(result)

        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as e:
            logger.error("Simulation failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "Error", f"Simulation failed: {e}")

    def _run_parameter_sweep(self):
        """Run parameter sweep with a progress dialog."""
        sweep_config = self.model.analysis_params
        num_steps = sweep_config.get("num_steps", 10)
        component_id = sweep_config.get("component_id", "?")

        progress = QProgressDialog(
            f"Running parameter sweep on {component_id}...",
            "Cancel",
            0,
            num_steps,
            self,
        )
        progress.setWindowTitle("Parameter Sweep")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        def on_progress(step, total):
            progress.setValue(step)
            progress.setLabelText(f"Running step {step + 1} of {total}...")
            QApplication.processEvents()
            return not progress.wasCanceled()

        result = self.simulation_ctrl.run_parameter_sweep(
            sweep_config,
            progress_callback=on_progress,
        )
        progress.setValue(num_steps)
        progress.close()

        # Add sweep_labels to the data for the plot dialog
        if result.data:
            from .format_utils import format_value

            result.data["sweep_labels"] = [format_value(v).strip() for v in result.data.get("sweep_values", [])]

        return result

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
            op_data = result.data if result.data else {}
            # Handle new dict format with node_voltages/branch_currents
            if isinstance(op_data, dict) and "node_voltages" in op_data:
                node_voltages = op_data["node_voltages"]
                branch_currents = op_data.get("branch_currents", {})
            else:
                # Backward compat: plain dict of voltages
                node_voltages = op_data
                branch_currents = {}

            if node_voltages:
                self._last_results = node_voltages
                self.results_text.append("\nNODE VOLTAGES:")
                self.results_text.append("-" * 40)
                for node, voltage in sorted(node_voltages.items()):
                    self.results_text.append(f"  {node:15s} : {voltage:12.6f} V")
                self.results_text.append("-" * 40)
                if branch_currents:
                    self.results_text.append("\nBRANCH CURRENTS:")
                    self.results_text.append("-" * 40)
                    for device, current in sorted(branch_currents.items()):
                        self.results_text.append(f"  {device:15s} : {current:12.6e} A")
                    self.results_text.append("-" * 40)
                self.canvas.set_op_results(node_voltages, branch_currents)

                # Calculate and display power dissipation
                self._calculate_power(node_voltages)
            else:
                self.results_text.append("\nNo node voltages found in output.")
                self.canvas.clear_op_results()
                self.properties_panel.clear_simulation_results()

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
                self._show_or_overlay_plot("DC Sweep", sweep_data, DCSweepPlotDialog)
            else:
                self.results_text.append("\nDC Sweep data - see raw output below")
            self.canvas.clear_op_results()
            self.properties_panel.clear_simulation_results()

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
                self._show_or_overlay_plot("AC Sweep", ac_data, ACSweepPlotDialog)
            else:
                self.results_text.append("\nAC Sweep data - see raw output below")
            self.canvas.clear_op_results()
            self.properties_panel.clear_simulation_results()

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

                # Check for overlay on existing waveform dialog
                if self._waveform_dialog is not None and self._waveform_dialog.isVisible():
                    reply = QMessageBox.question(
                        self,
                        "Overlay Results",
                        "A waveform window is already open.\n\n"
                        "Yes = Overlay new results on existing plot\n"
                        "No = Replace with new results only",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self._waveform_dialog.add_dataset(tran_data)
                        self._waveform_dialog.raise_()
                        self._waveform_dialog.activateWindow()
                    else:
                        self._waveform_dialog.close()
                        self._waveform_dialog.deleteLater()
                        self._waveform_dialog = WaveformDialog(tran_data, self)
                        self._waveform_dialog.show()
                else:
                    # Clean up previous waveform dialog
                    if self._waveform_dialog is not None:
                        self._waveform_dialog.close()
                        self._waveform_dialog.deleteLater()
                    self._waveform_dialog = WaveformDialog(tran_data, self)
                    self._waveform_dialog.show()
            else:
                self.results_text.append("\nNo transient data found in output.")
            self.canvas.clear_op_results()
            self.properties_panel.clear_simulation_results()

        elif self.model.analysis_type == "Temperature Sweep":
            temp_data = result.data if result.data else {}
            if isinstance(temp_data, dict) and "node_voltages" in temp_data:
                node_voltages = temp_data["node_voltages"]
            else:
                node_voltages = temp_data
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
            self.canvas.clear_op_results()
            self.properties_panel.clear_simulation_results()

        elif self.model.analysis_type == "Parameter Sweep":
            sweep_data = result.data if result.data else None
            if sweep_data:
                self._last_results = sweep_data
                comp_id = sweep_data.get("component_id", "?")
                base_type = sweep_data.get("base_analysis_type", "?")
                labels = sweep_data.get("sweep_labels", [])
                step_results = sweep_data.get("results", [])
                ok_count = sum(1 for r in step_results if r.success)

                self.results_text.append("\nPARAMETER SWEEP RESULTS:")
                self.results_text.append("-" * 40)
                self.results_text.append(f"  Component:      {comp_id}")
                self.results_text.append(f"  Base analysis:  {base_type}")
                self.results_text.append(f"  Steps:          {ok_count}/{len(step_results)} succeeded")
                if labels:
                    self.results_text.append(f"  Range:          {labels[0]} to {labels[-1]}")
                if sweep_data.get("cancelled"):
                    self.results_text.append("  (sweep was cancelled)")
                self.results_text.append("-" * 40)

                if result.errors:
                    self.results_text.append("\nStep errors:")
                    for err in result.errors[:10]:
                        self.results_text.append(f"  - {err}")

                if ok_count > 0:
                    self.results_text.append("\nPlot opened in a new window.")
                    self._show_plot_dialog(ParameterSweepPlotDialog(sweep_data, self))
            else:
                self.results_text.append("\nNo parameter sweep data.")
            self.canvas.clear_op_results()
            self.properties_panel.clear_simulation_results()

        self.results_text.append("=" * 70)

        if self._last_results is not None:
            self.btn_export_csv.setEnabled(True)

    def _calculate_power(self, node_voltages):
        """Calculate and display power dissipation for all components."""
        from simulation.power_calculator import calculate_power, total_power

        components = self.circuit_ctrl.model.components
        nodes = self.circuit_ctrl.model.nodes
        power_data = calculate_power(components, nodes, node_voltages)

        if power_data:
            # Build voltage-across data for properties panel
            voltage_data = {}
            # Build terminal-to-node lookup
            term_to_label = {}
            for node in nodes:
                label = node.get_label()
                for comp_id, term_idx in node.terminals:
                    term_to_label[(comp_id, term_idx)] = label

            for comp in components:
                cid = comp.component_id
                l0 = term_to_label.get((cid, 0))
                l1 = term_to_label.get((cid, 1))
                if l0 and l1 and l0 in node_voltages and l1 in node_voltages:
                    voltage_data[cid] = node_voltages[l0] - node_voltages[l1]

            tp = total_power(power_data)
            self.properties_panel.set_simulation_results(power_data, voltage_data, tp)

            # Show summary in results text
            from GUI.format_utils import format_value

            self.results_text.append("\nPOWER DISSIPATION:")
            self.results_text.append("-" * 40)
            for cid, p in sorted(power_data.items()):
                sign = "dissipating" if p >= 0 else "supplying"
                self.results_text.append(f"  {cid:15s} : {format_value(abs(p), 'W'):>12s} ({sign})")
            self.results_text.append("-" * 40)
            self.results_text.append(f"  {'Total':15s} : {format_value(abs(tp), 'W'):>12s}")
        else:
            self.properties_panel.clear_simulation_results()

    def _show_plot_dialog(self, dialog):
        """Show a plot dialog, closing any previous one."""
        if self._plot_dialog is not None:
            self._plot_dialog.close()
            self._plot_dialog.deleteLater()
        self._plot_dialog = dialog
        self._plot_dialog.show()

    def _show_or_overlay_plot(self, analysis_type, data, dialog_class):
        """Show a new plot or overlay data on an existing compatible dialog.

        If a plot dialog of the same analysis type is already open, the user
        is asked whether to overlay the new results or replace the old plot.
        """
        if (
            self._plot_dialog is not None
            and self._plot_dialog.isVisible()
            and getattr(self._plot_dialog, "analysis_type", None) == analysis_type
        ):
            reply = QMessageBox.question(
                self,
                "Overlay Results",
                "A plot window is already open.\n\n"
                "Yes = Overlay new results on existing plot\n"
                "No = Replace with new results only",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._plot_dialog.add_dataset(data)
                self._plot_dialog.raise_()
                self._plot_dialog.activateWindow()
                return

        self._show_plot_dialog(dialog_class(data, self))

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

    def set_analysis_parameter_sweep(self):
        """Set analysis type to Parameter Sweep with configuration dialog"""
        if not self.model.components:
            QMessageBox.warning(
                self,
                "No Components",
                "Add components to the circuit before configuring a parameter sweep.",
            )
            self.op_action.setChecked(True)
            return

        dialog = ParameterSweepDialog(self.model.components, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Parameter Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Parameter Sweep on {params['component_id']} "
                        f"({params['num_steps']} steps, base: {params['base_analysis_type']})",
                        3000,
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Parameters",
                    "Please enter valid sweep parameters. Start and stop values must be different.",
                )
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
        elif analysis_type == "Parameter Sweep":
            self.sweep_action.setChecked(True)

    # View Operations

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
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1E1E1E; color: #D4D4D4; }
                QMenuBar { background-color: #2D2D2D; color: #D4D4D4; }
                QMenuBar::item:selected { background-color: #3D3D3D; }
                QMenu { background-color: #2D2D2D; color: #D4D4D4; }
                QMenu::item:selected { background-color: #3D3D3D; }
                QLabel { color: #D4D4D4; }
                QPushButton {
                    background-color: #3D3D3D; color: #D4D4D4;
                    border: 1px solid #555555; padding: 4px 12px; border-radius: 3px;
                }
                QPushButton:hover { background-color: #4D4D4D; }
                QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #2D2D2D; color: #D4D4D4;
                    border: 1px solid #555555;
                }
                QSplitter::handle { background-color: #3D3D3D; }
                QScrollBar { background-color: #2D2D2D; }
                QScrollBar::handle { background-color: #555555; }
                QGroupBox { color: #D4D4D4; border: 1px solid #555555; }
                QTableWidget { background-color: #2D2D2D; color: #D4D4D4;
                    gridline-color: #555555; }
                QHeaderView::section { background-color: #3D3D3D; color: #D4D4D4; }
            """)
        else:
            self.setStyleSheet("")

        # Refresh canvas (grid + components)
        self.canvas.refresh_theme()

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
        # Preserve auto-save defaults if not yet set
        if settings.value("autosave/interval") is None:
            settings.setValue("autosave/interval", 60)
        if settings.value("autosave/enabled") is None:
            settings.setValue("autosave/enabled", True)
        settings.setValue("view/show_statistics", self.statistics_panel.isVisible())
        settings.setValue("view/theme", theme_manager.current_theme.name)

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

    def closeEvent(self, event):
        """Save settings before closing"""
        self._save_settings()
        self.file_ctrl.clear_auto_save()
        super().closeEvent(event)

    # Auto-save and crash recovery

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
