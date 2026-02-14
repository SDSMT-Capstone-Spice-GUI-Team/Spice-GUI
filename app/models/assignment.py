"""Data model for assignment bundles (.spice-assignment files).

Bundles a template and a rubric into a single distributable file.
No Qt dependencies.
"""

from dataclasses import dataclass
from typing import Optional

from .template import TemplateData


@dataclass
class AssignmentBundle:
    """A bundled assignment containing both a template and a rubric.

    Serializes to a JSON file with extension ``.spice-assignment``.
    """

    assignment_version: str = "1.0"
    template: Optional[TemplateData] = None
    rubric: Optional[dict] = None  # Raw rubric dict (validated on load)

    def to_dict(self) -> dict:
        data: dict = {"assignment_version": self.assignment_version}
        if self.template is not None:
            data["template"] = self.template.to_dict()
        if self.rubric is not None:
            data["rubric"] = self.rubric
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AssignmentBundle":
        template = None
        if "template" in data and data["template"] is not None:
            template = TemplateData.from_dict(data["template"])
        return cls(
            assignment_version=data.get("assignment_version", "1.0"),
            template=template,
            rubric=data.get("rubric"),
        )
