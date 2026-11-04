"""Tests for the manual "Check for Update" status dialog (issue #905).

Verifies that ``CheckUpdateDialog`` shows a checking indicator, drives a
``_CheckUpdateWorker`` to completion, and displays the correct message for each
``UpdateOutcome`` with a Download button that is only enabled when a release is
``AVAILABLE``. The worker's network call is monkeypatched so no real request is
made.
"""

from unittest.mock import MagicMock, patch

import pytest
from GUI.update_dialog import (CheckUpdateDialog, UpdateDialog,
                               _CheckUpdateWorker)
from PyQt6.QtCore import QCoreApplication
from services.update_checker import (DownloadResult, LatestRelease,
                                     UpdateOutcome, UpdateResult)

OWNER = "SDSMT-Capstone-Spice-GUI-Team"
REPO = "Spice-GUI"


class TestCheckUpdateWorker:
    def test_worker_runs_to_completion(self, qtbot, monkeypatch):
        result = UpdateResult(UpdateOutcome.UP_TO_DATE)
        monkeypatch.setattr("GUI.update_dialog.check_for_update_status", lambda current_version, owner, repo: result)

        worker = _CheckUpdateWorker(owner=OWNER, repo=REPO, current_version="0.1.0")
        received: list = []
        worker.finished_check.connect(received.append)
        worker.start()
        qtbot.waitUntil(lambda: worker._finished, timeout=5000)
        QCoreApplication.processEvents()
        assert received == [result]

    def test_worker_passes_version_owner_repo(self, qtbot, monkeypatch):
        captured = {}

        def fake_status(current_version, owner, repo):
            captured.update(current_version=current_version, owner=owner, repo=repo)
            return UpdateResult(UpdateOutcome.ERROR, error="x")

        monkeypatch.setattr("GUI.update_dialog.check_for_update_status", fake_status)
        worker = _CheckUpdateWorker(owner="acme", repo="app", current_version="9.9.9")
        worker.start()
        qtbot.waitUntil(lambda: worker._finished, timeout=5000)
        assert captured == {"current_version": "9.9.9", "owner": "acme", "repo": "app"}


class TestCheckUpdateDialog:
    def test_initially_shows_checking(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            "GUI.update_dialog.check_for_update_status",
            lambda current_version, owner, repo: UpdateResult(UpdateOutcome.ERROR, error="x"),
        )
        dialog = CheckUpdateDialog(parent=None)
        dialog.start()
        qtbot.addWidget(dialog)
        assert dialog._status_label.text() == "Checking for updates…"
        # No result visible until the worker finishes.
        assert not dialog._result_text.isVisible()
        # join the worker so the process can exit (avoid hanging on interpreter shutdown)
        qtbot.waitUntil(lambda: dialog._worker._finished, timeout=5000)

    def test_available_shows_download(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            "GUI.update_dialog.check_for_update_status",
            lambda current_version, owner, repo: UpdateResult(
                UpdateOutcome.AVAILABLE, latest=LatestRelease("1.2.0", "https://dl/SpiceGUI.exe")
            ),
        )
        dialog = CheckUpdateDialog(parent=None)
        dialog.start()
        qtbot.addWidget(dialog)
        worker = dialog._worker
        qtbot.waitUntil(lambda: worker._finished, timeout=5000)
        QCoreApplication.processEvents()
        assert "1.2.0 is available" in dialog._result_text.text()
        assert dialog._download_btn.isEnabled()
        assert dialog._download_btn._release == LatestRelease("1.2.0", "https://dl/SpiceGUI.exe")

    def test_up_to_date_hides_download(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            "GUI.update_dialog.check_for_update_status",
            lambda current_version, owner, repo: UpdateResult(UpdateOutcome.UP_TO_DATE),
        )
        dialog = CheckUpdateDialog(parent=None)
        dialog.start()
        qtbot.addWidget(dialog)
        worker = dialog._worker
        qtbot.waitUntil(lambda: worker._finished, timeout=5000)
        QCoreApplication.processEvents()
        assert "up to date" in dialog._result_text.text().lower()
        assert not dialog._download_btn.isEnabled()

    def test_error_shows_message_no_download(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            "GUI.update_dialog.check_for_update_status",
            lambda current_version, owner, repo: UpdateResult(UpdateOutcome.ERROR, error="Offline"),
        )
        dialog = CheckUpdateDialog(parent=None)
        dialog.start()
        qtbot.addWidget(dialog)
        worker = dialog._worker
        qtbot.waitUntil(lambda: worker._finished, timeout=5000)
        QCoreApplication.processEvents()
        assert "Offline" in dialog._result_text.text()
        assert not dialog._download_btn.isEnabled()

    def test_download_runs_on_worker_and_quits_on_success(self, qtbot, monkeypatch):
        # The download runs on a background worker; patch the function where the
        # worker calls it so no real I/O happens.
        with patch(
            "GUI.update_dialog.download_and_open_installer",
            MagicMock(return_value=DownloadResult(launched=True)),
        ):
            dialog = CheckUpdateDialog(parent=None)
            dialog.start()
            qtbot.addWidget(dialog)
            qtbot.waitUntil(lambda: dialog._worker._finished, timeout=5000)
            result = UpdateResult(UpdateOutcome.AVAILABLE, latest=LatestRelease("1.2.0", "https://dl/SpiceGUI.exe"))
            dialog._on_check_finished(result)
            assert dialog._download_btn.isEnabled()
            dialog._on_download()
            # The download happened on a worker; the buttons are disabled while it runs.
            assert not dialog._download_btn.isEnabled()
            qtbot.waitUntil(lambda: dialog._worker._finished, timeout=5000)
            QCoreApplication.processEvents()
            # After a successful download the app quits via _quit_after_launch.
            assert dialog._status_label.text() == "The installer has launched. Quitting to let it install…"

    def test_download_reports_failure_and_reenables_buttons(self, qtbot, monkeypatch):
        with patch(
            "GUI.update_dialog.download_and_open_installer",
            MagicMock(return_value=DownloadResult(launched=False)),
        ):
            dialog = CheckUpdateDialog(parent=None)
            dialog.start()
            qtbot.addWidget(dialog)
            qtbot.waitUntil(lambda: dialog._worker._finished, timeout=5000)
            dialog._on_check_finished(
                UpdateResult(UpdateOutcome.AVAILABLE, latest=LatestRelease("1.2.0", "https://dl/SpiceGUI.exe"))
            )
            dialog._on_download()
            qtbot.waitUntil(lambda: dialog._worker._finished, timeout=5000)
            QCoreApplication.processEvents()
            assert dialog._status_label.text() == "Download failed. You can try again."
            assert dialog._download_btn.isEnabled()
            assert dialog._dismiss_btn.isEnabled()

    def test_uses_versioned_release_url(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            "GUI.update_dialog.check_for_update_status",
            lambda current_version, owner, repo: UpdateResult(
                UpdateOutcome.AVAILABLE, latest=LatestRelease("1.2.0", None)
            ),
        )
        dialog = CheckUpdateDialog(parent=None)
        dialog.start()
        qtbot.addWidget(dialog)
        worker = dialog._worker
        qtbot.waitUntil(lambda: worker._finished, timeout=5000)
        QCoreApplication.processEvents()
        assert "1.2.0" in dialog._result_text.text()
        # A release with no installer URL should be handled gracefully.
        assert not dialog._download_btn.isEnabled()


