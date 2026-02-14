"""Simulation preset manager - save/load analysis configurations as named presets."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Built-in presets shipped with the application
BUILTIN_PRESETS = [
    {
        "name": "Quick Transient",
        "analysis_type": "Transient",
        "builtin": True,
        "params": {"duration": 0.01, "step": 1e-05, "startTime": 0},
    },
    {
        "name": "Audio AC Sweep",
        "analysis_type": "AC Sweep",
        "builtin": True,
        "params": {"fStart": 20, "fStop": 20000, "points": 100, "sweepType": "dec"},
    },
    {
        "name": "Wide AC Sweep",
        "analysis_type": "AC Sweep",
        "builtin": True,
        "params": {"fStart": 1, "fStop": 1e9, "points": 100, "sweepType": "dec"},
    },
    {
        "name": "Fine DC Sweep 0-5V",
        "analysis_type": "DC Sweep",
        "builtin": True,
        "params": {"source": "V1", "min": 0, "max": 5, "step": 0.01},
    },
    {
        "name": "Industrial Temp Range",
        "analysis_type": "Temperature Sweep",
        "builtin": True,
        "params": {"tempStart": -40, "tempStop": 85, "tempStep": 25},
    },
    {
        "name": "Audio Band Noise",
        "analysis_type": "Noise",
        "builtin": True,
        "params": {
            "output_node": "out",
            "source": "V1",
            "fStart": 20,
            "fStop": 20000,
            "points": 100,
            "sweepType": "dec",
        },
    },
    {
        "name": "Wideband Noise",
        "analysis_type": "Noise",
        "builtin": True,
        "params": {
            "output_node": "out",
            "source": "V1",
            "fStart": 1,
            "fStop": 1e9,
            "points": 100,
            "sweepType": "dec",
        },
    },
]


class PresetManager:
    """Manages simulation presets (built-in + user-defined).

    Presets are stored as JSON in a user-writable file. Built-in presets
    are always available and cannot be deleted.
    """

    def __init__(self, preset_file: Optional[Path] = None):
        if preset_file is None:
            preset_file = self._default_preset_path()
        self._preset_file = preset_file
        self._user_presets: list[dict] = []
        self._load()

    @staticmethod
    def _default_preset_path() -> Path:
        """Return the default path for the user presets file."""
        config_dir = Path.home() / ".spice-gui"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "simulation_presets.json"

    # --- Public API ---

    def get_presets(self, analysis_type: Optional[str] = None) -> list[dict]:
        """Return all presets, optionally filtered by analysis type."""
        all_presets = BUILTIN_PRESETS + self._user_presets
        if analysis_type:
            return [p for p in all_presets if p["analysis_type"] == analysis_type]
        return list(all_presets)

    def get_preset_by_name(
        self, name: str, analysis_type: Optional[str] = None
    ) -> Optional[dict]:
        """Look up a preset by name (and optionally analysis type)."""
        for p in self.get_presets(analysis_type):
            if p["name"] == name:
                return p
        return None

    def save_preset(self, name: str, analysis_type: str, params: dict) -> dict:
        """Save a user preset. Overwrites if name+type already exists."""
        # Don't overwrite built-in presets
        for bp in BUILTIN_PRESETS:
            if bp["name"] == name and bp["analysis_type"] == analysis_type:
                raise ValueError(f"Cannot overwrite built-in preset '{name}'")

        # Remove existing user preset with same name+type
        self._user_presets = [
            p
            for p in self._user_presets
            if not (p["name"] == name and p["analysis_type"] == analysis_type)
        ]

        preset = {
            "name": name,
            "analysis_type": analysis_type,
            "params": params.copy(),
        }
        self._user_presets.append(preset)
        self._save()
        return preset

    def delete_preset(self, name: str, analysis_type: Optional[str] = None) -> bool:
        """Delete a user preset. Returns True if deleted, False if not found or built-in."""
        for bp in BUILTIN_PRESETS:
            if bp["name"] == name and (
                analysis_type is None or bp["analysis_type"] == analysis_type
            ):
                return False  # Can't delete built-in

        before = len(self._user_presets)
        self._user_presets = [
            p
            for p in self._user_presets
            if not (
                p["name"] == name
                and (analysis_type is None or p["analysis_type"] == analysis_type)
            )
        ]
        if len(self._user_presets) < before:
            self._save()
            return True
        return False

    # --- Persistence ---

    def _load(self):
        """Load user presets from disk."""
        if not self._preset_file.exists():
            self._user_presets = []
            return
        try:
            data = json.loads(self._preset_file.read_text())
            self._user_presets = data.get("presets", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load presets from %s: %s", self._preset_file, e)
            self._user_presets = []

    def _save(self):
        """Write user presets to disk."""
        try:
            self._preset_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"presets": self._user_presets}
            self._preset_file.write_text(json.dumps(data, indent=2))
        except OSError as e:
            logger.error("Failed to save presets to %s: %s", self._preset_file, e)
