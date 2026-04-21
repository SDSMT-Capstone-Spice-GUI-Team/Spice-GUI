"""Palette layout profiles.

Profiles let users (e.g. instructors) restrict which components and
categories appear in the component palette without affecting the underlying
component model.  The "full" profile is the default and exposes the live
``COMPONENT_CATEGORIES`` dict so newly registered components/subcircuits
appear automatically.

Built-in profiles are defined in code (no I/O).  Optional user profiles
may be dropped into ``<settings_dir>/palette_profiles/*.json`` and are
discovered at call time.  Any error loading a user profile is logged and
ignored — palette behaviour falls back to the full layout.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from controllers.settings_service import settings
from models.component import COMPONENT_CATEGORIES

logger = logging.getLogger(__name__)

# Profile key stored in settings
_SETTINGS_KEY = "palette/profile"

# Special key meaning "use the full live COMPONENT_CATEGORIES dict"
FULL_PROFILE_KEY = "full"
DEFAULT_PROFILE_KEY = FULL_PROFILE_KEY

# Built-in non-full profiles. Each value is {display_name, categories}.
# ``categories`` is an ordered mapping of category-name -> [component-name,...].
# Component names that are not present in the registry are silently dropped
# by the palette, so these definitions are forward-compatible.
_BUILTIN_PROFILES: Dict[str, Dict] = {
    "circuits_1": {
        "display_name": "Circuits 1 (Passives + DC)",
        "categories": {
            "Passive": ["Resistor", "Capacitor", "Inductor"],
            "Sources": ["Voltage Source", "Current Source"],
            "Other": ["Ground"],
        },
    },
    "circuits_2": {
        "display_name": "Circuits 2 (+ Diodes, Op-Amps, AC)",
        "categories": {
            "Passive": ["Resistor", "Capacitor", "Inductor"],
            "Sources": ["Voltage Source", "Current Source", "Waveform Source"],
            "Semiconductors": ["Diode", "LED", "Zener Diode"],
            "Other": ["Op-Amp", "Ground", "Transformer"],
        },
    },
}


def _user_profiles_dir() -> Path:
    """Return the platform-appropriate user profiles directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Preferences"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "SDSMT" / "SDM Spice" / "palette_profiles"


def _load_user_profiles() -> Dict[str, Dict]:
    """Discover user-defined profiles from disk.

    Returns an empty dict on any error.  Each profile file should look like:

        {
          "name": "My Layout",
          "categories": {
            "Passives": ["Resistor", "Capacitor"],
            "Sources":  ["Voltage Source"]
          }
        }
    """
    out: Dict[str, Dict] = {}
    d = _user_profiles_dir()
    try:
        if not d.exists():
            return out
        for path in sorted(d.glob("*.json")):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                cats = data.get("categories")
                if not isinstance(cats, dict):
                    continue
                # Coerce to {str: [str, ...]} defensively
                clean: Dict[str, List[str]] = {}
                for cname, comps in cats.items():
                    if isinstance(cname, str) and isinstance(comps, list):
                        clean[cname] = [c for c in comps if isinstance(c, str)]
                key = f"user:{path.stem}"
                out[key] = {
                    "display_name": str(data.get("name", path.stem)),
                    "categories": clean,
                }
            except (OSError, json.JSONDecodeError, ValueError):
                logger.warning("Failed to load palette profile %s", path, exc_info=True)
    except OSError:
        logger.warning("Failed to scan palette profiles dir %s", d, exc_info=True)
    return out


def list_profiles() -> List[Tuple[str, str]]:
    """Return ``[(display_name, key), ...]`` for all available profiles."""
    items: List[Tuple[str, str]] = [("Full (all components)", FULL_PROFILE_KEY)]
    for key, prof in _BUILTIN_PROFILES.items():
        items.append((str(prof["display_name"]), key))
    for key, prof in _load_user_profiles().items():
        items.append((str(prof["display_name"]), key))
    return items


def get_active_profile_key() -> str:
    """Return the currently active profile key (defaults to ``FULL_PROFILE_KEY``)."""
    val = settings.get(_SETTINGS_KEY)
    if isinstance(val, str) and val:
        return val
    return DEFAULT_PROFILE_KEY


def set_active_profile_key(key: str) -> None:
    """Persist the active profile key."""
    settings.set(_SETTINGS_KEY, key)


def get_layout(key: str | None = None) -> Dict[str, List[str]]:
    """Return ``{category: [component, ...]}`` for the given profile key.

    Unknown keys fall back to the full layout.  Returned dicts for the
    ``full`` profile are the live ``COMPONENT_CATEGORIES`` reference so
    newly registered subcircuits show up without a reload; built-in and
    user profiles return their own static dicts.
    """
    if key is None:
        key = get_active_profile_key()
    if key == FULL_PROFILE_KEY:
        return COMPONENT_CATEGORIES
    if key in _BUILTIN_PROFILES:
        return _BUILTIN_PROFILES[key]["categories"]
    user = _load_user_profiles()
    if key in user:
        return user[key]["categories"]
    logger.info("Unknown palette profile %r — using full layout", key)
    return COMPONENT_CATEGORIES
