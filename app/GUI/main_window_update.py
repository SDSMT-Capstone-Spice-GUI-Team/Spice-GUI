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
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from services import update_checker

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """Dialog showing the result of an update check.

    Renders any :func:`services.update_checker.check_for_update` status so the
    same dialog serves the startup notification, the manual "Check for Update",
    and the up-to-date / network-error outcomes.  Network and download work is
    delegated to :mod:`services.update_checker`; this view only decides which
    buttons to show based on ``result["status"]``.

    The dialog displays what the user is running, what the latest release is
    (when the fetch succeeded), and a human-readable status line.
    """

    def __init__(
        self,
        result: dict,
        current_version: str = "?",
        parent=None,
    ):
        super().__init__(parent)
        self._result = result
        self.current_version = current_version
        self.version = result.get("version")

        if result["status"] == "update_available":
            self.setWindowTitle("Update Available")
        else:
            self.setWindowTitle("Check for Update")

        layout = QVBoxLayout(self)
        layout.addWidget(self._format_status(result))

        # Current / latest version info.
        version_widget = QWidget()
        version_layout = QHBoxLayout(version_widget)
        version_layout.addWidget(QLabel(f"You are running: {current_version}"))
        if result.get("version"):
            version_layout.addWidget(QLabel(f"Latest release: {result['version']}"))
        version_layout.addStretch(1)
        layout.addWidget(version_widget)

        # Buttons ----------------------------------------------------------
        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.clicked.connect(self.close)
        button_layout.addWidget(dismiss_btn)

        if result["status"] == "update_available":
            skip_btn = QPushButton("Don't remind me for this version")
            skip_btn.clicked.connect(self._on_skip)
            button_layout.addWidget(skip_btn)

            download_btn = QPushButton("Download")
            download_btn.setDefault(True)
            download_btn.clicked.connect(self._on_download)
            button_layout.addWidget(download_btn)

        layout.addWidget(buttons)

    def _format_status(self, result: dict) -> QLabel:
        status = result["status"]
        if status == "up_to_date":
            return QLabel("You are running the latest version.")
        if status == "network_error":
            return QLabel("Couldn't check for updates. Check your internet connection and try again.")
        if status == "skipped":
            return QLabel(
                "A newer release exists, but you chose not to be reminded. "
                f"Release {result.get('version')} is available. "
                "Use 'Check for Update' to install it, or click Dismiss.",
            )
        return QLabel(f"Version {result.get('version')} is available.")

    def _on_download(self):
        """Download and launch the installer, then close the dialog."""
        try:
            installer_path = update_checker.download_installer(remote_tag=self.version)
        except Exception as exc:  # noqa: BLE001 — never surface a traceback to the user
            logger.warning("Update download failed: %s", exc)
            installer_path = None
        if installer_path is None:
            # Fall back to opening the release page so the user isn't stuck.
            update_checker.open_installer(update_checker.LATEST_RELEASE_URL)
        else:
            update_checker.open_installer(installer_path)
        self.close()

    def _on_skip(self):
        """Persist the skip preference, then close."""
        if self.version:
            settings.set(update_checker.SETTINGS_KEY_SKIP_VERSION, self.version)
        self.close()


class UpdateMixin:
    """Mixin providing the startup and manual update-check flow for MainWindow."""

    def schedule_update_check(self, current_version: str):
        """Run the startup update check after the window paints.

        The check runs on the main event loop via ``QTimer`` so it does not block
        startup.  Nothing happens on offline machines (the network call is
        swallowed by :mod:`services.update_checker`).
        """
        self._current_version = current_version
        self._check_for_update(current_version)

    def _check_for_update(self, current_version: str | None = None, *, notify: bool = True):
        """Run an update check and (optionally) show the result dialog.

        Called by :meth:`schedule_update_check` (startup, ``notify=False``) and by
        the manual "Check for Update" help action (``notify=True``).  Never
        blocks: the network request runs on the main event loop and offline
        failures are logged, not shown.
        """
        if current_version is None:
            current_version = getattr(self, "_current_version", "?")

        def _run_check():
            try:
                latest = update_checker.latest_release_tag()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Update check raised: %s", exc)
                latest = None

            result = update_checker.check_for_update(
                current_version,
                latest,
                skipped_version=settings.get_str(
                    update_checker.SETTINGS_KEY_SKIP_VERSION,
                    "",
                ),
            )

            if result["status"] == "network_error":
                logger.debug("Update check failed: %s", current_version)
                return

            # Startup stays silent unless an update is available; the manual
            # check always surfaces the result so the user can see the fetch.
            if not notify and result["status"] != "update_available":
                return

            logger.debug("Running version %s is up to date", current_version)
            dialog = UpdateDialog(result, current_version, parent=self)
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.show()

        QTimer.singleShot(0, _run_check)
