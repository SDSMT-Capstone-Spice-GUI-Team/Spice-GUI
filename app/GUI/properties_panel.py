from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QFormLayout, QGroupBox, QPushButton, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from .waveform_dialog import WaveformDialog


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
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title.setFont(title_font)
        layout.addWidget(title)

        # Properties group box
        self.properties_group = QGroupBox("Component Properties")
        self.form_layout = QFormLayout(self.properties_group)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Component ID field (read-only)
        self.id_label = QLabel("-")
        self.id_label.setStyleSheet("QLabel { color: #666; }")
        self.form_layout.addRow("ID:", self.id_label)

        # Component Type field (read-only)
        self.type_label = QLabel("-")
        self.type_label.setStyleSheet("QLabel { color: #666; }")
        self.form_layout.addRow("Type:", self.type_label)

        # Value field (editable)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., 10k, 100u, 5V")
        self.value_input.textChanged.connect(self.on_value_changed)
        self.form_layout.addRow("Value:", self.value_input)

        # Rotation field (editable via combo box)
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["0°", "90°", "180°", "270°"])
        self.rotation_combo.currentIndexChanged.connect(self.on_rotation_changed)
        self.form_layout.addRow("Rotation:", self.rotation_combo)

        # Position fields (read-only, for information)
        self.position_label = QLabel("-")
        self.position_label.setStyleSheet("QLabel { color: #666; }")
        self.form_layout.addRow("Position:", self.position_label)

        # Number of terminals (read-only)
        self.terminals_label = QLabel("-")
        self.terminals_label.setStyleSheet("QLabel { color: #666; }")
        self.form_layout.addRow("Terminals:", self.terminals_label)

        layout.addWidget(self.properties_group)

        # Apply button
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)

        # Waveform configuration button (shown only for waveform sources)
        self.waveform_button = QPushButton("Configure Waveform...")
        self.waveform_button.clicked.connect(self.configure_waveform)
        self.waveform_button.setVisible(False)
        layout.addWidget(self.waveform_button)

        # Help text
        help_text = QLabel(
            "Select a component on the canvas to edit its properties.\n\n"
            "Value examples:\n"
            "• Resistors: 1k, 10k, 1M\n"
            "• Capacitors: 1u, 100n, 1p\n"
            "• Inductors: 1m, 100u, 1n\n"
            "• Sources: 5V, 3.3V, 1A"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(
            "QLabel { background-color: #f9f9f9; padding: 8px; "
            "border: 1px solid #ddd; border-radius: 3px; font-size: 9pt; }"
        )
        layout.addWidget(help_text)

        layout.addStretch()

        # Initially show "no selection" state
        self.show_no_selection()

    def show_no_selection(self):
        """Display message when no component is selected"""
        self.properties_group.setEnabled(False)
        self.id_label.setText("-")
        self.type_label.setText("-")
        self.value_input.clear()
        self.value_input.setPlaceholderText("No component selected")
        self.rotation_combo.setCurrentIndex(0)
        self.position_label.setText("-")
        self.terminals_label.setText("-")
        self.apply_button.setEnabled(False)
        self.waveform_button.setVisible(False)
        self.current_component = None

    def show_component(self, component):
        """Display properties for the given component"""
        if component is None:
            self.show_no_selection()
            return

        self.current_component = component
        self.properties_group.setEnabled(True)
        self.apply_button.setEnabled(True)

        # Update fields with component data
        self.id_label.setText(component.component_id)
        self.type_label.setText(component.component_type)

        # Block signals temporarily to avoid triggering change events
        self.value_input.blockSignals(True)
        self.rotation_combo.blockSignals(True)

        self.value_input.setText(component.value)
        self.value_input.setPlaceholderText(f"Default: {component.DEFAULT_VALUE}")

        # Set rotation combo box
        rotation_index = int(component.rotation_angle / 90) % 4
        self.rotation_combo.setCurrentIndex(rotation_index)

        # Update position
        pos = component.pos()
        self.position_label.setText(f"({pos.x():.0f}, {pos.y():.0f})")

        # Update terminals count
        self.terminals_label.setText(str(component.TERMINALS))

        # Re-enable signals
        self.value_input.blockSignals(False)
        self.rotation_combo.blockSignals(False)

        # Show/hide waveform button for waveform sources
        if component.component_type == 'Waveform Source':
            self.waveform_button.setVisible(True)
        else:
            self.waveform_button.setVisible(False)

    def on_value_changed(self):
        """Handle value input changes"""
        if self.current_component:
            self.apply_button.setEnabled(True)

    def on_rotation_changed(self, index):
        """Handle rotation changes"""
        if self.current_component:
            new_rotation = index * 90
            if new_rotation != self.current_component.rotation_angle:
                self.property_changed.emit(
                    self.current_component.component_id,
                    'rotation',
                    new_rotation
                )

    def apply_changes(self):
        """Apply property changes to the current component"""
        if not self.current_component:
            return

        # Get the new value
        new_value = self.value_input.text().strip()

        # Validate the value is not empty
        if not new_value:
            self.value_input.setText(self.current_component.value)
            return

        # Emit signal if value changed
        if new_value != self.current_component.value:
            self.property_changed.emit(
                self.current_component.component_id,
                'value',
                new_value
            )

        self.apply_button.setEnabled(False)

    def update_position_display(self):
        """Update the position display for the current component"""
        if self.current_component:
            pos = self.current_component.pos()
            self.position_label.setText(f"({pos.x():.0f}, {pos.y():.0f})")

    def configure_waveform(self):
        """Open waveform configuration dialog"""
        if not self.current_component:
            return

        if self.current_component.component_type != 'Waveform Source':
            return

        dialog = WaveformDialog(self.current_component, self)
        if dialog.exec():
            # Get configured parameters
            waveform_type, params = dialog.get_parameters()

            # Update component
            self.current_component.waveform_type = waveform_type
            self.current_component.waveform_params[waveform_type] = params

            # Update the value display to show the SPICE representation
            if hasattr(self.current_component, 'get_spice_value'):
                spice_value = self.current_component.get_spice_value()
                self.value_input.setText(spice_value)
                self.current_component.value = spice_value

            # Emit property changed signal
            self.property_changed.emit(
                self.current_component.component_id,
                'waveform',
                (waveform_type, params)
            )