class TestUpdateDialogSkip:
    """The "Skip this version" button must not trigger a download (issue #1).

    Regression test: the Skip button used to share the ``Open`` standard button
    whose accept role also fired ``accepted`` and started a download. Skip is now
    a separate ``ActionRole`` button so clicking it neither downloads nor
    reports success.
    """

    def test_skip_does_not_download_installer(self, qtbot, monkeypatch):
        # If Skip were still wired to download, this assertion would fail: the
        # installer must never be fetched when the user chooses to skip.
        with patch("GUI.update_dialog.download_and_open_installer", MagicMock(return_value=DownloadResult(launched=False))) as download:
            dialog = UpdateDialog(LatestRelease("1.2.0", "https://dl/SpiceGUI.exe"), parent=None)
            qtbot.addWidget(dialog)
            # Patch settings so _skip can record the skip without real I/O.
            monkeypatch.setattr("controllers.settings_service.settings", MagicMock())
            dialog._skip()
            QCoreApplication.processEvents()
            download.assert_not_called()
            # Skip must not run a background worker either.
            assert dialog._worker is None

    def test_skip_still_downloads_when_download_pressed(self, qtbot, monkeypatch):
        # Sanity check: the download path itself still works — only Skip is
        # exempt — so the Skip test above is meaningful.
        with patch("GUI.update_dialog.download_and_open_installer", MagicMock(return_value=DownloadResult(launched=True))):
            dialog = UpdateDialog(LatestRelease("1.2.0", "https://dl/SpiceGUI.exe"), parent=None)
            qtbot.addWidget(dialog)
            monkeypatch.setattr("controllers.settings_service.settings", MagicMock())
            dialog._accept()
            qtbot.waitUntil(lambda: dialog._worker is None or dialog._worker._finished, timeout=5000)
            QCoreApplication.processEvents()
            assert dialog._status_label.text() == "The installer has launched. Quitting to let it install…"


def test_check_for_update_shows_dialog(qtbot, monkeypatch):
    """Clicking "Check for Update" must display the dialog (issue #905).

    Regression test: the HelpMixin hook used to create the dialog and start the
    worker but never call ``show()``, so in dev mode (where the worker returns an
    error immediately) the user saw nothing.
    """
    from GUI.main_window_help import HelpMixin
    from GUI.update_dialog import CheckUpdateDialog

    monkeypatch.setattr(
        "GUI.update_dialog.check_for_update_status",
        lambda current_version, owner, repo: UpdateResult(UpdateOutcome.ERROR, error="x"),
    )

    class Host(HelpMixin):
        pass

    host = Host()
    with patch("GUI.update_dialog.CheckUpdateDialog") as dialog_cls:
        fake_dialog = MagicMock()
        fake_dialog._worker = MagicMock()
        fake_dialog._worker._finished = True
        dialog_cls.return_value = fake_dialog

        host._check_for_update()

        dialog_cls.assert_called_once_with(host)
        fake_dialog.show.assert_called_once_with()
        fake_dialog.start.assert_called_once_with()
