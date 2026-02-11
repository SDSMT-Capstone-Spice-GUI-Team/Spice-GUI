"""Movable text annotation for the circuit canvas."""

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QInputDialog


class AnnotationItem(QGraphicsTextItem):
    """A free-form text annotation that can be placed on the canvas.

    Supports move, double-click to edit, delete, bold, font size,
    and serialization for save/load.
    """

    def __init__(self, text="Annotation", x=0.0, y=0.0, font_size=10, bold=False, color="#FFFFFF"):
        super().__init__(text)
        self.setPos(x, y)
        self.setDefaultTextColor(QColor(color))
        self._color_hex = color

        font = QFont()
        font.setPointSize(font_size)
        font.setBold(bold)
        self.setFont(font)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(90)  # Above wires, below debug overlays

    # -- Editing ---------------------------------------------------------------

    def mouseDoubleClickEvent(self, event):
        """Open a dialog to edit the annotation text (via canvas for undo support)."""
        if self.scene() and self.scene().views():
            canvas = self.scene().views()[0]
            if hasattr(canvas, "_edit_annotation"):
                canvas._edit_annotation(self)
                return
        # Fallback: direct edit without undo
        text, ok = QInputDialog.getText(None, "Edit Annotation", "Text:", text=self.toPlainText())
        if ok and text:
            self.setPlainText(text)

    # -- Serialization ---------------------------------------------------------

    def to_dict(self):
        font = self.font()
        return {
            "text": self.toPlainText(),
            "x": self.pos().x(),
            "y": self.pos().y(),
            "font_size": font.pointSize(),
            "bold": font.bold(),
            "color": self._color_hex,
        }

    @staticmethod
    def from_dict(data):
        return AnnotationItem(
            text=data.get("text", "Annotation"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            font_size=data.get("font_size", 10),
            bold=data.get("bold", False),
            color=data.get("color", "#FFFFFF"),
        )
