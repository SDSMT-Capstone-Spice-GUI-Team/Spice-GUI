# simulation module imported lazily in methods that need it for faster startup
import json
import logging
import os
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QMessageBox, QTextEdit,
                             QSplitter, QLabel, QDialog, QStackedWidget)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt, QSettings
from .component_palette import ComponentPalette
from .circuit_canvas import CircuitCanvas
from .analysis_dialog import AnalysisDialog
from .properties_panel import PropertiesPanel
from .waveform_dialog import WaveformDialog
from .styles import theme_manager, DEFAULT_WINDOW_SIZE, DEFAULT_SPLITTER_SIZES

logger = logging.getLogger(__name__)

# Define the session file path
SESSION_FILE = "last_session.txt"


class CircuitDesignGUI(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.setGeometry(100, 100, *DEFAULT_WINDOW_SIZE)
        self.current_file = None

        # Analysis settings
        self.analysis_type = "DC Operating Point"
        self.analysis_params = {}

        # NgspiceRunner initialized lazily on first use
        self._ngspice_runner = None

        # Last simulation results for CSV export
        self._last_results = None
        self._last_results_type = None

        self.init_ui()
        self.create_menu_bar()

        # Restore user preferences
        self._restore_settings()

        # Load the last session when the app starts
        self._load_last_session()

    @property
    def ngspice_runner(self):
        """Lazy initialization of NgspiceRunner for faster startup"""
        if self._ngspice_runner is None:
            from simulation import NgspiceRunner
            self._ngspice_runner = NgspiceRunner()
        return self._ngspice_runner

    def _save_session(self, file_path):
        """Saves the absolute path of the current file to disk."""
        try:
            # Use abspath to ensure the path is valid after an application restart
            with open(SESSION_FILE, 'w') as f:
                f.write(os.path.abspath(file_path))
        except OSError as e:
            logger.error("Error saving session: %s", e)

    def _save_settings(self):
        """Save user preferences via QSettings."""
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState())
        settings.setValue("splitter/sizes", self.center_splitter.sizes())
        settings.setValue("analysis/type", self.analysis_type)
        settings.setValue("view/show_labels", self.canvas.show_component_labels)
        settings.setValue("view/show_values", self.canvas.show_component_values)
        settings.setValue("view/show_nodes", self.canvas.show_node_labels)

    def _restore_settings(self):
        """Restore user preferences from QSettings."""
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
            self.analysis_type = analysis_type

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
        """Save settings before closing."""
        self._save_settings()
        super().closeEvent(event)

    def _load_last_session(self):
        """Loads the last saved file path and tries to open the circuit."""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    file_path = f.read().strip()

                # Check if the path is valid and the file still exists
                if file_path and os.path.exists(file_path):
                    logger.info("Hot-reload: reloading last file: %s", file_path)
                    # Call the existing load method to restore state
                    self.load_circuit(file_path, is_reload=True)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error("Error loading last session: %s", e)

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
        instructions.setStyleSheet(theme_manager.stylesheet('instructions_panel'))
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

        self.canvas = CircuitCanvas()
        btn_zoom_in.clicked.connect(lambda: self.canvas.zoom_in())
        btn_zoom_out.clicked.connect(lambda: self.canvas.zoom_out())
        btn_zoom_fit.clicked.connect(lambda: self.canvas.zoom_fit())
        self.canvas.zoomChanged.connect(self._on_zoom_changed)
        self.canvas.componentRightClicked.connect(self.on_component_right_clicked)
        self.canvas.canvasClicked.connect(self.on_canvas_clicked)
        self.palette.componentDoubleClicked.connect(self.canvas.add_component_at_center)
        canvas_layout.addWidget(self.canvas)
        center_splitter.addWidget(canvas_widget)
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

        # A stack to show either the properties panel or a blank widget
        self.properties_stack = QStackedWidget()
        self.properties_panel = PropertiesPanel()
        self.properties_panel.property_changed.connect(self.on_property_changed)
        
        blank_widget = QWidget() # A blank placeholder
        
        self.properties_stack.addWidget(blank_widget)       # Index 0
        self.properties_stack.addWidget(self.properties_panel) # Index 1
        
        right_panel_layout.addWidget(self.properties_stack)
        
        right_panel_layout.addStretch() # Pushes buttons to the bottom
        right_panel_layout.addWidget(QLabel("Actions"))
        self.btn_save = QPushButton("Save Circuit")
        self.btn_save.clicked.connect(self.save_circuit)
        right_panel_layout.addWidget(self.btn_save)
        self.btn_load = QPushButton("Load Circuit")
        self.btn_load.clicked.connect(self.load_circuit)
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
        """Create menu bar with File and Edit menus"""
        menubar = self.menuBar()
        if menubar is None:
            return

        # File menu
        file_menu = menubar.addMenu("&File")
        if file_menu is None:
            return

        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_circuit)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_circuit)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_circuit_quick)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_circuit)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_img_action = QAction("Export &Image...", self)
        export_img_action.triggered.connect(self.export_image)
        file_menu.addAction(export_img_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        if edit_menu is None:
            return

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.canvas.copy_selected)
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.canvas.paste_clipboard)
        edit_menu.addAction(paste_action)

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.canvas.cut_selected)
        edit_menu.addAction(cut_action)

        edit_menu.addSeparator()

        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        rotate_cw_action = QAction("Rotate Clockwise", self)
        rotate_cw_action.setShortcut("R")
        rotate_cw_action.triggered.connect(
            lambda: self.canvas.rotate_selected(True))
        edit_menu.addAction(rotate_cw_action)

        rotate_ccw_action = QAction("Rotate Counter-Clockwise", self)
        rotate_ccw_action.setShortcut("Shift+R")
        rotate_ccw_action.triggered.connect(
            lambda: self.canvas.rotate_selected(False))
        edit_menu.addAction(rotate_ccw_action)

        edit_menu.addSeparator()

        clear_action = QAction("&Clear Canvas", self)
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

        view_menu.addSeparator()

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut("Ctrl+=")
        zoom_in_action.triggered.connect(lambda: self.canvas.zoom_in())
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.canvas.zoom_out())
        view_menu.addAction(zoom_out_action)

        zoom_fit_action = QAction("&Fit to Circuit", self)
        zoom_fit_action.setShortcut("Ctrl+0")
        zoom_fit_action.triggered.connect(lambda: self.canvas.zoom_fit())
        view_menu.addAction(zoom_fit_action)

        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut("Ctrl+1")
        zoom_reset_action.triggered.connect(lambda: self.canvas.zoom_reset())
        view_menu.addAction(zoom_reset_action)
        view_menu.addAction(self.show_nodes_action)

        # Simulation menu
        sim_menu = menubar.addMenu("&Simulation")
        if sim_menu is None:
            return

        netlist_action = QAction("Generate &Netlist", self)
        netlist_action.setShortcut("Ctrl+G")
        netlist_action.triggered.connect(self.generate_netlist)
        sim_menu.addAction(netlist_action)

        run_action = QAction("&Run Simulation", self)
        run_action.setShortcut("F5")
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

        # Create action group for mutually exclusive analysis types
        from PyQt6.QtGui import QActionGroup
        self.analysis_group = QActionGroup(self)
        self.analysis_group.addAction(op_action)
        self.analysis_group.addAction(dc_action)
        self.analysis_group.addAction(ac_action)
        self.analysis_group.addAction(tran_action)

        self.op_action = op_action
        self.dc_action = dc_action
        self.ac_action = ac_action
        self.tran_action = tran_action

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
        """Update the zoom level display."""
        self.zoom_label.setText(f"{level * 100:.0f}%")

    def new_circuit(self):
        """Create a new circuit"""
        if len(self.canvas.components) > 0:
            reply = QMessageBox.question(
                self, "New Circuit",
                "Current circuit will be lost. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.canvas.clear_circuit()
        self.current_file = None
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.results_text.clear()

    def delete_selected(self):
        """Delete selected items from canvas"""
        self.canvas.delete_selected()

    def set_analysis_op(self):
        """Set analysis type to DC Operating Point"""
        self.analysis_type = "DC Operating Point"
        self.analysis_params = {}
        statusbar = self.statusBar()
        if statusbar is not None:
            statusbar.showMessage("Analysis: DC Operating Point (.op)", 3000)

    def set_analysis_dc(self):
        """Set analysis type to DC Sweep with parameters"""
        dialog = AnalysisDialog("DC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "DC Sweep"
                self.analysis_params = params
                statusBar = self.statusBar()
                if statusBar is not None:
                    statusBar.showMessage(
                        f"Analysis: DC Sweep (V: {params['min']}V to {params['max']}V, step {params['step']}V)",
                        3000
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters",
                                    "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_ac(self):
        """Set analysis type to AC Sweep with parameters"""
        dialog = AnalysisDialog("AC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "AC Sweep"
                self.analysis_params = params
                statusBar = self.statusBar()
                if statusBar is not None:
                    statusBar.showMessage(
                        f"Analysis: AC Sweep ({params['fStart']}Hz to {params['fStop']}Hz, {params['points']} pts/decade)",
                        3000
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters",
                                    "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_transient(self):
        """Set analysis type to Transient with parameters"""
        dialog = AnalysisDialog("Transient", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "Transient"
                self.analysis_params = params
                statusBar = self.statusBar()
                if statusBar is not None:
                    statusBar.showMessage(
                        f"Analysis: Transient (duration: {params['duration']}s, step: {params['step']}s)",
                        3000
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters",
                                    "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def save_circuit_quick(self):
        """Quick save to current file"""
        if self.current_file:
            try:
                data = self.canvas.to_dict()
                with open(self.current_file, 'w') as f:
                    json.dump(data, f, indent=2)
                statusBar = self.statusBar()
                if statusBar is None:
                    return
                statusBar.showMessage(f"Saved to {self.current_file}", 3000)
            except (OSError, TypeError) as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save: {str(e)}")
        else:
            self.save_circuit()

    def save_circuit(self):
        """Save circuit to JSON file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Circuit", "", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                data = self.canvas.to_dict()
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                self.current_file = filename
                self.setWindowTitle(f"Circuit Design GUI - {filename}")
                self._save_session(filename)  # Save session on successful save
                QMessageBox.information(
                    self, "Success", "Circuit saved successfully!")
            except (OSError, TypeError) as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save: {str(e)}")

    def load_circuit(self, filename=None, is_reload=False):
        """Load circuit from JSON file"""
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Circuit", "", "JSON Files (*.json);;All Files (*)"
            )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                self.canvas.from_dict(data)
                self.current_file = filename
                self.setWindowTitle(f"Circuit Design GUI - {filename}")

                # Save the successfully loaded file path
                self._save_session(filename)

                if not is_reload:
                    QMessageBox.information(
                        self, "Success", "Circuit loaded successfully!")
            except json.JSONDecodeError:
                QMessageBox.critical(
                    self, "Invalid File",
                    "This file is not valid JSON. It may be corrupted or "
                    "is not a valid SDM Spice circuit file.")
            except ValueError as e:
                QMessageBox.critical(
                    self, "Invalid Circuit File",
                    f"This file appears to be corrupted or is not a valid "
                    f"SDM Spice circuit file.\n\nDetails: {e}")
            except (OSError, KeyError, TypeError, AttributeError) as e:
                logger.error("Failed to load circuit: %s", e, exc_info=True)
                QMessageBox.critical(
                    self, "Error", f"Failed to load: {str(e)}")

    def export_image(self):
        """Export the circuit diagram as a PNG or SVG image."""
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Image", "",
            "PNG Image (*.png);;SVG Image (*.svg)"
        )
        if not filename:
            return

        scene = self.canvas.scene

        # Compute bounding rect of circuit items (excluding grid)
        from .component_item import ComponentItem
        from .wire_item import WireItem
        from .annotation_item import AnnotationItem
        circuit_items = [
            item for item in scene.items()
            if isinstance(item, (ComponentItem, WireItem, AnnotationItem))
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

        if filename.lower().endswith('.svg'):
            from PyQt6.QtSvg import QSvgGenerator
            from PyQt6.QtCore import QSize
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
            from PyQt6.QtGui import QImage, QPainter
            from PyQt6.QtCore import Qt
            scale = 2  # 2x resolution for crisp output
            width = int(source_rect.width() * scale)
            height = int(source_rect.height() * scale)
            image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.white)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            from PyQt6.QtCore import QRectF
            target_rect = QRectF(0, 0, width, height)
            scene.render(painter, target=target_rect, source=source_rect)
            painter.end()
            image.save(filename)

        QMessageBox.information(self, "Export Image", f"Circuit exported to:\n{filename}")

    def clear_canvas(self):
        """Clear the canvas"""
        reply = QMessageBox.question(
            self, "Clear Canvas",
            "Are you sure you want to clear the canvas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_circuit()

    def generate_netlist(self):
        """Generate SPICE netlist"""
        try:
            netlist = self.create_netlist()
            self.results_text.setPlainText("SPICE Netlist:\n\n" + netlist)
        except (ValueError, KeyError, TypeError) as e:
            QMessageBox.critical(
                self, "Error", f"Failed to generate netlist: {str(e)}")

    def create_netlist(self, wrdata_filepath=None):
        '''Create SPICE netlist from circuit'''
        from simulation import NetlistGenerator
        nodes, terminal_to_node = self.canvas.get_model_nodes_and_terminal_map()
        kwargs = dict(
            components=self.canvas.get_model_components(),
            wires=self.canvas.get_model_wires(),
            nodes=nodes,
            terminal_to_node=terminal_to_node,
            analysis_type=self.analysis_type,
            analysis_params=self.analysis_params,
        )
        if wrdata_filepath is not None:
            kwargs['wrdata_filepath'] = wrdata_filepath
        generator = NetlistGenerator(**kwargs)
        return generator.generate()

    def run_simulation(self):
        '''Run SPICE simulation using ngspice'''
        try:
            # Validate circuit before simulation
            from simulation import validate_circuit
            is_valid, errors, warnings = validate_circuit(
                self.canvas.get_model_components(),
                self.canvas.get_model_wires(),
                self.analysis_type
            )
            if not is_valid:
                self.results_text.setPlainText(
                    "CIRCUIT VALIDATION FAILED\n" + "=" * 40 + "\n\n"
                    + "\n".join(f"  - {e}" for e in errors)
                )
                if warnings:
                    self.results_text.append(
                        "\nWarnings:\n" + "\n".join(f"  - {w}" for w in warnings)
                    )
                return

            # Generate timestamped wrdata path for transient results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            wrdata_filepath = os.path.join(
                self.ngspice_runner.output_dir, f"wrdata_{timestamp}.txt"
            )

            netlist = self.create_netlist(wrdata_filepath=wrdata_filepath)

            self.results_text.setPlainText("Running ngspice simulation...")

            ngspice_path = self.ngspice_runner.find_ngspice()
            if ngspice_path is None:
                self.results_text.append("\nERROR: ngspice not found!\n")
                self.results_text.append("Please install ngspice:")
                self.results_text.append(
                    "- Windows: http://ngspice.sourceforge.net/download.html")
                self.results_text.append(
                    "- Linux: sudo apt-get install ngspice")
                self.results_text.append("- Mac: brew install ngspice")
                return

            self.results_text.append(f"Found ngspice: {ngspice_path}")

            success, output_file, stdout, stderr = self.ngspice_runner.run_simulation(
                netlist)

            if not success:
                self.results_text.append("ERROR: Simulation failed!\n")
                if stderr:
                    self.results_text.append(f"Error: {stderr}")
                if stdout:
                    self.results_text.append(f"Output: {stdout}")
                return

            # For transient analysis, the `wrdata` command in the netlist creates
            # a clean data file. We parse that directly for reliability.
            if self.analysis_type == "Transient":
                self._display_formatted_results(None, wrdata_filepath, is_wrdata=True)
            else:
                # For other analysis types, parse the stdout dump.
                output = self.ngspice_runner.read_output(output_file)
                self._display_formatted_results(output, output_file, is_wrdata=False)

        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as e:
            logger.error("Simulation failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "Error", f"Simulation failed: {str(e)}")

    def _display_formatted_results(self, output, filepath, is_wrdata=False):
        """Format and display simulation results based on analysis type"""
        from simulation import ResultParser
        self._last_results = None
        self._last_results_type = self.analysis_type
        self.btn_export_csv.setEnabled(False)

        self.results_text.setPlainText("\n" + "=" * 70 + "")
        self.results_text.append(f"SIMULATION COMPLETE - {self.analysis_type}")
        self.results_text.append("=" * 70 + "")

        if self.analysis_type == "DC Operating Point":
            # Parse and display operating point results
            node_voltages = ResultParser.parse_op_results(output)

            if node_voltages:
                self._last_results = node_voltages
                self.results_text.append("\nNODE VOLTAGES:")
                self.results_text.append("-" * 40 + "")
                for node, voltage in sorted(node_voltages.items()):
                    self.results_text.append(f"  {node:15s} : {voltage:12.6f} V")

                self.canvas.set_node_voltages(node_voltages)
                self.results_text.append("-" * 40 + "")
            else:
                self.results_text.append("\nNo node voltages found in output.")
                self.canvas.clear_node_voltages()

        elif self.analysis_type == "DC Sweep":
            # Parse and display DC sweep results
            sweep_data = ResultParser.parse_dc_results(output)
            if sweep_data:
                self._last_results = sweep_data
                self.results_text.append("\nDC SWEEP RESULTS:")
                self.results_text.append("-" * 40 + "")
                self.results_text.append(str(sweep_data) + "")
            else:
                self.results_text.append("\nDC Sweep data - see raw output below")
            self.canvas.clear_node_voltages()

        elif self.analysis_type == "AC Sweep":
            # Parse and display AC sweep results
            ac_data = ResultParser.parse_ac_results(output)
            if ac_data:
                self._last_results = ac_data
                self.results_text.append("\nAC SWEEP RESULTS:")
                self.results_text.append("-" * 40 + "")
                self.results_text.append(str(ac_data) + "")
            else:
                self.results_text.append("\nAC Sweep data - see raw output below")
            self.canvas.clear_node_voltages()

        elif self.analysis_type == "Transient":
            # Parse and display transient results
            if is_wrdata:
                tran_data = ResultParser.parse_transient_results(filepath)
            else:
                tran_data = ResultParser.parse_transient_results(output)

            if tran_data:
                self._last_results = tran_data
                self.results_text.append("\nTRANSIENT ANALYSIS RESULTS:")

                # Format and display the table in the text area
                table_string = ResultParser.format_results_as_table(tran_data)
                self.results_text.append(table_string)

                self.results_text.append("\n" + "-" * 40 + "")
                self.results_text.append("Waveform plot has also been generated in a new window.")

                # Clean up previous waveform dialog if it exists
                if hasattr(self, 'waveform_dialog') and self.waveform_dialog is not None:
                    self.waveform_dialog.close()
                    self.waveform_dialog.deleteLater()

                # Show waveform plot
                self.waveform_dialog = WaveformDialog(tran_data, self)
                self.waveform_dialog.show()
            else:
                self.results_text.append("\nNo transient data found in output.")
            self.canvas.clear_node_voltages()

        self.results_text.append("=" * 70 + "")

        if self._last_results is not None:
            self.btn_export_csv.setEnabled(True)

    def export_results_csv(self):
        """Export the last simulation results to a CSV file."""
        if self._last_results is None:
            return

        from simulation.csv_exporter import (
            export_op_results, export_dc_sweep_results,
            export_ac_results, export_transient_results, write_csv,
        )

        circuit_name = os.path.basename(self.current_file) if self.current_file else ""

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

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Results to CSV", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                write_csv(csv_content, filename)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(f"Results exported to {filename}", 3000)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def on_component_right_clicked(self, component, event_pos):
        """Handle right-click on a component."""
        if component:
            self.properties_panel.show_component(component)
            self.properties_stack.setCurrentIndex(1)  # Show properties
        else:
            self.properties_stack.setCurrentIndex(0)  # Show blank

    def on_canvas_clicked(self):
        """Handle click on an empty canvas area."""
        self.properties_stack.setCurrentIndex(0)  # Show blank
        self.properties_panel.show_no_selection()

    def on_property_changed(self, component_id, property_name, new_value):
        """Handle property changes from properties panel"""
        # Find the component
        component = self.canvas.components.get(component_id)
        if not component:
            return

        if property_name == 'value':
            # Update component value
            component.value = new_value
            component.update()
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Updated {component_id} value to {new_value}", 2000)

        elif property_name == 'rotation':
            component.rotation_angle = new_value
            component.update_terminals()
            component.update()

            # Reroute connected wires
            self.canvas.reroute_connected_wires(component)

            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Rotated {component_id} to {new_value}°", 2000)

            # Update the properties panel to reflect the change
            self.properties_panel.show_component(component)

        elif property_name == 'waveform':
            # Waveform changes are applied directly by PropertiesPanel
            component.update()
            statusBar = self.statusBar()
            if statusBar:
                statusBar.showMessage(f"Updated {component_id} waveform configuration", 2000)
