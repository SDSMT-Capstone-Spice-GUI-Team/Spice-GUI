"""Dialog for editing file-level recommended components."""

from models.component import COMPONENT_TYPES
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from .styles import COMPONENTS


class RecommendedComponentsDialog(QDialog):
    """Dialog to select which components are recommended for the current file."""

    def __init__(self, current_recommendations: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Recommended Components")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Select components to recommend in the palette for this file.\n"
                "Recommended components appear at the top of the palette."
            )
        )

        lists_layout = QHBoxLayout()

        # Available components (left)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Available:"))
        self._available_list = QListWidget()
        self._available_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self._available_list)
        lists_layout.addLayout(left_layout)

        # Buttons in the middle
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        self._add_btn = QPushButton(">")
        self._add_btn.setFixedWidth(40)
        self._add_btn.setToolTip("Add selected to recommended")
        self._add_btn.clicked.connect(self._add_selected)
        btn_layout.addWidget(self._add_btn)
        self._remove_btn = QPushButton("<")
        self._remove_btn.setFixedWidth(40)
        self._remove_btn.setToolTip("Remove selected from recommended")
        self._remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self._remove_btn)
        btn_layout.addStretch()
        lists_layout.addLayout(btn_layout)

        # Recommended components (right)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Recommended:"))
        self._recommended_list = QListWidget()
        self._recommended_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_layout.addWidget(self._recommended_list)
        lists_layout.addLayout(right_layout)

        layout.addLayout(lists_layout)

        # OK / Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Populate lists
        rec_set = set(current_recommendations)
        for comp_type in COMPONENT_TYPES:
            if comp_type not in COMPONENTS:
                continue
            if comp_type in rec_set:
                self._recommended_list.addItem(QListWidgetItem(comp_type))
            else:
                self._available_list.addItem(QListWidgetItem(comp_type))

    def _add_selected(self):
        """Move selected items from available to recommended."""
        for item in self._available_list.selectedItems():
            self._recommended_list.addItem(QListWidgetItem(item.text()))
            self._available_list.takeItem(self._available_list.row(item))

    def _remove_selected(self):
        """Move selected items from recommended to available."""
        for item in self._recommended_list.selectedItems():
            self._available_list.addItem(QListWidgetItem(item.text()))
            self._recommended_list.takeItem(self._recommended_list.row(item))

    def get_recommended(self) -> list[str]:
        """Return the list of recommended component type names."""
        return [self._recommended_list.item(i).text() for i in range(self._recommended_list.count())]
