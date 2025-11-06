from PyQt6.QtWidgets import (
    QVBoxLayout,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
)

class AnalysisDialog(QDialog):
    """Dialog for configuring analysis parameters"""
    
    def __init__(self, analysis_type, parent=None):
        super().__init__(parent)
        self.analysis_type = analysis_type
        self.parameters = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle(f"{self.analysis_type} Parameters")
        layout = QVBoxLayout(self)
        
        # Create form layout for parameters
        form_layout = QFormLayout()
        
        if self.analysis_type == "DC Sweep":
            self.min_field = QLineEdit("0")
            self.max_field = QLineEdit("10")
            self.step_field = QLineEdit("0.1")
            
            form_layout.addRow("Minimum Voltage (V):", self.min_field)
            form_layout.addRow("Maximum Voltage (V):", self.max_field)
            form_layout.addRow("Step Size (V):", self.step_field)
            
        elif self.analysis_type == "AC Sweep":
            self.min_field = QLineEdit("1")
            self.max_field = QLineEdit("1000000")
            self.points_field = QLineEdit("100")
            
            form_layout.addRow("Start Frequency (Hz):", self.min_field)
            form_layout.addRow("Stop Frequency (Hz):", self.max_field)
            form_layout.addRow("Points per Decade:", self.points_field)
            
        elif self.analysis_type == "Transient":
            self.duration_field = QLineEdit("1")
            self.step_field = QLineEdit("0.001")
            
            form_layout.addRow("Duration (s):", self.duration_field)
            form_layout.addRow("Time Step (s):", self.step_field)
        
        layout.addLayout(form_layout)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_parameters(self):
        """Get the parameters from the dialog"""
        if self.analysis_type == "DC Sweep":
            try:
                return {
                    'min': float(self.min_field.text()),
                    'max': float(self.max_field.text()),
                    'step': float(self.step_field.text())
                }
            except ValueError:
                return None
                
        elif self.analysis_type == "AC Sweep":
            try:
                return {
                    'fStart': float(self.min_field.text()),
                    'fStop': float(self.max_field.text()),
                    'points': int(self.points_field.text())
                }
            except ValueError:
                return None
                
        elif self.analysis_type == "Transient":
            try:
                return {
                    'duration': float(self.duration_field.text()),
                    'step': float(self.step_field.text())
                }
            except ValueError:
                return None
        
        return {}
