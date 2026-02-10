"""Tests for the CircuitStatisticsPanel widget."""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel

pytest.importorskip("PyQt6")

from GUI.circuit_statistics_panel import CircuitStatisticsPanel
from PyQt6.QtWidgets import QFormLayout


@pytest.fixture
def stats_panel(qtbot):
    """Create a CircuitStatisticsPanel wired to a fresh model/controller."""
    model = CircuitModel()
    circuit_ctrl = CircuitController(model)
    sim_ctrl = SimulationController(model, circuit_ctrl)
    panel = CircuitStatisticsPanel(model, circuit_ctrl, sim_ctrl)
    qtbot.addWidget(panel)
    return panel, model, circuit_ctrl


def _add_resistor(ctrl, pos=(0.0, 0.0)):
    return ctrl.add_component("Resistor", pos)


def _add_vsource(ctrl, pos=(100.0, 0.0)):
    return ctrl.add_component("Voltage Source", pos)


def _add_ground(ctrl, pos=(100.0, 100.0)):
    return ctrl.add_component("Ground", pos)


class TestStatisticsEmpty:
    """Tests on an empty circuit."""

    def test_empty_circuit_component_count(self, stats_panel):
        panel, _, _ = stats_panel
        assert panel._total_components_label.text() == "0"

    def test_empty_circuit_wire_count(self, stats_panel):
        panel, _, _ = stats_panel
        assert panel._wire_count_label.text() == "0"

    def test_empty_circuit_node_count(self, stats_panel):
        panel, _, _ = stats_panel
        assert panel._node_count_label.text() == "0"

    def test_empty_circuit_ground_dash(self, stats_panel):
        panel, _, _ = stats_panel
        assert panel._ground_label.text() == "-"

    def test_empty_circuit_floating_dash(self, stats_panel):
        panel, _, _ = stats_panel
        assert panel._floating_label.text() == "-"


class TestStatisticsWithComponents:
    """Tests after adding components via controller."""

    def test_component_count_updates(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_resistor(ctrl)
        assert panel._total_components_label.text() == "1"

    def test_multiple_components(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_resistor(ctrl)
        _add_vsource(ctrl)
        _add_ground(ctrl)
        assert panel._total_components_label.text() == "3"

    def test_component_breakdown_shows_types(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_resistor(ctrl, (0, 0))
        _add_resistor(ctrl, (50, 0))
        ctrl.add_component("Capacitor", (100, 0))

        form = panel._components_form
        labels = []
        for i in range(form.rowCount()):
            label_item = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if label_item and label_item.widget():
                labels.append(label_item.widget().text())
        assert "Resistor:" in labels
        assert "Capacitor:" in labels

    def test_ground_present(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_ground(ctrl)
        assert "Yes" in panel._ground_label.text()

    def test_ground_missing(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_resistor(ctrl)
        assert "No" in panel._ground_label.text()

    def test_component_removed_updates(self, stats_panel):
        panel, _, ctrl = stats_panel
        r1 = _add_resistor(ctrl)
        assert panel._total_components_label.text() == "1"
        ctrl.remove_component(r1.component_id)
        assert panel._total_components_label.text() == "0"


class TestStatisticsWiresAndNodes:
    """Tests for wire and node tracking."""

    def test_wire_count(self, stats_panel):
        panel, _, ctrl = stats_panel
        r1 = _add_resistor(ctrl)
        v1 = _add_vsource(ctrl)
        ctrl.add_wire(r1.component_id, 0, v1.component_id, 0)
        assert panel._wire_count_label.text() == "1"

    def test_node_count(self, stats_panel):
        panel, _, ctrl = stats_panel
        r1 = _add_resistor(ctrl)
        v1 = _add_vsource(ctrl)
        ctrl.add_wire(r1.component_id, 0, v1.component_id, 0)
        assert int(panel._node_count_label.text()) >= 1


class TestStatisticsFloating:
    """Tests for floating terminal detection."""

    def test_floating_terminals_detected(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_resistor(ctrl)
        # R1 has 2 terminals, neither connected
        assert "terminal" in panel._floating_label.text().lower()

    def test_all_connected_no_floating(self, stats_panel):
        panel, _, ctrl = stats_panel
        r1 = _add_resistor(ctrl)
        v1 = _add_vsource(ctrl)
        gnd = _add_ground(ctrl)
        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)
        assert "All connected" in panel._floating_label.text()


class TestStatisticsClear:
    """Tests for circuit clear."""

    def test_clear_resets_counts(self, stats_panel):
        panel, _, ctrl = stats_panel
        _add_resistor(ctrl)
        _add_vsource(ctrl)
        assert panel._total_components_label.text() == "2"
        ctrl.clear_circuit()
        assert panel._total_components_label.text() == "0"
        assert panel._wire_count_label.text() == "0"
        assert panel._node_count_label.text() == "0"


class TestStatisticsNetlist:
    """Tests for netlist preview."""

    def test_empty_netlist_message(self, stats_panel):
        panel, _, _ = stats_panel
        text = panel._netlist_text.toPlainText()
        assert "add components" in text.lower()

    def test_netlist_preview_shows_content(self, stats_panel):
        panel, _, ctrl = stats_panel
        r1 = _add_resistor(ctrl)
        v1 = _add_vsource(ctrl)
        gnd = _add_ground(ctrl)
        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)
        text = panel._netlist_text.toPlainText()
        # Should contain SPICE component lines
        assert "R" in text and "V" in text
