"""Wire Routing Preferences dialog for configuring pathfinder cost parameters."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .path_finding import ROUTING_PRESETS, RoutingConfig
from .styles import theme_manager


class RoutingPreferencesDialog(QDialog):
    """Dialog for configuring wire routing cost parameters.

    Exposes bend penalty, crossing penalty, same-net bonus, and base cost
    as adjustable spinboxes, with built-in presets for common routing styles.
    """

    def __init__(self, parent=None, apply_all_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Wire Routing Preferences")
        self.setMinimumWidth(400)
        self._apply_all_callback = apply_all_callback
        self._build_ui()
        self._load_current_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        for name in ROUTING_PRESETS:
            self.preset_combo.addItem(name)
        self.preset_combo.addItem("Custom")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        # Parameter spinboxes
        form = QFormLayout()

        self.bend_spin = QDoubleSpinBox()
        self.bend_spin.setRange(0.5, 20.0)
        self.bend_spin.setSingleStep(0.5)
        self.bend_spin.setDecimals(1)
        self.bend_spin.setToolTip("Higher values produce straighter wires with fewer bends")
        form.addRow("Bend penalty:", self.bend_spin)

        self.crossing_spin = QDoubleSpinBox()
        self.crossing_spin.setRange(1.0, 100.0)
        self.crossing_spin.setSingleStep(5.0)
        self.crossing_spin.setDecimals(1)
        self.crossing_spin.setToolTip("Higher values avoid crossing wires from different nets")
        form.addRow("Crossing penalty:", self.crossing_spin)

        self.bundling_spin = QDoubleSpinBox()
        self.bundling_spin.setRange(0.01, 10.0)
        self.bundling_spin.setSingleStep(0.1)
        self.bundling_spin.setDecimals(2)
        self.bundling_spin.setToolTip("Lower values encourage wires from the same net to share paths")
        form.addRow("Same-net bonus:", self.bundling_spin)

        self.base_cost_spin = QDoubleSpinBox()
        self.base_cost_spin.setRange(0.1, 10.0)
        self.base_cost_spin.setSingleStep(0.1)
        self.base_cost_spin.setDecimals(1)
        self.base_cost_spin.setToolTip("Base cost per grid cell traversed")
        form.addRow("Base move cost:", self.base_cost_spin)

        layout.addLayout(form)

        # Connect spinbox changes to detect custom values
        for spin in (self.bend_spin, self.crossing_spin, self.bundling_spin, self.base_cost_spin):
            spin.valueChanged.connect(self._on_value_changed)

        # Apply to All Wires button
        if self._apply_all_callback:
            apply_btn = QPushButton("Apply to All Wires")
            apply_btn.setToolTip("Reroute all wires in the circuit using these settings")
            apply_btn.clicked.connect(self._on_apply_all)
            layout.addWidget(apply_btn)

        # OK / Cancel buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_current_values(self):
        """Load current routing config into spinboxes."""
        config = theme_manager.routing_config
        self._set_spinbox_values(config)
        self._update_preset_combo(config)

    def _set_spinbox_values(self, config):
        """Set all spinbox values from a RoutingConfig, blocking signals."""
        for spin in (self.bend_spin, self.crossing_spin, self.bundling_spin, self.base_cost_spin):
            spin.blockSignals(True)
        self.bend_spin.setValue(config.bend_penalty)
        self.crossing_spin.setValue(config.crossing_penalty)
        self.bundling_spin.setValue(config.same_net_bonus)
        self.base_cost_spin.setValue(config.base_cost)
        for spin in (self.bend_spin, self.crossing_spin, self.bundling_spin, self.base_cost_spin):
            spin.blockSignals(False)

    def _update_preset_combo(self, config):
        """Select the matching preset or 'Custom' if no match."""
        self.preset_combo.blockSignals(True)
        matched = False
        for i, (name, preset) in enumerate(ROUTING_PRESETS.items()):
            if (
                abs(config.bend_penalty - preset.bend_penalty) < 0.001
                and abs(config.crossing_penalty - preset.crossing_penalty) < 0.001
                and abs(config.same_net_bonus - preset.same_net_bonus) < 0.001
                and abs(config.base_cost - preset.base_cost) < 0.001
            ):
                self.preset_combo.setCurrentIndex(i)
                matched = True
                break
        if not matched:
            self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)  # "Custom"
        self.preset_combo.blockSignals(False)

    def _on_preset_changed(self, index):
        """Apply preset values to spinboxes."""
        preset_names = list(ROUTING_PRESETS.keys())
        if 0 <= index < len(preset_names):
            config = ROUTING_PRESETS[preset_names[index]]
            self._set_spinbox_values(config)

    def _on_value_changed(self, _value):
        """When a spinbox changes, update preset combo to 'Custom' if needed."""
        config = self.get_config()
        self._update_preset_combo(config)

    def _on_apply_all(self):
        """Apply current config and reroute all wires."""
        config = self.get_config()
        theme_manager.set_routing_config(config)
        if self._apply_all_callback:
            self._apply_all_callback()

    def get_config(self) -> RoutingConfig:
        """Return a RoutingConfig from the current spinbox values."""
        return RoutingConfig(
            bend_penalty=self.bend_spin.value(),
            crossing_penalty=self.crossing_spin.value(),
            same_net_bonus=self.bundling_spin.value(),
            base_cost=self.base_cost_spin.value(),
        )
