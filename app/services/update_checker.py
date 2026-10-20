"""Framework-free update checking against GitHub Releases.

This module is intentionally Qt-free so the version-comparison and network logic
can be unit-tested without importing PyQt6.  It only talks to the GitHub Releases
API, so all runtime imports are the standard library plus :mod:`requests` (which
is a pinned runtime dependency).

Responsibilities:

* Query the *latest* release tag for the bundled repo.
* Compare that tag against the running version.
* Download the release's ``.exe`` installer to a temp location and return its path
  so the caller (a Qt view) can launch it.

Every network or filesystem failure is logged and surfaced as ``None`` — the app
must never crash or show error dialogs when offline.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# GitHub repository the released bundles are published to.  Kept as a constant so
# the API and download URLs can be derived in one place.
REPO_OWNER = "SDSMT-Capstone-Spice-GUI-Team"
REPO_NAME = "Spice-GUI"
REPO = f"{REPO_OWNER}/{REPO_NAME}"

# Latest-release endpoint.  ``?per_page=1`` returns just the newest release,
# keeping the response small.
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPO}/releases/latest?per_page=1"

# Settings keys (persisted via ``settings_service``).
SETTINGS_KEY_SKIP_VERSION = "update/skipped_version"  # tag_name the user dismissed

# The installer asset name the release must include.  Kept lowercase for
# case-insensitive matching.
INSTALLER_ASSET_SUFFIX = ".exe"

DEFAULT_TIMEOUT_SECONDS = 5.0


def _parse_version(tag: str) -> Tuple[int, ...]:
    """Parse a dotted numeric version out of a release tag.

    Leading ``v`` is stripped and any non-numeric suffix (``-dev`` build info,
    git short hashes, etc.) is dropped.  The result is a tuple of the leading
    integer components, e.g. ``"v1.2.3-alpha"`` -> ``(1, 2, 3)``.
    """
    cleaned = tag.lstrip("vV")
    components: list[int] = []
    for chunk in cleaned.split("."):
        # ``"3abc"`` -> ``3``; take the leading integer digits if present.
        num = ""
        for char in chunk:
            if char.isdigit():
                num += char
            else:
                break
        if num:
            components.append(int(num))
        else:
            # First non-numeric chunk with no leading number — stop here.
            break
    return tuple(components)


def compare_versions(local: str, remote: str) -> int:
    """Return -1, 0, or 1 comparing ``local`` to ``remote``.

    * ``-1`` when ``local`` is older than ``remote``.
    * ``0`` when they are equal.
    * ``1`` when ``local`` is newer than ``remote``.

    Tags are compared numerically by leading dotted components.  A tag containing
    no numeric component (e.g. a bare ``"dev"``) is treated as older than any tag
    that does — this keeps ``dev`` builds from claiming to be newer than a real
    release, which is the intended behaviour for pre-release builds.
    """
    local_parts = _parse_version(local)
    remote_parts = _parse_version(remote)

    # Normalise to the same length for element-wise comparison.
    length = max(len(local_parts), len(remote_parts), 1)
    local_parts = local_parts + (0,) * (length - len(local_parts))
    remote_parts = remote_parts + (0,) * (length - len(remote_parts))

    for local_part, remote_part in zip(local_parts, remote_parts):
        if local_part < remote_part:
            return -1
        if local_part > remote_part:
            return 1
    return 0


def new_version_available(local: str, remote: str) -> bool:
    """Return True when ``remote`` (the published release) is newer than ``local``."""
    return compare_versions(local, remote) < 0


def latest_release_tag(*, api_url: str = LATEST_RELEASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[str]:
    """Return the latest published release tag, or ``None`` on any failure.

    A network timeout, connection error, non-200 status, malformed JSON, or an
    assetless response all result in ``None`` (logged) — never an exception.
    """
    try:
        response = requests.get(api_url, timeout=timeout)
    except requests.RequestException as exc:
        logger.debug("Update check request failed: %s", exc)
        return None

    if response.status_code != 200:
        logger.debug("Update check returned HTTP %s", response.status_code)
        return None

    try:
        data = response.json()
    except ValueError:
        logger.warning("Update check response was not valid JSON")
        return None

    tag = data.get("tag_name")
    if not tag:
        logger.debug("Latest release response had no tag_name")
        return None
    return str(tag)


def _find_installer_asset(release_data: dict) -> Optional[str]:
    """Return the browser_download_url for a matching ``.exe`` asset, if present."""
    assets = release_data.get("assets") or []
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(INSTALLER_ASSET_SUFFIX):
            url = asset.get("browser_download_url")
            if url:
                return url
    return None


def download_installer(
    *,
    remote_tag: str,
    api_url: str = LATEST_RELEASE_URL,
    tmp_dir: Optional[os.PathLike[str]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Optional[Path]:
    """Download the release's ``.exe`` installer to a temp file and return its path.

    Fetches the release metadata (no streaming) to locate the installer asset,
    then streams the asset itself so the body is not held entirely in memory.

    Returns ``None`` (logged) on any failure: network error, missing ``.exe``
    asset, or filesystem error.
    """
    # 1. Fetch the release metadata (no streaming) to locate the installer asset.
    try:
        release = requests.get(api_url, timeout=timeout)
    except requests.RequestException as exc:
        logger.debug("Installer download request failed: %s", exc)
        return None

    if release.status_code != 200:
        logger.debug("Installer download returned HTTP %s", release.status_code)
        return None

    try:
        release_data = release.json()
    except ValueError:
        logger.warning("Installer download response was not valid JSON")
        return None

    download_url = _find_installer_asset(release_data)
    if not download_url:
        logger.warning("Release %s has no .exe installer asset", remote_tag)
        return None

    # 2. Stream the actual installer download so we never hold the file in memory.
    try:
        response = requests.get(download_url, timeout=timeout, stream=True)
    except requests.RequestException as exc:
        logger.debug("Installer asset request failed: %s", exc)
        return None

    if response.status_code != 200:
        logger.debug("Installer asset returned HTTP %s", response.status_code)
        return None

    dest_dir = Path(tmp_dir) if tmp_dir is not None else Path(tempfile.gettempdir())
    try:
        # Use the release tag as the filename so the user sees a sensible name.
        safe_tag = "".join(ch if (ch.isalnum() or ch in ".-_") else "_" for ch in remote_tag)
        filename = f"SpiceGUI-{safe_tag}{INSTALLER_ASSET_SUFFIX}"
        target = dest_dir / filename

        with open(target, "wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
    except OSError as exc:
        logger.warning("Failed to write installer to %s: %s", target, exc)
        return None

    logger.info("Downloaded installer to %s", target)
    return target


def open_installer(path: os.PathLike[str] | str) -> None:
    """Launch the downloaded installer with the platform's default handler.

    Uses :func:`os.startfile` on Windows (the only supported platform).  On other
    platforms this is a no-op — the caller can fall back to reporting the path.
    """
    if sys.platform != "win32":
        logger.debug("open_installer is a no-op on platform %s", sys.platform)
        return
    try:
        os.startfile(path)  # noqa: S606 — user-chosen temp path, expected target
    except OSError as exc:
        logger.warning("Failed to open installer %s: %s", path, exc)
