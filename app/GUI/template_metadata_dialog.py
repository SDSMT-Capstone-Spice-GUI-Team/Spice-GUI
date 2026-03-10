"""Dialog for entering template metadata when saving as assignment template."""

from models.template import TemplateMetadata
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QPlainTextEdit, QVBoxLayout


class TemplateMetadataDialog(QDialog):
    """Dialog for entering assignment template metadata.

    Collects title, description, author, tags, and instructions
    when an instructor saves a circuit as a template.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save as Assignment Template")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., RC Low-Pass Filter Lab")
        form.addRow("Title:", self.title_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g., Dr. Smith")
        form.addRow("Author:", self.author_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of the assignment")
        form.addRow("Description:", self.description_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Comma-separated tags, e.g., filters, AC, lab-3")
        form.addRow("Tags:", self.tags_edit)

        layout.addLayout(form)

        self.instructions_edit = QPlainTextEdit()
        self.instructions_edit.setPlaceholderText("Assignment instructions for students...")
        self.instructions_edit.setMaximumHeight(120)
        layout.addWidget(self.instructions_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.title_edit.text().strip():
            self.title_edit.setFocus()
            self.title_edit.setStyleSheet("border: 1px solid red;")
            return
        self.accept()

    def get_metadata(self) -> TemplateMetadata:
        """Return the metadata entered in the dialog."""
        from datetime import date

        tags_text = self.tags_edit.text().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []

        return TemplateMetadata(
            title=self.title_edit.text().strip(),
            description=self.description_edit.text().strip(),
            author=self.author_edit.text().strip(),
            created=date.today().isoformat(),
            tags=tags,
        )

    def get_instructions(self) -> str:
        """Return the instructions text entered in the dialog."""
        return self.instructions_edit.toPlainText().strip()
