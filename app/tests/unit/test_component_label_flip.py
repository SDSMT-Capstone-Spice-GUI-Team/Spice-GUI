"""Tests that component text labels are not mirrored when a component is flipped.

Issue #810: When a component is horizontally flipped (F key), the flip
transform was being applied to the text label, making it unreadable.
The fix applies a counter-scale before drawing text so labels remain
in their original orientation regardless of component flip state.
"""

import inspect
import textwrap

import pytest


def _get_paint_source(cls):
    """Return dedented source of a class's paint method."""
    return textwrap.dedent(inspect.getsource(cls.paint))


def _find_call_indices(source, method_name):
    """Return line indices where painter.<method_name>(...) appears."""
    indices = []
    for i, line in enumerate(source.splitlines()):
        stripped = line.strip()
        if f"painter.{method_name}(" in stripped:
            indices.append(i)
    return indices


class TestLabelCounterFlipStructural:
    """Structural tests verifying the paint method counter-flips text.

    The counter-scale and drawText logic lives in the shared
    _draw_label_text() helper.  paint() delegates to it, so we verify:
    1. paint() calls _draw_label_text
    2. _draw_label_text contains scale() before drawText()
    """

    def test_base_paint_delegates_to_draw_label_text(self):
        """ComponentGraphicsItem.paint() must call _draw_label_text()."""
        from GUI.component_item import ComponentGraphicsItem

        src = _get_paint_source(ComponentGraphicsItem)
        assert "_draw_label_text(" in src, "paint() must delegate to _draw_label_text()"

    def test_ground_paint_delegates_to_draw_label_text(self):
        """Ground.paint() must call _draw_label_text()."""
        from GUI.component_item import Ground

        src = _get_paint_source(Ground)
        assert "_draw_label_text(" in src, "paint() must delegate to _draw_label_text()"

    def test_draw_label_text_applies_counter_scale_before_drawText(self):
        """_draw_label_text() must call scale() before drawText()."""
        from GUI.component_item import ComponentGraphicsItem

        src = textwrap.dedent(inspect.getsource(ComponentGraphicsItem._draw_label_text))
        scale_indices = _find_call_indices(src, "scale")
        drawtext_indices = _find_call_indices(src, "drawText")

        assert len(scale_indices) >= 1, "Must have counter-scale call"
        assert len(drawtext_indices) >= 1, "Must have drawText() call"
        assert scale_indices[0] < drawtext_indices[0], "Counter-scale must come before first drawText"


class TestLabelCounterFlipPainter:
    """Tests using a mock painter to verify counter-flip behaviour."""

    @pytest.fixture
    def _make_item(self):
        """Factory for component items with a mock canvas."""
        from unittest.mock import MagicMock

        from GUI.component_item import ComponentGraphicsItem, Ground

        def factory(cls_or_type, comp_id, **kwargs):
            if cls_or_type is Ground:
                item = Ground(comp_id)
            else:
                item = ComponentGraphicsItem(comp_id, cls_or_type)
            # Inject a mock canvas that enables labels
            mock_canvas = MagicMock()
            mock_canvas.show_component_labels = True
            mock_canvas.show_component_values = True
            item.canvas = mock_canvas
            for k, v in kwargs.items():
                setattr(item, k, v)
            return item

        return factory

    def _collect_scale_calls_around_drawText(self, item, flip_h=False, flip_v=False):
        """Paint the item with a tracking painter, return scale calls around drawText."""
        from unittest.mock import MagicMock

        item.model.flip_h = flip_h
        item.model.flip_v = flip_v

        painter = MagicMock()
        call_log = []

        def track_scale(*args):
            call_log.append(("scale", args))

        def track_drawText(*args):
            call_log.append(("drawText", args))

        painter.scale = track_scale
        painter.drawText = track_drawText

        item.paint(painter)
        return call_log

    def test_no_flip_no_counter_scale(self, _make_item):
        """When not flipped, no scale() should be called."""
        item = _make_item("Resistor", "R1")
        log = self._collect_scale_calls_around_drawText(item, flip_h=False, flip_v=False)
        scale_calls = [e for e in log if e[0] == "scale"]
        assert len(scale_calls) == 0, "No scale calls when component is not flipped"

    def test_flip_h_counter_scale_before_text(self, _make_item):
        """When flip_h is True, scale(-1,1) must be called twice -- once for the
        flip transform and once to undo it before drawing text."""
        item = _make_item("Resistor", "R1")
        log = self._collect_scale_calls_around_drawText(item, flip_h=True)

        scale_calls = [e for e in log if e[0] == "scale"]
        drawtext_calls = [e for e in log if e[0] == "drawText"]

        assert len(scale_calls) == 2, "Must have flip + counter-flip scale calls"
        assert len(drawtext_calls) >= 1, "Must draw text"

        # Both scale calls should be (-1, 1)
        for sc in scale_calls:
            assert sc[1] == (-1, 1), f"Expected scale(-1, 1), got scale{sc[1]}"

        # Counter-scale must precede drawText
        scale_indices = [i for i, e in enumerate(log) if e[0] == "scale"]
        text_indices = [i for i, e in enumerate(log) if e[0] == "drawText"]
        assert scale_indices[1] < text_indices[0], "Counter-scale must precede drawText"

    def test_flip_v_counter_scale_before_text(self, _make_item):
        """When flip_v is True, scale(1,-1) is called twice."""
        item = _make_item("Resistor", "R1")
        log = self._collect_scale_calls_around_drawText(item, flip_v=True)

        scale_calls = [e for e in log if e[0] == "scale"]
        assert len(scale_calls) == 2
        for sc in scale_calls:
            assert sc[1] == (1, -1)

    def test_flip_both_counter_scale_before_text(self, _make_item):
        """When both flip_h and flip_v are True, scale(-1,-1) is called twice."""
        item = _make_item("Resistor", "R1")
        log = self._collect_scale_calls_around_drawText(item, flip_h=True, flip_v=True)

        scale_calls = [e for e in log if e[0] == "scale"]
        assert len(scale_calls) == 2
        for sc in scale_calls:
            assert sc[1] == (-1, -1)

    def test_ground_flip_h_counter_scale(self, _make_item):
        """Ground component also counter-flips text when flip_h is True."""
        from GUI.component_item import Ground

        item = _make_item(Ground, "GND1")
        log = self._collect_scale_calls_around_drawText(item, flip_h=True)

        scale_calls = [e for e in log if e[0] == "scale"]
        drawtext_calls = [e for e in log if e[0] == "drawText"]

        assert len(scale_calls) == 2
        assert len(drawtext_calls) >= 1
        scale_indices = [i for i, e in enumerate(log) if e[0] == "scale"]
        text_indices = [i for i, e in enumerate(log) if e[0] == "drawText"]
        assert scale_indices[1] < text_indices[0]

    @pytest.mark.parametrize(
        "comp_type",
        ["Resistor", "Capacitor", "Inductor", "Voltage Source", "Current Source"],
    )
    def test_multiple_component_types_flip_h(self, _make_item, comp_type):
        """Counter-flip works for various component types (all use base paint)."""
        item = _make_item(comp_type, "X1")
        log = self._collect_scale_calls_around_drawText(item, flip_h=True)

        scale_calls = [e for e in log if e[0] == "scale"]
        assert len(scale_calls) == 2, f"{comp_type} must have counter-flip"
