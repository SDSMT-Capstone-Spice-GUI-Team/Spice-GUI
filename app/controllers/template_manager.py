"""
TemplateManager - Handles circuit template discovery, save, and load.

Templates are stored as JSON files with the same format as circuit files,
plus metadata fields (name, description, category). Built-in templates
ship with the application; user templates are saved to ~/.spice-gui/templates/.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from controllers.file_controller import validate_circuit_data
from models.circuit import CircuitModel

logger = logging.getLogger(__name__)

BUILTIN_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
USER_TEMPLATES_DIR = Path.home() / ".spice-gui" / "templates"


@dataclass
class TemplateInfo:
    """Metadata for a circuit template."""

    name: str
    description: str
    category: str
    filepath: Path
    is_builtin: bool


class TemplateManager:
    """Manages circuit template discovery, saving, and loading."""

    def __init__(
        self,
        builtin_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
    ):
        self.builtin_dir = builtin_dir or BUILTIN_TEMPLATES_DIR
        self.user_dir = user_dir or USER_TEMPLATES_DIR

    def _ensure_user_dir(self) -> None:
        """Create user templates directory if it doesn't exist."""
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> list[TemplateInfo]:
        """Return all available templates (built-in + user), sorted by category then name."""
        templates = []
        templates.extend(self._scan_directory(self.builtin_dir, is_builtin=True))
        templates.extend(self._scan_directory(self.user_dir, is_builtin=False))

        # Sort: category alphabetically, then name within category
        templates.sort(key=lambda t: (t.category, t.name))
        return templates

    def _scan_directory(self, directory: Path, is_builtin: bool) -> list[TemplateInfo]:
        """Scan a directory for template JSON files."""
        templates = []
        if not directory.exists():
            return templates

        for filepath in sorted(directory.glob("*.json")):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                templates.append(
                    TemplateInfo(
                        name=data.get("name", filepath.stem),
                        description=data.get("description", ""),
                        category=data.get("category", "Other"),
                        filepath=filepath,
                        is_builtin=is_builtin,
                    )
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read template %s: %s", filepath, e)

        return templates

    def load_template(self, filepath: Path) -> CircuitModel:
        """Load a template and return a CircuitModel with reset counters.

        Component IDs are preserved from the template (R1, C1, etc.) but
        the component_counter is recalculated to reflect the actual IDs
        present, so new components added by the user continue from the
        correct numbers.

        Args:
            filepath: Path to the template JSON file.

        Returns:
            A CircuitModel ready for editing.

        Raises:
            json.JSONDecodeError: If file is not valid JSON.
            ValueError: If file structure is invalid.
            OSError: If file cannot be read.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        validate_circuit_data(data)
        model = CircuitModel.from_dict(data)

        # Recalculate counters from the actual component IDs present
        # so that new components continue with correct numbering
        model.component_counter = self._calculate_counters(model)

        return model

    @staticmethod
    def _calculate_counters(model: CircuitModel) -> dict[str, int]:
        """Calculate component counters from actual component IDs.

        Parses IDs like 'R1', 'R2', 'C1' to determine the highest
        number used for each symbol prefix.
        """
        counters: dict[str, int] = {}
        for comp_id in model.components:
            # Split ID into prefix (letters) and suffix (digits)
            prefix = ""
            suffix = ""
            for ch in comp_id:
                if ch.isdigit() and prefix:
                    suffix += ch
                else:
                    if suffix:
                        break
                    prefix += ch

            if prefix and suffix:
                num = int(suffix)
                counters[prefix] = max(counters.get(prefix, 0), num)

        return counters

    def save_template(
        self,
        model: CircuitModel,
        name: str,
        description: str = "",
        category: str = "User",
    ) -> Path:
        """Save the current circuit as a user template.

        Args:
            model: The circuit model to save.
            name: Display name for the template.
            description: Optional description text.
            category: Category for grouping (default: "User").

        Returns:
            Path to the saved template file.

        Raises:
            OSError: If the file cannot be written.
        """
        self._ensure_user_dir()

        data = model.to_dict()
        data["name"] = name
        data["description"] = description
        data["category"] = category

        # Generate a filename from the template name
        filename = self._name_to_filename(name)
        filepath = self.user_dir / filename

        # Avoid overwriting: append a number if needed
        counter = 1
        while filepath.exists():
            stem = self._name_to_filename(name).replace(".json", "")
            filepath = self.user_dir / f"{stem}_{counter}.json"
            counter += 1

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    def delete_template(self, filepath: Path) -> bool:
        """Delete a user template. Cannot delete built-in templates.

        Returns:
            True if deleted, False if the template is built-in or doesn't exist.
        """
        if not filepath.exists():
            return False

        # Only allow deleting from user directory
        try:
            filepath.resolve().relative_to(self.user_dir.resolve())
        except ValueError:
            return False

        filepath.unlink()
        return True

    @staticmethod
    def _name_to_filename(name: str) -> str:
        """Convert a template name to a safe filename."""
        safe = "".join(c if c.isalnum() or c in " -_" else "" for c in name)
        safe = safe.strip().replace(" ", "_").lower()
        if not safe:
            safe = "template"
        return f"{safe}.json"
