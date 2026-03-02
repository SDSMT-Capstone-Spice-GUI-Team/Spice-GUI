"""Centralized application settings persistence.

Framework-agnostic JSON-file backend.  GUI dialogs, mixins,
and controllers should import ``settings`` from this module rather than
managing persistence directly.
"""

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, List

_ORG = "SDSMT"
_APP = "SDM Spice"


def _default_settings_path() -> Path:
    """Return the platform-appropriate settings file path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Preferences"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / _ORG / _APP / "settings.json"


class SettingsService:
    """JSON-file backed settings store providing a single access point.

    Typed helpers (``get_bool``, ``get_int``, etc.) ensure callers
    get the right Python type without manual coercion.
    """

    def __init__(self, path: "Path | None" = None) -> None:
        self._path = path or _default_settings_path()
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load settings from disk (silently ignore missing/corrupt file)."""
        try:
            if self._path.exists():
                with open(self._path, "r") as f:
                    self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self) -> None:
        """Persist settings to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            pass  # Best-effort persistence

    @staticmethod
    def _encode(value: Any) -> Any:
        """Encode a value for JSON storage.

        Binary data (``bytes``, ``bytearray``, or objects with a
        ``data()`` method like ``QByteArray``) is base64-encoded so
        callers can store opaque blobs without knowing about JSON.
        """
        # Duck-type byte-array objects (has .data() returning bytes) without framework imports
        if hasattr(value, "data") and callable(value.data):
            try:
                raw = bytes(value.data())
                return {"__bytes__": base64.b64encode(raw).decode("ascii")}
            except (TypeError, AttributeError):
                pass
        if isinstance(value, (bytes, bytearray)):
            return {"__bytes__": base64.b64encode(value).decode("ascii")}
        return value

    @staticmethod
    def _decode(value: Any) -> Any:
        """Decode a value from JSON storage."""
        if isinstance(value, dict) and "__bytes__" in value:
            return base64.b64decode(value["__bytes__"])
        return value

    # -- generic -------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Read a setting value (raw)."""
        val = self._data.get(key)
        if val is None:
            return default
        return self._decode(val)

    def set(self, key: str, value: Any) -> None:
        """Write a setting value."""
        if value is None:
            self._data.pop(key, None)
        else:
            self._data[key] = self._encode(value)
        self._save()

    # -- typed helpers --------------------------------------------------

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Read a boolean setting."""
        val = self._data.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    def get_int(self, key: str, default: int = 0) -> int:
        """Read an integer setting."""
        val = self._data.get(key)
        return int(val) if val is not None else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Read a float setting."""
        val = self._data.get(key)
        return float(val) if val is not None else default

    def get_str(self, key: str, default: str = "") -> str:
        """Read a string setting."""
        val = self._data.get(key)
        return str(val) if val is not None else default

    def get_json(self, key: str, default: Any = None) -> Any:
        """Read a JSON-encoded setting."""
        raw = self._data.get(key)
        if raw is None:
            return default if default is not None else []
        # Handle legacy string-encoded JSON (from a previous set() call)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return default if default is not None else []
        # Native JSON value (stored by set_json)
        return raw

    def set_json(self, key: str, value: Any) -> None:
        """Write a value as a JSON-native setting."""
        self._data[key] = value
        self._save()

    def get_list(self, key: str) -> List[str]:
        """Read a list setting."""
        val = self._data.get(key)
        if not isinstance(val, list):
            return []
        return val


# Module-level singleton — importable as ``from controllers.settings_service import settings``
settings = SettingsService()
