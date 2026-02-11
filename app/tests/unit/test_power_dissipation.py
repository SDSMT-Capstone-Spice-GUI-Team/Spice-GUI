"""Tests for power dissipation calculation and Properties Panel integration."""

import pytest
from models.component import ComponentData
from models.node import NodeData
from simulation.power_calculator import calculate_power, total_power


def _make_node(terminals, label, is_ground=False):
    """Helper to create a NodeData with the given terminals and label."""
    node = NodeData(
        terminals=set(terminals),
        wire_indices=set(),
        is_ground=is_ground,
        auto_label=label,
    )
    return node


# ── Power Calculator Unit Tests ──────────────────────────────────────


class TestCalculatePowerResistor:
    """Test power calculation for resistors."""

    def test_resistor_power_from_voltage(self):
        # 1k resistor with 5V across it: P = 25/1000 = 0.025W
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        nodeA = _make_node([("R1", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 0.0}

        result = calculate_power([r1], [nodeA, nodeB], voltages)
        assert "R1" in result
        assert result["R1"] == pytest.approx(0.025)

    def test_resistor_power_with_si_value(self):
        # 10k resistor, 10V across: P = 100/10000 = 0.01W
        r1 = ComponentData("R1", "Resistor", "10k", (0, 0))
        nodeA = _make_node([("R1", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        voltages = {"nodeA": 10.0, "nodeB": 0.0}

        result = calculate_power([r1], [nodeA, nodeB], voltages)
        assert result["R1"] == pytest.approx(0.01)

    def test_resistor_no_voltage_difference(self):
        # Same voltage on both terminals -> 0 power
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        nodeA = _make_node([("R1", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 5.0}

        result = calculate_power([r1], [nodeA, nodeB], voltages)
        assert result["R1"] == pytest.approx(0.0)


class TestCalculatePowerWithBranchCurrents:
    """Test power calculation when branch currents are available."""

    def test_source_power_from_branch_current(self):
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        nodeA = _make_node([("V1", 0)], "nodeA")
        nodeB = _make_node([("V1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 0.0}
        currents = {"v1": -0.01}  # 10mA flowing (negative = supplying)

        result = calculate_power([v1], [nodeA, nodeB], voltages, currents)
        assert "V1" in result
        assert result["V1"] == pytest.approx(-0.05)  # -50mW (supplying)

    def test_resistor_prefers_branch_current(self):
        # If branch current available, use P = V*I instead of V²/R
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        nodeA = _make_node([("R1", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 0.0}
        currents = {"r1": 0.005}

        result = calculate_power([r1], [nodeA, nodeB], voltages, currents)
        assert result["R1"] == pytest.approx(0.025)


class TestCalculatePowerSpecialCases:
    """Test power calculation edge cases."""

    def test_ground_excluded(self):
        gnd = ComponentData("GND1", "Ground", "0V", (0, 0))
        node0 = _make_node([("GND1", 0)], "0", is_ground=True)
        voltages = {"0": 0.0}

        result = calculate_power([gnd], [node0], voltages)
        assert "GND1" not in result

    def test_capacitor_zero_dc_power(self):
        c1 = ComponentData("C1", "Capacitor", "1u", (0, 0))
        nodeA = _make_node([("C1", 0)], "nodeA")
        nodeB = _make_node([("C1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 0.0}

        result = calculate_power([c1], [nodeA, nodeB], voltages)
        assert result["C1"] == pytest.approx(0.0)

    def test_inductor_zero_dc_power(self):
        l1 = ComponentData("L1", "Inductor", "1m", (0, 0))
        nodeA = _make_node([("L1", 0)], "nodeA")
        nodeB = _make_node([("L1", 1)], "nodeB")
        voltages = {"nodeA": 3.3, "nodeB": 0.0}

        result = calculate_power([l1], [nodeA, nodeB], voltages)
        assert result["L1"] == pytest.approx(0.0)

    def test_current_source_power(self):
        i1 = ComponentData("I1", "Current Source", "1A", (0, 0))
        nodeA = _make_node([("I1", 0)], "nodeA")
        nodeB = _make_node([("I1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 0.0}

        result = calculate_power([i1], [nodeA, nodeB], voltages)
        assert result["I1"] == pytest.approx(5.0)

    def test_empty_voltages_returns_empty(self):
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        result = calculate_power([r1], [], {})
        assert result == {}

    def test_missing_node_skips_component(self):
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        # Only one terminal mapped
        nodeA = _make_node([("R1", 0)], "nodeA")
        voltages = {"nodeA": 5.0}

        result = calculate_power([r1], [nodeA], voltages)
        assert "R1" not in result


class TestCalculatePowerDictInput:
    """Regression tests for #206: components dict passed instead of list."""

    def test_dict_values_work_as_components(self):
        """calculate_power should work with dict_values (components.values())."""
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        comp_dict = {"R1": r1, "R2": r2}
        nodeA = _make_node([("R1", 0), ("R2", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        nodeC = _make_node([("R2", 1)], "nodeC")
        voltages = {"nodeA": 10.0, "nodeB": 0.0, "nodeC": 0.0}

        result = calculate_power(list(comp_dict.values()), [nodeA, nodeB, nodeC], voltages)
        assert "R1" in result
        assert "R2" in result
        assert result["R1"] == pytest.approx(0.1)  # 10V^2 / 1k = 0.1W
        assert result["R2"] == pytest.approx(0.05)  # 10V^2 / 2k = 0.05W

    def test_raw_dict_raises_attribute_error(self):
        """Passing a dict directly (not .values()) should fail with AttributeError."""
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        comp_dict = {"R1": r1}
        nodeA = _make_node([("R1", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        voltages = {"nodeA": 5.0, "nodeB": 0.0}

        with pytest.raises(AttributeError, match="component_id"):
            calculate_power(comp_dict, [nodeA, nodeB], voltages)

    def test_multiple_components_power_sum(self):
        """Verify total power sums correctly with dict_values input."""
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 100))
        comp_dict = {"R1": r1, "V1": v1}
        node_pos = _make_node([("V1", 0), ("R1", 0)], "nodeA")
        node_gnd = _make_node([("V1", 1), ("R1", 1)], "0", is_ground=True)
        voltages = {"nodeA": 5.0, "0": 0.0}
        currents = {"v1": -0.005}

        result = calculate_power(list(comp_dict.values()), [node_pos, node_gnd], voltages, currents)
        assert result["R1"] == pytest.approx(0.025)
        assert result["V1"] == pytest.approx(-0.025)
        assert total_power(result) == pytest.approx(0.0)

    def test_single_component_dict_values(self):
        """Single-element dict_values works correctly."""
        r1 = ComponentData("R1", "Resistor", "100", (0, 0))
        comp_dict = {"R1": r1}
        nodeA = _make_node([("R1", 0)], "nodeA")
        nodeB = _make_node([("R1", 1)], "nodeB")
        voltages = {"nodeA": 1.0, "nodeB": 0.0}

        result = calculate_power(list(comp_dict.values()), [nodeA, nodeB], voltages)
        assert result["R1"] == pytest.approx(0.01)  # 1V^2 / 100 = 0.01W

    def test_empty_dict_values(self):
        """Empty dict_values produces empty result."""
        comp_dict = {}
        voltages = {"nodeA": 5.0}
        result = calculate_power(list(comp_dict.values()), [], voltages)
        assert result == {}


class TestTotalPower:
    """Test total power calculation."""

    def test_total_power_sums(self):
        power = {"R1": 0.025, "R2": 0.01, "V1": -0.035}
        assert total_power(power) == pytest.approx(0.0)

    def test_empty_dict(self):
        assert total_power({}) == pytest.approx(0.0)


# ── Properties Panel Integration ─────────────────────────────────────

pytest.importorskip("PyQt6")

from GUI.properties_panel import PropertiesPanel


class TestPropertiesPanelResults:
    """Test the simulation results section of the Properties Panel."""

    def test_results_hidden_by_default(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert panel.results_group.isHidden()

    def test_set_simulation_results_shows_group(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("R1", "Resistor", "1k", (0, 0))
        panel.show_component(comp)
        panel.set_simulation_results({"R1": 0.025}, {"R1": 5.0}, 0.025)
        assert not panel.results_group.isHidden()

    def test_clear_simulation_results_hides_group(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        panel.set_simulation_results({"R1": 0.025}, {}, 0.025)
        panel.clear_simulation_results()
        assert panel.results_group.isHidden()

    def test_power_label_shows_value(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("R1", "Resistor", "1k", (0, 0))
        panel.show_component(comp)
        panel.set_simulation_results({"R1": 0.025}, {}, 0.025)
        assert "mW" in panel.power_label.text() or "25" in panel.power_label.text()

    def test_voltage_label_shows_value(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("R1", "Resistor", "1k", (0, 0))
        panel.show_component(comp)
        panel.set_simulation_results({"R1": 0.025}, {"R1": 5.0}, 0.025)
        assert "V" in panel.voltage_label.text()

    def test_no_selection_hides_results(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        panel.set_simulation_results({"R1": 0.025}, {}, 0.025)
        panel.show_no_selection()
        assert panel.results_group.isHidden()

    def test_results_update_on_component_change(self, qtbot):
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        panel.set_simulation_results({"R1": 0.025, "R2": 0.01}, {}, 0.035)
        r2 = ComponentData("R2", "Resistor", "10k", (100, 0))
        panel.show_component(r2)
        assert not panel.results_group.isHidden()
        assert "10" in panel.power_label.text() or "mW" in panel.power_label.text()
