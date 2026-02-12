"""Data classes for assignment templates with instructor metadata."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TemplateMetadata:
    """Instructor-facing metadata for an assignment template."""

    title: str = ""
    description: str = ""
    author: str = ""
    created: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "created": self.created,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateMetadata":
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            created=data.get("created", ""),
            tags=list(data.get("tags", [])),
        )


@dataclass
class TemplateData:
    """A complete assignment template containing metadata and circuit data.

    The starter_circuit is what students receive (may be empty or partially
    built). The reference_circuit is the instructor's solution (optional,
    used for grading).
    """

    template_version: str = "1.0"
    metadata: TemplateMetadata = field(default_factory=TemplateMetadata)
    instructions: str = ""
    starter_circuit: Optional[dict] = None
    reference_circuit: Optional[dict] = None
    required_analysis: Optional[dict] = None

    def to_dict(self) -> dict:
        data = {
            "template_version": self.template_version,
            "metadata": self.metadata.to_dict(),
            "instructions": self.instructions,
        }
        if self.starter_circuit is not None:
            data["starter_circuit"] = self.starter_circuit
        if self.reference_circuit is not None:
            data["reference_circuit"] = self.reference_circuit
        if self.required_analysis is not None:
            data["required_analysis"] = self.required_analysis
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateData":
        return cls(
            template_version=data.get("template_version", "1.0"),
            metadata=TemplateMetadata.from_dict(data.get("metadata", {})),
            instructions=data.get("instructions", ""),
            starter_circuit=data.get("starter_circuit"),
            reference_circuit=data.get("reference_circuit"),
            required_analysis=data.get("required_analysis"),
        )
