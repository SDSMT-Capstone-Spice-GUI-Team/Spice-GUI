"""Main application window with MVC architecture.

MainWindow is composed from focused mixin modules:
- MenuBarMixin: menu bar construction and keybinding management
- FileOperationsMixin: file I/O, clipboard, undo/redo, examples
- SimulationMixin: simulation execution, result display, CSV export
- AnalysisSettingsMixin: analysis type configuration dialogs
- ViewOperationsMixin: theme, toggles, probe, zoom, image export
- PrintExportMixin: print, print preview, PDF export
- SettingsMixin: QSettings persistence, autosave, closeEvent
"""

import logging

from controllers.circuit_controller import CircuitController
from controllers.file_controller import FileController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .circuit_canvas import CircuitCanvasView
from .circuit_statistics_panel import CircuitStatisticsPanel
from .component_palette import ComponentPalette
from .grading_panel import GradingPanel
from .keybindings import KeybindingsRegistry
from .main_window_analysis import AnalysisSettingsMixin
from .main_window_file_ops import FileOperationsMixin
from .main_window_menus import MenuBarMixin
from .main_window_print import PrintExportMixin
from .main_window_settings import SettingsMixin
from .main_window_simulation import SimulationMixin
from .main_window_view import ViewOperationsMixin
from .properties_panel import PropertiesPanel
from .styles import DEFAULT_SPLITTER_SIZES, DEFAULT_WINDOW_SIZE, theme_manager

logger = logging.getLogger(__name__)


class MainWindow(
    MenuBarMixin,
    FileOperationsMixin,
    SimulationMixin,
    AnalysisSettingsMixin,
    ViewOperationsMixin,
    PrintExportMixin,
    SettingsMixin,
    QMainWindow,
):
    """Main application window with MVC architecture.

    This class handles UI construction and coordinates between the model
    and various views. Business logic is delegated to controllers.
    Method implementations live in the mixin classes listed above.
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

        # Results / Netlist tabbed panel
        self.results_tabs = QTabWidget()

        # Tab 1: Simulation Results
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Simulation Results"))
        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.setEnabled(False)
        self.btn_export_csv.clicked.connect(self.export_results_csv)
        results_header.addWidget(self.btn_export_csv)
        self.btn_export_excel = QPushButton("Export Excel")
        self.btn_export_excel.setEnabled(False)
        self.btn_export_excel.clicked.connect(self.export_results_excel)
        results_header.addWidget(self.btn_export_excel)
        results_header.addStretch()
        results_layout.addLayout(results_header)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        self.results_tabs.addTab(results_widget, "Results")

        # Tab 2: Netlist Preview
        from .netlist_preview import NetlistPreviewWidget

        self.netlist_preview = NetlistPreviewWidget()
        self.netlist_preview.refresh_btn.clicked.connect(self._refresh_netlist_preview)
        self.results_tabs.addTab(self.netlist_preview, "Netlist")

        center_splitter.addWidget(self.results_tabs)
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

        # Instructor grading panel
        self.grading_panel = GradingPanel(self.model, self)
        self.grading_panel.setVisible(False)
        right_panel_layout.addWidget(self.grading_panel)

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

    # Canvas/Selection Callbacks (tightly coupled to init_ui widgets)

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

        elif property_name == "initial_condition":
            component.initial_condition = new_value
            ic_display = new_value if new_value else "none"
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Updated {component_id} initial condition to {ic_display}", 2000)

    def _refresh_netlist_preview(self):
        """Regenerate and display the netlist in the preview panel."""
        try:
            netlist = self.simulation_ctrl.generate_netlist()
            self.netlist_preview.set_netlist(netlist)
        except (ValueError, KeyError, TypeError) as e:
            self.netlist_preview.set_error(str(e))
