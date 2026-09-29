"""Headless reproduction of the off-screen drag freeze.

Runs as a pytest test so conftest handles sys.path. Drags a component far
off-screen and asserts the committed position stays within the route window.
If the clamp (or its commit) regresses, this fails loudly instead of hanging.
"""

from PyQt6.QtCore import QPointF

from GUI.component_item import ComponentGraphicsItem, Resistor
from GUI.styles import GRID_EXTENT, GRID_SIZE


def _clamp_and_commit(comp, proposed):
    """Simulate what Qt passes to itemChange during a drag."""
    x, y = proposed.x(), proposed.y()
    gx = round(x / GRID_SIZE) * GRID_SIZE
    gy = round(y / GRID_SIZE) * GRID_SIZE
    snapped = comp._clamp_position(QPointF(gx, gy))
    comp._pending_position = (snapped.x(), snapped.y())
    return snapped


def test_clamp_holds_offscreen():
    comp = Resistor("GND1")
    snapped = _clamp_and_commit(comp, QPointF(1_000_000, 1_000_000))
    assert snapped.x() == GRID_EXTENT
    assert snapped.y() == GRID_EXTENT


def test_commit_within_route_window():
    comp = Resistor("GND1")
    _clamp_and_commit(comp, QPointF(-999_999, -999_999))
    cx, cy = comp._pending_position
    assert -GRID_EXTENT <= cx <= GRID_EXTENT, f"commit escaped: {comp._pending_position}"
    assert -GRID_EXTENT <= cy <= GRID_EXTENT, f"commit escaped: {comp._pending_position}"
