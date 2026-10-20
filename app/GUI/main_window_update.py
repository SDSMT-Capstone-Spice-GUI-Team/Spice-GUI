"""In-app update checker: startup version check and non-blocking notification.

This module wires the framework-free :mod:`services.update_checker` into the GUI.
It keeps all Qt concerns (the notification dialog, window placement) in the view
layer; the version comparison, network, and download logic live in
``services.update_checker`` so they stay testable without PyQt6.
"""

import logging

from controllers.settings_service import settings
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from services import update_checker

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """Non-blocking dialog offered when a newer release is available.

    The dialog lets the user download the installer, dismiss the notice, or
    suppress future notices for the current version.  All network and launch
    work is delegated to :mod:`services.update_checker`.
    """

    def __init__(self, current_version: str, latest_version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.setModal(False)  # non-blocking; keeps the app usable
        self.resize(420, 180)

        self._current_version = current_version
        self._latest_version = latest_version

        layout = QVBoxLayout(self)

        heading = QLabel(f"SDM-Spice — version {latest_version} is available")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        message = QLabel(f"You are running {current_version}. Download the latest installer to update.")
        message.setWordWrap(True)
        layout.addWidget(message)

        layout.addStretch(1)

        buttons = QWidget()
        button_layout = QVBoxLayout(buttons)
        self._download_btn = QPushButton("Download")
        self._download_btn.clicked.connect(self._on_download)
        button_layout.addWidget(self._download_btn)

        action_row = QWidget()
        action_layout = QVBoxLayout(action_row)
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.clicked.connect(self._on_dismiss)
        action_layout.addWidget(dismiss_btn)

        self._skip_btn = QPushButton("Don't remind me for this version")
        self._skip_btn.clicked.connect(self._on_skip)
        action_layout.addWidget(self._skip_btn)

        layout.addWidget(action_row)

    def _on_download(self):
        """Download and launch the installer, then close the dialog."""
        try:
            installer_path = update_checker.download_installer(
                remote_tag=self._latest_version,
            )
            if installer_path is None:
                # Fall back to opening the release page so the user isn't stuck.
                update_checker.open_installer(update_checker.LATEST_RELEASE_URL)
            else:
                update_checker.open_installer(installer_path)
        except Exception as exc:  # noqa: BLE001 — never surface a traceback to the user
            logger.warning("Update download failed: %s", exc)
        self.close()

    def _on_dismiss(self):
        """Close without downloading."""
        self.close()

    def _on_skip(self):
        """Persist the skip preference, then close."""
        settings.set(
            update_checker.SETTINGS_KEY_SKIP_VERSION,
            self._latest_version,
        )
        self.close()


class UpdateMixin:
    """Mixin providing the startup update-check flow for MainWindow."""

    def schedule_update_check(self, current_version: str):
        """Schedule the one-shot update check to run after the window paints.

        The check runs on the main event loop via ``QTimer`` so it does not block
        startup.  Nothing happens on offline machines (the network call is
        swallowed by :mod:`services.update_checker`).
        """

        def _run_check():
            try:
                latest = update_checker.latest_release_tag()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Update check raised: %s", exc)
                latest = None
            if not latest:
                return
            if update_checker.new_version_available(current_version, latest):
                skipped = settings.get_str(
                    update_checker.SETTINGS_KEY_SKIP_VERSION,
                    "",
                )
                if skipped == latest:
                    return
                dialog = UpdateDialog(current_version, latest, parent=self)
                dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                dialog.show()
            else:
                logger.debug("Running version %s is up to date (latest %s)", current_version, latest)

        QTimer.singleShot(0, _run_check)
