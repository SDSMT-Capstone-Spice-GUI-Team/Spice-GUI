"""Tests for DC operating point annotations on the circuit canvas.

Tests SI formatting, branch current parsing, canvas OP result storage,
stale-result clearing, and View menu toggle.
"""

import pytest
from simulation.result_parser import ResultParser, format_si

# ── format_si ──────────────────────────────────────────────────────────


class TestFormatSi:
    """Test SI prefix formatting utility."""

    def test_zero(self):
        assert format_si(0, "V") == "0.00 V"

    def test_volts(self):
        assert format_si(3.3, "V") == "3.30 V"

    def test_millivolts(self):
        assert format_si(0.0033, "V") == "3.30 mV"

    def test_microamps(self):
        assert format_si(0.0000021, "A") == "2.10 \u00b5A"

    def test_kilohertz(self):
        assert format_si(1500, "Hz") == "1.50 kHz"

    def test_negative(self):
        assert format_si(-0.005, "A") == "-5.00 mA"

    def test_nanoamps(self):
        assert format_si(1.5e-9, "A") == "1.50 nA"

    def test_picofarads(self):
        assert format_si(4.7e-12, "F") == "4.70 pF"

    def test_megaohm(self):
        assert format_si(2.2e6, "\u03a9") == "2.20 M\u03a9"

    def test_no_unit(self):
        result = format_si(1000)
        assert "k" in result

    def test_large_value(self):
        result = format_si(5e9, "Hz")
        assert "G" in result


# ── parse_op_results branch currents ───────────────────────────────────


class TestParseOpBranchCurrents:
    """Test branch current extraction from OP output."""

    def test_current_pattern_equals(self):
        output = "v(nodeA) = 5.0\ni(v1) = -0.0021\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(-0.0021)

    def test_current_pattern_device_bracket(self):
        output = "@r1[current] = 0.003\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["r1"] == pytest.approx(0.003)

    def test_current_print_format(self):
        output = "  I(v1)                        -2.100000e-03\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"]["v1"] == pytest.approx(-0.0021)

    def test_mixed_voltages_and_currents(self):
        output = "v(nodeA) = 5.0\nv(nodeB) = 2.5\ni(v1) = -0.005\n"
        result = ResultParser.parse_op_results(output)
        assert len(result["node_voltages"]) == 2
        assert len(result["branch_currents"]) == 1

    def test_no_currents(self):
        output = "v(nodeA) = 5.0\n"
        result = ResultParser.parse_op_results(output)
        assert result["branch_currents"] == {}


# ── Canvas OP result storage ───────────────────────────────────────────

pytest.importorskip("PyQt6")

from GUI.circuit_canvas import CircuitCanvasView


class TestCanvasOpResults:
    """Test canvas OP result storage and clearing."""

    def test_set_op_results(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        voltages = {"nodeA": 5.0, "nodeB": 2.5}
        currents = {"v1": -0.005}
        canvas.set_op_results(voltages, currents)
        assert canvas.node_voltages == voltages
        assert canvas.branch_currents == currents
        assert canvas.show_node_voltages is True

    def test_clear_op_results(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_op_results({"nodeA": 5.0}, {"v1": -0.005})
        canvas.clear_op_results()
        assert canvas.node_voltages == {}
        assert canvas.branch_currents == {}
        assert canvas.show_node_voltages is False

    def test_show_op_annotations_default_true(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        assert canvas.show_op_annotations is True

    def test_set_op_results_no_currents(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_op_results({"nodeA": 3.3})
        assert canvas.node_voltages == {"nodeA": 3.3}
        assert canvas.branch_currents == {}


# ── Canvas stale result clearing ───────────────────────────────────────


class TestCanvasStaleClearing:
    """Test that OP annotations clear when circuit is modified."""

    def _make_canvas_with_results(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_op_results({"nodeA": 5.0}, {"v1": -0.01})
        return canvas

    def test_component_added_clears(self, qtbot):
        canvas = self._make_canvas_with_results(qtbot)
        canvas._on_model_changed("component_added", None)
        assert canvas.node_voltages == {}

    def test_component_removed_clears(self, qtbot):
        canvas = self._make_canvas_with_results(qtbot)
        canvas._on_model_changed("component_removed", "R1")
        assert canvas.node_voltages == {}

    def test_wire_added_clears(self, qtbot):
        canvas = self._make_canvas_with_results(qtbot)
        canvas._on_model_changed("wire_added", None)
        assert canvas.node_voltages == {}

    def test_component_value_changed_clears(self, qtbot):
        canvas = self._make_canvas_with_results(qtbot)
        canvas._on_model_changed("component_value_changed", None)
        assert canvas.node_voltages == {}

    def test_component_moved_does_not_clear(self, qtbot):
        canvas = self._make_canvas_with_results(qtbot)
        canvas._on_model_changed("component_moved", None)
        assert canvas.node_voltages == {"nodeA": 5.0}
