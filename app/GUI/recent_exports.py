"""Track recent export operations for quick re-export.

Stores up to MAX_RECENT_EXPORTS entries in QSettings.  Each entry is a dict
with keys: path, format, export_function, timestamp.
"""

import json
import os
from datetime import datetime

from PyQt6.QtCore import QSettings

MAX_RECENT_EXPORTS = 5
SETTINGS_KEY = "export/recent_exports"


def get_recent_exports():
    """Return list of recent export dicts (most recent first).

    Each dict has keys: path, format, export_function, timestamp.
    Non-existent paths are filtered out.
    """
    settings = QSettings("SDSMT", "SDM Spice")
    raw = settings.value(SETTINGS_KEY, "[]")

    try:
        entries = json.loads(raw) if isinstance(raw, str) else []
    except (json.JSONDecodeError, TypeError):
        entries = []

    if not isinstance(entries, list):
        entries = []

    # Filter out files that no longer exist
    existing = [e for e in entries if isinstance(e, dict) and os.path.exists(e.get("path", ""))]
    if len(existing) != len(entries):
        settings.setValue(SETTINGS_KEY, json.dumps(existing))

    return existing


def add_recent_export(path, fmt, export_function):
    """Record an export operation.

    Args:
        path: file path that was exported to
        fmt: human-readable format name (e.g. "CSV", "Excel", "Image")
        export_function: callable name to repeat the export (e.g. "export_results_csv")
    """
    entry = {
        "path": str(path),
        "format": fmt,
        "export_function": export_function,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    entries = get_recent_exports()

    # Remove duplicate path
    entries = [e for e in entries if e.get("path") != entry["path"]]

    # Prepend
    entries.insert(0, entry)

    # Cap
    entries = entries[:MAX_RECENT_EXPORTS]

    settings = QSettings("SDSMT", "SDM Spice")
    settings.setValue(SETTINGS_KEY, json.dumps(entries))


def clear_recent_exports():
    """Clear all recent export entries."""
    settings = QSettings("SDSMT", "SDM Spice")
    settings.setValue(SETTINGS_KEY, "[]")
