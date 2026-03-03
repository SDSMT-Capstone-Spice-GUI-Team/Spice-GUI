"""Probe overlay subsystem extracted from CircuitCanvasView.

Handles interactive voltage/current probing: mode toggling, hit-testing
nodes and components, formatting results, and node-voltage display.
"""

from GUI.component_item import ComponentGraphicsItem
from PyQt6.QtCore import QPointF, Qt


class CanvasProbeOverlay:
    """Manages probe mode state, hit-testing, and result storage.

    Parameters
    ----------
    canvas : CircuitCanvasView
        The parent canvas view (provides scene, components, simulation
        results, and signal emission).
    """

    def __init__(self, canvas):
        self.canvas = canvas
        self.probe_mode = False
        self.probe_results = []

    # -- public API (called from canvas wrappers / main window) --------

    def set_probe_mode(self, active):
        """Enable or disable probe mode."""
        if active and self.canvas.wire_start_comp is not None:
            self.canvas.cancel_wire_drawing()
        self.probe_mode = active
        if active:
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.canvas.unsetCursor()
        self.canvas.scene.update()

    def clear_probes(self):
        """Remove all probe annotations."""
        self.probe_results = []
        self.canvas.scene.update()

    def display_node_voltages(self):
        """Enable display of node voltages."""
        self.canvas.show_node_voltages = True
        self.canvas.scene.update()

    def hide_node_voltages(self):
        """Disable display of node voltages."""
        self.canvas.show_node_voltages = False
        self.canvas.scene.update()

    # -- hit-testing ---------------------------------------------------

    def probe_at_position(self, scene_pos):
        """Probe the node or component at *scene_pos* and store result."""
        item = self.canvas.itemAt(self.canvas.mapFromScene(scene_pos))
        if isinstance(item, ComponentGraphicsItem):
            if self.canvas.node_voltages:
                return self._probe_component(item)
            comp_ref = item.component_id.lower()
            self.canvas.probeRequested.emit(comp_ref, "component")
            return None

        node = self.find_node_at_position(scene_pos)
        if node:
            if self.canvas.node_voltages:
                return self._probe_node(node)
            self.canvas.probeRequested.emit(node.get_label(), "node")
            return None

        return None

    def find_node_at_position(self, scene_pos):
        """Find a node near the given scene position."""
        for comp_id, comp in self.canvas.components.items():
            for term_idx in range(len(comp.terminals)):
                term_pos = comp.get_terminal_pos(term_idx)
                distance = (term_pos - scene_pos).manhattanLength()
                if distance < 20:
                    if self.canvas.controller:
                        return self.canvas.controller.find_node_for_terminal(comp_id, term_idx)
                    return self.canvas.terminal_to_node.get((comp_id, term_idx))
        return None

    # -- internal result builders --------------------------------------

    def _probe_node(self, node):
        """Create a probe result for a node."""
        from utils.format_utils import format_si

        label = node.get_label()
        if label not in self.canvas.node_voltages:
            return None

        voltage = self.canvas.node_voltages[label]
        pos = self._get_node_position(node)
        if not pos:
            return None

        result = {
            "type": "node",
            "label": label,
            "voltage": format_si(voltage, "V"),
            "pos": QPointF(pos.x(), pos.y()),
        }
        self.probe_results.append(result)
        self.canvas.scene.update()
        return result

    def _probe_component(self, comp_item):
        """Create a probe result for a component."""
        from utils.format_utils import format_si

        comp_id = comp_item.component_id
        comp_ref = comp_id.lower()

        lines = [comp_id]

        term_voltages = []
        for term_idx in range(len(comp_item.terminals)):
            terminal_key = (comp_id, term_idx)
            node = self.canvas.terminal_to_node.get(terminal_key)
            if node:
                node_label = node.get_label()
                if node_label in self.canvas.node_voltages:
                    v = self.canvas.node_voltages[node_label]
                    term_voltages.append((term_idx, node_label, v))

        if len(term_voltages) >= 2:
            v_across = term_voltages[0][2] - term_voltages[1][2]
            lines.append(f"V: {format_si(v_across, 'V')}")
        elif len(term_voltages) == 1:
            lines.append(f"V({term_voltages[0][1]}): {format_si(term_voltages[0][2], 'V')}")

        if comp_ref in self.canvas.branch_currents:
            current = self.canvas.branch_currents[comp_ref]
            lines.append(f"I: {format_si(current, 'A')}")

        if len(term_voltages) >= 2 and comp_ref in self.canvas.branch_currents:
            v_across = term_voltages[0][2] - term_voltages[1][2]
            power = abs(v_across * self.canvas.branch_currents[comp_ref])
            lines.append(f"P: {format_si(power, 'W')}")

        comp_rect = comp_item.boundingRect()
        center = comp_item.mapToScene(comp_rect.center())
        result = {
            "type": "component",
            "label": comp_id,
            "text": "\n".join(lines),
            "pos": QPointF(center.x() + comp_rect.width() / 2 + 10, center.y()),
        }
        self.probe_results.append(result)
        self.canvas.scene.update()
        return result

    def _get_node_position(self, node):
        """Get a representative QPointF position for a node."""
        if not node.terminals:
            return None
        positions = []
        for comp_id, term_idx in node.terminals:
            if comp_id in self.canvas.components:
                pos = self.canvas.components[comp_id].get_terminal_pos(term_idx)
                positions.append(pos)
        if not positions:
            return None
        avg_x = sum(p.x() for p in positions) / len(positions)
        avg_y = sum(p.y() for p in positions) / len(positions)
        return QPointF(avg_x, avg_y)
