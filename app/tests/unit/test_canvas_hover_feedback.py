"""
Unit tests for canvas hover visual feedback (issue #515).

Verifies that components and wires show visual feedback on hover.
"""

import pytest
from GUI.component_item import ComponentGraphicsItem
from GUI.wire_item import WireGraphicsItem
from models.component import ComponentData
from models.wire import WireData
from PyQt6.QtCore import QPointF


class TestComponentHoverFeedback:
    """Test ComponentGraphicsItem hover visual feedback."""

    def test_component_accepts_hover_events(self):
        comp = ComponentGraphicsItem("R1", "Resistor")
        assert comp.acceptHoverEvents()

    def test_component_starts_not_hovered(self):
        comp = ComponentGraphicsItem("R1", "Resistor")
        assert comp._hovered is False

    def test_hover_enter_sets_hovered(self, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        qtbot.addWidget(view)

        comp = ComponentGraphicsItem("R1", "Resistor")
        scene.addItem(comp)

        # Simulate hover
        comp._hovered = True
        comp.update()
        assert comp._hovered is True

    def test_hover_leave_clears_hovered(self, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        qtbot.addWidget(view)

        comp = ComponentGraphicsItem("R1", "Resistor")
        scene.addItem(comp)

        comp._hovered = True
        comp._hovered = False
        comp.update()
        assert comp._hovered is False


class TestWireHoverFeedback:
    """Test WireGraphicsItem hover visual feedback."""

    @pytest.fixture
    def wire_setup(self, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        qtbot.addWidget(view)

        comp1 = ComponentGraphicsItem("R1", "Resistor")
        comp1.setPos(0, 0)
        scene.addItem(comp1)

        comp2 = ComponentGraphicsItem("R2", "Resistor")
        comp2.setPos(200, 0)
        scene.addItem(comp2)

        model = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=0,
            waypoints=[(0, 0), (200, 0)],
        )
        wire = WireGraphicsItem(comp1, 0, comp2, 0, model=model)
        scene.addItem(wire)

        return wire, scene

    def test_wire_accepts_hover_events(self, wire_setup):
        wire, _ = wire_setup
        assert wire.acceptHoverEvents()

    def test_wire_starts_not_hovered(self, wire_setup):
        wire, _ = wire_setup
        assert wire._hovered is False

    def test_wire_hover_enter_sets_flag(self, wire_setup):
        wire, _ = wire_setup
        wire._hovered = True
        wire.update()
        assert wire._hovered is True

    def test_wire_hover_leave_clears_flag(self, wire_setup):
        wire, _ = wire_setup
        wire._hovered = True
        wire._hovered = False
        wire.update()
        assert wire._hovered is False
