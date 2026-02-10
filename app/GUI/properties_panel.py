# waveform_dialog imported lazily in configure_waveform() for faster startup
from models.component import DEFAULT_VALUES
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from .format_utils import validate_component_value
from .styles import theme_manager


class PropertiesPanel(QWidget):
    """Panel for editing component properties"""

    # Signal emitted when a property is changed
    property_changed = pyqtSignal(str, str, object)  # component_id, property_name, new_value

    def __init__(self):
        super().__init__()
        self.current_component = None
        self.init_ui()

    def init_ui(self):
        """Initialize the properties panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title = QLabel("Properties")
        title.setFont(theme_manager.font("panel_title"))
        layout.addWidget(title)

        # Properties group box
        self.properties_group = QGroupBox("Component Properties")
        self.form_layout = QFormLayout(self.properties_group)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Component ID field (read-only)
        self.id_label = QLabel("-")
        self.id_label.setStyleSheet(theme_manager.stylesheet("muted_label"))
        self.id_label.setToolTip("Unique identifier for this component (auto-generated)")
        self.form_layout.addRow("ID:", self.id_label)

        # Component Type field (read-only)
        self.type_label = QLabel("-")
        self.type_label.setStyleSheet(theme_manager.stylesheet("muted_label"))
        self.type_label.setToolTip("The type of circuit component")
        self.form_layout.addRow("Type:", self.type_label)

        # Value field (editable)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., 10k, 100u, 5V")
        self.value_input.setToolTip("Component value with optional SI suffix (e.g., 10k, 100n, 4.7M)")
        self.value_input.textChanged.connect(self.on_value_changed)
        self.form_layout.addRow("Value:", self.value_input)

        # Validation error label
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("QLabel { color: red; font-size: 9pt; }")
        self.error_label.setVisible(False)
        self.form_layout.addRow("", self.error_label)

        layout.addWidget(self.properties_group)

        # Apply button
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.setToolTip("Apply the changed value to the selected component")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)

        # Waveform configuration button (shown only for waveform sources)
        self.waveform_button = QPushButton("Configure Waveform...")
        self.waveform_button.setToolTip("Open waveform parameter configuration")
        self.waveform_button.clicked.connect(self.configure_waveform)
        self.waveform_button.setVisible(False)
        layout.addWidget(self.waveform_button)

        layout.addStretch()

        # Initially show "no selection" state
        self.show_no_selection()

    def show_no_selection(self):
        """Display message when no component is selected"""
        self.properties_group.setEnabled(False)
        self.id_label.setText("-")
        self.type_label.setText("-")
        self.value_input.clear()
        self.value_input.setReadOnly(False)
        self.value_input.setPlaceholderText("")
        self.apply_button.setEnabled(False)
        self.error_label.setVisible(False)
        self.waveform_button.setVisible(False)
        self.current_component = None

    def show_multi_selection(self, count):
        """Display summary when multiple components are selected."""
        self.current_component = None
        self.properties_group.setEnabled(False)
        self.id_label.setText(f"{count} items selected")
        self.type_label.setText("(multiple)")
        self.value_input.clear()
        self.value_input.setPlaceholderText("")
        self.apply_button.setEnabled(False)
        self.error_label.setVisible(False)
        self.waveform_button.setVisible(False)

    def show_component(self, component):
        """Display properties for the given component"""
        if component is None:
            self.show_no_selection()
            return

        self.current_component = component
        self.properties_group.setEnabled(True)
        self.apply_button.setEnabled(False)
        self.error_label.setVisible(False)

        # Update fields with component data
        self.id_label.setText(component.component_id)
        self.type_label.setText(component.component_type)

        # Block signals temporarily to avoid triggering change events
        self.value_input.blockSignals(True)
        self.value_input.setText(component.value)

        # Waveform sources use the Configure Waveform dialog for editing
        if component.component_type == "Waveform Source":
            self.value_input.setReadOnly(True)
            self.value_input.setPlaceholderText("Use 'Configure Waveform...' button")
            self.waveform_button.setVisible(True)
        else:
            self.value_input.setReadOnly(False)
            self.value_input.setPlaceholderText(f"Default: {DEFAULT_VALUES.get(component.component_type, '')}")
            self.waveform_button.setVisible(False)

        self.value_input.blockSignals(False)

    def on_value_changed(self):
        """Handle value input changes"""
        if self.current_component:
            self.apply_button.setEnabled(True)

    def apply_changes(self):
        """Apply property changes to the current component"""
        if not self.current_component:
            return

        # Get the new value
        new_value = self.value_input.text().strip()

        # Validate value format
        is_valid, error_msg = validate_component_value(new_value, self.current_component.component_type)
        if not is_valid:
            self.error_label.setText(error_msg)
            self.error_label.setVisible(True)
            return

        self.error_label.setVisible(False)

        # Emit signal if value changed
        if new_value != self.current_component.value:
            self.property_changed.emit(self.current_component.component_id, "value", new_value)

        self.apply_button.setEnabled(False)

    def configure_waveform(self):
        """Open waveform configuration dialog"""
        if not self.current_component:
            return

        if self.current_component.component_type != "Waveform Source":
            return

        from .waveform_config_dialog import WaveformConfigDialog

        dialog = WaveformConfigDialog(self.current_component, self)
        if dialog.exec():
            # Get configured parameters
            waveform_type, params = dialog.get_parameters()

            # Update component
            self.current_component.waveform_type = waveform_type
            self.current_component.waveform_params[waveform_type] = params

            # Update the value display to show the SPICE representation
            if hasattr(self.current_component, "get_spice_value"):
                spice_value = self.current_component.get_spice_value()
                self.value_input.setText(spice_value)
                self.current_component.value = spice_value

            # Emit property changed signal
            self.property_changed.emit(self.current_component.component_id, "waveform", (waveform_type, params))
