"""Regression tests for issue #975 (links #866) — drag ghost outlines.

When a component is dragged, ``MinimalViewportUpdate`` only repaints the
region the item moved *into*; the region it just left was never
invalidated, so the previous outline stayed on screen as a trailing
"stack" of thin square outlines.

The fix invalidates the previous position's scene-rect on every move, in
``itemChange``. ``_drag_old_rect`` is captured while ``pos()`` is still
valid (in ``ItemPositionChange``) and ``scene().update()`` is called on it
in ``ItemPositionHasChanged``, before the new position is drawn. This
mirrors the pattern in ``wire_item.py`` and deliberately avoids
``QGraphicsItem.ItemCoordinateCache``: Qt rasterizes cached items to a
raster <image> during vector output, which breaks the SVG export test
(#975) and degrades vector exports.
"""

from GUI.component_item import ComponentGraphicsItem, Resistor
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsScene


def _add_resistor(scene, comp_id, x=0, y=0):
    """Add a resistor to the scene at position (x, y)."""
    comp = Resistor(comp_id)
    scene.addItem(comp)
    comp.setPos(x, y)
    return comp


class TestDragGhostFix:
    """Dragging must invalidate its previous position to avoid ghost outlines."""

    def test_drag_old_rect_initialized_to_none(self):
        """The stale-position tracker starts cleared."""
        comp = ComponentGraphicsItem("C1", "resistor")
        assert getattr(comp, "_drag_old_rect", "MISSING") is None

    def test_drag_old_rect_captured_before_move(self):
        """Captured scene-rect is set while pos() is still the old position."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)
        proposed = QPointF(100, 0)
        # ItemPositionChange returns the committed (snapped) position; it also
        # stores the pre-move scene-rect that ItemPositionHasChanged later
        # invalidates.
        committed = comp.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            proposed,
        )
        assert committed == proposed
        old_rect = comp._drag_old_rect
        assert old_rect is not None and old_rect.isValid()
        # The captured rect is at the OLD position (near 0,0), not the new one.
        assert old_rect.left() < 50

    def test_itempositionhaschanged_inv_uses_previous_rect(self):
        """ItemPositionHasChanged invalidates the previously captured rect."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)
        # Prime the stale-position tracker as a real move would.
        item_change_value = comp.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionChange,
            QPointF(60, 0),
        )
        old_rect = comp._drag_old_rect
        assert old_rect is not None

        # Track scene().update() calls during the position-has-changed phase.
        calls = []
        original_update = scene.update
        scene.update = lambda *args: calls.append(args)

        # ItemPositionHasChanged moves the item to item_change_value.
        comp.itemChange(
            ComponentGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            item_change_value,
        )

        scene.update = original_update
        # The old scene-rect must have been passed to scene().update().
        invalidated = any(len(c) == 1 and c[0].isValid() and c[0] == old_rect for c in calls)
        assert invalidated, f"expected scene().update({old_rect}); got {calls}"
