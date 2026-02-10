"""Tests for component flip (horizontal/vertical mirror) in the model layer."""

import math

import pytest
from models.component import ComponentData


@pytest.fixture
def resistor():
    """A standard 2-terminal resistor at origin."""
    return ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 100.0),
    )


class TestFlipDefaults:
    def test_defaults_false(self, resistor):
        assert resistor.flip_h is False
        assert resistor.flip_v is False

    def test_terminal_positions_unchanged_without_flip(self, resistor):
        base = resistor.get_base_terminal_positions()
        world = resistor.get_terminal_positions()
        # Without flip or rotation, world = position + base
        for (bx, by), (wx, wy) in zip(base, world):
            assert wx == pytest.approx(resistor.position[0] + bx)
            assert wy == pytest.approx(resistor.position[1] + by)


class TestFlipTerminals:
    def test_flip_h_mirrors_x(self, resistor):
        base = resistor.get_base_terminal_positions()
        resistor.flip_h = True
        world = resistor.get_terminal_positions()
        for (bx, by), (wx, wy) in zip(base, world):
            assert wx == pytest.approx(resistor.position[0] - bx)
            assert wy == pytest.approx(resistor.position[1] + by)

    def test_flip_v_mirrors_y(self, resistor):
        base = resistor.get_base_terminal_positions()
        resistor.flip_v = True
        world = resistor.get_terminal_positions()
        for (bx, by), (wx, wy) in zip(base, world):
            assert wx == pytest.approx(resistor.position[0] + bx)
            assert wy == pytest.approx(resistor.position[1] - by)

    def test_flip_both_mirrors_xy(self, resistor):
        base = resistor.get_base_terminal_positions()
        resistor.flip_h = True
        resistor.flip_v = True
        world = resistor.get_terminal_positions()
        for (bx, by), (wx, wy) in zip(base, world):
            assert wx == pytest.approx(resistor.position[0] - bx)
            assert wy == pytest.approx(resistor.position[1] - by)

    def test_flip_h_with_rotation_90(self, resistor):
        """Flip is applied before rotation: flip_h negates base x, then rotate 90."""
        base = resistor.get_base_terminal_positions()
        resistor.flip_h = True
        resistor.rotation = 90
        world = resistor.get_terminal_positions()
        rad = math.radians(90)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        for (bx, by), (wx, wy) in zip(base, world):
            fx, fy = -bx, by  # flip_h
            expected_x = resistor.position[0] + fx * cos_a - fy * sin_a
            expected_y = resistor.position[1] + fx * sin_a + fy * cos_a
            assert wx == pytest.approx(expected_x)
            assert wy == pytest.approx(expected_y)


class TestFlipSerialization:
    def test_to_dict_includes_flip(self, resistor):
        resistor.flip_h = True
        resistor.flip_v = False
        d = resistor.to_dict()
        assert d["flip_h"] is True
        assert d["flip_v"] is False

    def test_from_dict_reads_flip(self, resistor):
        d = resistor.to_dict()
        d["flip_h"] = True
        d["flip_v"] = True
        restored = ComponentData.from_dict(d)
        assert restored.flip_h is True
        assert restored.flip_v is True

    def test_from_dict_defaults_missing_flip(self, resistor):
        d = resistor.to_dict()
        del d["flip_h"]
        del d["flip_v"]
        restored = ComponentData.from_dict(d)
        assert restored.flip_h is False
        assert restored.flip_v is False

    def test_round_trip(self, resistor):
        resistor.flip_h = True
        resistor.flip_v = True
        d = resistor.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.flip_h == resistor.flip_h
        assert restored.flip_v == resistor.flip_v
        assert restored.get_terminal_positions() == resistor.get_terminal_positions()
