"""
keybindings.py — Central registry for configurable keyboard shortcuts.

Stores default bindings and user overrides in a JSON config file.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default keybindings: action_name -> shortcut string
DEFAULTS = {
    # File
    "file.new": "Ctrl+N",
    "file.open": "Ctrl+O",
    "file.save": "Ctrl+S",
    "file.save_as": "Ctrl+Shift+S",
    "file.export_image": "Ctrl+E",
    "file.exit": "Ctrl+Q",
    # Edit
    "edit.undo": "Ctrl+Z",
    "edit.redo": "Ctrl+Shift+Z",
    "edit.copy": "Ctrl+C",
    "edit.cut": "Ctrl+X",
    "edit.paste": "Ctrl+V",
    "edit.delete": "Del",
    "edit.rotate_cw": "R",
    "edit.rotate_ccw": "Shift+R",
    "edit.flip_h": "F",
    "edit.flip_v": "Shift+F",
    "edit.select_all": "Ctrl+A",
    "edit.clear": "",
    # View
    "view.zoom_in": "Ctrl+=",
    "view.zoom_out": "Ctrl+-",
    "view.zoom_fit": "Ctrl+0",
    "view.zoom_reset": "Ctrl+1",
    # Simulation
    "sim.netlist": "Ctrl+G",
    "sim.run": "F5",
}

# Human-readable labels for each action
ACTION_LABELS = {
    "file.new": "New Circuit",
    "file.open": "Open...",
    "file.save": "Save",
    "file.save_as": "Save As...",
    "file.export_image": "Export Image...",
    "file.exit": "Exit",
    "edit.undo": "Undo",
    "edit.redo": "Redo",
    "edit.copy": "Copy",
    "edit.cut": "Cut",
    "edit.paste": "Paste",
    "edit.delete": "Delete Selected",
    "edit.rotate_cw": "Rotate Clockwise",
    "edit.rotate_ccw": "Rotate Counter-Clockwise",
    "edit.flip_h": "Flip Horizontal",
    "edit.flip_v": "Flip Vertical",
    "edit.select_all": "Select All",
    "edit.clear": "Clear Canvas",
    "view.zoom_in": "Zoom In",
    "view.zoom_out": "Zoom Out",
    "view.zoom_fit": "Fit to Circuit",
    "view.zoom_reset": "Reset Zoom",
    "sim.netlist": "Generate Netlist",
    "sim.run": "Run Simulation",
}

_CONFIG_DIR = Path.home() / ".spice-gui"
_CONFIG_FILE = _CONFIG_DIR / "keybindings.json"


class KeybindingsRegistry:
    """Central registry for keyboard shortcuts with load/save support."""

    def __init__(self, config_path=None):
        self._bindings = dict(DEFAULTS)
        self._config_path = Path(config_path) if config_path else _CONFIG_FILE
        self.load()

    def get(self, action_name):
        """Return the shortcut string for the given action."""
        return self._bindings.get(action_name, "")

    def set(self, action_name, shortcut):
        """Set the shortcut for the given action."""
        self._bindings[action_name] = shortcut

    def get_all(self):
        """Return a copy of all current bindings."""
        return dict(self._bindings)

    def get_conflicts(self):
        """Return list of (shortcut, [action1, action2, ...]) for duplicates."""
        shortcut_to_actions = {}
        for action, shortcut in self._bindings.items():
            if not shortcut:
                continue
            key = shortcut.lower()
            if key not in shortcut_to_actions:
                shortcut_to_actions[key] = []
            shortcut_to_actions[key].append(action)
        return [(s, actions) for s, actions in shortcut_to_actions.items() if len(actions) > 1]

    def reset_defaults(self):
        """Reset all bindings to defaults."""
        self._bindings = dict(DEFAULTS)

    def save(self):
        """Save user overrides to JSON config file."""
        # Only save non-default bindings
        overrides = {k: v for k, v in self._bindings.items() if v != DEFAULTS.get(k)}
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(overrides, f, indent=2)
        except OSError as e:
            logger.error("Failed to save keybindings: %s", e)

    def load(self):
        """Load user overrides from JSON config file."""
        if not self._config_path.exists():
            return
        try:
            with open(self._config_path) as f:
                overrides = json.load(f)
            for key, value in overrides.items():
                if key in self._bindings:
                    self._bindings[key] = value
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load keybindings config: %s", e)
