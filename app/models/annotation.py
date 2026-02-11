"""Data class for text annotations on the circuit canvas."""

from dataclasses import dataclass


@dataclass
class AnnotationData:
    """A free-form text annotation placed on the canvas.

    Annotations have no electrical significance — they are purely visual
    labels for documentation purposes.
    """

    text: str = "Annotation"
    x: float = 0.0
    y: float = 0.0
    font_size: int = 10
    bold: bool = False
    color: str = "#FFFFFF"

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "font_size": self.font_size,
            "bold": self.bold,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnnotationData":
        return cls(
            text=data.get("text", "Annotation"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            font_size=data.get("font_size", 10),
            bold=data.get("bold", False),
            color=data.get("color", "#FFFFFF"),
        )
