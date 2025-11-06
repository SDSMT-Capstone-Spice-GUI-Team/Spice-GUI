from simulation import NetlistGenerator, NgspiceRunner, ResultParser
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QMessageBox, QTextEdit,
                             QSplitter, QLabel, QDialog)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt
from .component_palette import ComponentPalette
from .circuit_canvas import CircuitCanvas
from .analysis_dialog import AnalysisDialog

# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
}

GRID_SIZE = 20


class CircuitDesignGUI(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Design GUI - Student Prototype")
        self.setGeometry(100, 100, 1200, 800)
        self.current_file = None

        # Analysis settings
        self.analysis_type = "Operational Point"
        self.analysis_params = {}

        # Initialize ngspice runner
        self.ngspice_runner = NgspiceRunner()

        self.init_ui()
        self.create_menu_bar()

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel - Component palette
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Component Palette"))
        # our palette is not an actual Qt palette item
        # self.palette = ComponentPalette()
        # left_panel.addWidget(self.palette)
        left_panel.addWidget(ComponentPalette())

        # Instructions
        instructions = QLabel(
            "📦 Drag components from palette to canvas\n"
            "🔌 Left-click terminal → click another terminal to wire\n"
            "🖱️ Drag components to move (wires follow!)\n"
            "🔄 Press R to rotate selected\n"
            "🗑️ Right-click for context menu\n"
            "⌫ Delete key to remove selected\n"
            "\n"
            "Wires auto-route using A* path finding!"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }")
        left_panel.addWidget(instructions)

        main_layout.addLayout(left_panel, 1)

        # Center - Canvas and results
        center_splitter = QSplitter(Qt.Orientation.Vertical)

        # Canvas
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.addWidget(
            QLabel("Circuit Canvas (Grid-Aligned Routing)"))
        self.canvas = CircuitCanvas()
        canvas_layout.addWidget(self.canvas)
        center_splitter.addWidget(canvas_widget)

        # Results display
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.addWidget(QLabel("Simulation Results"))
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        center_splitter.addWidget(results_widget)

        center_splitter.setSizes([500, 300])
        main_layout.addWidget(center_splitter, 3)

        # Right panel - Controls
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Actions"))

        # File operations
        self.btn_save = QPushButton("Save Circuit")
        self.btn_save.clicked.connect(self.save_circuit)
        right_panel.addWidget(self.btn_save)

        self.btn_load = QPushButton("Load Circuit")
        self.btn_load.clicked.connect(self.load_circuit)
        right_panel.addWidget(self.btn_load)

        self.btn_clear = QPushButton("Clear Canvas")
        self.btn_clear.clicked.connect(self.clear_canvas)
        right_panel.addWidget(self.btn_clear)

        right_panel.addWidget(QLabel(""))  # Spacer

        # Simulation operations
        self.btn_netlist = QPushButton("Generate Netlist")
        self.btn_netlist.clicked.connect(self.generate_netlist)
        right_panel.addWidget(self.btn_netlist)

        self.btn_simulate = QPushButton("Run Simulation")
        self.btn_simulate.clicked.connect(self.run_simulation)
        right_panel.addWidget(self.btn_simulate)

        right_panel.addStretch()
        main_layout.addLayout(right_panel, 1)

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

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        if edit_menu is None:
            return

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

        op_action = QAction("&Operational Point (.op)", self)
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
        """Set analysis type to Operational Point"""
        self.analysis_type = "Operational Point"
        self.analysis_params = {}
        statusbar = self.statusBar()
        if statusbar is None:
            print("status bar is missing function showMessage()")
        else:
            statusbar.showMessage("Analysis: Operational Point (.op)", 3000)

    def set_analysis_dc(self):
        """Set analysis type to DC Sweep with parameters"""
        dialog = AnalysisDialog("DC Sweep", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.analysis_type = "DC Sweep"
                self.analysis_params = params
                statusBar = self.statusBar()
                if statusBar is None:
                    print("status bar is missing function showMessage()")
                else:
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
                if statusBar is None:
                    print("status bar is missing function showMessage()")
                else:
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
                if statusBar is None:
                    print("status bar is missing function showMessage()")
                else:
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
            except Exception as e:
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
                QMessageBox.information(
                    self, "Success", "Circuit saved successfully!")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save: {str(e)}")

    def load_circuit(self):
        """Load circuit from JSON file"""
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
                QMessageBox.information(
                    self, "Success", "Circuit loaded successfully!")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load: {str(e)}")

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
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to generate netlist: {str(e)}")

    def create_netlist(self):
        '''Create SPICE netlist from circuit'''
        generator = NetlistGenerator(
            components=self.canvas.components,
            wires=self.canvas.wires,
            nodes=self.canvas.nodes,
            terminal_to_node=self.canvas.terminal_to_node,
            analysis_type=self.analysis_type,
            analysis_params=self.analysis_params
        )
        return generator.generate()

    def run_simulation(self):
        '''Run SPICE simulation using ngspice'''
        try:
            netlist = self.create_netlist()

            self.results_text.setPlainText("Running ngspice simulation...\n\n")

            ngspice_path = self.ngspice_runner.find_ngspice()
            if ngspice_path is None:
                self.results_text.append("ERROR: ngspice not found!\n\n")
                self.results_text.append("Please install ngspice:\n")
                self.results_text.append(
                    "- Windows: http://ngspice.sourceforge.net/download.html\n")
                self.results_text.append(
                    "- Linux: sudo apt-get install ngspice\n")
                self.results_text.append("- Mac: brew install ngspice\n")
                return

            self.results_text.append(f"Found ngspice at: {ngspice_path}\n\n")

            success, output_file, stdout, stderr = self.ngspice_runner.run_simulation(
                netlist)

            if not success:
                self.results_text.append("ERROR: Simulation failed!\n\n")
                if stderr:
                    self.results_text.append(f"Error: {stderr}\n")
                if stdout:
                    self.results_text.append(f"Output: {stdout}\n")
                return

            output = self.ngspice_runner.read_output(output_file)

            self.results_text.append(f"Simulation complete!\n")
            self.results_text.append(f"Output saved to: {output_file}\n")
            self.results_text.append("="*60 + "\n")
            self.results_text.append("Simulation Results:\n")
            self.results_text.append("="*60 + "\n\n")
            self.results_text.append(output)

            if self.analysis_type == "Operational Point":
                node_voltages = ResultParser.parse_op_results(output)
                if node_voltages:
                    self.canvas.set_node_voltages(node_voltages)
                    self.results_text.append("\n" + "="*60 + "\n")
                    self.results_text.append(
                        "Node voltages displayed on canvas\n")
                else:
                    self.canvas.clear_node_voltages()
            else:
                self.canvas.clear_node_voltages()

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Simulation failed: {str(e)}")
            import traceback
            self.results_text.append(
                f"\n\nError details:\n{traceback.format_exc()}")
