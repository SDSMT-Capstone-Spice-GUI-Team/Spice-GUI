"""Ngspice path detection and preference management.

Locates a usable ngspice executable from three sources (in priority order):

1. **User preference** -- a previously-stored path in application settings.
2. **Bundled copy** -- shipped inside the PyInstaller distribution.
3. **System install** -- found on ``PATH`` or in well-known directories.

When both a bundled and system copy exist the first launch will ask the
user to choose (via :func:`prompt_ngspice_choice`).  The choice is
persisted so subsequent launches are non-interactive.
"""

import logging
import os
import platform
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Settings keys
SETTINGS_KEY_NGSPICE_PATH = "ngspice/path"
SETTINGS_KEY_NGSPICE_SOURCE = "ngspice/source"  # "bundled" | "system" | "custom"


def _is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _bundle_root() -> Path:
    """Return the root directory of the PyInstaller bundle.

    In a --onedir build this is the directory containing the executable.
    Falls back to the current working directory when not frozen.
    """
    if _is_frozen():
        return Path(sys.executable).parent
    # During development, allow an env-var override for testing.
    return Path(os.environ.get("SPICEGUI_BUNDLE_ROOT", Path.cwd()))


def bundled_ngspice_path() -> str | None:
    """Return the path to the bundled ngspice executable, or *None*.

    The bundled copy is expected at ``<bundle_root>/ngspice/bin/ngspice``
    (with ``.exe`` on Windows).
    """
    root = _bundle_root()
    exe_name = "ngspice.exe" if platform.system() == "Windows" else "ngspice"
    candidate = root / "ngspice" / "bin" / exe_name
    if candidate.is_file():
        return str(candidate)
    return None


def system_ngspice_path() -> str | None:
    """Return the path to a system-installed ngspice, or *None*.

    Checks ``PATH`` first, then platform-specific well-known directories.
    """
    which_result = shutil.which("ngspice")
    if which_result:
        return which_result

    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Program Files (x86)\ngspice\bin\ngspice.exe",
            r"C:\ngspice\bin\ngspice.exe",
            r"C:\ngspice-42\Spice64\bin\ngspice.exe",
            r"C:\Program Files\Spice64\bin\ngspice.exe",
            r"C:\Program Files\ngspice\bin\ngspice.exe",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/bin/ngspice",
            "/usr/local/bin/ngspice",
        ]
    elif system == "Darwin":
        candidates = [
            "/usr/local/bin/ngspice",
            "/opt/homebrew/bin/ngspice",
        ]
    else:
        candidates = []

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def resolve_ngspice_path(settings=None) -> str | None:
    """Return the ngspice executable path to use.

    Resolution order:

    1. Persisted user preference (if the file still exists).
    2. Bundled copy.
    3. System install.

    Parameters
    ----------
    settings:
        A :class:`~controllers.settings_service.SettingsService`-compatible
        object.  When *None*, settings are not consulted and only bundled /
        system detection is used (useful in tests and CLI mode).
    """
    # 1. Check stored preference
    if settings is not None:
        stored = settings.get_str(SETTINGS_KEY_NGSPICE_PATH, "")
        if stored and os.path.isfile(stored):
            logger.debug("Using stored ngspice path: %s", stored)
            return stored
        if stored:
            # Stored path no longer valid -- fall through to re-detect.
            logger.warning("Stored ngspice path no longer exists: %s", stored)

    # 2. Bundled copy
    bundled = bundled_ngspice_path()
    if bundled:
        logger.debug("Using bundled ngspice: %s", bundled)
        return bundled

    # 3. System install
    system = system_ngspice_path()
    if system:
        logger.debug("Using system ngspice: %s", system)
        return system

    return None


def detect_ngspice_sources() -> dict[str, str | None]:
    """Return a dict with keys ``bundled`` and ``system``, each
    containing the corresponding executable path or *None*.
    """
    return {
        "bundled": bundled_ngspice_path(),
        "system": system_ngspice_path(),
    }


def save_ngspice_preference(settings, path: str, source: str) -> None:
    """Persist the user's ngspice choice.

    Parameters
    ----------
    settings:
        SettingsService instance.
    path:
        Absolute path to the chosen ngspice executable.
    source:
        One of ``"bundled"``, ``"system"``, or ``"custom"``.
    """
    settings.set(SETTINGS_KEY_NGSPICE_PATH, path)
    settings.set(SETTINGS_KEY_NGSPICE_SOURCE, source)


def needs_user_choice(settings=None) -> bool:
    """Return True when both bundled and system ngspice exist and the user
    has not yet chosen which to use.
    """
    if settings is not None:
        stored = settings.get_str(SETTINGS_KEY_NGSPICE_PATH, "")
        if stored:
            return False

    sources = detect_ngspice_sources()
    return sources["bundled"] is not None and sources["system"] is not None
