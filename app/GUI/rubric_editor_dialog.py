"""Rubric editor dialog for visual rubric creation and editing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFileDialog, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QSpinBox, QSplitter, QVBoxLayout,
                             QWidget)

if TYPE_CHECKING:
    from grading.rubric import Rubric

logger = logging.getLogger(__name__)

# Parameter definitions per check type: list of (param_key, label, widget_type, default)
# widget_type: "str", "int", "float", "bool"
_CHECK_TYPE_PARAMS: dict[str, list[tuple[str, str, str, object]]] = {
    "component_exists": [
        ("component_id", "Component ID", "str", ""),
        ("component_type", "Component Type", "str", ""),
        ("min_count", "Min Count", "int", 1),
    ],
    "component_value": [
        ("component_id", "Component ID", "str", ""),
        ("expected_value", "Expected Value", "str", ""),
        ("tolerance_pct", "Tolerance (%)", "float", 0.0),
    ],
    "component_count": [
        ("component_type", "Component Type", "str", ""),
        ("expected_count", "Expected Count", "int", 0),
    ],
    "topology": [
        ("component_a", "Component A", "str", ""),
        ("component_b", "Component B", "str", ""),
        ("shared_node", "Shared Node (connected)", "bool", True),
    ],
    "ground": [
        ("component_id", "Component ID (optional)", "str", ""),
    ],
    "analysis_type": [
        ("expected_type", "Expected Analysis Type", "str", ""),
    ],
}


class RubricEditorDialog(QDialog):
    """Dialog for creating and editing grading rubrics visually."""

    def __init__(self, rubric: Optional[Rubric] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rubric Editor")
        self.setMinimumSize(700, 500)
        self._rubric: Optional[Rubric] = None
        self._param_widgets: dict[str, QWidget] = {}
        self._updating_ui = False
        self._init_ui()
        if rubric is not None:
            self._load_rubric_into_ui(rubric)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Title row
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Rubric Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Voltage Divider Assignment")
        self.title_edit.textChanged.connect(self._on_title_changed)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # Points summary
        self.points_label = QLabel("Total Points: 0")
        self.points_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.points_label)

        # Splitter: check list (left) | check editor (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left: checks list ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.checks_list = QListWidget()
        self.checks_list.currentRowChanged.connect(self._on_check_selected)
        left_layout.addWidget(self.checks_list)

        list_btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._on_add_check)
        list_btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._on_remove_check)
        list_btn_layout.addWidget(self.remove_btn)

        self.move_up_btn = QPushButton("Up")
        self.move_up_btn.setEnabled(False)
        self.move_up_btn.clicked.connect(self._on_move_up)
        list_btn_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("Down")
        self.move_down_btn.setEnabled(False)
        self.move_down_btn.clicked.connect(self._on_move_down)
        list_btn_layout.addWidget(self.move_down_btn)

        left_layout.addLayout(list_btn_layout)
        splitter.addWidget(left_widget)

        # --- Right: check detail editor ---
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        # Check ID and type
        basic_group = QGroupBox("Check Settings")
        basic_form = QFormLayout(basic_group)

        self.check_id_edit = QLineEdit()
        self.check_id_edit.setPlaceholderText("e.g., has_resistor")
        self.check_id_edit.textChanged.connect(self._on_detail_changed)
        basic_form.addRow("Check ID:", self.check_id_edit)

        self.check_type_combo = QComboBox()
        self.check_type_combo.addItems(sorted(_CHECK_TYPE_PARAMS.keys()))
        self.check_type_combo.currentTextChanged.connect(self._on_check_type_changed)
        basic_form.addRow("Check Type:", self.check_type_combo)

        self.points_spin = QSpinBox()
        self.points_spin.setRange(0, 1000)
        self.points_spin.setValue(1)
        self.points_spin.valueChanged.connect(self._on_detail_changed)
        basic_form.addRow("Points:", self.points_spin)

        detail_layout.addWidget(basic_group)

        # Dynamic parameters
        self.params_group = QGroupBox("Parameters")
        self.params_layout = QFormLayout(self.params_group)
        detail_layout.addWidget(self.params_group)

        # Feedback fields
        feedback_group = QGroupBox("Feedback Messages")
        feedback_form = QFormLayout(feedback_group)

        self.feedback_pass_edit = QLineEdit()
        self.feedback_pass_edit.setPlaceholderText("Message when check passes")
        self.feedback_pass_edit.textChanged.connect(self._on_detail_changed)
        feedback_form.addRow("Pass:", self.feedback_pass_edit)

        self.feedback_fail_edit = QLineEdit()
        self.feedback_fail_edit.setPlaceholderText("Message when check fails")
        self.feedback_fail_edit.textChanged.connect(self._on_detail_changed)
        feedback_form.addRow("Fail:", self.feedback_fail_edit)

        detail_layout.addWidget(feedback_group)
        detail_layout.addStretch()

        self.detail_widget.setEnabled(False)
        splitter.addWidget(self.detail_widget)

        splitter.setSizes([250, 450])
        layout.addWidget(splitter)

        # Validation label
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: red;")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        # Bottom buttons: Load, Save, OK, Cancel
        bottom_layout = QHBoxLayout()

        load_btn = QPushButton("Load...")
        load_btn.clicked.connect(self._on_load)
        bottom_layout.addWidget(load_btn)

        save_btn = QPushButton("Save...")
        save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(save_btn)

        bottom_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        bottom_layout.addWidget(button_box)

        layout.addLayout(bottom_layout)

        # Build initial param widgets for the default check type
        self._rebuild_param_widgets(self.check_type_combo.currentText())

    # --- Check list management ---

    def _on_add_check(self):
        """Add a new check with default values."""
        existing_ids = self._get_all_check_ids()
        n = 1
        while f"check_{n}" in existing_ids:
            n += 1
        check_id = f"check_{n}"

        check_data = {
            "check_id": check_id,
            "check_type": "component_exists",
            "points": 1,
            "params": {},
            "feedback_pass": "",
            "feedback_fail": "",
        }

        item = QListWidgetItem(f"{check_id} (component_exists, 1pt)")
        item.setData(Qt.ItemDataRole.UserRole, check_data)
        self.checks_list.addItem(item)
        self.checks_list.setCurrentItem(item)
        self._update_points_total()
        self._validate()

    def _on_remove_check(self):
        row = self.checks_list.currentRow()
        if row >= 0:
            self.checks_list.takeItem(row)
            self._update_points_total()
            self._validate()

    def _on_move_up(self):
        row = self.checks_list.currentRow()
        if row > 0:
            item = self.checks_list.takeItem(row)
            self.checks_list.insertItem(row - 1, item)
            self.checks_list.setCurrentRow(row - 1)

    def _on_move_down(self):
        row = self.checks_list.currentRow()
        if row < self.checks_list.count() - 1:
            item = self.checks_list.takeItem(row)
            self.checks_list.insertItem(row + 1, item)
            self.checks_list.setCurrentRow(row + 1)

    def _on_check_selected(self, row: int):
        has_selection = row >= 0
        self.remove_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and row > 0)
        self.move_down_btn.setEnabled(
            has_selection and row < self.checks_list.count() - 1
        )
        self.detail_widget.setEnabled(has_selection)

        if not has_selection:
            return

        item = self.checks_list.item(row)
        if item is None:
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if data is None:
            return

        self._updating_ui = True
        try:
            self.check_id_edit.setText(data.get("check_id", ""))
            self.check_type_combo.setCurrentText(
                data.get("check_type", "component_exists")
            )
            self.points_spin.setValue(data.get("points", 1))
            self.feedback_pass_edit.setText(data.get("feedback_pass", ""))
            self.feedback_fail_edit.setText(data.get("feedback_fail", ""))
            self._rebuild_param_widgets(data.get("check_type", "component_exists"))
            self._populate_param_widgets(data.get("params", {}))
        finally:
            self._updating_ui = False

    # --- Detail editing ---

    def _on_title_changed(self):
        """Re-validate when title changes."""
        self._validate()

    def _on_detail_changed(self):
        """Sync detail form changes back to the list item data."""
        if self._updating_ui:
            return

        row = self.checks_list.currentRow()
        if row < 0:
            return

        item = self.checks_list.item(row)
        if item is None:
            return

        data = item.data(Qt.ItemDataRole.UserRole) or {}
        data["check_id"] = self.check_id_edit.text().strip()
        data["check_type"] = self.check_type_combo.currentText()
        data["points"] = self.points_spin.value()
        data["feedback_pass"] = self.feedback_pass_edit.text()
        data["feedback_fail"] = self.feedback_fail_edit.text()
        data["params"] = self._collect_param_values()
        item.setData(Qt.ItemDataRole.UserRole, data)

        # Update list display text
        item.setText(f"{data['check_id']} ({data['check_type']}, {data['points']}pt)")

        self._update_points_total()
        self._validate()

    def _on_check_type_changed(self, check_type: str):
        """Rebuild parameter widgets when check type changes."""
        self._rebuild_param_widgets(check_type)
        if not self._updating_ui:
            self._on_detail_changed()

    # --- Dynamic parameter widgets ---

    def _rebuild_param_widgets(self, check_type: str):
        """Rebuild the parameter form for the given check type."""
        # Clear existing
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)
        self._param_widgets.clear()

        params = _CHECK_TYPE_PARAMS.get(check_type, [])
        for key, label, widget_type, default in params:
            widget = self._create_param_widget(widget_type, default)
            self._param_widgets[key] = widget
            self.params_layout.addRow(f"{label}:", widget)

    def _create_param_widget(self, widget_type: str, default: object) -> QWidget:
        """Create a parameter input widget of the appropriate type."""
        if widget_type == "int":
            w = QSpinBox()
            w.setRange(0, 10000)
            w.setValue(int(default) if default else 0)
            w.valueChanged.connect(self._on_detail_changed)
            return w
        elif widget_type == "float":
            w = QDoubleSpinBox()
            w.setRange(0.0, 100.0)
            w.setDecimals(2)
            w.setValue(float(default) if default else 0.0)
            w.valueChanged.connect(self._on_detail_changed)
            return w
        elif widget_type == "bool":
            w = QCheckBox()
            w.setChecked(bool(default))
            w.stateChanged.connect(self._on_detail_changed)
            return w
        else:
            w = QLineEdit()
            w.setText(str(default) if default else "")
            w.textChanged.connect(self._on_detail_changed)
            return w

    def _populate_param_widgets(self, params: dict):
        """Fill parameter widgets from a params dict."""
        for key, widget in self._param_widgets.items():
            value = params.get(key)
            if value is None:
                continue
            if isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

    def _collect_param_values(self) -> dict:
        """Collect current parameter values from widgets."""
        params = {}
        for key, widget in self._param_widgets.items():
            if isinstance(widget, QSpinBox):
                params[key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                params[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                params[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text:
                    params[key] = text
        return params

    # --- Validation ---

    def _validate(self) -> list[str]:
        """Validate the rubric and return a list of error messages."""
        errors: list[str] = []

        if not self.title_edit.text().strip():
            errors.append("Rubric title is required.")

        count = self.checks_list.count()
        if count == 0:
            errors.append("At least one check is required.")

        check_ids: set[str] = set()
        for i in range(count):
            item = self.checks_list.item(i)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            cid = data.get("check_id", "")
            if not cid:
                errors.append(f"Check #{i + 1} has no ID.")
            elif cid in check_ids:
                errors.append(f"Duplicate check ID: '{cid}'.")
            check_ids.add(cid)

            ctype = data.get("check_type", "")
            required = self._required_params_for_type(ctype)
            params = data.get("params", {})
            for rp in required:
                if not params.get(rp):
                    errors.append(f"Check '{cid}': missing required parameter '{rp}'.")

        self.validation_label.setText("\n".join(errors))
        return errors

    @staticmethod
    def _required_params_for_type(check_type: str) -> list[str]:
        """Return required param keys for a check type."""
        reqs = {
            "component_exists": [],  # at least one of id/type, but both optional
            "component_value": ["component_id", "expected_value"],
            "component_count": ["component_type", "expected_count"],
            "topology": ["component_a", "component_b"],
            "ground": [],
            "analysis_type": ["expected_type"],
        }
        return reqs.get(check_type, [])

    def _update_points_total(self):
        """Update the total points label from all checks."""
        total = 0
        for i in range(self.checks_list.count()):
            item = self.checks_list.item(i)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            total += data.get("points", 0)
        self.points_label.setText(f"Total Points: {total}")

    def _get_all_check_ids(self) -> set[str]:
        """Get all check IDs currently in the list."""
        ids: set[str] = set()
        for i in range(self.checks_list.count()):
            item = self.checks_list.item(i)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            cid = data.get("check_id", "")
            if cid:
                ids.add(cid)
        return ids

    # --- Save / Load ---

    def _on_save(self):
        """Save the rubric to a .spice-rubric file."""
        errors = self._validate()
        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "Please fix errors before saving:\n\n" + "\n".join(errors),
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rubric",
            "",
            "Rubric Files (*.spice-rubric);;All Files (*)",
        )
        if not filename:
            return

        try:
            rubric = self._build_rubric()
            from grading.rubric import save_rubric

            save_rubric(rubric, filename)
            QMessageBox.information(self, "Saved", f"Rubric saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save rubric:\n{e}")

    def _on_load(self):
        """Load a rubric from a .spice-rubric file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Rubric",
            "",
            "Rubric Files (*.spice-rubric);;All Files (*)",
        )
        if not filename:
            return

        try:
            from grading.rubric import load_rubric

            rubric = load_rubric(filename)
            self._load_rubric_into_ui(rubric)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load rubric:\n{e}")

    def _load_rubric_into_ui(self, rubric: Rubric):
        """Populate the UI from a Rubric object."""
        self._updating_ui = True
        try:
            self.title_edit.setText(rubric.title)
            self.checks_list.clear()

            for check in rubric.checks:
                data = check.to_dict()
                item = QListWidgetItem(
                    f"{data['check_id']} ({data['check_type']}, {data['points']}pt)"
                )
                item.setData(Qt.ItemDataRole.UserRole, data)
                self.checks_list.addItem(item)

            self._update_points_total()
            self._validate()

            if self.checks_list.count() > 0:
                self.checks_list.setCurrentRow(0)
        finally:
            self._updating_ui = False

    # --- Build rubric from UI ---

    def _build_rubric(self) -> Rubric:
        """Build a Rubric object from the current UI state."""
        from grading.rubric import Rubric, RubricCheck

        checks = []
        total = 0
        for i in range(self.checks_list.count()):
            item = self.checks_list.item(i)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            checks.append(RubricCheck.from_dict(data))
            total += data.get("points", 0)

        return Rubric(
            title=self.title_edit.text().strip(),
            total_points=total,
            checks=checks,
        )

    def _on_accept(self):
        """Validate and accept the dialog."""
        errors = self._validate()
        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "Please fix errors before proceeding:\n\n" + "\n".join(errors),
            )
            return

        self._rubric = self._build_rubric()
        self.accept()

    def get_rubric(self) -> Optional[Rubric]:
        """Return the built rubric, or None if dialog was cancelled."""
        return self._rubric
