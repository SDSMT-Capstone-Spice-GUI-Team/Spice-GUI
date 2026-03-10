"""Tests for wire z-order rendering (issue #157).

Wires must render above components but below selection handles and preview lines.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QPointF


def _make_mock_component(comp_id, terminal_pos=None):
    """Create a mock component with terminal positions."""
    comp = MagicMock()
    comp.component_id = comp_id
    comp.get_terminal_pos = MagicMock(return_value=terminal_pos if terminal_pos else QPointF(0, 0))
    return comp


@pytest.fixture
def mock_components():
    """Two mock components for wire creation."""
    start = _make_mock_component("R1", QPointF(0, 0))
    end = _make_mock_component("R2", QPointF(100, 0))
    return start, end


class TestWireZOrder:
    """Wire z-value must be explicitly set above components."""

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_z_value_is_one(self, mock_update, mock_components):
        """WireGraphicsItem should have z-value of 1."""
        from GUI.wire_item import WireGraphicsItem

        start, end = mock_components
        wire = WireGraphicsItem(start, 0, end, 0, canvas=None)
        assert wire.zValue() == 1

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_z_above_components(self, mock_update, mock_components):
        """Wires (z=1) must render above components (z=0)."""
        from GUI.component_item import Resistor
        from GUI.wire_item import WireGraphicsItem

        start, end = mock_components
        wire = WireGraphicsItem(start, 0, end, 0, canvas=None)

        # Components default to z=0
        resistor = Resistor("R_test")
        assert wire.zValue() > resistor.zValue()

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_z_below_preview(self, mock_update, mock_components):
        """Wires (z=1) must render below the wire preview line (z=100)."""
        from GUI.wire_item import WireGraphicsItem

        start, end = mock_components
        wire = WireGraphicsItem(start, 0, end, 0, canvas=None)
        # Wire preview uses z=100 per circuit_canvas.py:557
        assert wire.zValue() < 100

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_z_value_explicit_not_default(self, mock_update, mock_components):
        """Z-value should be explicitly set, not relying on default (0)."""
        from GUI.wire_item import WireGraphicsItem

        start, end = mock_components
        wire = WireGraphicsItem(start, 0, end, 0, canvas=None)
        # Default QGraphicsItem z-value is 0; wire must be different
        assert wire.zValue() != 0

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_z_below_annotations(self, mock_update, mock_components):
        """Wires (z=1) must render below annotations (z=90)."""
        from GUI.wire_item import WireGraphicsItem

        start, end = mock_components
        wire = WireGraphicsItem(start, 0, end, 0, canvas=None)
        # Annotations use z=90 per annotation_item.py:30
        assert wire.zValue() < 90

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_selectable_flag_still_set(self, mock_update, mock_components):
        """Z-value change should not affect selectability."""
        from GUI.wire_item import WireGraphicsItem
        from PyQt6.QtWidgets import QGraphicsPathItem

        start, end = mock_components
        wire = WireGraphicsItem(start, 0, end, 0, canvas=None)
        assert wire.flags() & QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable

    @patch("GUI.wire_item.WireGraphicsItem.update_position")
    def test_wire_from_dict_has_z_value(self, mock_update, mock_components):
        """Wires created via from_dict should also have z=1."""
        from GUI.wire_item import WireGraphicsItem
        from models.wire import WireData

        start, end = mock_components
        wire_data = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=0,
        )
        components_dict = {"R1": start, "R2": end}
        wire = WireGraphicsItem.from_dict(wire_data.to_dict(), components_dict, canvas=None)
        assert wire.zValue() == 1
