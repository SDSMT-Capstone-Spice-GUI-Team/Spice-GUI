"""
keybindings_dialog.py — Preferences dialog for configuring keyboard shortcuts.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .keybindings import ACTION_LABELS


class KeybindingsDialog(QDialog):
    """Dialog for viewing and editing keyboard shortcuts."""

    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Keybindings")
        self.setMinimumSize(500, 500)

        self._registry = registry
        self._edits = {}  # action_name -> new shortcut string

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Double-click a shortcut to change it. Press Escape to clear."))

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        header = self._table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        self._populate_table()

        # Buttons
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _populate_table(self):
        bindings = self._registry.get_all()
        actions = sorted(bindings.keys())
        self._table.setRowCount(len(actions))

        for row, action in enumerate(actions):
            # Action label (read-only)
            label = ACTION_LABELS.get(action, action)
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            label_item.setData(Qt.ItemDataRole.UserRole, action)
            self._table.setItem(row, 0, label_item)

            # Shortcut (editable via custom widget)
            shortcut = self._edits.get(action, bindings.get(action, ""))
            shortcut_item = QTableWidgetItem(shortcut)
            self._table.setItem(row, 1, shortcut_item)

        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def _on_cell_double_clicked(self, row, col):
        if col != 1:
            return

        action_item = self._table.item(row, 0)
        if action_item is None:
            return
        action_name = action_item.data(Qt.ItemDataRole.UserRole)

        # Use QKeySequenceEdit for shortcut capture
        editor = QKeySequenceEdit(self)
        current = self._table.item(row, 1)
        if current and current.text():
            editor.setKeySequence(QKeySequence(current.text()))

        # Replace the cell with the editor temporarily
        self._table.setCellWidget(row, 1, editor)
        editor.setFocus()

        def on_editing_finished():
            seq = editor.keySequence()
            shortcut_str = seq.toString()
            self._table.removeCellWidget(row, 1)
            shortcut_item = self._table.item(row, 1)
            if shortcut_item:
                shortcut_item.setText(shortcut_str)
            self._edits[action_name] = shortcut_str

        editor.editingFinished.connect(on_editing_finished)

    def _on_save(self):
        # Apply edits to registry
        for row in range(self._table.rowCount()):
            action_item = self._table.item(row, 0)
            shortcut_item = self._table.item(row, 1)
            if action_item and shortcut_item:
                action_name = action_item.data(Qt.ItemDataRole.UserRole)
                self._registry.set(action_name, shortcut_item.text())

        # Check for conflicts
        conflicts = self._registry.get_conflicts()
        if conflicts:
            msg_parts = []
            for shortcut, actions in conflicts:
                labels = [ACTION_LABELS.get(a, a) for a in actions]
                msg_parts.append(f"  {shortcut}: {', '.join(labels)}")
            QMessageBox.warning(
                self,
                "Shortcut Conflicts",
                "The following shortcuts are assigned to multiple actions:\n\n"
                + "\n".join(msg_parts)
                + "\n\nPlease resolve conflicts before saving.",
            )
            return

        self._registry.save()
        self.accept()

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            "Reset Keybindings",
            "Reset all keybindings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._registry.reset_defaults()
            self._edits.clear()
            self._table.clearContents()
            self._table.cellDoubleClicked.disconnect()
            self._populate_table()
