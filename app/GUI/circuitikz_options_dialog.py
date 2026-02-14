"""Dialog for configuring CircuiTikZ export options."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QGroupBox,
                             QVBoxLayout)

SETTINGS_PREFIX = "circuitikz/"


class CircuiTikZOptionsDialog(QDialog):
    """Options dialog for CircuiTikZ LaTeX export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CircuiTikZ Export Options")
        self.setMinimumWidth(350)
        self._build_ui()
        self._restore_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Style group ---
        style_group = QGroupBox("Component Style")
        style_layout = QFormLayout()

        self.style_combo = QComboBox()
        self.style_combo.addItems(["American", "European"])
        self.style_combo.setToolTip(
            "American: zigzag resistors, coil inductors\nEuropean: rectangle resistors, rectangle inductors"
        )
        style_layout.addRow("Drawing style:", self.style_combo)
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # --- Scale group ---
        scale_group = QGroupBox("Coordinate Scale")
        scale_layout = QFormLayout()

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(1.0, 200.0)
        self.scale_spin.setValue(20.0)
        self.scale_spin.setSuffix(" px/unit")
        self.scale_spin.setToolTip(
            "Pixels per TikZ unit. Default 20 means 1 grid square = 1 TikZ unit.\n"
            "Larger values produce a more compact diagram."
        )
        scale_layout.addRow("Scale factor:", self.scale_spin)
        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)

        # --- Labels group ---
        labels_group = QGroupBox("Labels")
        labels_layout = QVBoxLayout()

        self.include_ids_cb = QCheckBox("Include component IDs (e.g. R1, C1)")
        self.include_ids_cb.setChecked(True)
        labels_layout.addWidget(self.include_ids_cb)

        self.include_values_cb = QCheckBox("Include component values (e.g. 1k, 100n)")
        self.include_values_cb.setChecked(True)
        labels_layout.addWidget(self.include_values_cb)

        self.include_net_labels_cb = QCheckBox("Include net labels (e.g. Vout, GND)")
        self.include_net_labels_cb.setChecked(True)
        labels_layout.addWidget(self.include_net_labels_cb)

        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)

        # --- Output group ---
        output_group = QGroupBox("Output Format")
        output_layout = QVBoxLayout()

        self.standalone_cb = QCheckBox("Standalone document (full .tex with preamble)")
        self.standalone_cb.setChecked(True)
        self.standalone_cb.setToolTip(
            "Checked: generates a complete .tex file that compiles on its own.\n"
            "Unchecked: generates only the circuitikz environment block."
        )
        output_layout.addWidget(self.standalone_cb)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._save_settings()
        self.accept()

    def get_options(self):
        """Return the selected options as a dict suitable for generate()."""
        return {
            "style": "european" if self.style_combo.currentIndex() == 1 else "american",
            "scale": self.scale_spin.value(),
            "include_ids": self.include_ids_cb.isChecked(),
            "include_values": self.include_values_cb.isChecked(),
            "include_net_labels": self.include_net_labels_cb.isChecked(),
            "standalone": self.standalone_cb.isChecked(),
        }

    def _save_settings(self):
        settings = QSettings("SDSMT", "SDM Spice")
        opts = self.get_options()
        settings.setValue(f"{SETTINGS_PREFIX}style", opts["style"])
        settings.setValue(f"{SETTINGS_PREFIX}scale", opts["scale"])
        settings.setValue(f"{SETTINGS_PREFIX}include_ids", opts["include_ids"])
        settings.setValue(f"{SETTINGS_PREFIX}include_values", opts["include_values"])
        settings.setValue(
            f"{SETTINGS_PREFIX}include_net_labels", opts["include_net_labels"]
        )
        settings.setValue(f"{SETTINGS_PREFIX}standalone", opts["standalone"])

    def _restore_settings(self):
        settings = QSettings("SDSMT", "SDM Spice")

        style = settings.value(f"{SETTINGS_PREFIX}style", "american")
        self.style_combo.setCurrentIndex(1 if style == "european" else 0)

        scale = settings.value(f"{SETTINGS_PREFIX}scale")
        if scale is not None:
            self.scale_spin.setValue(float(scale))

        include_ids = settings.value(f"{SETTINGS_PREFIX}include_ids")
        if include_ids is not None:
            self.include_ids_cb.setChecked(include_ids == "true" or include_ids is True)

        include_values = settings.value(f"{SETTINGS_PREFIX}include_values")
        if include_values is not None:
            self.include_values_cb.setChecked(
                include_values == "true" or include_values is True
            )

        include_net_labels = settings.value(f"{SETTINGS_PREFIX}include_net_labels")
        if include_net_labels is not None:
            self.include_net_labels_cb.setChecked(
                include_net_labels == "true" or include_net_labels is True
            )

        standalone = settings.value(f"{SETTINGS_PREFIX}standalone")
        if standalone is not None:
            self.standalone_cb.setChecked(standalone == "true" or standalone is True)
