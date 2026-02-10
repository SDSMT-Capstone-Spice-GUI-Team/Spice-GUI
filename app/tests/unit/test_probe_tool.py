"""Tests for interactive voltage/current probe tool (Issue #140).

Tests probe mode toggling, node probing, component probing, probe clearing,
stale-result clearing of probes, and sweep probe signal emission.
"""

import pytest

pytest.importorskip("PyQt6")

from GUI.circuit_canvas import CircuitCanvasView
from GUI.circuit_node import Node
from PyQt6.QtCore import QPointF, Qt

# ── Probe mode toggling ──────────────────────────────────────────────


class TestProbeMode:
    """Test probe mode activation and deactivation."""

    def test_probe_mode_default_off(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        assert canvas.probe_mode is False

    def test_set_probe_mode_on(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_probe_mode(True)
        assert canvas.probe_mode is True

    def test_set_probe_mode_off(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_probe_mode(True)
        canvas.set_probe_mode(False)
        assert canvas.probe_mode is False

    def test_probe_mode_changes_cursor(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_probe_mode(True)
        assert canvas.cursor().shape() == Qt.CursorShape.CrossCursor

    def test_probe_mode_restores_cursor(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        original_cursor = canvas.cursor().shape()
        canvas.set_probe_mode(True)
        canvas.set_probe_mode(False)
        assert canvas.cursor().shape() == original_cursor


# ── Probe results storage ────────────────────────────────────────────


class TestProbeResults:
    """Test probe result storage and clearing."""

    def test_probe_results_initially_empty(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        assert canvas.probe_results == []

    def test_clear_probes(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.probe_results = [{"type": "node", "label": "nodeA"}]
        canvas.clear_probes()
        assert canvas.probe_results == []


# ── Node probing ─────────────────────────────────────────────────────


class TestProbeNode:
    """Test probing individual nodes for voltage values."""

    def _make_canvas_with_node(self, qtbot):
        """Create a canvas with a node and OP results."""
        from unittest.mock import MagicMock

        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)

        # Create a mock component so node.get_position() works
        comp = MagicMock()
        comp.component_id = "R1"
        comp.get_terminal_pos = MagicMock(return_value=QPointF(100, 100))
        canvas.components["R1"] = comp

        # Create a node and add it
        node = Node()
        node.auto_label = "nodeA"
        node.terminals = [("R1", 0)]
        canvas.nodes.append(node)
        canvas.terminal_to_node[("R1", 0)] = node
        # Set OP results
        canvas.set_op_results({"nodeA": 5.0}, {"r1": 0.005})
        return canvas, node

    def test_probe_node_creates_result(self, qtbot):
        canvas, node = self._make_canvas_with_node(qtbot)
        result = canvas._probe_node(node)
        assert result is not None
        assert result["type"] == "node"
        assert result["label"] == "nodeA"
        assert "5.00 V" in result["voltage"]

    def test_probe_node_adds_to_results(self, qtbot):
        canvas, node = self._make_canvas_with_node(qtbot)
        canvas._probe_node(node)
        assert len(canvas.probe_results) == 1

    def test_probe_node_unknown_label(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_op_results({"nodeA": 5.0})
        node = Node()
        node.auto_label = "nodeX"
        node.terminals = [("R2", 0)]
        result = canvas._probe_node(node)
        assert result is None


# ── Component probing ─────────────────────────────────────────────────


class TestProbeComponent:
    """Test probing components for voltage/current/power values."""

    def _make_canvas_with_component(self, qtbot):
        """Create a canvas with a component, nodes, and OP results."""
        from unittest.mock import MagicMock

        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)

        # Create mock component item
        comp = MagicMock()
        comp.component_id = "R1"
        comp.terminals = [(0, 0), (0, 40)]  # Two terminals
        comp.boundingRect.return_value = MagicMock(
            center=MagicMock(return_value=QPointF(20, 20)),
            width=MagicMock(return_value=40),
        )
        comp.mapToScene = MagicMock(return_value=QPointF(120, 120))
        canvas.components["R1"] = comp

        # Create two nodes connected to the component terminals
        node_a = Node()
        node_a.auto_label = "nodeA"
        node_a.terminals = [("R1", 0)]
        node_b = Node()
        node_b.auto_label = "nodeB"
        node_b.terminals = [("R1", 1)]
        canvas.nodes = [node_a, node_b]
        canvas.terminal_to_node[("R1", 0)] = node_a
        canvas.terminal_to_node[("R1", 1)] = node_b

        # Set OP results
        canvas.set_op_results({"nodeA": 5.0, "nodeB": 2.5}, {"r1": 0.0025})

        return canvas, comp

    def test_probe_component_creates_result(self, qtbot):
        canvas, comp = self._make_canvas_with_component(qtbot)
        result = canvas._probe_component(comp)
        assert result is not None
        assert result["type"] == "component"
        assert result["label"] == "R1"

    def test_probe_component_shows_voltage(self, qtbot):
        canvas, comp = self._make_canvas_with_component(qtbot)
        result = canvas._probe_component(comp)
        assert "V:" in result["text"]
        assert "2.50 V" in result["text"]

    def test_probe_component_shows_current(self, qtbot):
        canvas, comp = self._make_canvas_with_component(qtbot)
        result = canvas._probe_component(comp)
        assert "I:" in result["text"]
        assert "2.50 mA" in result["text"]

    def test_probe_component_shows_power(self, qtbot):
        canvas, comp = self._make_canvas_with_component(qtbot)
        result = canvas._probe_component(comp)
        # Power = |V * I| = |2.5 * 0.0025| = 6.25 mW
        assert "P:" in result["text"]
        assert "6.25 mW" in result["text"]

    def test_probe_component_adds_to_results(self, qtbot):
        canvas, comp = self._make_canvas_with_component(qtbot)
        canvas._probe_component(comp)
        assert len(canvas.probe_results) == 1


# ── Stale result clearing ────────────────────────────────────────────


class TestProbeStaleClearing:
    """Test that probe results clear when circuit is modified."""

    def _make_canvas_with_probe(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.set_op_results({"nodeA": 5.0}, {"v1": -0.01})
        canvas.probe_results = [{"type": "node", "label": "nodeA"}]
        return canvas

    def test_component_added_clears_probes(self, qtbot):
        canvas = self._make_canvas_with_probe(qtbot)
        canvas._on_model_changed("component_added", None)
        assert canvas.probe_results == []

    def test_wire_removed_clears_probes(self, qtbot):
        canvas = self._make_canvas_with_probe(qtbot)
        canvas._on_model_changed("wire_removed", None)
        assert canvas.probe_results == []

    def test_circuit_cleared_clears_probes(self, qtbot):
        canvas = self._make_canvas_with_probe(qtbot)
        canvas._on_model_changed("circuit_cleared", None)
        assert canvas.probe_results == []


# ── Sweep probe signal emission ──────────────────────────────────────


class TestProbeSweepSignal:
    """Test that probe emits signal for sweep analyses."""

    def _make_canvas_no_op(self, qtbot):
        """Create a canvas with no OP results (simulating sweep analysis)."""
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        canvas.probe_mode = True
        # No node_voltages set - simulates sweep analysis
        return canvas

    def test_probe_requested_signal_exists(self, qtbot):
        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        # Verify the signal exists
        assert hasattr(canvas, "probeRequested")

    def test_probe_node_emits_signal_when_no_op(self, qtbot):
        canvas = self._make_canvas_no_op(qtbot)
        node = Node()
        node.auto_label = "nodeA"
        node.terminals = [("R1", 0)]
        canvas.nodes.append(node)
        canvas.terminal_to_node[("R1", 0)] = node

        # Mock find_node_at_position to return our node
        canvas.find_node_at_position = lambda pos: node

        # Use itemAt returning None (not clicking a component)
        canvas.itemAt = lambda pos: None

        signals = []
        canvas.probeRequested.connect(lambda name, ptype: signals.append((name, ptype)))

        from PyQt6.QtCore import QPointF

        canvas._probe_at_position(QPointF(0, 0))
        assert len(signals) == 1
        assert signals[0] == ("nodeA", "node")
