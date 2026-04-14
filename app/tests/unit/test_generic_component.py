"""Tests for the generic component fallback (#909).

Unknown component types (e.g. subcircuits like LM7812) should load and
render as a generic rectangle instead of crashing with ValueError.
"""

from GUI.component_item import ComponentGraphicsItem, GenericComponent, create_component
from models.component import ComponentData


class TestGenericComponentFromDict:
    """from_dict should return a GenericComponent for unknown types."""

    def test_unknown_type_returns_generic_component(self):
        data = {
            "id": "LM7812_1",
            "type": "LM7812",
            "value": "1u",
            "pos": {"x": 100.0, "y": 200.0},
        }
        comp = ComponentGraphicsItem.from_dict(data)
        assert isinstance(comp, GenericComponent)
        assert comp.component_type == "LM7812"
        assert comp.component_id == "LM7812_1"

    def test_unknown_type_has_terminals(self):
        data = {
            "id": "X1",
            "type": "SubcircuitFoo",
            "value": "1",
            "pos": {"x": 0.0, "y": 0.0},
        }
        comp = ComponentGraphicsItem.from_dict(data)
        # Default 2-terminal layout for unknown types
        assert len(comp.terminals) == 2

    def test_unknown_type_preserves_position(self):
        data = {
            "id": "X1",
            "type": "LM7812",
            "value": "1u",
            "pos": {"x": 50.0, "y": 75.0},
        }
        comp = ComponentGraphicsItem.from_dict(data)
        assert comp.pos().x() == 50.0
        assert comp.pos().y() == 75.0

    def test_known_type_still_works(self):
        data = {
            "id": "R1",
            "type": "Resistor",
            "value": "1k",
            "pos": {"x": 0.0, "y": 0.0},
        }
        comp = ComponentGraphicsItem.from_dict(data)
        assert not isinstance(comp, GenericComponent)
        assert comp.component_type == "Resistor"


class TestCreateComponentFallback:
    """create_component should fall back to GenericComponent."""

    def test_unknown_type_creates_generic(self):
        comp = create_component("LM7812", "X1")
        assert isinstance(comp, GenericComponent)
        assert comp.component_type == "LM7812"

    def test_known_type_still_works(self):
        comp = create_component("Resistor", "R1")
        assert not isinstance(comp, GenericComponent)


class TestGenericRenderer:
    """The generic renderer should not raise on draw or obstacle shape."""

    def test_get_renderer_returns_fallback(self):
        from GUI.renderers import get_renderer

        renderer = get_renderer("LM7812", "IEEE")
        assert renderer is not None

    def test_get_obstacle_shape(self):
        from GUI.renderers import get_renderer

        renderer = get_renderer("UnknownChip", "IEEE")
        shape = renderer.get_obstacle_shape(None)
        assert len(shape) == 4
