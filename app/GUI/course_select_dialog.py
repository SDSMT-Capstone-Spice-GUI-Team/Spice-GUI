"""CourseSelectDialog - Startup / View-menu dialog for picking a course profile.

Users choose from available course profiles to tailor the GUI
(visible components, analyses, and panels) for their class.
"""

from __future__ import annotations

from controllers.profile_manager import profile_manager
from controllers.settings_service import settings
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

_SETTINGS_KEY = "course/profile_id"


class CourseSelectDialog(QDialog):
    """Modal dialog that lets users pick a course profile."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Course Profile")
        self.setMinimumWidth(420)
        self._setup_ui()
        self._populate_profiles()
        self._select_current_profile()

    # ── UI construction ──────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Choose a course profile to customise the interface:")
        header.setWordWrap(True)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)

        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: gray;")
        layout.addWidget(self._desc_label)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        self._ok_button = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)
        layout.addWidget(self._buttons)

    # ── Data ─────────────────────────────────────────────────────────

    def _populate_profiles(self):
        self._profiles = profile_manager.list_profiles()
        for profile in self._profiles:
            item = QListWidgetItem(profile.name)
            item.setData(Qt.ItemDataRole.UserRole, profile.id)
            self._list.addItem(item)

    def _select_current_profile(self):
        """Pre-select the remembered (or active) profile."""
        saved_id = settings.get_str(_SETTINGS_KEY, "")
        current_id = saved_id or profile_manager.get_profile().id
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == current_id:
                self._list.setCurrentRow(row)
                return

    # ── Slots ────────────────────────────────────────────────────────

    def _on_selection_changed(self, row: int):
        if row < 0 or row >= len(self._profiles):
            self._desc_label.setText("")
            self._ok_button.setEnabled(False)
            return
        self._desc_label.setText(self._profiles[row].description)
        self._ok_button.setEnabled(True)

    def _on_double_click(self, item: QListWidgetItem):
        self._on_accept()

    def _on_accept(self):
        profile = self.selected_profile()
        if profile is None:
            return
        profile_manager.set_profile(profile.id)
        settings.set(_SETTINGS_KEY, profile.id)
        self.accept()

    # ── Public API ───────────────────────────────────────────────────

    def selected_profile(self):
        """Return the currently highlighted CourseProfile, or None."""
        row = self._list.currentRow()
        if 0 <= row < len(self._profiles):
            return self._profiles[row]
        return None
