"""
Monte Carlo Configuration Dialog — Configure tolerance simulation.

Allows users to set number of runs, per-component tolerances and
distribution, and select the base analysis type.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QGroupBox,
                             QHeaderView, QLabel, QLineEdit, QSpinBox,
                             QTableWidget, QTableWidgetItem, QVBoxLayout)

# Base analysis types available for Monte Carlo
MC_BASE_ANALYSIS_TYPES = [
    "DC Operating Point",
    "Transient",
    "AC Sweep",
    "DC Sweep",
]


class MonteCarloDialog(QDialog):
    """Dialog for configuring Monte Carlo tolerance analysis."""

    def __init__(self, components, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monte Carlo Analysis Configuration")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)

        from simulation.monte_carlo import MC_ELIGIBLE_TYPES

        self._components = components
        self._eligible = {
            cid: comp
            for cid, comp in components.items()
            if comp.component_type in MC_ELIGIBLE_TYPES
        }
        self._base_field_widgets = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        desc = QLabel(
            "Run the simulation multiple times with randomly varied component "
            "values to assess the impact of manufacturing tolerances."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Run Configuration ---
        run_group = QGroupBox("Simulation")
        run_form = QFormLayout(run_group)

        self.num_runs_spin = QSpinBox()
        self.num_runs_spin.setRange(2, 1000)
        self.num_runs_spin.setValue(20)
        self.num_runs_spin.setToolTip("Number of Monte Carlo runs (2-1000)")
        run_form.addRow("Number of runs:", self.num_runs_spin)

        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(MC_BASE_ANALYSIS_TYPES)
        self.analysis_combo.setToolTip("Analysis type to run at each Monte Carlo step")
        self.analysis_combo.currentTextChanged.connect(self._on_analysis_changed)
        run_form.addRow("Base analysis:", self.analysis_combo)

        self._base_form = QFormLayout()
        run_form.addRow(self._base_form)
        layout.addWidget(run_group)

        # Build initial base analysis fields
        self._build_base_form()

        # --- Tolerance Table ---
        tol_group = QGroupBox("Component Tolerances")
        tol_layout = QVBoxLayout(tol_group)

        if not self._eligible:
            tol_layout.addWidget(QLabel("No eligible components in the circuit."))
            self.tol_table = None
        else:
            self.tol_table = QTableWidget()
            self.tol_table.setToolTip(
                "Set tolerance and distribution for each component"
            )
            self.tol_table.setColumnCount(4)
            self.tol_table.setHorizontalHeaderLabels(
                ["Component", "Type", "Tolerance (%)", "Distribution"]
            )
            self.tol_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            self.tol_table.setRowCount(len(self._eligible))

            for row, (cid, comp) in enumerate(sorted(self._eligible.items())):
                # Component ID
                id_item = QTableWidgetItem(f"{cid} ({comp.value})")
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tol_table.setItem(row, 0, id_item)

                # Type
                type_item = QTableWidgetItem(comp.component_type)
                type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tol_table.setItem(row, 1, type_item)

                # Tolerance spin
                tol_spin = QDoubleSpinBox()
                from simulation.monte_carlo import DEFAULT_TOLERANCES

                tol_spin.setRange(0.0, 50.0)
                tol_spin.setSuffix("%")
                tol_spin.setDecimals(1)
                tol_spin.setToolTip("Component value tolerance as a percentage (0-50%)")
                default_tol = DEFAULT_TOLERANCES.get(comp.component_type, 5.0)
                tol_spin.setValue(default_tol)
                self.tol_table.setCellWidget(row, 2, tol_spin)

                # Distribution combo
                dist_combo = QComboBox()
                dist_combo.addItems(["Gaussian", "Uniform"])
                dist_combo.setToolTip(
                    "Gaussian: normal distribution; Uniform: equal probability across range"
                )
                self.tol_table.setCellWidget(row, 3, dist_combo)

            tol_layout.addWidget(self.tol_table)

        layout.addWidget(tol_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_analysis_changed(self, analysis_type):
        self._build_base_form()

    def _build_base_form(self):
        """Build form fields for the selected base analysis type."""
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
        """Get all Monte Carlo parameters.

        Returns:
            dict with keys: num_runs, base_analysis_type, base_params,
                            tolerances
            or None if validation fails.
        """
        from .format_utils import parse_value

        try:
            num_runs = self.num_runs_spin.value()
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

            # Build tolerances from table
            tolerances = {}
            if self.tol_table is not None:
                for row, (cid, comp) in enumerate(sorted(self._eligible.items())):
                    tol_spin = self.tol_table.cellWidget(row, 2)
                    dist_combo = self.tol_table.cellWidget(row, 3)
                    tol_pct = tol_spin.value()
                    if tol_pct > 0:
                        tolerances[cid] = {
                            "tolerance_pct": tol_pct,
                            "distribution": dist_combo.currentText().lower(),
                        }

            if not tolerances:
                return None

            return {
                "num_runs": num_runs,
                "base_analysis_type": base_analysis_type,
                "base_params": base_params,
                "tolerances": tolerances,
            }
        except (ValueError, TypeError):
            return None
