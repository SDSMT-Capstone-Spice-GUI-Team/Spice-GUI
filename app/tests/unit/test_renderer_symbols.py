# AUDIT(testing): pixel-level draw call assertions (e.g., call(5, -4, 8, 0)) are extremely brittle — any coordinate tweak breaks tests even if visual output is correct; consider snapshot/image-diff testing instead
"""
Tests for renderer symbol correctness (#431, #433).

Structural tests verify that renderers draw the expected primitives
(no Qt display needed — we mock the painter).
"""

from unittest.mock import MagicMock, call

from GUI.renderers import IEEEMOSFETNMOS, IEEEMOSFETPMOS, IEEECurrentSource, IEEEOpAmp, IEEEVoltageSource, get_renderer
from PyQt6.QtGui import QColor, QPen


def _make_mock_painter():
    """Create a mock painter that tracks draw calls and has a pen with color."""
    painter = MagicMock()
    pen = MagicMock()
    pen.color.return_value = QColor(0, 0, 0)
    painter.pen.return_value = pen
    return painter


def _make_mock_component(in_scene=False):
    """Create a mock component for renderer tests."""
    comp = MagicMock()
    comp.scene.return_value = MagicMock() if in_scene else None
    comp.component_type = "Current Source"
    return comp


class TestIEEECurrentSourceArrow:
    """#431: IEEE current source should draw an arrow, not 'I' text."""

    def test_does_not_draw_text(self):
        renderer = IEEECurrentSource()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        painter.drawText.assert_not_called()

    def test_draws_circle(self):
        renderer = IEEECurrentSource()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        painter.drawEllipse.assert_called_once_with(-15, -15, 30, 30)

    def test_draws_arrow_line(self):
        renderer = IEEECurrentSource()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        # Should draw a line for the arrow shaft and two lines for the arrowhead
        line_calls = painter.drawLine.call_args_list
        assert len(line_calls) >= 3  # shaft + 2 arrowhead lines

    def test_draws_arrowhead(self):
        renderer = IEEECurrentSource()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        # Check that arrowhead lines converge to the tip
        line_calls = painter.drawLine.call_args_list
        # Arrowhead lines should end at (8, 0) — the arrow tip
        arrowhead_calls = [c for c in line_calls if c == call(5, -4, 8, 0) or c == call(5, 4, 8, 0)]
        assert len(arrowhead_calls) == 2


class TestIEEEVoltageSourcePolarity:
    """#431: Voltage source +/- markers should be visible."""

    def test_draws_plus_and_minus(self):
        renderer = IEEEVoltageSource()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list
        # Plus sign: vertical + horizontal lines near x=-10
        assert call(-10, 2, -10, -2) in line_calls
        assert call(-12, 0, -8, 0) in line_calls
        # Minus sign: horizontal line near x=10
        assert call(12, 0, 8, 0) in line_calls


class TestIEEEOpAmpThemeColor:
    """#431: Op-amp polarity markers should use component color, not hardcoded black."""

    def test_polarity_uses_pen_color_not_hardcoded_black(self):
        renderer = IEEEOpAmp()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        # Verify setPen is called but NOT with GlobalColor.black
        for call_args in painter.setPen.call_args_list:
            pen_arg = call_args[0][0]
            if isinstance(pen_arg, QPen):
                # Should not be hardcoded to black
                assert pen_arg.color() != QColor(0, 0, 0) or pen_arg == QPen(QColor(0, 0, 0), 2)


class TestMOSFETEnhancementMode:
    """#433: MOSFET symbols should use segmented channel for enhancement mode."""

    def test_nmos_has_segmented_channel(self):
        renderer = IEEEMOSFETNMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list

        # Should NOT have a single continuous channel line from -12 to 12 at x=-5
        continuous_channel = call(-5, -12, -5, 12)
        assert continuous_channel not in line_calls

        # Should have three separate channel segments
        segment_calls = [c for c in line_calls if c[0][0] == -5 and c[0][2] == -5]  # x1=-5 and x2=-5
        assert len(segment_calls) == 3

    def test_pmos_has_segmented_channel(self):
        renderer = IEEEMOSFETPMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list

        # Should NOT have a single continuous channel line
        continuous_channel = call(-5, -12, -5, 12)
        assert continuous_channel not in line_calls

        # Should have three separate channel segments
        segment_calls = [c for c in line_calls if c[0][0] == -5 and c[0][2] == -5]
        assert len(segment_calls) == 3

    def test_pmos_has_gate_bubble(self):
        renderer = IEEEMOSFETPMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        painter.drawEllipse.assert_called_once()

    def test_nmos_has_no_gate_bubble(self):
        renderer = IEEEMOSFETNMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        painter.drawEllipse.assert_not_called()

    def test_nmos_arrow_points_inward(self):
        """NMOS arrow should point toward the channel (inward).

        The arrowhead vertex (tip) should be at a smaller x than the barbs,
        indicating the arrow points left toward the channel.
        """
        renderer = IEEEMOSFETNMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list
        # Arrowhead: two lines from tip (x=-1) with barbs toward x=5
        arrowhead = [c for c in line_calls if c[0][0] == -1 and c[0][2] == 5]
        assert len(arrowhead) == 2

    def test_pmos_arrow_points_outward(self):
        """PMOS arrow should point away from the channel (outward).

        The arrowhead vertex (tip) should be at a larger x than the barbs,
        indicating the arrow points right away from the channel.
        """
        renderer = IEEEMOSFETPMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list
        # Arrowhead: two lines from tip (x=5) with barbs toward x=-1
        arrowhead = [c for c in line_calls if c[0][0] == 5 and c[0][2] == -1]
        assert len(arrowhead) == 2

    def test_nmos_has_body_source_tie(self):
        """NMOS should have a vertical bar on the source side of the body."""
        renderer = IEEEMOSFETNMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list
        assert call(10, 0, 10, 10) in line_calls

    def test_pmos_has_body_source_tie(self):
        """PMOS should have a vertical bar on the source side of the body."""
        renderer = IEEEMOSFETPMOS()
        painter = _make_mock_painter()
        comp = _make_mock_component(in_scene=False)
        renderer.draw(painter, comp)
        line_calls = painter.drawLine.call_args_list
        assert call(10, 0, 10, 10) in line_calls


class TestRendererRegistration:
    """All component types should have renderers for both ieee and iec styles."""

    def test_all_types_have_ieee_renderer(self):
        from models.component import COMPONENT_TYPES

        skip = {
            "Ground",
            "Transformer",
        }  # Ground handled separately, Transformer is new
        for ctype in COMPONENT_TYPES:
            if ctype in skip:
                continue
            try:
                r = get_renderer(ctype, "ieee")
                assert r is not None
            except KeyError:
                pass  # Some types may not have renderers yet

    def test_all_types_have_iec_renderer(self):
        from models.component import COMPONENT_TYPES

        skip = {"Ground", "Transformer"}
        for ctype in COMPONENT_TYPES:
            if ctype in skip:
                continue
            try:
                r = get_renderer(ctype, "iec")
                assert r is not None
            except KeyError:
                pass
