from PyQt6.QtWidgets import (
    QVBoxLayout, QDialog, QFormLayout, QLineEdit, 
    QDialogButtonBox, QComboBox, QLabel
)
from .format_utils import parse_value


class AnalysisDialog(QDialog):
    """Enhanced dialog for configuring analysis parameters"""

    # Tooltips for analysis parameter fields (keyed by field key)
    FIELD_TOOLTIPS = {
        'source': 'Name of the voltage source to sweep (e.g., V1)',
        'min': 'Starting voltage for the DC sweep in volts',
        'max': 'Ending voltage for the DC sweep in volts',
        'step': 'Increment between each sweep point',
        'fStart': 'Starting frequency for the sweep in Hz',
        'fStop': 'Ending frequency for the sweep in Hz',
        'points': 'Number of frequency samples per 10x frequency range',
        'sweepType': 'Frequency scale: dec (decade), oct (octave), or lin (linear)',
        'duration': 'Total simulation time (use SI suffixes: 10m = 10 ms)',
        'startTime': 'Time at which to begin recording results',
    }

    # Analysis type configurations
    ANALYSIS_CONFIGS = {
        "DC Operating Point": {
            "fields": [],
            "description": "Calculate DC operating point of the circuit"
        },
        "DC Sweep": {
            "fields": [
                ("Source", "source", "text", "V1"),
                ("Start Voltage (V)", "min", "float", "0"),
                ("Stop Voltage (V)", "max", "float", "10"),
                ("Step Size (V)", "step", "float", "0.1")
            ],
            "description": "Sweep a voltage source and measure circuit response"
        },
        "AC Sweep": {
            "fields": [
                ("Start Frequency (Hz)", "fStart", "float", "1"),
                ("Stop Frequency (Hz)", "fStop", "float", "1e6"),
                ("Points per Decade", "points", "int", "100"),
                ("Sweep Type", "sweepType", "combo", ["dec", "oct", "lin"], "dec")
            ],
            "description": "Frequency domain analysis"
        },
        "Transient": {
            "fields": [
                ("Stop Time (e.g., 10m, 100u)", "duration", "float", "10m"),
                ("Time Step (e.g., 1u, 10n)", "step", "float", "10u"),
                ("Start Time", "startTime", "float", "0")
            ],
            "description": "Time domain analysis"
        }
    }
    
    def __init__(self, analysis_type=None, parent=None):
        super().__init__(parent)
        self.analysis_type = analysis_type
        self.field_widgets = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Analysis type selector (if not provided)
        if self.analysis_type is None:
            self.type_combo = QComboBox()
            self.type_combo.addItems(self.ANALYSIS_CONFIGS.keys())
            self.type_combo.setToolTip("Select the type of circuit analysis to run")
            self.type_combo.currentTextChanged.connect(self._on_type_changed)
            layout.addWidget(QLabel("Analysis Type:"))
            layout.addWidget(self.type_combo)
            self.analysis_type = self.type_combo.currentText()
        
        # Description label
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # Form layout for parameters
        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)
        
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

            tooltip = self.FIELD_TOOLTIPS.get(key, '')
            if tooltip:
                widget.setToolTip(tooltip)

            self.field_widgets[key] = (widget, field_type)
            self.form_layout.addRow(f"{label}:", widget)
    
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

        return ""