"""Preview dialog for assignment templates showing metadata and circuit summary."""

from typing import Optional

from models.template import TemplateData
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class TemplatePreviewDialog(QDialog):
    """Dialog to preview a template before loading it.

    Shows metadata (title, author, description, tags, instructions)
    and a read-only component/wire summary of the starter circuit.
    """

    def __init__(self, template_data: TemplateData, parent=None):
        super().__init__(parent)
        self._template = template_data
        self._setup_ui()
        self._populate(template_data)

    def _setup_ui(self):
        self.setWindowTitle("Template Preview")
        self.setMinimumSize(600, 450)

        layout = QVBoxLayout(self)

        # --- Metadata section ---
        meta_group = QGroupBox("Template Information")
        meta_layout = QVBoxLayout(meta_group)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.title_label.setWordWrap(True)
        meta_layout.addWidget(self.title_label)

        info_row = QHBoxLayout()
        self.author_label = QLabel()
        self.author_label.setStyleSheet("color: gray;")
        info_row.addWidget(self.author_label)
        self.date_label = QLabel()
        self.date_label.setStyleSheet("color: gray;")
        info_row.addWidget(self.date_label)
        info_row.addStretch()
        meta_layout.addLayout(info_row)

        self.tags_label = QLabel()
        self.tags_label.setWordWrap(True)
        meta_layout.addWidget(self.tags_label)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        meta_layout.addWidget(self.description_label)

        layout.addWidget(meta_group)

        # --- Instructions section ---
        instructions_group = QGroupBox("Instructions")
        instructions_layout = QVBoxLayout(instructions_group)

        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMaximumHeight(120)
        instructions_layout.addWidget(self.instructions_text)

        layout.addWidget(instructions_group)

        # --- Circuit preview section ---
        circuit_group = QGroupBox("Starter Circuit Preview")
        circuit_layout = QVBoxLayout(circuit_group)

        self.circuit_tree = QTreeWidget()
        self.circuit_tree.setHeaderLabels(["Item", "Details"])
        self.circuit_tree.setMaximumHeight(180)
        self.circuit_tree.setAlternatingRowColors(True)
        circuit_layout.addWidget(self.circuit_tree)

        self.circuit_summary = QLabel()
        self.circuit_summary.setStyleSheet("color: gray; font-style: italic;")
        circuit_layout.addWidget(self.circuit_summary)

        layout.addWidget(circuit_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Load Template")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, template: TemplateData):
        """Fill the dialog with template data."""
        meta = template.metadata

        # Metadata
        self.title_label.setText(meta.title or "(Untitled)")
        self.author_label.setText(f"Author: {meta.author}" if meta.author else "")
        self.date_label.setText(f"Created: {meta.created}" if meta.created else "")
        self.tags_label.setText(f"Tags: {', '.join(meta.tags)}" if meta.tags else "")
        self.description_label.setText(meta.description or "(No description)")

        # Instructions
        if template.instructions:
            self.instructions_text.setPlainText(template.instructions)
        else:
            self.instructions_text.setPlainText("(No instructions provided)")

        # Circuit preview
        self._populate_circuit_tree(template.starter_circuit)

    def _populate_circuit_tree(self, circuit_data: Optional[dict]):
        """Build a tree view of the circuit components and wires."""
        self.circuit_tree.clear()

        if circuit_data is None:
            self.circuit_summary.setText("No starter circuit (empty canvas)")
            return

        components = circuit_data.get("components", [])
        wires = circuit_data.get("wires", [])

        # Components
        if components:
            comp_root = QTreeWidgetItem(self.circuit_tree, ["Components", f"({len(components)})"])
            comp_root.setExpanded(True)
            for comp in components:
                comp_id = comp.get("component_id", "?")
                comp_type = comp.get("component_type", "?")
                value = comp.get("value", "")
                item = QTreeWidgetItem(comp_root, [comp_id, f"{comp_type} — {value}"])

        # Wires
        if wires:
            wire_root = QTreeWidgetItem(self.circuit_tree, ["Wires", f"({len(wires)})"])
            for wire in wires:
                start = f"{wire.get('start_component_id', '?')}:{wire.get('start_terminal', '?')}"
                end = f"{wire.get('end_component_id', '?')}:{wire.get('end_terminal', '?')}"
                QTreeWidgetItem(wire_root, [f"{start} → {end}", ""])

        # Analysis info
        analysis = circuit_data.get("analysis_type")
        if analysis and analysis != "DC Operating Point":
            QTreeWidgetItem(self.circuit_tree, ["Analysis Type", analysis])

        # Summary
        has_ref = self._template.reference_circuit is not None
        parts = [
            f"{len(components)} component(s)",
            f"{len(wires)} wire(s)",
        ]
        if has_ref:
            parts.append("reference circuit included")
        self.circuit_summary.setText(", ".join(parts))

        self.circuit_tree.resizeColumnToContents(0)

    def get_template(self) -> TemplateData:
        """Return the template data (for use after accept)."""
        return self._template
