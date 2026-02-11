"""
Parameter Sweep Dialog — Configure sweeping a component parameter across a range
of values with a selectable base analysis type.
"""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from .format_utils import format_value, parse_value

# Component types whose primary value can be swept
SWEEPABLE_TYPES = {
    "Resistor",
    "Capacitor",
    "Inductor",
    "Voltage Source",
    "Current Source",
    "VCVS",
    "CCVS",
    "VCCS",
    "CCCS",
}

# Base analysis types available for parameter sweep
BASE_ANALYSIS_TYPES = [
    "DC Operating Point",
    "Transient",
    "AC Sweep",
    "DC Sweep",
]


class ParameterSweepDialog(QDialog):
    """Dialog for configuring a parameter sweep across component values."""

    def __init__(self, components, parent=None):
        """
        Args:
            components: dict of component_id -> ComponentData from the circuit model
            parent: parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Parameter Sweep Configuration")
        self.setMinimumWidth(420)

        # Filter to sweepable components
        self._sweepable = {cid: comp for cid, comp in components.items() if comp.component_type in SWEEPABLE_TYPES}

        self._base_field_widgets = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Description
        desc = QLabel(
            "Sweep a component parameter across a range of values, running the selected analysis at each step."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Sweep Configuration ---
        sweep_group = QGroupBox("Sweep Parameter")
        sweep_form = QFormLayout(sweep_group)

        # Component selector
        self.component_combo = QComboBox()
        self.component_combo.setToolTip("Select a component whose value will be swept")
        if self._sweepable:
            for cid, comp in sorted(self._sweepable.items()):
                self.component_combo.addItem(f"{cid} ({comp.component_type}: {comp.value})", cid)
        else:
            self.component_combo.addItem("(no sweepable components)")
            self.component_combo.setEnabled(False)
        sweep_form.addRow("Component:", self.component_combo)

        # Start / Stop / Steps
        self.start_edit = QLineEdit("1k")
        self.start_edit.setToolTip("Start value (supports SI prefixes: 1k, 100n, etc.)")
        sweep_form.addRow("Start Value:", self.start_edit)

        self.stop_edit = QLineEdit("10k")
        self.stop_edit.setToolTip("Stop value (supports SI prefixes)")
        sweep_form.addRow("Stop Value:", self.stop_edit)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(2, 100)
        self.steps_spin.setValue(10)
        self.steps_spin.setToolTip("Number of sweep steps (2-100)")
        sweep_form.addRow("Number of Steps:", self.steps_spin)

        layout.addWidget(sweep_group)

        # --- Base Analysis Configuration ---
        analysis_group = QGroupBox("Base Analysis")
        analysis_layout = QVBoxLayout(analysis_group)

        self.analysis_combo = QComboBox()
        self.analysis_combo.setToolTip("Analysis type to run at each sweep step")
        self.analysis_combo.addItems(BASE_ANALYSIS_TYPES)
        self.analysis_combo.currentTextChanged.connect(self._on_analysis_changed)
        analysis_layout.addWidget(self.analysis_combo)

        self._base_form = QFormLayout()
        analysis_layout.addLayout(self._base_form)

        layout.addWidget(analysis_group)

        # Build initial base analysis form
        self._build_base_form()

        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Set defaults from first component
        self._update_defaults_from_component()
        self.component_combo.currentIndexChanged.connect(lambda _: self._update_defaults_from_component())

    def _update_defaults_from_component(self):
        """Update start/stop defaults based on selected component's current value."""
        cid = self.component_combo.currentData()
        if cid and cid in self._sweepable:
            comp = self._sweepable[cid]
            try:
                current_val = parse_value(comp.value)
                # Default: sweep from 1/10 to 10x current value
                start = current_val / 10
                stop = current_val * 10
                self.start_edit.setText(format_value(start).strip().replace(" ", ""))
                self.stop_edit.setText(format_value(stop).strip().replace(" ", ""))
            except (ValueError, TypeError):
                pass

    def _on_analysis_changed(self, analysis_type):
        self._build_base_form()

    def _build_base_form(self):
        """Build form fields for the selected base analysis type."""
        # Clear existing
        while self._base_form.count():
            item = self._base_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._base_field_widgets.clear()

        from .analysis_dialog import AnalysisDialog

        analysis_type = self.analysis_combo.currentText()
        config = AnalysisDialog.ANALYSIS_CONFIGS.get(analysis_type, {})

        tooltips = config.get("tooltips", {})
        for field_config in config.get("fields", []):
            if field_config[2] == "combo":
                label, key, _, options, default = field_config
                widget = QComboBox()
                widget.addItems(options)
                widget.setCurrentText(default)
            else:
                label, key, field_type, default = field_config
                widget = QLineEdit(str(default))

            tooltip = tooltips.get(key)
            if tooltip:
                widget.setToolTip(tooltip)

            self._base_field_widgets[key] = (widget, field_config[2])
            self._base_form.addRow(f"{label}:", widget)

    def get_parameters(self):
        """
        Get all sweep parameters.

        Returns:
            dict with keys: component_id, start, stop, num_steps,
                            base_analysis_type, base_params
            or None if validation fails.
        """
        try:
            component_id = self.component_combo.currentData()
            if not component_id:
                return None

            start = parse_value(self.start_edit.text())
            stop = parse_value(self.stop_edit.text())
            num_steps = self.steps_spin.value()

            if start == stop:
                return None

            base_analysis_type = self.analysis_combo.currentText()

            # Parse base analysis params
            base_params = {"analysis_type": base_analysis_type}
            for key, (widget, field_type) in self._base_field_widgets.items():
                if field_type == "combo":
                    base_params[key] = widget.currentText()
                elif field_type == "float":
                    base_params[key] = parse_value(widget.text())
                elif field_type == "int":
                    base_params[key] = int(parse_value(widget.text()))
                else:
                    base_params[key] = widget.text()

            return {
                "component_id": component_id,
                "start": start,
                "stop": stop,
                "num_steps": num_steps,
                "base_analysis_type": base_analysis_type,
                "base_params": base_params,
            }
        except (ValueError, TypeError):
            return None
