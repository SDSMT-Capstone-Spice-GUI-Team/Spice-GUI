"""Tests for the manual "Check for Update" status dialog (issue #905).

Verifies that ``CheckUpdateDialog`` shows a checking indicator, drives a
``_CheckUpdateWorker`` to completion, and displays the correct message for each
``UpdateOutcome`` with a Download button that is only enabled when a release is
``AVAILABLE``. The worker's network call is monkeypatched so no real request is
made.
"""

from unittest.mock import MagicMock, patch

from GUI.update_dialog import CheckUpdateDialog, _CheckUpdateWorker
from PyQt6.QtCore import QCoreApplication
from services.update_checker import LatestRelease, UpdateOutcome, UpdateResult

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

    def test_download_calls_and_hides_buttons(self, qtbot, monkeypatch):
        monkeypatch.setattr("GUI.update_dialog.download_and_open_installer", MagicMock())
        dialog = CheckUpdateDialog(parent=None)
        dialog.start()
        qtbot.addWidget(dialog)
        # join the worker so the process can exit (avoid hanging on interpreter shutdown)
        qtbot.waitUntil(lambda: dialog._worker._finished, timeout=5000)
        result = UpdateResult(UpdateOutcome.AVAILABLE, latest=LatestRelease("1.2.0", "https://dl/SpiceGUI.exe"))
        dialog._on_check_finished(result)
        dialog._on_download()
        from GUI import update_dialog as mod

        mod.download_and_open_installer.assert_called_once_with(result.latest)
        assert not dialog._download_btn.isVisible()
        assert not dialog._dismiss_btn.isVisible()

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
