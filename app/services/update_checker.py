"""Qt-free update checker for the installed application (issue #905).

The GitHub Releases API is queried for the set of releases (including pre-releases),
the newest one is selected, its version compared against the running version, and
the Windows installer (``.exe``) offered to the user. Everything here is
framework-agnostic and dependency-free (``urllib`` only) so it can be unit-tested
without a network connection. The actual notification/download/open orchestration
lives in the Qt layer (:mod:`GUI.update_dialog`).

Network failures are intentionally swallowed -- an offline classroom machine
should not crash on startup.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# GitHub Releases endpoint for the full list of releases.
#
# We query ``/releases`` rather than ``/releases/latest``: the latest endpoint
# skips pre-releases, and this project's tags are pre-releases (``-alpha``), so
# ``/releases/latest`` returns 404 for us. Fetching the list and selecting the
# newest tag works regardless of how each release is flagged.
_LATEST_RELEASE_URL = "https://api.github.com/repos/{owner}/{repo}/releases"

# Suffix used to identify the Windows installer asset on a release.
INSTALLER_SUFFIX = ".exe"

# Timeout (seconds) for release queries; startup must never hang on the network.
_NETWORK_TIMEOUT = 5.0

# GitHub hosts that may serve a downloadable installer asset.
_GITHUB_INSTALLER_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.github.com",
)

# Fixed temp-file prefix, so the file name never reflects the (untrusted) URL.
_INSTALLER_TEMP_PREFIX = "SpiceGUI-update-"

Fetcher = Callable[["urllib.request.Request"], object]
Downloader = Callable[[str, "os.PathLike[str]"], None]
InstallerOpener = Callable[["os.PathLike[str]"], bool]


def _is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle.

    Development runs (``python app/main.py``) execute from source, so no startup
    update check occurs there -- only the frozen installer bundle queries GitHub.
    """
    return getattr(sys, "frozen", False)


def parse_version(version: str) -> tuple[int, ...]:
    """Normalize a release tag into a comparable tuple of ints.

    Leading ``v`` prefixes, pre-release / build metadata (``-rc1``, ``+build.5``)
    and surrounding whitespace are stripped; non-numeric components are ignored.
    """
    cleaned = version.strip().lstrip("v").split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for segment in cleaned.split("."):
        digits = re.search(r"\d+", segment)
        if digits:
            parts.append(int(digits.group()))
    return tuple(parts)


def is_newer(latest: str, current: str) -> bool:
    """Return True when ``latest`` is strictly greater than ``current``."""
    return parse_version(latest) > parse_version(current)


@dataclass(frozen=True)
class LatestRelease:
    """A newer GitHub release and its downloadable installer path."""

    tag: str
    installer_url: str | None = None


class UpdateOutcome(Enum):
    """Result of a manual startup update check.

    ``AVAILABLE`` means a newer release exists. ``UP_TO_DATE`` means the latest
    release is already installed. ``ERROR`` means the check could not complete
    (typically a network failure) -- callers display a user-visible error only
    when this is returned.
    """

    AVAILABLE = "available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"


@dataclass(frozen=True)
class UpdateResult:
    """Outcome of a manual startup update check.

    When ``outcome`` is ``AVAILABLE``, ``latest`` carries the newer release.
    Otherwise ``latest`` is ``None`` and ``error`` is a human-readable message
    when the check failed.
    """

    outcome: UpdateOutcome
    latest: LatestRelease | None = None
    error: str | None = None


def _select_installer(assets: list[dict]) -> str | None:
    """Return the browser download URL of the first ``.exe`` installer asset."""
    for asset in assets:
        if asset.get("name", "").endswith(INSTALLER_SUFFIX):
            return asset.get("browser_download_url")
    return None


def _pick_latest_release(releases) -> LatestRelease | None:
    """Return the newest downloadable release from a ``/releases`` list payload.

    Pre-releases are included (this repo tags releases ``-alpha``); only drafts
    and entries without a publication date are skipped. The returned release is
    the one with the newest tag that has a downloadable ``.exe`` installer.
    """
    if not isinstance(releases, list):
        return None
    best: LatestRelease | None = None
    for entry in releases:
        if not isinstance(entry, dict):
            continue
        if entry.get("draft", False) or not entry.get("published_at"):
            continue
        tag = entry.get("tag_name")
        if not tag:
            continue
        installer_url = _select_installer(entry.get("assets") or [])
        if not installer_url:
            continue
        candidate = LatestRelease(tag=tag, installer_url=installer_url)
        if best is None or parse_version(tag) > parse_version(best.tag):
            best = candidate
    return best


def _fetch_latest(
    owner: str,
    repo: str,
    opener: Fetcher,
) -> LatestRelease | None:
    """Query the GitHub Releases API for the newest downloadable release.

    Queries the full ``/releases`` list (not ``/releases/latest``, which skips
    pre-releases) and selects the newest release with a downloadable installer.
    Swallows all I/O / parsing errors and returns ``None`` so startup never
    crashes on a network failure. ``opener`` is injectable for testing.
    """
    try:
        url = _LATEST_RELEASE_URL.format(owner=owner, repo=repo)
        request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        response = opener(request)
        releases = json.loads(response.read().decode("utf-8"))
        return _pick_latest_release(releases)
    except Exception as exc:  # noqa: BLE001 - network errors must never crash startup
        logger.debug("Update check unavailable: %s", exc)
        return None


