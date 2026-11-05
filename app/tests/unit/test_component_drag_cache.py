"""Regression tests for issue #975 (links #866) — drag ghost outlines.

Dragging a component off the region it just left was never invalidated, so the
old outline stayed on screen (the classic QGraphicsView ghosting artifact).
The fix caches the item with
``QGraphicsItem.CacheMode.ItemCoordinateCache`` (``ItemCache`` only exists in
newer PyQt6, so we use the pre-6.7-compatible name): Qt then
auto-invalidates both the old and new cache rectangles on every move, so the
previous outline is drawn over.

These tests pin that invariant directly. There is no pixel-rendering test
possible headless; what we *can* assert deterministically is that the item
carries the cache mode that makes the fix work. If a future change removes
``setCacheMode(ItemCache)`` (e.g. to squeeze out a bit of memory), the
ghosting comes back and this test fails first.
"""

from GUI.component_item import ComponentGraphicsItem, Resistor
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene


def _add_resistor(scene, comp_id, x=0, y=0):
    """Add a resistor to the scene at position (x, y)."""
    comp = Resistor(comp_id)
    scene.addItem(comp)
    comp.setPos(x, y)
    return comp


class TestDragCacheMode:
    """The component must be cached so dragging leaves no trailing outlines."""

    def test_item_cache_mode_set_on_base_component(self):
        """ComponentGraphicsItem sets ItemCache by default (no ghost outlines)."""
        comp = ComponentGraphicsItem("C1", "resistor")
        assert comp.cacheMode() == (
            QGraphicsItem.CacheMode.ItemCoordinateCache
        ), "Component must use ItemCache to invalidate its old position on drag"

    def test_item_cache_mode_set_on_resistor(self):
        """A concrete Resistor inherits the cache mode from the base item."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1")
        assert comp.cacheMode() == QGraphicsItem.CacheMode.ItemCoordinateCache

    def test_item_cache_mode_survives_position_change(self):
        """Moving the item (simulating a drag frame) keeps the cache mode set,
        so Qt keeps invalidating the old rectangle every move."""
        scene = QGraphicsScene()
        comp = _add_resistor(scene, "R1", 0, 0)
        # Simulate a single drag frame of the whole-translation movement that
        # previously left the old outline uncleared.
        comp.setPos(QPointF(100, 0))
        assert comp.cacheMode() == QGraphicsItem.CacheMode.ItemCoordinateCache
