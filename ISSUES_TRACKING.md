# Update Checker — PR Review Issues

Tracking for the issues found in the `905-add-in-app-update-checker` PR review
(BananaPix4613). Addressed in order of severity. Keep this file so we never
lose track of what's going on.

## Blocking
- [x] **#2 `/releases/latest` 404s on prereleases** — DONE: `/releases` list + `_pick_latest_release`.
- [x] **#3 Hard-coded version** — DONE: `cli.py` imports `_version.py` with dev fallback; `_version.py` created; release workflow (`.github/workflows/release-installer.yml`) writes the git tag into `_version.py` before the PyInstaller build. Regression test added: `TestVersion.test_version_falls_back_when_version_file_missing` (`app/tests/unit/test_cli.py`).
- [x] **#1 Skip button also downloads** — DONE: button fix (separate `ActionRole` button), download now offloaded to `_DownloadWorker` (see #9). Regression tests added: `TestUpdateDialogSkip::test_skip_does_not_download_installer` and `::test_skip_still_downloads_when_download_pressed` (`app/tests/unit/test_update_check_dialog.py`).

## Security / robustness
- [x] **#4 No download timeout / loads installer into memory** — `_download_to` now times out and streams with `copyfileobj`; download also runs on `_DownloadWorker` now.
- [x] **#5 http:// allowed** — `_validate_installer_url` now requires HTTPS.
- [x] **#6 Host not verified** — `_is_github_host` restricts to GitHub download hosts.
- [x] **#7 Temp suffix from URL** — fixed prefix/suffix.

## UX / performance
- [x] **#8 `processEvents()` busy-wait** — removed the spin loop.
- [x] **#9 Startup check on UI thread** — added `_UpdateCheckWorker`; startup check now runs off-thread. Both "Download"/"Install" buttons now download on `_DownloadWorker` and show a "Downloading…" status label; the old synchronous UI-thread download is gone.
- [x] **#11 "no installer" reported before version check** — moved inside `is_newer`.
- [x] **#10 Double delay** (`main.py`) — DONE: main.py now passes `delay_ms=0` so there is a single 1.5s deferral.
- [x] **#12 Quit app after launching installer** — DONE: on download success both dialogs quit the app so the installer can replace the running executable.

## Verify
- [x] `make lint` (ruff + isort + black, all pass) and `make test` (4605 passed, 7 warnings) green.
