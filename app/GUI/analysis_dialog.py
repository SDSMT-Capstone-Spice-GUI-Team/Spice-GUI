from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QVBoxLayout)

from .format_utils import parse_value
from .meas_dialog import ANALYSIS_DOMAIN_MAP, MeasurementDialog

# Analysis types that support .meas directives
_MEAS_SUPPORTED_TYPES = set(ANALYSIS_DOMAIN_MAP.keys())


class AnalysisDialog(QDialog):
    """Enhanced dialog for configuring analysis parameters with preset support"""

    # Analysis type configurations
    ANALYSIS_CONFIGS = {
        "DC Operating Point": {
            "fields": [],
            "description": "Calculate DC operating point of the circuit",
            "tooltips": {},
        },
        "DC Sweep": {
            "fields": [
                ("Source", "source", "text", "V1"),
                ("Start Voltage (V)", "min", "float", "0"),
                ("Stop Voltage (V)", "max", "float", "10"),
                ("Step Size (V)", "step", "float", "0.1"),
            ],
            "description": "Sweep a voltage source and measure circuit response",
            "tooltips": {
                "source": "Name of the voltage source to sweep (e.g., V1)",
                "min": "Starting voltage for the DC sweep (V)",
                "max": "Ending voltage for the DC sweep (V)",
                "step": "Voltage increment between sweep points (V)",
            },
        },
        "AC Sweep": {
            "fields": [
                ("Start Frequency (Hz)", "fStart", "float", "1"),
                ("Stop Frequency (Hz)", "fStop", "float", "1e6"),
                ("Points per Decade", "points", "int", "100"),
                ("Sweep Type", "sweepType", "combo", ["dec", "oct", "lin"], "dec"),
            ],
            "description": "Frequency domain analysis",
            "tooltips": {
                "fStart": "Starting frequency for the AC sweep (Hz)",
                "fStop": "Ending frequency for the AC sweep (Hz)",
                "points": "Number of frequency points per decade (log scale)",
                "sweepType": "Frequency scale: dec (decade/log), oct (octave), lin (linear)",
            },
        },
        "Transient": {
            "fields": [
                ("Stop Time (e.g., 10m, 100u)", "duration", "float", "10m"),
                ("Time Step (e.g., 1u, 10n)", "step", "float", "10u"),
                ("Start Time", "startTime", "float", "0"),
            ],
            "description": "Time domain analysis",
            "tooltips": {
                "duration": "Total simulation time (supports SI prefixes: 10m = 10 ms, 100u = 100 \u00b5s)",
                "step": "Maximum time step for the simulation (supports SI prefixes: 1u = 1 \u00b5s)",
                "startTime": "Time at which to start recording output data (default: 0)",
            },
        },
        "Temperature Sweep": {
            "fields": [
                ("Start Temperature (\u00b0C)", "tempStart", "float", "-40"),
                ("Stop Temperature (\u00b0C)", "tempStop", "float", "85"),
                ("Step Size (\u00b0C)", "tempStep", "float", "25"),
            ],
            "description": (
                "Sweep temperature and run a DC operating point analysis "
                "at each temperature to see how circuit behavior changes"
            ),
            "tooltips": {
                "tempStart": "Starting temperature in degrees Celsius",
                "tempStop": "Ending temperature in degrees Celsius",
                "tempStep": "Temperature increment between sweep points (\u00b0C)",
            },
        },
        "Noise": {
            "fields": [
                ("Output Node", "output_node", "text", "out"),
                ("Input Source", "source", "text", "V1"),
                ("Start Frequency (Hz)", "fStart", "float", "1"),
                ("Stop Frequency (Hz)", "fStop", "float", "1e6"),
                ("Points per Decade", "points", "int", "100"),
                ("Sweep Type", "sweepType", "combo", ["dec", "oct", "lin"], "dec"),
            ],
            "description": (
                "Noise spectral density analysis — computes output and input-referred noise vs. frequency"
            ),
            "tooltips": {
                "output_node": "Node name (or number) where output noise is measured, e.g. 'out' or '2'",
                "source": "Name of the input source used as noise reference (e.g. V1)",
                "fStart": "Starting frequency for the noise sweep (Hz)",
                "fStop": "Ending frequency for the noise sweep (Hz)",
                "points": "Number of frequency points per decade (log scale)",
                "sweepType": "Frequency scale: dec (decade/log), oct (octave), lin (linear)",
            },
        },
        "Sensitivity": {
            "fields": [
                ("Output Node", "output_node", "text", "out"),
            ],
            "description": (
                "DC sensitivity analysis — shows how much each component value "
                "affects the selected output voltage. Useful for identifying the "
                "most critical components in your circuit."
            ),
            "tooltips": {
                "output_node": (
                    "Node name (or number) to analyze, e.g. 'out' or '2'. "
                    "The analysis computes dV(node)/d(parameter) for every component."
                ),
            },
        },
        "Transfer Function": {
            "fields": [
                ("Output Variable", "output_var", "text", "v(out)"),
                ("Input Source", "input_source", "text", "V1"),
            ],
            "description": (
                "Small-signal DC transfer function — computes voltage gain (or "
                "transresistance), input impedance, and output impedance"
            ),
            "tooltips": {
                "output_var": "Output variable: v(node) for voltage gain or i(Vname) for transresistance",
                "input_source": "Name of the independent source to vary (e.g. V1, I1)",
            },
        },
        "Pole-Zero": {
            "fields": [
                ("Input Node (+)", "input_pos", "text", "1"),
                ("Input Node (-)", "input_neg", "text", "0"),
                ("Output Node (+)", "output_pos", "text", "2"),
                ("Output Node (-)", "output_neg", "text", "0"),
                ("Transfer Type", "transfer_type", "combo", ["vol", "cur"], "vol"),
                ("Analysis", "pz_type", "combo", ["pz", "pol", "zer"], "pz"),
            ],
            "description": (
                "Pole-Zero analysis — computes poles and zeros of the circuit "
                "transfer function for stability and frequency response analysis"
            ),
            "tooltips": {
                "input_pos": "Positive input port node (number or name)",
                "input_neg": "Negative input port node (number or name, 0 for ground)",
                "output_pos": "Positive output port node (number or name)",
                "output_neg": "Negative output port node (number or name, 0 for ground)",
                "transfer_type": "Transfer type: vol (voltage gain) or cur (current gain)",
                "pz_type": "Analysis scope: pz (poles and zeros), pol (poles only), zer (zeros only)",
            },
        },
    }

    def __init__(self, analysis_type=None, parent=None, preset_manager=None):
        super().__init__(parent)
        self.analysis_type = analysis_type
        self.field_widgets = {}
        self._measurements = []  # list of measurement entry dicts
        if preset_manager is None:
            from simulation.preset_manager import PresetManager

            preset_manager = PresetManager()
        self._preset_manager = preset_manager
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)

        # Analysis type selector (if not provided)
        if self.analysis_type is None:
            self.type_combo = QComboBox()
            self.type_combo.setToolTip("Select the type of circuit analysis to perform")
            self.type_combo.addItems(self.ANALYSIS_CONFIGS.keys())
            self.type_combo.currentTextChanged.connect(self._on_type_changed)
            layout.addWidget(QLabel("Analysis Type:"))
            layout.addWidget(self.type_combo)
            self.analysis_type = self.type_combo.currentText()

        # Description label
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # --- Preset controls ---
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("Load a saved parameter preset")
        self.preset_combo.setMinimumWidth(180)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo, 1)

        self.save_preset_btn = QPushButton("Save")
        self.save_preset_btn.setToolTip("Save current parameters as a preset")
        self.save_preset_btn.clicked.connect(self._save_preset)
        preset_layout.addWidget(self.save_preset_btn)

        self.delete_preset_btn = QPushButton("Delete")
        self.delete_preset_btn.setToolTip("Delete the selected preset")
        self.delete_preset_btn.clicked.connect(self._delete_preset)
        preset_layout.addWidget(self.delete_preset_btn)

        layout.addLayout(preset_layout)

        # Form layout for parameters
        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)

        # Measurements button (shown only for supported analysis types)
        meas_layout = QHBoxLayout()
        self.meas_btn = QPushButton("Measurements...")
        self.meas_btn.setToolTip(
            "Configure automated .meas directives for this analysis"
        )
        self.meas_btn.clicked.connect(self._open_meas_dialog)
        meas_layout.addWidget(self.meas_btn)
        self.meas_label = QLabel("No measurements configured")
        self.meas_label.setStyleSheet("color: gray;")
        meas_layout.addWidget(self.meas_label, 1)
        layout.addLayout(meas_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Build initial form
        self._build_form()

    def _on_type_changed(self, analysis_type):
        """Handle analysis type change"""
        self.analysis_type = analysis_type
        self._build_form()

    def _build_form(self):
        """Build form based on analysis type"""
        # Clear existing form
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.field_widgets.clear()

        # Set window title and description
        self.setWindowTitle(f"{self.analysis_type} Parameters")
        config = self.ANALYSIS_CONFIGS[self.analysis_type]
        self.desc_label.setText(config["description"])

        # Build fields
        tooltips = config.get("tooltips", {})
        for field_config in config["fields"]:
            # Unpack based on field type
            if field_config[2] == "combo":  # (label, key, "combo", options, default)
                label, key, field_type, options, default = field_config
                widget = QComboBox()
                widget.addItems(options)
                widget.setCurrentText(default)
            else:  # (label, key, type, default)
                label, key, field_type, default = field_config
                widget = QLineEdit(str(default))

            tooltip = tooltips.get(key)
            if tooltip:
                widget.setToolTip(tooltip)

            self.field_widgets[key] = (widget, field_type)
            self.form_layout.addRow(f"{label}:", widget)

        # Show/hide measurements button based on analysis type
        meas_visible = self.analysis_type in _MEAS_SUPPORTED_TYPES
        self.meas_btn.setVisible(meas_visible)
        self.meas_label.setVisible(meas_visible)
        if not meas_visible:
            self._measurements.clear()
        self._update_meas_label()

        # Refresh preset dropdown for this analysis type
        self._refresh_preset_combo()

    def get_parameters(self):
        """Get parameters from dialog with validation"""
        params = {"analysis_type": self.analysis_type}

        try:
            for key, (widget, field_type) in self.field_widgets.items():
                if field_type == "combo":
                    params[key] = widget.currentText()
                elif field_type == "float":
                    params[key] = parse_value(widget.text())
                elif field_type == "int":
                    params[key] = int(parse_value(widget.text()))
                else:  # text
                    params[key] = widget.text()

            # Include measurement directives if any are configured
            if self._measurements:
                params["measurements"] = [
                    e["directive"] for e in self._measurements if e.get("directive")
                ]

            return params

        except ValueError:
            return None

    def get_ngspice_command(self):
        """Generate NGSPICE command from parameters"""
        params = self.get_parameters()
        if params is None:
            return None

        if self.analysis_type == "DC Operating Point":
            return ".op"

        elif self.analysis_type == "DC Sweep":
            source = params.get("source", "V1")
            start = params.get("min", 0)
            stop = params.get("max", 10)
            step = params.get("step", 0.1)
            return f".dc {source} {start} {stop} {step}"

        elif self.analysis_type == "AC Sweep":
            fstart = params.get("fStart", 1)
            fstop = params.get("fStop", 1e6)
            points = params.get("points", 100)
            sweep_type = params.get("sweepType", "dec")
            return f".ac {sweep_type} {points} {fstart} {fstop}"

        elif self.analysis_type == "Transient":
            tstep = params.get("step", 0.001)
            tstop = params.get("duration", 1)
            tstart = params.get("startTime", 0)
            return f".tran {tstep} {tstop} {tstart}"

        elif self.analysis_type == "Temperature Sweep":
            tstart = params.get("tempStart", -40)
            tstop = params.get("tempStop", 85)
            tstep = params.get("tempStep", 25)
            return f".step temp {tstart} {tstop} {tstep}"

        elif self.analysis_type == "Noise":
            output = params.get("output_node", "out")
            source = params.get("source", "V1")
            fstart = params.get("fStart", 1)
            fstop = params.get("fStop", 1e6)
            points = params.get("points", 100)
            sweep_type = params.get("sweepType", "dec")
            return f".noise v({output}) {source} {sweep_type} {points} {fstart} {fstop}"

        elif self.analysis_type == "Sensitivity":
            output = params.get("output_node", "out")
            return f".sens v({output})"

        elif self.analysis_type == "Transfer Function":
            output_var = params.get("output_var", "v(out)")
            input_source = params.get("input_source", "V1")
            return f".tf {output_var} {input_source}"

        elif self.analysis_type == "Pole-Zero":
            inp = params.get("input_pos", "1")
            inn = params.get("input_neg", "0")
            outp = params.get("output_pos", "2")
            outn = params.get("output_neg", "0")
            tf_type = params.get("transfer_type", "vol")
            pz_type = params.get("pz_type", "pz")
            return f".pz {inp} {inn} {outp} {outn} {tf_type} {pz_type}"

        return ""

    # --- Measurement management ---

    def _open_meas_dialog(self):
        """Open the measurement configuration dialog."""
        domain = ANALYSIS_DOMAIN_MAP.get(self.analysis_type, "tran")
        dialog = MeasurementDialog(
            domain=domain,
            parent=self,
            measurements=self._measurements,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._measurements = dialog.get_entries()
            self._update_meas_label()

    def _update_meas_label(self):
        """Update the label showing measurement count."""
        count = len(self._measurements)
        if count == 0:
            self.meas_label.setText("No measurements configured")
            self.meas_label.setStyleSheet("color: gray;")
        elif count == 1:
            self.meas_label.setText("1 measurement configured")
            self.meas_label.setStyleSheet("")
        else:
            self.meas_label.setText(f"{count} measurements configured")
            self.meas_label.setStyleSheet("")

    # --- Preset management ---

    def _refresh_preset_combo(self):
        """Rebuild the preset dropdown for the current analysis type."""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("(none)")

        presets = self._preset_manager.get_presets(self.analysis_type)
        for p in presets:
            suffix = " [built-in]" if p.get("builtin") else ""
            self.preset_combo.addItem(f"{p['name']}{suffix}", p["name"])

        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        self._update_delete_button()

    def _on_preset_selected(self, index):
        """Load the selected preset into the form fields."""
        if index <= 0:
            self._update_delete_button()
            return

        preset_name = self.preset_combo.itemData(index)
        if preset_name is None:
            return

        preset = self._preset_manager.get_preset_by_name(
            preset_name, self.analysis_type
        )
        if preset is None:
            return

        self._apply_preset_params(preset["params"])
        self._update_delete_button()

    def _apply_preset_params(self, params):
        """Set form widget values from a params dict."""
        for key, (widget, field_type) in self.field_widgets.items():
            if key not in params:
                continue
            value = params[key]
            if field_type == "combo":
                widget.setCurrentText(str(value))
            else:
                widget.setText(str(value))

    def _save_preset(self):
        """Save current parameters as a named preset."""
        params = self.get_parameters()
        if params is None:
            QMessageBox.warning(
                self,
                "Invalid Parameters",
                "Please enter valid parameters before saving a preset.",
            )
            return

        # Remove analysis_type key from params (stored separately)
        save_params = {k: v for k, v in params.items() if k != "analysis_type"}

        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return

        name = name.strip()
        try:
            self._preset_manager.save_preset(name, self.analysis_type, save_params)
            self._refresh_preset_combo()
            # Select the newly saved preset
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == name:
                    self.preset_combo.setCurrentIndex(i)
                    break
        except ValueError as e:
            QMessageBox.warning(self, "Cannot Save", str(e))

    def _delete_preset(self):
        """Delete the currently selected user preset."""
        index = self.preset_combo.currentIndex()
        if index <= 0:
            return

        preset_name = self.preset_combo.itemData(index)
        if preset_name is None:
            return

        preset = self._preset_manager.get_preset_by_name(
            preset_name, self.analysis_type
        )
        if preset and preset.get("builtin"):
            QMessageBox.information(
                self, "Built-in Preset", "Built-in presets cannot be deleted."
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{preset_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._preset_manager.delete_preset(preset_name, self.analysis_type)
            self._refresh_preset_combo()

    def _update_delete_button(self):
        """Enable/disable the delete button based on selection."""
        index = self.preset_combo.currentIndex()
        if index <= 0:
            self.delete_preset_btn.setEnabled(False)
            return

        preset_name = self.preset_combo.itemData(index)
        preset = self._preset_manager.get_preset_by_name(
            preset_name, self.analysis_type
        )
        self.delete_preset_btn.setEnabled(
            preset is not None and not preset.get("builtin", False)
        )