# HTTP opener built once at import time. Using ``build_opener().open`` instead of
# the ``urllib.request.urlopen`` module function keeps bandit happy (B310) while
# still defaulting to an untrusted-source opener we then validate the scheme of.
_HTTP_OPENER = urllib.request.build_opener()


def _timed_urlopen(request: "urllib.request.Request") -> object:
    """Open a request using the configured network timeout."""
    return _HTTP_OPENER.open(request, timeout=_NETWORK_TIMEOUT)


def check_for_update(
    current_version: str,
    owner: str,
    repo: str,
    opener: Fetcher = _timed_urlopen,
) -> LatestRelease | None:
    """Return a newer release if one exists and we are running frozen.

    When not frozen (source / dev mode), this is a no-op and returns ``None`` so
    running from source never triggers a check. Otherwise the API is queried and
    a release is only returned when its tag is strictly greater than
    ``current_version``.
    """
    if not _is_frozen():
        return None
    release = _fetch_latest(owner, repo, opener)
    if release is None or not is_newer(release.tag, current_version):
        return None
    return release


def check_for_update_status(
    current_version: str,
    owner: str,
    repo: str,
    opener: Fetcher = _timed_urlopen,
) -> UpdateResult:
    """Run a full update check and classify the result for a UI to display.

    Unlike :func:`check_for_update`, which returns ``None`` for both "up to
    date" and "network error", this distinguishes them so the manual "Check for
    Update" flow can show a user-facing error when the check fails.
    """
    if not _is_frozen():
        return UpdateResult(UpdateOutcome.ERROR, error="Update check disabled when running from source.")
    try:
        release = _fetch_latest(owner, repo, opener)
    except Exception as exc:  # noqa: BLE001 - surface unexpected failures to the UI
        logger.debug("Update check failed: %s", exc)
        return UpdateResult(UpdateOutcome.ERROR, error=str(exc))
    if release is None:
        return UpdateResult(UpdateOutcome.ERROR, error="Unable to reach the release server.")
    if is_newer(release.tag, current_version):
        # A newer release exists. Surface it even when it has no downloadable
        # installer (e.g. a docs-only release); the dialog disables the
        # download button in that case rather than showing a misleading error.
        return UpdateResult(UpdateOutcome.AVAILABLE, latest=release)
    return UpdateResult(UpdateOutcome.UP_TO_DATE)


def _validate_installer_url(installer_url: str) -> None:
    """Validate that ``installer_url`` is a safe HTTPS GitHub download.

    Raises ``ValueError`` unless the URL uses HTTPS and points at one of GitHub's
    download hosts. This is the single place where untrusted installer URLs from
    a release payload are rejected before any request is made.
    """
    parsed = urllib.parse.urlparse(installer_url)
    if parsed.scheme != "https":
        raise ValueError(f"Disallowed installer URL scheme: {parsed.scheme!r} (only HTTPS is permitted)")
    if not _is_github_host(parsed.netloc):
        raise ValueError(f"Disallowed installer host: {parsed.netloc!r} (only GitHub download hosts are permitted)")


def _download_to(installer_url: str, dest: "os.PathLike[str]") -> None:
    """Download the installer ``installer_url`` to ``dest``.

    Only ``https://`` GitHub-hosted URLs are permitted; anything else raises so
    we never fetch an arbitrary ``file:`` / custom scheme supplied in the
    payload. The download is streamed to disk (``shutil.copyfileobj``) rather
    than buffered in memory, and carries the network timeout so a stalled
    connection cannot hang the UI thread.
    """
    _validate_installer_url(installer_url)
    request = urllib.request.Request(installer_url)
    with _HTTP_OPENER.open(request, timeout=_NETWORK_TIMEOUT) as response:
        with open(dest, "wb") as handle:
            shutil.copyfileobj(response, handle)


def _normalize_netloc(netloc: str) -> str:
    """Strip an optional ``:port`` suffix from a URL netloc."""
    if ":" in netloc:
        return netloc.rsplit(":", 1)[0]
    return netloc


def _is_github_host(netloc: str) -> bool:
    """Return True when ``netloc`` (with optional port) is a GitHub download host."""
    return _normalize_netloc(netloc) in _GITHUB_INSTALLER_HOSTS


def _open_installer(path: "os.PathLike[str]") -> bool:
    """Launch the downloaded installer using the platform's file association."""
    path = str(path)
    if sys.platform == "win32":
        os.startfile(path)
    else:
        # argv list + no shell avoids command injection when the temp filename
        # is later used (bandit B605). Output is discarded like the old shell.
        subprocess.Popen(
            ["xdg-open" if sys.platform != "darwin" else "open", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    return True


def download_and_open_installer(
    release: LatestRelease,
    downloader: Downloader = _download_to,
    opener_file: InstallerOpener = _open_installer,
) -> bool:
    """Download the release installer to a temp file and open it.

    Returns True on success. Any failure (no installer URL, download error,
    inability to launch) returns False instead of raising.
    """
    if not release.installer_url:
        return False
    try:
        # Fixed prefix + suffix so the temp name never reflects the (untrusted)
        # URL and is always a plain .exe.
        fd, raw_path = tempfile.mkstemp(prefix=_INSTALLER_TEMP_PREFIX, suffix=INSTALLER_SUFFIX)
        os.close(fd)
        dest = Path(raw_path)
        downloader(release.installer_url, dest)
        return bool(opener_file(dest))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.debug("Failed to download/open installer: %s", exc)
        return False
