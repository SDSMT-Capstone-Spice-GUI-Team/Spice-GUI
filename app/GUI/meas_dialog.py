"""
Measurement Dialog — GUI builder for ngspice .meas directives.

Provides a dialog for composing .meas measurement directives without
needing to know the exact syntax.  Supports statistical measures
(AVG, RMS, MIN, MAX, PP, INTEG), point queries (FIND...AT,
FIND...WHEN), and timing measurements (TRIG...TARG).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

# Maps the GUI analysis type name to the .meas domain keyword
ANALYSIS_DOMAIN_MAP = {
    "Transient": "tran",
    "AC Sweep": "ac",
    "DC Sweep": "dc",
}

# Measurement types offered in the GUI
MEAS_TYPES = [
    ("AVG", "Average value over a range"),
    ("RMS", "Root-mean-square over a range"),
    ("MIN", "Minimum value over a range"),
    ("MAX", "Maximum value over a range"),
    ("PP", "Peak-to-peak (max minus min)"),
    ("INTEG", "Integral over a range"),
    ("FIND_AT", "Find value at a specific point"),
    ("FIND_WHEN", "Find value when a condition is met"),
    ("TRIG_TARG", "Timing between trigger and target events"),
]


def build_directive(domain, name, meas_type, params):
    """Build a .meas directive string from structured parameters.

    Args:
        domain: "tran", "ac", or "dc"
        name: measurement name (e.g., "rise_time")
        meas_type: one of the MEAS_TYPES keys
        params: dict with type-specific fields

    Returns:
        str: a complete .meas directive
    """
    variable = params.get("variable", "v(out)")

    if meas_type in ("AVG", "RMS", "MIN", "MAX", "PP", "INTEG"):
        directive = f".meas {domain} {name} {meas_type} {variable}"
        from_val = params.get("from_val", "").strip()
        to_val = params.get("to_val", "").strip()
        if from_val:
            directive += f" FROM={from_val}"
        if to_val:
            directive += f" TO={to_val}"
        return directive

    if meas_type == "FIND_AT":
        at_val = params.get("at_val", "0")
        return f".meas {domain} {name} FIND {variable} AT={at_val}"

    if meas_type == "FIND_WHEN":
        when_var = params.get("when_var", "v(in)")
        when_val = params.get("when_val", "0.5")
        cross = params.get("cross", "")
        directive = f".meas {domain} {name} FIND {variable} WHEN {when_var}={when_val}"
        if cross:
            directive += f" {cross}"
        return directive

    if meas_type == "TRIG_TARG":
        trig_var = params.get("trig_var", "v(in)")
        trig_val = params.get("trig_val", "0.5")
        trig_edge = params.get("trig_edge", "RISE=1")
        targ_var = params.get("targ_var", variable)
        targ_val = params.get("targ_val", "0.5")
        targ_edge = params.get("targ_edge", "RISE=1")
        return (
            f".meas {domain} {name} TRIG {trig_var} VAL={trig_val} {trig_edge} "
            f"TARG {targ_var} VAL={targ_val} {targ_edge}"
        )

    return f".meas {domain} {name} {meas_type} {variable}"


class MeasurementEntryDialog(QDialog):
    """Sub-dialog for configuring a single .meas directive."""

    def __init__(self, domain="tran", parent=None, initial=None):
        """
        Args:
            domain: "tran", "ac", or "dc"
            parent: parent widget
            initial: optional dict to pre-populate for editing
        """
        super().__init__(parent)
        self._domain = domain
        self.setWindowTitle("Add Measurement")
        self.setMinimumWidth(400)
        self._dynamic_widgets = []
        self._init_ui()
        if initial:
            self._load_initial(initial)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit("meas1")
        self.name_edit.setToolTip("Unique name for this measurement (no spaces)")
        form.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        for key, desc in MEAS_TYPES:
            self.type_combo.addItem(f"{key} — {desc}", key)
        self.type_combo.setToolTip("Type of measurement to perform")
        self.type_combo.currentIndexChanged.connect(self._rebuild_fields)
        form.addRow("Type:", self.type_combo)

        self.var_edit = QLineEdit("v(out)")
        self.var_edit.setToolTip("Signal to measure, e.g., v(out), v(2), i(R1)")
        form.addRow("Variable:", self.var_edit)

        layout.addLayout(form)

        # Dynamic fields container
        self._dynamic_group = QGroupBox("Parameters")
        self._dynamic_layout = QFormLayout(self._dynamic_group)
        layout.addWidget(self._dynamic_group)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: gray; font-family: monospace;")
        layout.addWidget(QLabel("Directive preview:"))
        layout.addWidget(self.preview_label)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Build initial dynamic fields and preview
        self._rebuild_fields()

        # Connect change signals for live preview
        self.name_edit.textChanged.connect(self._update_preview)
        self.var_edit.textChanged.connect(self._update_preview)

    def _rebuild_fields(self):
        """Rebuild the dynamic fields based on selected measurement type."""
        # Clear existing dynamic widgets
        for widget in self._dynamic_widgets:
            widget.deleteLater()
        self._dynamic_widgets.clear()
        while self._dynamic_layout.count():
            item = self._dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        meas_type = self.type_combo.currentData()

        if meas_type in ("AVG", "RMS", "MIN", "MAX", "PP", "INTEG"):
            self.from_edit = QLineEdit()
            self.from_edit.setPlaceholderText("optional, e.g., 0 or 1m")
            self.from_edit.setToolTip("Start of measurement range (leave empty for full range)")
            self.from_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("From:", self.from_edit)
            self._dynamic_widgets.append(self.from_edit)

            self.to_edit = QLineEdit()
            self.to_edit.setPlaceholderText("optional, e.g., 10m")
            self.to_edit.setToolTip("End of measurement range (leave empty for full range)")
            self.to_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("To:", self.to_edit)
            self._dynamic_widgets.append(self.to_edit)

        elif meas_type == "FIND_AT":
            self.at_edit = QLineEdit("1m")
            self.at_edit.setToolTip("The exact point (time/frequency/voltage) at which to sample the variable")
            self.at_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("At value:", self.at_edit)
            self._dynamic_widgets.append(self.at_edit)

        elif meas_type == "FIND_WHEN":
            self.when_var_edit = QLineEdit("v(in)")
            self.when_var_edit.setToolTip("Condition variable, e.g., v(in)")
            self.when_var_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("When variable:", self.when_var_edit)
            self._dynamic_widgets.append(self.when_var_edit)

            self.when_val_edit = QLineEdit("0.5")
            self.when_val_edit.setToolTip("Value that the condition variable must equal")
            self.when_val_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Equals:", self.when_val_edit)
            self._dynamic_widgets.append(self.when_val_edit)

            self.cross_combo = QComboBox()
            self.cross_combo.addItems(["", "RISE=1", "FALL=1", "CROSS=1", "RISE=2", "FALL=2"])
            self.cross_combo.setToolTip("Which crossing to use (empty = first crossing)")
            self.cross_combo.currentIndexChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Crossing:", self.cross_combo)
            self._dynamic_widgets.append(self.cross_combo)

        elif meas_type == "TRIG_TARG":
            self.trig_var_edit = QLineEdit("v(in)")
            self.trig_var_edit.setToolTip("Trigger signal")
            self.trig_var_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Trigger variable:", self.trig_var_edit)
            self._dynamic_widgets.append(self.trig_var_edit)

            self.trig_val_edit = QLineEdit("0.5")
            self.trig_val_edit.setToolTip("Trigger threshold value")
            self.trig_val_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Trigger value:", self.trig_val_edit)
            self._dynamic_widgets.append(self.trig_val_edit)

            self.trig_edge_combo = QComboBox()
            self.trig_edge_combo.addItems(["RISE=1", "FALL=1", "CROSS=1"])
            self.trig_edge_combo.setToolTip("Trigger edge: rising, falling, or any crossing")
            self.trig_edge_combo.currentIndexChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Trigger edge:", self.trig_edge_combo)
            self._dynamic_widgets.append(self.trig_edge_combo)

            self.targ_var_edit = QLineEdit("v(out)")
            self.targ_var_edit.setToolTip("Target signal")
            self.targ_var_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Target variable:", self.targ_var_edit)
            self._dynamic_widgets.append(self.targ_var_edit)

            self.targ_val_edit = QLineEdit("0.5")
            self.targ_val_edit.setToolTip("Target threshold value")
            self.targ_val_edit.textChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Target value:", self.targ_val_edit)
            self._dynamic_widgets.append(self.targ_val_edit)

            self.targ_edge_combo = QComboBox()
            self.targ_edge_combo.addItems(["RISE=1", "FALL=1", "CROSS=1"])
            self.targ_edge_combo.setToolTip("Target edge: rising, falling, or any crossing")
            self.targ_edge_combo.currentIndexChanged.connect(self._update_preview)
            self._dynamic_layout.addRow("Target edge:", self.targ_edge_combo)
            self._dynamic_widgets.append(self.targ_edge_combo)

        self._update_preview()

    def _update_preview(self):
        """Update the directive preview text."""
        data = self.get_data()
        if data:
            directive = build_directive(self._domain, data["name"], data["meas_type"], data["params"])
            self.preview_label.setText(directive)
        else:
            self.preview_label.setText("")

    def get_data(self):
        """Return structured data for this measurement.

        Returns:
            dict with keys: name, meas_type, params, directive
            or None if name is empty.
        """
        name = self.name_edit.text().strip()
        if not name:
            return None

        meas_type = self.type_combo.currentData()
        variable = self.var_edit.text().strip() or "v(out)"

        params = {"variable": variable}

        if meas_type in ("AVG", "RMS", "MIN", "MAX", "PP", "INTEG"):
            if hasattr(self, "from_edit"):
                params["from_val"] = self.from_edit.text().strip()
            if hasattr(self, "to_edit"):
                params["to_val"] = self.to_edit.text().strip()

        elif meas_type == "FIND_AT":
            if hasattr(self, "at_edit"):
                params["at_val"] = self.at_edit.text().strip() or "0"

        elif meas_type == "FIND_WHEN":
            if hasattr(self, "when_var_edit"):
                params["when_var"] = self.when_var_edit.text().strip() or "v(in)"
            if hasattr(self, "when_val_edit"):
                params["when_val"] = self.when_val_edit.text().strip() or "0.5"
            if hasattr(self, "cross_combo"):
                params["cross"] = self.cross_combo.currentText()

        elif meas_type == "TRIG_TARG":
            if hasattr(self, "trig_var_edit"):
                params["trig_var"] = self.trig_var_edit.text().strip() or "v(in)"
            if hasattr(self, "trig_val_edit"):
                params["trig_val"] = self.trig_val_edit.text().strip() or "0.5"
            if hasattr(self, "trig_edge_combo"):
                params["trig_edge"] = self.trig_edge_combo.currentText()
            if hasattr(self, "targ_var_edit"):
                params["targ_var"] = self.targ_var_edit.text().strip() or "v(out)"
            if hasattr(self, "targ_val_edit"):
                params["targ_val"] = self.targ_val_edit.text().strip() or "0.5"
            if hasattr(self, "targ_edge_combo"):
                params["targ_edge"] = self.targ_edge_combo.currentText()

        directive = build_directive(self._domain, name, meas_type, params)
        return {"name": name, "meas_type": meas_type, "params": params, "directive": directive}

    def _load_initial(self, data):
        """Pre-populate form from a data dict."""
        if "name" in data:
            self.name_edit.setText(data["name"])

        if "meas_type" in data:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == data["meas_type"]:
                    self.type_combo.setCurrentIndex(i)
                    break

        params = data.get("params", {})
        if "variable" in params:
            self.var_edit.setText(params["variable"])

        # Rebuild dynamic fields after setting the type
        self._rebuild_fields()

        meas_type = data.get("meas_type", "")
        if meas_type in ("AVG", "RMS", "MIN", "MAX", "PP", "INTEG"):
            if hasattr(self, "from_edit") and "from_val" in params:
                self.from_edit.setText(params["from_val"])
            if hasattr(self, "to_edit") and "to_val" in params:
                self.to_edit.setText(params["to_val"])
        elif meas_type == "FIND_AT":
            if hasattr(self, "at_edit") and "at_val" in params:
                self.at_edit.setText(params["at_val"])
        elif meas_type == "FIND_WHEN":
            if hasattr(self, "when_var_edit") and "when_var" in params:
                self.when_var_edit.setText(params["when_var"])
            if hasattr(self, "when_val_edit") and "when_val" in params:
                self.when_val_edit.setText(params["when_val"])
            if hasattr(self, "cross_combo") and "cross" in params:
                self.cross_combo.setCurrentText(params["cross"])
        elif meas_type == "TRIG_TARG":
            if hasattr(self, "trig_var_edit") and "trig_var" in params:
                self.trig_var_edit.setText(params["trig_var"])
            if hasattr(self, "trig_val_edit") and "trig_val" in params:
                self.trig_val_edit.setText(params["trig_val"])
            if hasattr(self, "trig_edge_combo") and "trig_edge" in params:
                self.trig_edge_combo.setCurrentText(params["trig_edge"])
            if hasattr(self, "targ_var_edit") and "targ_var" in params:
                self.targ_var_edit.setText(params["targ_var"])
            if hasattr(self, "targ_val_edit") and "targ_val" in params:
                self.targ_val_edit.setText(params["targ_val"])
            if hasattr(self, "targ_edge_combo") and "targ_edge" in params:
                self.targ_edge_combo.setCurrentText(params["targ_edge"])

        self._update_preview()


class MeasurementDialog(QDialog):
    """Dialog for managing a list of .meas measurement directives.

    Used as a sub-dialog from AnalysisDialog to configure automated
    measurements that run alongside the main analysis.
    """

    def __init__(self, domain="tran", parent=None, measurements=None):
        """
        Args:
            domain: "tran", "ac", or "dc" — determines the .meas domain keyword
            parent: parent widget
            measurements: optional list of measurement data dicts to pre-populate
        """
        super().__init__(parent)
        self._domain = domain
        self._entries = list(measurements or [])
        self.setWindowTitle("Configure Measurements")
        self.setMinimumWidth(550)
        self.setMinimumHeight(350)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        desc = QLabel(
            "Add automated measurements to the simulation. "
            "These generate .meas directives that ngspice evaluates "
            "and reports alongside the main analysis results."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Measurement table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Directive"])
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Buttons row
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add...")
        self.add_btn.setToolTip("Add a new measurement")
        self.add_btn.clicked.connect(self._add_measurement)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit...")
        self.edit_btn.setToolTip("Edit the selected measurement")
        self.edit_btn.clicked.connect(self._edit_measurement)
        btn_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setToolTip("Remove the selected measurement")
        self.remove_btn.clicked.connect(self._remove_measurement)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # OK / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_table()

    def _refresh_table(self):
        """Rebuild the table from self._entries."""
        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            name_item = QTableWidgetItem(entry.get("name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            type_item = QTableWidgetItem(entry.get("meas_type", ""))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, type_item)

            directive_item = QTableWidgetItem(entry.get("directive", ""))
            directive_item.setFlags(directive_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, directive_item)

        self._update_buttons()

    def _update_buttons(self):
        """Enable/disable edit and remove buttons based on selection."""
        has_selection = bool(self.table.selectedItems())
        self.edit_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)

    def _add_measurement(self):
        """Open sub-dialog to add a new measurement."""
        # Auto-generate a unique name
        existing_names = {e["name"] for e in self._entries}
        counter = len(self._entries) + 1
        while f"meas{counter}" in existing_names:
            counter += 1
        default_name = f"meas{counter}"

        dialog = MeasurementEntryDialog(
            domain=self._domain,
            parent=self,
            initial={"name": default_name},
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                self._entries.append(data)
                self._refresh_table()

    def _edit_measurement(self):
        """Open sub-dialog to edit the selected measurement."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._entries):
            return

        dialog = MeasurementEntryDialog(
            domain=self._domain,
            parent=self,
            initial=self._entries[row],
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                self._entries[row] = data
                self._refresh_table()

    def _remove_measurement(self):
        """Remove the selected measurement."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        del self._entries[row]
        self._refresh_table()

    def get_directives(self):
        """Return the list of .meas directive strings.

        Returns:
            list[str]: directive strings ready for netlist insertion
        """
        return [e["directive"] for e in self._entries if e.get("directive")]

    def get_entries(self):
        """Return the full list of measurement entry dicts.

        These include structured data (name, meas_type, params, directive)
        so they can be stored for later editing.
        """
        return list(self._entries)
