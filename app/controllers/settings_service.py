"""Centralized application settings persistence.

All QSettings access goes through this module, ensuring a single point
of contact for the platform's persistence layer.  GUI dialogs, mixins,
and controllers should import ``settings`` from this module rather than
constructing ``QSettings`` directly.
"""

import json
from typing import Any, List

from PyQt6.QtCore import QSettings

_ORG = "SDSMT"
_APP = "SDM Spice"


class SettingsService:
    """Thin wrapper around QSettings providing a single access point.

    Typed helpers (``get_bool``, ``get_int``, etc.) handle the
    string-coercion quirks of ``QSettings`` so callers don't have to.
    """

    def __init__(self) -> None:
        self._qs = QSettings(_ORG, _APP)

    # -- generic -------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Read a setting value (raw)."""
        return self._qs.value(key, default)

    def set(self, key: str, value: Any) -> None:
        """Write a setting value."""
        self._qs.setValue(key, value)

    # -- typed helpers --------------------------------------------------

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Read a boolean setting (handles QSettings string coercion)."""
        val = self._qs.value(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"

    def get_int(self, key: str, default: int = 0) -> int:
        """Read an integer setting."""
        val = self._qs.value(key, default)
        return int(val) if val is not None else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Read a float setting."""
        val = self._qs.value(key, default)
        return float(val) if val is not None else default

    def get_str(self, key: str, default: str = "") -> str:
        """Read a string setting."""
        val = self._qs.value(key, default)
        return str(val) if val is not None else default

    def get_json(self, key: str, default: Any = None) -> Any:
        """Read a JSON-encoded setting."""
        raw = self._qs.value(key)
        if raw is None:
            return default if default is not None else []
        try:
            return json.loads(raw) if isinstance(raw, str) else (default if default is not None else [])
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else []

    def set_json(self, key: str, value: Any) -> None:
        """Write a value as JSON string."""
        self._qs.setValue(key, json.dumps(value))

    def get_list(self, key: str) -> List[str]:
        """Read a list setting (QSettings may return a single string or a list)."""
        val = self._qs.value(key, [])
        if not isinstance(val, list):
            return []
        return val


# Module-level singleton — importable as ``from controllers.settings_service import settings``
settings = SettingsService()
