from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QFormLayout, QPushButton,
                             QGroupBox, QDialogButtonBox)
from PyQt6.QtCore import Qt


class WaveformDialog(QDialog):
    """Dialog for configuring waveform source parameters"""

    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle(f"Waveform Configuration - {component.component_id}")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)

        # Waveform type selector
        type_group = QGroupBox("Waveform Type")
        type_layout = QHBoxLayout(type_group)

        type_label = QLabel("Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["SIN", "PULSE", "EXP"])
        self.type_combo.setCurrentText(self.component.waveform_type)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)

        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()

        layout.addWidget(type_group)

        # Parameter input group
        self.params_group = QGroupBox("Parameters")
        self.params_layout = QFormLayout(self.params_group)
        layout.addWidget(self.params_group)

        # Create input fields for all waveform types
        self.param_inputs = {}
        self.create_param_inputs()

        # Update display for current waveform type
        self.on_type_changed(self.component.waveform_type)

        # Help text
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet(
            "QLabel { background-color: #f9f9f9; padding: 8px; "
            "border: 1px solid #ddd; border-radius: 3px; font-size: 9pt; }"
        )
        layout.addWidget(self.help_label)
        self.update_help_text()

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def create_param_inputs(self):
        """Create input fields for all parameter types"""
        # SIN parameters
        self.param_inputs['SIN'] = {
            'offset': QLineEdit(self.component.waveform_params['SIN']['offset']),
            'amplitude': QLineEdit(self.component.waveform_params['SIN']['amplitude']),
            'frequency': QLineEdit(self.component.waveform_params['SIN']['frequency']),
            'delay': QLineEdit(self.component.waveform_params['SIN']['delay']),
            'theta': QLineEdit(self.component.waveform_params['SIN']['theta']),
            'phase': QLineEdit(self.component.waveform_params['SIN']['phase'])
        }

        # PULSE parameters
        self.param_inputs['PULSE'] = {
            'v1': QLineEdit(self.component.waveform_params['PULSE']['v1']),
            'v2': QLineEdit(self.component.waveform_params['PULSE']['v2']),
            'td': QLineEdit(self.component.waveform_params['PULSE']['td']),
            'tr': QLineEdit(self.component.waveform_params['PULSE']['tr']),
            'tf': QLineEdit(self.component.waveform_params['PULSE']['tf']),
            'pw': QLineEdit(self.component.waveform_params['PULSE']['pw']),
            'per': QLineEdit(self.component.waveform_params['PULSE']['per'])
        }

        # EXP parameters
        self.param_inputs['EXP'] = {
            'v1': QLineEdit(self.component.waveform_params['EXP']['v1']),
            'v2': QLineEdit(self.component.waveform_params['EXP']['v2']),
            'td1': QLineEdit(self.component.waveform_params['EXP']['td1']),
            'tau1': QLineEdit(self.component.waveform_params['EXP']['tau1']),
            'td2': QLineEdit(self.component.waveform_params['EXP']['td2']),
            'tau2': QLineEdit(self.component.waveform_params['EXP']['tau2'])
        }

    def on_type_changed(self, waveform_type):
        """Update parameter fields when waveform type changes"""
        # Clear existing fields
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)

        # Add fields for selected waveform type
        if waveform_type == 'SIN':
            self.params_layout.addRow("Offset (V):", self.param_inputs['SIN']['offset'])
            self.params_layout.addRow("Amplitude (V):", self.param_inputs['SIN']['amplitude'])
            self.params_layout.addRow("Frequency (Hz):", self.param_inputs['SIN']['frequency'])
            self.params_layout.addRow("Delay (s):", self.param_inputs['SIN']['delay'])
            self.params_layout.addRow("Theta (1/s):", self.param_inputs['SIN']['theta'])
            self.params_layout.addRow("Phase (deg):", self.param_inputs['SIN']['phase'])

        elif waveform_type == 'PULSE':
            self.params_layout.addRow("Initial Value (V):", self.param_inputs['PULSE']['v1'])
            self.params_layout.addRow("Pulsed Value (V):", self.param_inputs['PULSE']['v2'])
            self.params_layout.addRow("Delay Time (s):", self.param_inputs['PULSE']['td'])
            self.params_layout.addRow("Rise Time (s):", self.param_inputs['PULSE']['tr'])
            self.params_layout.addRow("Fall Time (s):", self.param_inputs['PULSE']['tf'])
            self.params_layout.addRow("Pulse Width (s):", self.param_inputs['PULSE']['pw'])
            self.params_layout.addRow("Period (s):", self.param_inputs['PULSE']['per'])

        elif waveform_type == 'EXP':
            self.params_layout.addRow("Initial Value (V):", self.param_inputs['EXP']['v1'])
            self.params_layout.addRow("Pulsed Value (V):", self.param_inputs['EXP']['v2'])
            self.params_layout.addRow("Rise Delay (s):", self.param_inputs['EXP']['td1'])
            self.params_layout.addRow("Rise Tau (s):", self.param_inputs['EXP']['tau1'])
            self.params_layout.addRow("Fall Delay (s):", self.param_inputs['EXP']['td2'])
            self.params_layout.addRow("Fall Tau (s):", self.param_inputs['EXP']['tau2'])

        self.update_help_text()

    def update_help_text(self):
        """Update help text based on selected waveform type"""
        waveform_type = self.type_combo.currentText()

        if waveform_type == 'SIN':
            help_text = (
                "Sine Wave: V(t) = Offset + Amplitude × sin(2π × Frequency × t + Phase)\n\n"
                "• Offset: DC offset voltage\n"
                "• Amplitude: Peak amplitude of sine wave\n"
                "• Frequency: Frequency in Hz (use k for kHz, Meg for MHz)\n"
                "• Delay: Time before sine wave starts\n"
                "• Theta: Damping factor (usually 0)\n"
                "• Phase: Phase shift in degrees"
            )
        elif waveform_type == 'PULSE':
            help_text = (
                "Pulse Wave: Rectangular pulse train\n\n"
                "• Initial/Pulsed Value: Low and high voltage levels\n"
                "• Delay Time: Time before first pulse\n"
                "• Rise/Fall Time: Edge transition times\n"
                "• Pulse Width: Duration of high level\n"
                "• Period: Time between pulse starts"
            )
        elif waveform_type == 'EXP':
            help_text = (
                "Exponential Wave: Exponential rise and fall\n\n"
                "• Initial/Pulsed Value: Starting and target voltages\n"
                "• Rise Delay: Time before exponential rise\n"
                "• Rise Tau: Time constant for rise\n"
                "• Fall Delay: Time before exponential fall\n"
                "• Fall Tau: Time constant for fall"
            )
        else:
            help_text = "Select a waveform type to see help"

        self.help_label.setText(help_text)

    def get_parameters(self):
        """Get the configured parameters"""
        waveform_type = self.type_combo.currentText()
        params = {}

        for key, input_widget in self.param_inputs[waveform_type].items():
            params[key] = input_widget.text().strip()

        return waveform_type, params
