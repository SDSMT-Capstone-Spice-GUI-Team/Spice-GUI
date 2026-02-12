"""Tests for initial condition (.ic) support on capacitors and inductors."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData

# ---------------------------------------------------------------------------
# ComponentData model tests
# ---------------------------------------------------------------------------


class TestComponentDataIC:
    def test_default_ic_is_none(self):
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        assert comp.initial_condition is None

    def test_set_ic(self):
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        comp.initial_condition = "5"
        assert comp.initial_condition == "5"

    def test_ic_in_constructor(self):
        comp = ComponentData("L1", "Inductor", "10m", (0.0, 0.0), initial_condition="0.1")
        assert comp.initial_condition == "0.1"


# ---------------------------------------------------------------------------
# Serialization round-trip tests
# ---------------------------------------------------------------------------


class TestICSerializer:
    def test_to_dict_without_ic(self):
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        d = comp.to_dict()
        assert "initial_condition" not in d

    def test_to_dict_with_ic(self):
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        comp.initial_condition = "5"
        d = comp.to_dict()
        assert d["initial_condition"] == "5"

    def test_from_dict_without_ic(self):
        d = {"type": "Capacitor", "id": "C1", "value": "1u", "pos": {"x": 0, "y": 0}}
        comp = ComponentData.from_dict(d)
        assert comp.initial_condition is None

    def test_from_dict_with_ic(self):
        d = {"type": "Capacitor", "id": "C1", "value": "1u", "pos": {"x": 0, "y": 0}, "initial_condition": "5"}
        comp = ComponentData.from_dict(d)
        assert comp.initial_condition == "5"

    def test_round_trip_capacitor(self):
        comp = ComponentData("C1", "Capacitor", "100n", (10.0, 20.0))
        comp.initial_condition = "3.3"
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.initial_condition == "3.3"
        assert restored.value == "100n"

    def test_round_trip_inductor(self):
        comp = ComponentData("L1", "Inductor", "10m", (0.0, 0.0))
        comp.initial_condition = "0.5"
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.initial_condition == "0.5"

    def test_round_trip_no_ic(self):
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.initial_condition is None


# ---------------------------------------------------------------------------
# Netlist generation tests
# ---------------------------------------------------------------------------


def _make_rc_circuit(cap_ic=None, ind_ic=None):
    """Build a minimal circuit with R, C, L, voltage source, and ground."""
    model = CircuitModel()

    v1 = ComponentData("V1", "Voltage Source", "5", (0, 0))
    r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
    c1 = ComponentData("C1", "Capacitor", "1u", (200, 0))
    if cap_ic:
        c1.initial_condition = cap_ic
    l1 = ComponentData("L1", "Inductor", "10m", (300, 0))
    if ind_ic:
        l1.initial_condition = ind_ic
    gnd = ComponentData("GND1", "Ground", "0", (0, 100))

    model.components = {c.component_id: c for c in [v1, r1, c1, l1, gnd]}

    # Wire: V1(1) -> R1(0), R1(1) -> C1(0), C1(1) -> GND
    # V1(0) -> GND, L1(0) -> R1(1), L1(1) -> GND
    model.wires = [
        WireData("V1", 1, "R1", 0),
        WireData("R1", 1, "C1", 0),
        WireData("C1", 1, "GND1", 0),
        WireData("V1", 0, "GND1", 0),
        WireData("R1", 1, "L1", 0),
        WireData("L1", 1, "GND1", 0),
    ]
    model.rebuild_nodes()
    model.analysis_type = "Transient"
    model.analysis_params = {"duration": 0.01, "step": 1e-5, "startTime": 0}
    return model


class TestNetlistIC:
    def test_capacitor_without_ic(self):
        model = _make_rc_circuit()
        from simulation import NetlistGenerator

        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        # C1 line should NOT have IC=
        for line in netlist.split("\n"):
            if line.startswith("C1 "):
                assert "IC=" not in line
                break

    def test_capacitor_with_ic(self):
        model = _make_rc_circuit(cap_ic="5")
        from simulation import NetlistGenerator

        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        for line in netlist.split("\n"):
            if line.startswith("C1 "):
                assert "IC=5" in line
                break
        else:
            pytest.fail("C1 line not found in netlist")

    def test_inductor_with_ic(self):
        model = _make_rc_circuit(ind_ic="0.1")
        from simulation import NetlistGenerator

        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        for line in netlist.split("\n"):
            if line.startswith("L1 "):
                assert "IC=0.1" in line
                break
        else:
            pytest.fail("L1 line not found in netlist")

    def test_both_with_ic(self):
        model = _make_rc_circuit(cap_ic="3.3", ind_ic="50m")
        from simulation import NetlistGenerator

        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        found_c = found_l = False
        for line in netlist.split("\n"):
            if line.startswith("C1 "):
                assert "IC=3.3" in line
                found_c = True
            if line.startswith("L1 "):
                assert "IC=50m" in line
                found_l = True
        assert found_c and found_l

    def test_ic_format_in_netlist_line(self):
        """IC value should appear as instance parameter: C1 node1 node2 1u IC=5"""
        model = _make_rc_circuit(cap_ic="5")
        from simulation import NetlistGenerator

        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        for line in netlist.split("\n"):
            if line.startswith("C1 "):
                # Should end with "1u IC=5"
                assert line.endswith("1u IC=5")
                break


# ---------------------------------------------------------------------------
# Properties panel tests (qtbot)
# ---------------------------------------------------------------------------


class TestPropertiesPanelIC:
    def test_ic_field_visible_for_capacitor(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        panel.show_component(comp)
        assert not panel.ic_input.isHidden()
        assert not panel.ic_label.isHidden()

    def test_ic_field_visible_for_inductor(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("L1", "Inductor", "10m", (0.0, 0.0))
        panel.show_component(comp)
        assert not panel.ic_input.isHidden()

    def test_ic_field_hidden_for_resistor(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("R1", "Resistor", "1k", (0.0, 0.0))
        panel.show_component(comp)
        assert panel.ic_input.isHidden()
        assert panel.ic_label.isHidden()

    def test_ic_field_populated(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        comp.initial_condition = "5"
        panel.show_component(comp)
        assert panel.ic_input.text() == "5"

    def test_ic_label_capacitor(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        panel.show_component(comp)
        assert "V" in panel.ic_label.text()  # "Initial V:"

    def test_ic_label_inductor(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("L1", "Inductor", "10m", (0.0, 0.0))
        panel.show_component(comp)
        assert "I" in panel.ic_label.text()  # "Initial I:"

    def test_apply_emits_ic_change(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("C1", "Capacitor", "1u", (0.0, 0.0))
        panel.show_component(comp)

        signals = []
        panel.property_changed.connect(lambda *a: signals.append(a))

        panel.ic_input.setText("5")
        panel.apply_changes()

        ic_signals = [s for s in signals if s[1] == "initial_condition"]
        assert len(ic_signals) == 1
        assert ic_signals[0] == ("C1", "initial_condition", "5")
