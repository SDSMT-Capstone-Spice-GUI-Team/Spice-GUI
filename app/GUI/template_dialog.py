"""Dialogs for circuit template save and load."""

from typing import Optional

from controllers.template_manager import TemplateInfo, TemplateManager
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton,
                             QTextEdit, QVBoxLayout)


class NewFromTemplateDialog(QDialog):
    """Dialog for creating a new circuit from a template."""

    def __init__(self, template_manager: TemplateManager, parent=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.selected_template: Optional[TemplateInfo] = None
        self._setup_ui()
        self._populate_templates()

    def _setup_ui(self):
        self.setWindowTitle("New from Template")
        self.setMinimumSize(500, 400)

        layout = QHBoxLayout(self)

        # Left: template list
        left = QVBoxLayout()
        left.addWidget(QLabel("Templates:"))
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_selection_changed)
        self.template_list.itemDoubleClicked.connect(self._on_double_click)
        left.addWidget(self.template_list)

        # Delete button for user templates
        self.delete_btn = QPushButton("Delete Template")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        left.addWidget(self.delete_btn)

        layout.addLayout(left, stretch=2)

        # Right: details
        right = QVBoxLayout()
        right.addWidget(QLabel("Details:"))

        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.name_label.setWordWrap(True)
        right.addWidget(self.name_label)

        self.category_label = QLabel("")
        self.category_label.setStyleSheet("color: gray;")
        right.addWidget(self.category_label)

        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        right.addWidget(self.description_label)

        right.addStretch()

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        right.addWidget(buttons)

        layout.addLayout(right, stretch=1)

    def _populate_templates(self):
        """Load and display all templates grouped by category."""
        self.template_list.clear()
        templates = self.template_manager.list_templates()

        current_category = None
        for template in templates:
            if template.category != current_category:
                current_category = template.category
                header = QListWidgetItem(f"--- {current_category} ---")
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                self.template_list.addItem(header)

            label = template.name
            if not template.is_builtin:
                label += " (user)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, template)
            item.setToolTip(template.description)
            self.template_list.addItem(item)

    def _on_selection_changed(self, current: Optional[QListWidgetItem], _previous):
        if current is None:
            self._clear_details()
            return

        template = current.data(Qt.ItemDataRole.UserRole)
        if template is None:
            self._clear_details()
            return

        self.selected_template = template
        self.name_label.setText(template.name)
        self.category_label.setText(f"Category: {template.category}")
        self.description_label.setText(template.description or "(No description)")
        self.ok_button.setEnabled(True)
        self.delete_btn.setEnabled(not template.is_builtin)

    def _clear_details(self):
        self.selected_template = None
        self.name_label.setText("")
        self.category_label.setText("")
        self.description_label.setText("")
        self.ok_button.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def _on_double_click(self, item: QListWidgetItem):
        template = item.data(Qt.ItemDataRole.UserRole)
        if template is not None:
            self.selected_template = template
            self.accept()

    def _on_delete(self):
        if self.selected_template is None or self.selected_template.is_builtin:
            return

        reply = QMessageBox.question(
            self,
            "Delete Template",
            f'Delete user template "{self.selected_template.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.template_manager.delete_template(self.selected_template.filepath)
            self._populate_templates()
            self._clear_details()

    def get_selected_template(self) -> Optional[TemplateInfo]:
        return self.selected_template


class SaveAsTemplateDialog(QDialog):
    """Dialog for saving the current circuit as a template."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Save as Template")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. My RC Filter")
        layout.addRow("Name:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(
            "Optional description of the circuit template..."
        )
        self.description_edit.setMaximumHeight(80)
        layout.addRow("Description:", self.description_edit)

        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText(
            "e.g. Filters, Amplifiers, Power (default: User)"
        )
        layout.addRow("Category:", self.category_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.name_edit.textChanged.connect(
            lambda text: self.ok_button.setEnabled(bool(text.strip()))
        )

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Template name is required.")
            return
        self.accept()

    def get_values(self) -> tuple[str, str, str]:
        """Return (name, description, category) entered by the user."""
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        category = self.category_edit.text().strip() or "User"
        return name, description, category
