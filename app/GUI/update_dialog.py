"""Notification dialog for in-app update (issue #905).

Presents a newer GitHub release to the user with three choices: download the
installer, dismiss the notification now, or skip reminders for this version.
All update *logic* lives in the Qt-free :mod:`services.update_checker`; this
module only renders it and reports the user's choice.
"""

import logging

from cli import __version__
from PyQt6.QtCore import QSize, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
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


def _quit_after_launch() -> None:
    """Quit the app so a launched installer can replace running files.

    Callers launch the installer (non-blocking) and then exit; on Windows the
    running executable otherwise stays locked while the installer installs.
    """
    app = QApplication.instance()
    if app is not None:
        app.quit()


def _is_version_skipped(tag: str) -> bool:
    """Return True when the user has already dismissed this release."""
    from controllers.settings_service import settings

    return settings.get_str("update/skipped_version", "") == tag


def _maybe_show_update(release: "LatestRelease | None", parent, skipped=None) -> None:
    """Show the update dialog when appropriate, once the worker reports a result.

    Runs on the main thread via the worker's signal. The dialog is shown only
    when a newer release exists and (unless ``skipped`` is supplied) the user has
    not dismissed this version. ``skipped`` is an optional zero-arg callable,
    called on the main thread, so settings access never leaves the UI thread.
    """
    if release is None:
        return
    if skipped is not None and skipped():
        return
    UpdateDialog(release, parent=parent).exec()


def schedule_update_check(
    parent,
    release: "LatestRelease | None" = None,
    delay_ms: int = NOTIFICATION_DELAY_MS,
    skipped=None,
):
    """Defer the startup update check, then show the dialog if a newer release exists.

    Only runs for frozen PyInstaller bundles (see ``update_checker._is_frozen``)
    so running from source never queries GitHub. A late ``release`` may be passed
    to avoid another round-trip to the network.

    The network check runs on a background worker (never the UI thread), so the
    window never freezes while GitHub is queried; the notification dialog is only
    shown once a newer release is confirmed. ``skipped`` is an optional zero-arg
    callable (main thread) that returns True when this version was dismissed.
    """
    worker = _UpdateCheckWorker(
        owner="SDSMT-Capstone-Spice-GUI-Team",
        repo="Spice-GUI",
        current_version=__version__,
    )
    worker.finished_check.connect(lambda release: _maybe_show_update(release, parent, skipped))
    worker.start()
    QTimer.singleShot(delay_ms, worker.stop)


class _UpdateCheckWorker(QThread):
    """Runs a one-shot startup update check on a background thread.

    Emits the newer release (or ``None`` when the app is up to date, or the
    check did not complete) on ``finished_check``. ``stop()`` requests a quick
    abort for a slow network by setting a flag the worker checks between calls.
    """

    finished_check = pyqtSignal(object)

    def __init__(self, owner: str, repo: str, current_version: str):
        super().__init__()
        self._owner = owner
        self._repo = repo
        self._current_version = current_version
        self._finished = False
        self._stopped = False

    def stop(self) -> None:
        """Request the worker to abort as soon as convenient."""
        self._stopped = True

    def run(self) -> None:
        if self._stopped:
            self.finished_check.emit(None)
            return
        result = check_for_update(
            current_version=self._current_version,
            owner=self._owner,
            repo=self._repo,
        )
        self.finished_check.emit(result)
        self._finished = True


class _DownloadWorker(QThread):
    """Downloads an installer on a background thread to avoid freezing the UI.

    Emits ``downloading`` with a short status string while the run is in
    progress and ``done`` with a bool (True = downloaded and launched) when it
    finishes. ``stop()`` requests an early abort; the check is only consulted on
    entry since :func:`download_and_open_installer` already carries a timeout.
    """

    downloading = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, release: LatestRelease):
        super().__init__()
        self._release = release
        self._finished = False
        self._stopped = False

    def stop(self) -> None:
        """Request the worker to abort as soon as convenient."""
        self._stopped = True

    def run(self) -> None:
        if self._stopped:
            self.done.emit(False)
            return
        self.downloading.emit("Downloading the installer…")
        success = download_and_open_installer(self._release)
        self.done.emit(success)
        self._finished = True


class UpdateDialog(QDialog):
    """Three-button dialog offering to download a newer release's installer."""

    def __init__(self, release: LatestRelease, parent=None):
        super().__init__(parent)
        self._release = release
        self._worker: _DownloadWorker | None = None
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

        # Optional status label shown while a download is in progress.
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # Standard buttons. We resolve the returned role to our action enum.
        #
        # "Skip this version" is added as a separate button with an explicit
        # ActionRole (not the ``Open`` standard button, whose accept role would
        # also emit ``accepted`` and trigger a download).
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        self._accept_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._accept_btn.setText("Download")
        self._dismiss_btn = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self._dismiss_btn.setText("Dismiss")
        self._skip_btn = self._buttons.addButton("Skip this version", QDialogButtonBox.ButtonRole.ActionRole)
        self._skip_btn.clicked.connect(self._skip)
        self._buttons.accepted.connect(self._accept)
        self._buttons.rejected.connect(self._reject)
        layout.addWidget(self._buttons)

    def _accept(self):
        """Download the installer on a background thread, then quit the app.

        Runs on the UI thread; the download itself is offloaded to a
        ``_DownloadWorker`` so the window never freezes (issue #4/#9). While it
        runs we show the status label and stop accepting further input.
        """
        self._status_label.show()
        self._status_label.setText("Downloading the installer…")
        self._accept_btn.setDisabled(True)
        self._dismiss_btn.setDisabled(True)
        self._skip_btn.setDisabled(True)
        worker = _DownloadWorker(self._release)
        worker.done.connect(self._accept_done)
        self._worker = worker
        worker.start()

    def _accept_done(self, success: bool) -> None:
        """Called on the main thread when the background download finishes.

        After a successful download we quit the app so the installer can replace
        the running executable (issue #12); on failure we restore the buttons.
        """
        if success:
            self._status_label.setText("The installer has launched. Quitting to let it install…")
            QTimer.singleShot(1000, self._quit_now)
        else:
            self._status_label.setText("Download failed. You can try again.")
            self._accept_btn.setDisabled(False)
            self._dismiss_btn.setDisabled(False)
            self._skip_btn.setDisabled(False)

    def _quit_now(self) -> None:
        """Close the dialog and quit the application."""
        self.done(0)
        _quit_after_launch()

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

        # Run the download on a background thread so the window never freezes
        # (issues #4/#9); report progress and quit on success.
        self._download_btn.setDisabled(True)
        self._dismiss_btn.setDisabled(True)
        self._status_label.show()
        self._status_label.setText("Downloading the installer…")

        worker = _DownloadWorker(release)
        worker.done.connect(self._on_download_done)
        self._worker = worker
        worker.start()

    def _on_download_done(self, success: bool) -> None:
        """Called on the main thread when the background download finishes.

        After a successful download we quit the app so the installer can replace
        the running executable (issue #12); on failure we re-enable the buttons.
        """
        if success:
            self._status_label.setText("The installer has launched. Quitting to let it install…")
            QTimer.singleShot(1000, self._quit_now)
        else:
            self._status_label.setText("Download failed. You can try again.")
            self._download_btn.setDisabled(False)
            self._dismiss_btn.setDisabled(False)

    def _quit_now(self) -> None:
        """Close the dialog and quit the application."""
        self.done(0)
        _quit_after_launch()

    def _dismiss(self):
        self.done(0)
