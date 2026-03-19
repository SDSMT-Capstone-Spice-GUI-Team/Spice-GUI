"""
FileController - Handles circuit file I/O and session persistence.

File dialog interaction is the responsibility of the view layer.
Recent files tracking uses the centralized settings service for cross-session persistence.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

from controllers.settings_service import settings
from models.circuit import CircuitModel

SESSION_FILE = "last_session.txt"
AUTOSAVE_FILE = ".autosave_recovery.json"
MAX_RECENT_FILES = 10
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def check_file_size(filepath: Path, max_size: int = MAX_FILE_SIZE) -> None:
    """Raise ValueError if *filepath* exceeds *max_size* bytes."""
    size = os.path.getsize(filepath)
    if size > max_size:
        mb = size / (1024 * 1024)
        limit_mb = max_size / (1024 * 1024)
        raise ValueError(f"File is too large ({mb:.1f} MB). Maximum allowed size is {limit_mb:.0f} MB.")


from models.circuit_schema_validator import validate_circuit_data  # noqa: F401 — re-exported for compatibility


class FileController:
    """
    Manages circuit file I/O and session persistence.

    Handles saving/loading circuit data as JSON and tracking
    the current file path for quick-save and session restore.
    """

    def __init__(
        self,
        model: Optional[CircuitModel] = None,
        circuit_ctrl=None,
        session_file: str = SESSION_FILE,
        autosave_file: str = AUTOSAVE_FILE,
    ):
        self.model = model or CircuitModel()
        self.circuit_ctrl = circuit_ctrl
        self.current_file: Optional[Path] = None
        self._session_file = session_file
        self._autosave_file = Path(__file__).resolve().parent.parent / autosave_file

    def _replace_model(self, new_model: CircuitModel) -> None:
        """Replace the current model's data with *new_model* in place.

        Validates the parsed data **before** clearing the existing circuit
        so that a corrupt import can never cause data loss.  Copies all
        fields from *new_model* into ``self.model`` so that existing
        references to the model object remain valid.
        """
        parsed_data = new_model.to_dict()
        validate_circuit_data(parsed_data)

        self.model.clear()
        self.model.components = new_model.components
        self.model.wires = new_model.wires
        self.model.nodes = new_model.nodes
        self.model.terminal_to_node = new_model.terminal_to_node
        self.model.component_counter = new_model.component_counter
        self.model.analysis_type = new_model.analysis_type
        self.model.analysis_params = new_model.analysis_params
        self.model.annotations = new_model.annotations
        self.model.recommended_components = new_model.recommended_components

    def load_from_model(self, new_model: CircuitModel) -> None:
        """Replace the current circuit with *new_model* and notify observers.

        This is the public entry-point that GUI code should call when it
        already has a ``CircuitModel`` instance (e.g. from template or
        assignment loading).  It preserves the existing model reference,
        copies data across, and fires a ``model_loaded`` notification.
        """
        self._replace_model(new_model)
        if self.circuit_ctrl:
            self.circuit_ctrl.clear_undo_history()
            self.circuit_ctrl._notify("model_loaded", None)

    def new_circuit(self) -> None:
        """Clear the circuit and reset file state."""
        self.model.clear()
        self.current_file = None
        if self.circuit_ctrl:
            self.circuit_ctrl.clear_undo_history()

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
        fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, filepath)
        except BaseException:
            os.unlink(tmp)
            raise
        self.current_file = filepath
        self._save_session()
        self.add_recent_file(filepath)  # Track in recent files

        if self.circuit_ctrl:
            self.circuit_ctrl._notify("model_saved", None)

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
        check_file_size(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        validate_circuit_data(data)

        new_model = CircuitModel.from_dict(data)
        self._replace_model(new_model)

        self.current_file = filepath
        self._save_session()
        self.add_recent_file(filepath)

        if self.circuit_ctrl:
            self.circuit_ctrl.clear_undo_history()
            self.circuit_ctrl._notify("model_loaded", None)

    def load_from_dict(self, data: dict) -> None:
        """Load circuit from a pre-validated dict (e.g. from clipboard).

        Updates the model in place (preserving the reference so views stay connected).
        Does not update current_file or session tracking.
        """
        new_model = CircuitModel.from_dict(data)
        self._replace_model(new_model)

        if self.circuit_ctrl:
            self.circuit_ctrl.clear_undo_history()
            self.circuit_ctrl._notify("model_loaded", None)

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
            session_path = Path(self._session_file)
            content = os.path.abspath(str(self.current_file)) if self.current_file else ""
            fd, tmp = tempfile.mkstemp(dir=session_path.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp, session_path)
            except BaseException:
                os.unlink(tmp)
                raise
        except OSError:
            logger.warning("Failed to save session file %s", self._session_file, exc_info=True)

    def load_last_session(self) -> Optional[Path]:
        """
        Load last session file path if it exists.

        Returns:
            Path to the last opened file, or None.
        """
        if not os.path.exists(self._session_file):
            return None
        try:
            with open(self._session_file, "r", encoding="utf-8") as f:
                path_str = f.read().strip()
                if path_str:
                    path = Path(path_str)
                    if path.exists():
                        return path
        except OSError:
            logger.warning("Failed to read session file %s", self._session_file, exc_info=True)
        return None

    def get_recent_files(self) -> List[str]:
        """
        Get list of recently opened files.

        Returns:
            List of file paths (most recent first), with non-existent files removed.
        """
        recent = settings.get_list("file/recent_files")

        # Filter out files that no longer exist
        existing = [f for f in recent if os.path.exists(f)]

        # Update settings if we removed any
        if len(existing) != len(recent):
            settings.set("file/recent_files", existing)

        return existing

    def add_recent_file(self, filepath: Path) -> None:
        """
        Add a file to the recent files list.

        Args:
            filepath: Path to add to recent files.
        """
        filepath_str = str(filepath.absolute())
        recent = self.get_recent_files()

        # Remove if already in list (we'll add to front)
        if filepath_str in recent:
            recent.remove(filepath_str)

        # Add to front
        recent.insert(0, filepath_str)

        # Keep only MAX_RECENT_FILES
        recent = recent[:MAX_RECENT_FILES]

        # Save to settings
        settings.set("file/recent_files", recent)

    def clear_recent_files(self) -> None:
        """Clear the recent files list."""
        settings.set("file/recent_files", [])

    # ------------------------------------------------------------------
    # Auto-save and crash recovery
    # ------------------------------------------------------------------

    def auto_save(self) -> None:
        """Save circuit to the auto-save recovery file.

        Unlike save_circuit(), this does NOT update current_file,
        recent files, or session state.
        """
        try:
            data = self.model.to_dict()
            data["_autosave_source"] = str(self.current_file) if self.current_file else ""
            fd, tmp = tempfile.mkstemp(dir=self._autosave_file.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp, self._autosave_file)
            except BaseException:
                os.unlink(tmp)
                raise
        except (OSError, TypeError):
            logger.warning("Auto-save failed for %s", self._autosave_file, exc_info=True)

    def has_auto_save(self) -> bool:
        """Return True if an auto-save recovery file exists."""
        return self._autosave_file.exists()

    def load_auto_save(self) -> Optional[str]:
        """Load circuit from the auto-save recovery file.

        Returns:
            The original file path (str) the auto-save was based on,
            or empty string if it was an unsaved circuit. Returns None
            on failure.
        """
        try:
            with open(self._autosave_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            source_path = data.pop("_autosave_source", "")
            validate_circuit_data(data)

            new_model = CircuitModel.from_dict(data)
            self._replace_model(new_model)

            if source_path:
                self.current_file = Path(source_path)

            if self.circuit_ctrl:
                self.circuit_ctrl._notify("model_loaded", None)

            return source_path
        except (OSError, json.JSONDecodeError, ValueError):
            logger.warning("Failed to load auto-save from %s", self._autosave_file, exc_info=True)
            return None

    def import_netlist(self, filepath) -> None:
        """Import a SPICE netlist file (.cir, .spice) into the current model.

        Parses the netlist, creates components with auto-layout,
        wires them according to node connectivity, and optionally
        sets the analysis type.

        Args:
            filepath: Path or string to the netlist file.

        Raises:
            OSError: If the file cannot be read.
            simulation.netlist_parser.NetlistParseError: If parsing fails.
        """
        from simulation.netlist_parser import import_netlist

        filepath = Path(filepath)
        check_file_size(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        new_model, analysis = import_netlist(text)

        if analysis:
            new_model.analysis_type = analysis["type"]
            new_model.analysis_params = analysis["params"]

        self._replace_model(new_model)

        self.current_file = None
        self.add_recent_file(filepath)

        if self.circuit_ctrl:
            self.circuit_ctrl._notify("model_loaded", None)

    def import_asc(self, filepath) -> list[str]:
        """Import an LTspice .asc schematic file into the current model.

        Parses the .asc schematic, maps LTspice components to Spice-GUI
        types, creates wires based on coordinate matching, and optionally
        sets the analysis type.

        Args:
            filepath: Path or string to the .asc file.

        Returns:
            List of warning messages (unsupported components, etc.)

        Raises:
            OSError: If the file cannot be read.
            simulation.asc_parser.AscParseError: If parsing fails.
        """
        from simulation.asc_parser import import_asc

        filepath = Path(filepath)
        check_file_size(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        new_model, analysis, warnings = import_asc(text)

        if analysis:
            new_model.analysis_type = analysis["type"]
            new_model.analysis_params = analysis["params"]

        self._replace_model(new_model)

        self.current_file = None
        self.add_recent_file(filepath)

        if self.circuit_ctrl:
            self.circuit_ctrl._notify("model_loaded", None)

        return warnings

    def import_circuitikz(self, filepath) -> list[str]:
        """Import a CircuiTikZ LaTeX file into the current model.

        Parses the LaTeX code, maps CircuiTikZ components to Spice-GUI
        types, reconstructs wire connections, and reverses the coordinate
        transform.

        Args:
            filepath: Path or string to the .tex file.

        Returns:
            List of warning messages (unsupported components, etc.)

        Raises:
            OSError: If the file cannot be read.
            simulation.circuitikz_parser.CircuitikzParseError: If parsing fails.
        """
        from simulation.circuitikz_parser import import_circuitikz

        filepath = Path(filepath)
        check_file_size(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        new_model, warnings = import_circuitikz(text)
        self._replace_model(new_model)

        self.current_file = None
        self.add_recent_file(filepath)

        if self.circuit_ctrl:
            self.circuit_ctrl._notify("model_loaded", None)

        return warnings

    # --- Export helpers ---

    def export_bom(self, filepath: str, circuit_name: str = "") -> None:
        """Export a Bill of Materials. Format is determined by file extension.

        Raises:
            OSError: If the file cannot be written.
        """
        from simulation.bom_exporter import export_bom_csv, export_bom_excel, write_bom_csv

        if filepath.lower().endswith(".xlsx"):
            export_bom_excel(self.model.components, filepath, circuit_name=circuit_name)
        else:
            content = export_bom_csv(self.model.components, circuit_name=circuit_name)
            write_bom_csv(content, filepath)

    def import_svg(self, filepath) -> None:
        """Import a shareable SVG file that contains embedded circuit data.

        Extracts the circuit JSON from the SVG metadata and replaces
        the current model.

        Args:
            filepath: Path or string to the .svg file.

        Raises:
            OSError: If the file cannot be read.
            ValueError: If the SVG contains no embedded circuit data
                or the data is corrupt.
        """
        from simulation.svg_shareable import extract_circuit_data

        filepath = Path(filepath)
        check_file_size(filepath)

        data = extract_circuit_data(filepath)
        if data is None:
            raise ValueError(
                "This SVG file does not contain embedded circuit data.\n"
                "Only SVGs exported with 'Export Image' (SVG format) from Spice-GUI can be imported."
            )

        validate_circuit_data(data)
        new_model = CircuitModel.from_dict(data)
        self._replace_model(new_model)

        self.current_file = None
        self.add_recent_file(filepath)

        if self.circuit_ctrl:
            self.circuit_ctrl._notify("model_loaded", None)

    def export_asc(self, filepath: str) -> None:
        """Export the circuit as an LTspice .asc schematic.

        Raises:
            OSError: If the file cannot be written.
        """
        from simulation.asc_exporter import export_asc, write_asc

        content = export_asc(self.model)
        write_asc(content, filepath)

    def clear_auto_save(self) -> None:
        """Delete the auto-save recovery file if it exists."""
        try:
            self._autosave_file.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to delete auto-save file %s", self._autosave_file, exc_info=True)
