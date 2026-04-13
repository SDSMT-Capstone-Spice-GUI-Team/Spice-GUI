"""Dialog for importing, browsing, and managing the subcircuit library."""

from GUI.subcircuit_gui_registration import register_subcircuit_gui
from models.subcircuit_library import SubcircuitLibrary, register_subcircuit_component
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class SubcircuitLibraryDialog(QDialog):
    """Dialog to import, view, and delete subcircuit definitions."""

    def __init__(self, library: SubcircuitLibrary, parent=None):
        super().__init__(parent)
        self._library = library
        self.setWindowTitle("Subcircuit Library")
        self.setMinimumSize(600, 400)
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Description
        desc = QLabel("Manage imported .subckt definitions. Imported subcircuits appear in the component palette.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Name", "Terminals", "Description", "Built-in"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

        # Buttons
        btn_layout = QHBoxLayout()
        self._import_btn = QPushButton("Import .subckt File...")
        self._import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(self._import_btn)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _refresh_table(self):
        names = self._library.names()
        self._table.setRowCount(len(names))
        for row, name in enumerate(names):
            defn = self._library.get(name)
            self._table.setItem(row, 0, QTableWidgetItem(name))
            self._table.setItem(row, 1, QTableWidgetItem(", ".join(defn.terminals)))
            self._table.setItem(row, 2, QTableWidgetItem(defn.description))
            builtin_item = QTableWidgetItem("Yes" if defn.builtin else "No")
            builtin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, builtin_item)

    def _on_import(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Subcircuit File(s)",
            "",
            "SPICE files (*.subckt *.sub *.lib *.sp *.spice *.cir *.mod);;All files (*)",
        )
        if not paths:
            return

        imported = []
        errors = []
        for path in paths:
            try:
                defs = self._library.import_file(path)
                for d in defs:
                    register_subcircuit_component(d)
                    register_subcircuit_gui(d)
                imported.extend(defs)
            except (ValueError, OSError, KeyError) as exc:
                errors.append(f"{path}: {exc}")

        self._refresh_table()

        if errors:
            QMessageBox.warning(
                self,
                "Import Errors",
                "Some files could not be imported:\n\n" + "\n".join(errors),
            )
        elif imported:
            names = ", ".join(d.name for d in imported)
            QMessageBox.information(self, "Import Successful", f"Imported subcircuits: {names}")

    def _on_delete(self):
        selected_rows = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        names_to_delete = []
        for row in sorted(selected_rows):
            name_item = self._table.item(row, 0)
            if name_item:
                names_to_delete.append(name_item.text())

        # Check for built-ins
        builtin_names = [n for n in names_to_delete if self._library.get(n) and self._library.get(n).builtin]
        if builtin_names:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                f"Built-in subcircuits cannot be deleted: {', '.join(builtin_names)}",
            )
            names_to_delete = [n for n in names_to_delete if n not in builtin_names]

        if not names_to_delete:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete {len(names_to_delete)} subcircuit(s)?\n\n" + ", ".join(names_to_delete),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for name in names_to_delete:
                self._library.remove(name)
            self._refresh_table()
