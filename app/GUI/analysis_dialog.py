from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .format_utils import parse_value


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
    }

    def __init__(self, analysis_type=None, parent=None, preset_manager=None):
        super().__init__(parent)
        self.analysis_type = analysis_type
        self.field_widgets = {}
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

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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

        return ""

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

        preset = self._preset_manager.get_preset_by_name(preset_name, self.analysis_type)
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
            QMessageBox.warning(self, "Invalid Parameters", "Please enter valid parameters before saving a preset.")
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

        preset = self._preset_manager.get_preset_by_name(preset_name, self.analysis_type)
        if preset and preset.get("builtin"):
            QMessageBox.information(self, "Built-in Preset", "Built-in presets cannot be deleted.")
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
        preset = self._preset_manager.get_preset_by_name(preset_name, self.analysis_type)
        self.delete_preset_btn.setEnabled(preset is not None and not preset.get("builtin", False))
