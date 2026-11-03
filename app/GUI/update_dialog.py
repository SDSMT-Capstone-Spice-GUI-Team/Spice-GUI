"""Notification dialog for in-app update (issue #905).

Presents a newer GitHub release to the user with three choices: download the
installer, dismiss the notification now, or skip reminders for this version.
All update *logic* lives in the Qt-free :mod:`services.update_checker`; this
module only renders it and reports the user's choice.
"""

import logging

from cli import __version__
from PyQt6.QtCore import QSize, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from services.update_checker import (
    LatestRelease,
    UpdateResult,
    check_for_update,
    check_for_update_status,
    download_and_open_installer,
)

logger = logging.getLogger(__name__)

# Delay (ms) before surfacing the update notification so the window paints first.
NOTIFICATION_DELAY_MS = 1500


def schedule_update_check(
    parent,
    release: "LatestRelease | None" = None,
    delay_ms: int = NOTIFICATION_DELAY_MS,
):
    """Defer the startup update check until the next tick, then show the dialog.

    Only runs for frozen PyInstaller bundles (see ``update_checker._is_frozen``)
    so running from source never queries GitHub. If a newer release exists and
    the user has not skipped it, the notification dialog is shown. A late
    ``release`` may be passed to avoid another round-trip to the network;
    otherwise the check is performed here (network errors are swallowed).
    """
    from controllers.settings_service import settings

    def run_check():
        current = release or check_for_update(
            current_version=__version__,
            owner="SDSMT-Capstone-Spice-GUI-Team",
            repo="Spice-GUI",
        )
        if current is None:
            return
        skipped = settings.get_str("update/skipped_version", "")
        if skipped == current.tag:
            return
        UpdateDialog(current, parent=parent).exec()

    QTimer.singleShot(delay_ms, run_check)


class UpdateDialog(QDialog):
    """Three-button dialog offering to download a newer release's installer."""

    def __init__(self, release: LatestRelease, parent=None):
        super().__init__(parent)
        self._release = release
        self.setWindowTitle("Update Available")
        self.resize(QSize(480, 200))
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(f"Version {self._release.tag} is available!")
        title.setWordWrap(True)
        layout.addWidget(title)

        message = QLabel(
            "A new version of SDM Spice is available. "
            "Click <b>Download</b> to fetch the installer, "
            "<b>Dismiss</b> to be reminded later, or "
            "<b>Skip this version</b> to stop being asked about it."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        # Standard buttons. We resolve the returned role to our action enum.
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Open,
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Download")
        self._buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Dismiss")
        self._buttons.button(QDialogButtonBox.StandardButton.Open).setText("Skip this version")
        self._buttons.accepted.connect(self._accept)
        self._buttons.rejected.connect(self._reject)
        self._buttons.button(QDialogButtonBox.StandardButton.Open).clicked.connect(self._skip)
        layout.addWidget(self._buttons)

    def _accept(self):
        """Download and open the installer, then close."""
        download_and_open_installer(self._release)
        self.done(0)

    def _reject(self):
        """Dismiss — close without doing anything."""
        self.done(0)

    def _skip(self):
        """Skip reminders for this version, then close."""
        from controllers.settings_service import settings

        settings.set("update/skipped_version", self._release.tag)
        self.done(0)


class _CheckUpdateWorker(QThread):
    """Runs the update check on a background thread to avoid freezing the UI."""

    checking = pyqtSignal()
    finished_check = pyqtSignal(object)

    def __init__(self, owner: str, repo: str, current_version: str):
        super().__init__()
        self._owner = owner
        self._repo = repo
        self._current_version = current_version
        self._finished = False

    def run(self) -> None:
        self.checking.emit()
        result = check_for_update_status(
            current_version=self._current_version,
            owner=self._owner,
            repo=self._repo,
        )
        self.finished_check.emit(result)
        self._finished = True


class CheckUpdateDialog(QDialog):
    """Modal dialog that runs a startup check and reports the outcome.

    Shows a "Checking…" indicator while the worker queries GitHub, then renders
    one of three outcomes: an update is available (with a Download button), the
    app is up to date, or the check failed with an error message.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: _CheckUpdateWorker | None = None
        self._result_text: QLabel
        self._download_btn: QPushButton
        self._dismiss_btn: QPushButton
        self._status_label: QLabel
        self._build_ui()

    def start(self) -> None:
        """Start the background worker. Call this after constructing the dialog."""
        self._start_worker()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setWindowTitle("Check for Updates")
        self.resize(QSize(480, 240))

        self._status_label = QLabel("Checking for updates…")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._result_text = QLabel()
        self._result_text.setWordWrap(True)
        self._result_text.hide()
        layout.addWidget(self._result_text)
        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._download_btn = QPushButton("Download")
        self._download_btn.setDisabled(True)
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.hide()
        button_row.addWidget(self._download_btn)
        self._dismiss_btn = QPushButton("Dismiss")
        self._dismiss_btn.clicked.connect(self._dismiss)
        self._dismiss_btn.hide()
        button_row.addWidget(self._dismiss_btn)
        layout.addLayout(button_row)

    def _start_worker(self):
        self._worker = _CheckUpdateWorker(
            owner="SDSMT-Capstone-Spice-GUI-Team",
            repo="Spice-GUI",
            current_version=__version__,
        )
        self._worker.finished_check.connect(self._on_check_finished)
        self._worker.start()

    def _on_check_finished(self, result: UpdateResult) -> None:
        self._status_label.hide()
        self._result_text.show()
        self._dismiss_btn.show()

        if result.outcome.value == "available":
            if result.latest is None or result.latest.installer_url is None:
                # We found a newer release but it has no downloadable installer
                # asset. Still surface the version so the user knows it exists, but
                # leave the Download button disabled.
                if result.latest is not None:
                    self._result_text.setText(
                        f"Version {result.latest.tag} is available, " "but no installer could be downloaded."
                    )
                else:
                    self._result_text.setText("Couldn't check for updates: no release information available.")
                return
            self._download_btn.setEnabled(True)
            self._download_btn._release = result.latest  # type: ignore[attr-defined]
            self._result_text.setText(f"Version {result.latest.tag} is available. Click Download to get the installer.")
        elif result.outcome.value == "up_to_date":
            self._result_text.setText("You're all set — this app is up to date.")
        else:
            self._result_text.setText(f"Couldn't check for updates: {result.error}")

    def _on_download(self) -> None:
        release = self._download_btn._release  # type: ignore[attr-defined]

        download_and_open_installer(release)
        self._download_btn.hide()
        self._dismiss_btn.hide()

    def _dismiss(self):
        self.done(0)
