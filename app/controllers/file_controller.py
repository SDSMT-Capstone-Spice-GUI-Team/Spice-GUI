"""
FileController - Handles circuit file I/O and session persistence.

This module contains no Qt dependencies. File dialog interaction
is the responsibility of the view layer.
"""

import json
import os
from pathlib import Path
from typing import Optional

from models.circuit import CircuitModel


SESSION_FILE = "last_session.txt"


def validate_circuit_data(data) -> None:
    """
    Validate JSON structure before loading.

    Raises ValueError with a descriptive message if anything is wrong.
    This is the same validation that was previously in CircuitCanvas._validate_circuit_data.
    """
    if not isinstance(data, dict):
        raise ValueError("File does not contain a valid circuit object.")

    if 'components' not in data or not isinstance(data['components'], list):
        raise ValueError("Missing or invalid 'components' list.")
    if 'wires' not in data or not isinstance(data['wires'], list):
        raise ValueError("Missing or invalid 'wires' list.")

    comp_ids = set()
    for i, comp in enumerate(data['components']):
        for key in ('id', 'type', 'value', 'pos'):
            if key not in comp:
                raise ValueError(
                    f"Component #{i + 1} is missing required field '{key}'.")
        pos = comp['pos']
        if not isinstance(pos, dict) or 'x' not in pos or 'y' not in pos:
            raise ValueError(
                f"Component '{comp.get('id', i)}' has invalid position data.")
        if not isinstance(pos['x'], (int, float)) or not isinstance(pos['y'], (int, float)):
            raise ValueError(
                f"Component '{comp['id']}' position values must be numeric.")
        comp_ids.add(comp['id'])

    for i, wire in enumerate(data['wires']):
        for key in ('start_comp', 'end_comp', 'start_term', 'end_term'):
            if key not in wire:
                raise ValueError(
                    f"Wire #{i + 1} is missing required field '{key}'.")
        if wire['start_comp'] not in comp_ids:
            raise ValueError(
                f"Wire #{i + 1} references unknown component '{wire['start_comp']}'.")
        if wire['end_comp'] not in comp_ids:
            raise ValueError(
                f"Wire #{i + 1} references unknown component '{wire['end_comp']}'.")


class FileController:
    """
    Manages circuit file I/O and session persistence.

    Handles saving/loading circuit data as JSON and tracking
    the current file path for quick-save and session restore.
    """

    def __init__(self, model: Optional[CircuitModel] = None,
                 circuit_ctrl=None,
                 session_file: str = SESSION_FILE):
        self.model = model or CircuitModel()
        self.circuit_ctrl = circuit_ctrl  # Phase 5: For observer notifications
        self.current_file: Optional[Path] = None
        self._session_file = session_file

    def new_circuit(self) -> None:
        """Clear the circuit and reset file state."""
        self.model.clear()
        self.current_file = None

    def save_circuit(self, filepath) -> None:
        """
        Save circuit to JSON file.

        Args:
            filepath: Path or string to save to.

        Raises:
            OSError: If the file cannot be written.
            TypeError: If model data is not JSON-serializable.
        """
        filepath = Path(filepath)
        data = self.model.to_dict()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        self.current_file = filepath
        self._save_session()

        # Phase 5: Notify observers of save
        if self.circuit_ctrl:
            self.circuit_ctrl._notify('model_saved', None)

    def load_circuit(self, filepath) -> None:
        """
        Load circuit from JSON file.

        Validates JSON structure before loading. Updates the model
        in place (preserving the reference so views stay connected).

        Args:
            filepath: Path or string to load from.

        Raises:
            json.JSONDecodeError: If file is not valid JSON.
            ValueError: If file structure is invalid.
            OSError: If the file cannot be read.
        """
        filepath = Path(filepath)
        with open(filepath, 'r') as f:
            data = json.load(f)

        validate_circuit_data(data)

        new_model = CircuitModel.from_dict(data)

        # Update current model in place (preserving reference)
        self.model.clear()
        self.model.components = new_model.components
        self.model.wires = new_model.wires
        self.model.nodes = new_model.nodes
        self.model.terminal_to_node = new_model.terminal_to_node
        self.model.component_counter = new_model.component_counter

        self.current_file = filepath
        self._save_session()

        # Phase 5: Notify observers of load
        if self.circuit_ctrl:
            self.circuit_ctrl._notify('model_loaded', None)

    def has_file(self) -> bool:
        """Return whether a current file path is set (for quick-save)."""
        return self.current_file is not None

    def get_window_title(self, base: str = "Circuit Design GUI") -> str:
        """Get window title based on current file."""
        if self.current_file:
            return f"{base} - {self.current_file.name}"
        return base

    def _save_session(self) -> None:
        """Save current file path for session restore."""
        try:
            with open(self._session_file, 'w') as f:
                f.write(os.path.abspath(str(self.current_file))
                        if self.current_file else "")
        except OSError:
            pass  # Session save is best-effort

    def load_last_session(self) -> Optional[Path]:
        """
        Load last session file path if it exists.

        Returns:
            Path to the last opened file, or None.
        """
        try:
            with open(self._session_file, 'r') as f:
                path_str = f.read().strip()
                if path_str:
                    path = Path(path_str)
                    if path.exists():
                        return path
        except OSError:
            pass
        return None
