"""TemplateController - Handles assignment template I/O for instructor tools.

Templates wrap a standard circuit JSON with instructor metadata (title,
description, instructions) and optionally a reference solution circuit.
File extension: .spice-template (JSON internally).
"""

import json
from pathlib import Path
from typing import Optional

from controllers.file_controller import validate_circuit_data
from models.circuit import CircuitModel
from models.template import TemplateData, TemplateMetadata

TEMPLATE_EXTENSION = ".spice-template"


def validate_template_data(data: dict) -> None:
    """Validate template JSON structure before loading.

    Raises ValueError with a descriptive message if anything is wrong.
    """
    if not isinstance(data, dict):
        raise ValueError("File does not contain a valid template object.")

    if "template_version" not in data:
        raise ValueError("Missing 'template_version' field.")

    if "metadata" not in data or not isinstance(data["metadata"], dict):
        raise ValueError("Missing or invalid 'metadata' section.")

    metadata = data["metadata"]
    if not metadata.get("title"):
        raise ValueError("Template metadata must include a non-empty 'title'.")

    # Validate embedded circuits if present
    if "starter_circuit" in data and data["starter_circuit"] is not None:
        validate_circuit_data(data["starter_circuit"])

    if "reference_circuit" in data and data["reference_circuit"] is not None:
        validate_circuit_data(data["reference_circuit"])


class TemplateController:
    """Manages assignment template save/load operations.

    Works alongside FileController — FileController handles regular circuit
    files, TemplateController handles the template envelope format.
    """

    def save_as_template(
        self,
        filepath,
        metadata: TemplateMetadata,
        starter_circuit: Optional[CircuitModel] = None,
        reference_circuit: Optional[CircuitModel] = None,
        instructions: str = "",
        required_analysis: Optional[dict] = None,
    ) -> None:
        """Save a circuit as an assignment template.

        Args:
            filepath: Path to save the template file.
            metadata: Template metadata (title, author, etc.).
            starter_circuit: Circuit students start with (optional).
            reference_circuit: Instructor's solution circuit (optional).
            instructions: Assignment instructions text.
            required_analysis: Expected analysis type and params (optional).

        Raises:
            OSError: If the file cannot be written.
            TypeError: If data is not JSON-serializable.
        """
        filepath = Path(filepath)

        template = TemplateData(
            metadata=metadata,
            instructions=instructions,
            starter_circuit=(starter_circuit.to_dict() if starter_circuit else None),
            reference_circuit=(reference_circuit.to_dict() if reference_circuit else None),
            required_analysis=required_analysis,
        )

        with open(filepath, "w") as f:
            json.dump(template.to_dict(), f, indent=2)

    def load_template(self, filepath) -> TemplateData:
        """Load a template file and return parsed TemplateData.

        Args:
            filepath: Path to the template file.

        Returns:
            TemplateData with metadata and optional circuit dicts.

        Raises:
            json.JSONDecodeError: If file is not valid JSON.
            ValueError: If template structure is invalid.
            OSError: If the file cannot be read.
        """
        filepath = Path(filepath)
        with open(filepath, "r") as f:
            data = json.load(f)

        validate_template_data(data)
        return TemplateData.from_dict(data)

    def create_circuit_from_template(self, template: TemplateData) -> CircuitModel:
        """Create a new CircuitModel from a template's starter circuit.

        If the template has no starter_circuit, returns an empty model
        with the template's required analysis settings applied.

        Args:
            template: The loaded template data.

        Returns:
            A new CircuitModel ready for the student to work with.
        """
        if template.starter_circuit is not None:
            model = CircuitModel.from_dict(template.starter_circuit)
        else:
            model = CircuitModel()

        # Apply required analysis settings if specified
        if template.required_analysis:
            analysis_type = template.required_analysis.get("type")
            if analysis_type:
                model.analysis_type = analysis_type
            analysis_params = template.required_analysis.get("params")
            if analysis_params:
                model.analysis_params = analysis_params.copy()

        return model

    def get_reference_circuit(self, template: TemplateData) -> Optional[CircuitModel]:
        """Extract the reference (solution) circuit from a template.

        Args:
            template: The loaded template data.

        Returns:
            CircuitModel of the solution, or None if not included.
        """
        if template.reference_circuit is not None:
            return CircuitModel.from_dict(template.reference_circuit)
        return None

    def get_template_metadata(self, filepath) -> TemplateMetadata:
        """Read template metadata without loading the full circuit data.

        Useful for browsing/listing templates without deserializing circuits.

        Args:
            filepath: Path to the template file.

        Returns:
            TemplateMetadata with title, description, author, etc.

        Raises:
            json.JSONDecodeError: If file is not valid JSON.
            ValueError: If template structure is invalid.
            OSError: If the file cannot be read.
        """
        filepath = Path(filepath)
        with open(filepath, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("File does not contain a valid template object.")
        if "metadata" not in data or not isinstance(data["metadata"], dict):
            raise ValueError("Missing or invalid 'metadata' section.")
        if not data["metadata"].get("title"):
            raise ValueError("Template metadata must include a non-empty 'title'.")

        return TemplateMetadata.from_dict(data["metadata"])
