"""
layer_control_widget.py

Widget for controlling algorithm layer visibility and displaying performance metrics
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from .styles import theme_manager


class LayerControlWidget(QWidget):
    """Widget for controlling visibility of algorithm layers"""

    # Signal emitted when layer visibility changes: (algorithm_type, visible)
    layerVisibilityChanged = pyqtSignal(str, bool)

    # Signal to request performance report update
    performanceReportRequested = pyqtSignal()

    def __init__(self, layer_manager, parent=None):
        """
        Initialize layer control widget

        Args:
            layer_manager: AlgorithmLayerManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.checkboxes = {}  # algorithm_type -> QCheckBox

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title = QLabel("Algorithm Layers")
        title.setStyleSheet(theme_manager.stylesheet("title_bold"))
        layout.addWidget(title)

        # Layer checkboxes group
        layers_group = QGroupBox("Visibility")
        layers_layout = QVBoxLayout()

        for layer in self.layer_manager.get_all_layers():
            checkbox_layout = QHBoxLayout()

            # Color indicator
            color_label = QLabel("  ")
            color_label.setAutoFillBackground(True)
            palette = color_label.palette()
            palette.setColor(QPalette.ColorRole.Window, layer.color)
            color_label.setPalette(palette)
            color_label.setFixedSize(20, 20)
            checkbox_layout.addWidget(color_label)

            # Checkbox for visibility
            checkbox = QCheckBox(layer.name)
            checkbox.setChecked(layer.visible)
            checkbox.stateChanged.connect(
                lambda state, alg=layer.algorithm_type: self._on_visibility_changed(alg, state)
            )
            self.checkboxes[layer.algorithm_type] = checkbox
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.addStretch()

            layers_layout.addLayout(checkbox_layout)

        layers_group.setLayout(layers_layout)
        layout.addWidget(layers_group)

        # Action buttons
        button_layout = QHBoxLayout()

        show_all_btn = QPushButton("Show All")
        show_all_btn.clicked.connect(self._show_all_layers)
        button_layout.addWidget(show_all_btn)

        hide_all_btn = QPushButton("Hide All")
        hide_all_btn.clicked.connect(self._hide_all_layers)
        button_layout.addWidget(hide_all_btn)

        layout.addLayout(button_layout)

        # Performance metrics area
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QVBoxLayout()

        self.metrics_text = QTextEdit()
        self.metrics_text.setReadOnly(True)
        self.metrics_text.setMaximumHeight(150)
        self.metrics_text.setStyleSheet(theme_manager.stylesheet("metrics_text"))
        metrics_layout.addWidget(self.metrics_text)

        refresh_btn = QPushButton("Refresh Metrics")
        refresh_btn.clicked.connect(self._refresh_metrics)
        metrics_layout.addWidget(refresh_btn)

        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        layout.addStretch()
        self.setLayout(layout)

        # Initial metrics update
        self._refresh_metrics()

    def _on_visibility_changed(self, algorithm_type, state):
        """Handle checkbox state change"""
        visible = state == Qt.CheckState.Checked.value
        self.layer_manager.set_layer_visibility(algorithm_type, visible)
        self.layerVisibilityChanged.emit(algorithm_type, visible)

    def _show_all_layers(self):
        """Show all algorithm layers"""
        for algorithm_type, checkbox in self.checkboxes.items():
            checkbox.setChecked(True)

    def _hide_all_layers(self):
        """Hide all algorithm layers"""
        for algorithm_type, checkbox in self.checkboxes.items():
            checkbox.setChecked(False)

    def _refresh_metrics(self):
        """Update performance metrics display"""
        report = self.layer_manager.get_performance_report()
        self.metrics_text.setPlainText(report)
        self.performanceReportRequested.emit()

    def update_metrics(self):
        """Public method to update metrics from external sources"""
        self._refresh_metrics()

    def set_layer_visibility(self, algorithm_type, visible):
        """Programmatically set layer visibility"""
        if algorithm_type in self.checkboxes:
            self.checkboxes[algorithm_type].setChecked(visible)


class CompactLayerControlWidget(QWidget):
    """Compact horizontal version of layer controls for placement above canvas"""

    # Signal emitted when layer visibility changes: (algorithm_type, visible)
    layerVisibilityChanged = pyqtSignal(str, bool)

    def __init__(self, layer_manager, parent=None):
        """
        Initialize compact layer control widget

        Args:
            layer_manager: AlgorithmLayerManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.checkboxes = {}

        self._setup_ui()

    def _setup_ui(self):
        """Setup the compact horizontal UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        # Title
        title = QLabel("Layers:")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        # Layer checkboxes
        for layer in self.layer_manager.get_all_layers():
            # Color indicator with checkbox
            checkbox = QCheckBox(f"■ {layer.name}")
            checkbox.setChecked(layer.visible)

            # Apply color to checkbox text
            color = layer.color
            checkbox.setStyleSheet(f"color: rgb({color.red()}, {color.green()}, {color.blue()});")

            checkbox.stateChanged.connect(
                lambda state, alg=layer.algorithm_type: self._on_visibility_changed(alg, state)
            )
            self.checkboxes[layer.algorithm_type] = checkbox
            layout.addWidget(checkbox)

        layout.addStretch()

        # Show metrics button
        metrics_btn = QPushButton("Show Metrics")
        metrics_btn.clicked.connect(self._show_metrics)
        layout.addWidget(metrics_btn)

        self.setLayout(layout)

    def _on_visibility_changed(self, algorithm_type, state):
        """Handle checkbox state change"""
        visible = state == Qt.CheckState.Checked.value
        self.layer_manager.set_layer_visibility(algorithm_type, visible)
        self.layerVisibilityChanged.emit(algorithm_type, visible)

    def _show_metrics(self):
        """Display performance metrics in a message box or console"""
        pass

    def set_layer_visibility(self, algorithm_type, visible):
        """Programmatically set layer visibility"""
        if algorithm_type in self.checkboxes:
            self.checkboxes[algorithm_type].setChecked(visible)
