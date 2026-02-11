"""Tests for rerouting neighboring wires after wire deletion (issue #158).

After deleting a wire, remaining wires connected to the same components
should be rerouted to potentially find shorter paths.
"""

from unittest.mock import MagicMock, call, patch

import pytest


class TestRerouteWiresNearComponents:
    """_reroute_wires_near_components should reroute affected wires only."""

    def _make_canvas(self):
        """Create a minimal mock canvas with the real _reroute method."""
        from GUI.circuit_canvas import CircuitCanvasView

        # Grab the unbound method so we can call it on our mock
        reroute = CircuitCanvasView._reroute_wires_near_components

        canvas = MagicMock()
        canvas._reroute_wires_near_components = lambda comps: reroute(canvas, comps)
        canvas.scene = MagicMock()
        return canvas

    def _make_wire(self, start_comp, end_comp):
        wire = MagicMock()
        wire.start_comp = start_comp
        wire.end_comp = end_comp
        return wire

    def test_reroutes_wire_sharing_start_component(self):
        """A wire sharing the start component of the deleted wire should be rerouted."""
        canvas = self._make_canvas()
        comp_a = MagicMock(name="A")
        comp_b = MagicMock(name="B")
        comp_c = MagicMock(name="C")

        wire = self._make_wire(comp_a, comp_c)
        canvas.wires = [wire]

        canvas._reroute_wires_near_components({comp_a, comp_b})

        wire.update_position.assert_called_once()

    def test_reroutes_wire_sharing_end_component(self):
        """A wire sharing the end component of the deleted wire should be rerouted."""
        canvas = self._make_canvas()
        comp_a = MagicMock(name="A")
        comp_b = MagicMock(name="B")
        comp_c = MagicMock(name="C")

        wire = self._make_wire(comp_c, comp_b)
        canvas.wires = [wire]

        canvas._reroute_wires_near_components({comp_a, comp_b})

        wire.update_position.assert_called_once()

    def test_does_not_reroute_unrelated_wire(self):
        """A wire not connected to any affected component should NOT be rerouted."""
        canvas = self._make_canvas()
        comp_a = MagicMock(name="A")
        comp_b = MagicMock(name="B")
        comp_c = MagicMock(name="C")
        comp_d = MagicMock(name="D")

        wire = self._make_wire(comp_c, comp_d)
        canvas.wires = [wire]

        canvas._reroute_wires_near_components({comp_a, comp_b})

        wire.update_position.assert_not_called()

    def test_reroutes_multiple_affected_wires(self):
        """All wires connected to affected components should be rerouted."""
        canvas = self._make_canvas()
        comp_a = MagicMock(name="A")
        comp_b = MagicMock(name="B")
        comp_c = MagicMock(name="C")

        wire1 = self._make_wire(comp_a, comp_c)
        wire2 = self._make_wire(comp_c, comp_b)
        wire3 = self._make_wire(comp_c, comp_c)  # unrelated
        canvas.wires = [wire1, wire2, wire3]

        canvas._reroute_wires_near_components({comp_a, comp_b})

        wire1.update_position.assert_called_once()
        wire2.update_position.assert_called_once()
        wire3.update_position.assert_not_called()

    def test_scene_updated_when_wires_rerouted(self):
        """Scene should be updated after rerouting."""
        canvas = self._make_canvas()
        comp_a = MagicMock(name="A")

        wire = self._make_wire(comp_a, MagicMock())
        canvas.wires = [wire]

        canvas._reroute_wires_near_components({comp_a})

        canvas.scene.update.assert_called_once()

    def test_scene_not_updated_when_no_wires_rerouted(self):
        """Scene should NOT be updated if no wires were affected."""
        canvas = self._make_canvas()
        comp_a = MagicMock(name="A")
        comp_b = MagicMock(name="B")

        wire = self._make_wire(comp_b, comp_b)
        canvas.wires = [wire]

        canvas._reroute_wires_near_components({comp_a})

        canvas.scene.update.assert_not_called()

    def test_empty_wire_list(self):
        """No error when there are no remaining wires."""
        canvas = self._make_canvas()
        canvas.wires = []

        # Should not raise
        canvas._reroute_wires_near_components({MagicMock()})

        canvas.scene.update.assert_not_called()


class TestHandleWireRemovedReroutes:
    """_handle_wire_removed should trigger reroute for neighbors."""

    def test_handle_wire_removed_calls_reroute(self):
        """After removing a wire, _reroute_wires_near_components should be called."""
        from GUI.circuit_canvas import CircuitCanvasView

        handle = CircuitCanvasView._handle_wire_removed

        canvas = MagicMock()
        canvas._handle_wire_removed = lambda idx: handle(canvas, idx)

        comp_a = MagicMock(name="A")
        comp_b = MagicMock(name="B")
        wire = MagicMock()
        wire.start_comp = comp_a
        wire.end_comp = comp_b
        canvas.wires = [wire]

        canvas._handle_wire_removed(0)

        canvas._reroute_wires_near_components.assert_called_once_with({comp_a, comp_b})

    def test_handle_wire_removed_removes_from_scene(self):
        """Wire should be removed from scene."""
        from GUI.circuit_canvas import CircuitCanvasView

        handle = CircuitCanvasView._handle_wire_removed

        canvas = MagicMock()
        canvas._handle_wire_removed = lambda idx: handle(canvas, idx)

        wire = MagicMock()
        canvas.wires = [wire]

        canvas._handle_wire_removed(0)

        canvas.scene.removeItem.assert_called_once_with(wire)
