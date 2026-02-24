"""
Tests for issue #430 / #432 — edited component values must be reflected
in the generated netlist.

These are pure model-layer tests (no Qt dependencies).
"""

from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator


def make_component(component_type, component_id, value, position=(0.0, 0.0)):
    """Helper to create a ComponentData with minimal boilerplate."""
    return ComponentData(
        component_id=component_id,
        component_type=component_type,
        value=value,
        position=position,
    )


def make_wire(start_id, start_term, end_id, end_term):
    """Helper to create a WireData."""
    return WireData(
        start_component_id=start_id,
        start_terminal=start_term,
        end_component_id=end_id,
        end_terminal=end_term,
    )


def _generate(components, wires, nodes, terminal_to_node):
    """Helper to generate a netlist string from circuit data."""
    gen = NetlistGenerator(
        components=components,
        wires=wires,
        nodes=nodes,
        terminal_to_node=terminal_to_node,
        analysis_type="DC Operating Point",
        analysis_params={},
    )
    return gen.generate()


class TestEditedValueInNetlist:
    """Verify that changing comp.value before netlist generation
    produces a netlist with the new value (#430)."""

    def test_resistor_edited_value_in_netlist(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        # Simulate editing the resistor value
        components["R1"].value = "57k"
        netlist = _generate(components, wires, nodes, t2n)
        assert "57k" in netlist
        assert "1k" not in netlist.split("R1")[1].split("\n")[0]

    def test_voltage_source_edited_value_in_netlist(self, simple_resistor_circuit):
        components, wires, nodes, t2n = simple_resistor_circuit
        components["V1"].value = "12V"
        netlist = _generate(components, wires, nodes, t2n)
        assert "12V" in netlist

    def test_capacitor_edited_value_in_netlist(self):
        """Capacitor with changed value should appear in netlist."""
        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "C1": make_component("Capacitor", "C1", "1u", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "C1", 0),
            make_wire("C1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("C1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("C1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        t2n = {
            ("V1", 0): node_a,
            ("C1", 0): node_a,
            ("C1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }

        # Edit capacitor value
        components["C1"].value = "47n"
        netlist = _generate(components, wires, [node_a, node_gnd], t2n)
        assert "47n" in netlist


class TestDiodeEditedModelInNetlist:
    """Verify that changing diode model parameters before netlist generation
    produces a netlist with the new parameters (#432)."""

    def test_diode_edited_params_in_netlist(self):
        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "D1": make_component("Diode", "D1", "IS=1e-14 N=1", (100, 0)),
            "R1": make_component("Resistor", "R1", "1k", (200, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
        }
        wires = [
            make_wire("V1", 0, "D1", 0),
            make_wire("D1", 1, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("D1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("D1", 1), ("R1", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        t2n = {
            ("V1", 0): node_a,
            ("D1", 0): node_a,
            ("D1", 1): node_b,
            ("R1", 0): node_b,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }

        # Simulate editing the diode model parameters
        components["D1"].value = "IS=5e-12 N=2.0 RS=10"
        netlist = _generate(components, wires, [node_a, node_b, node_gnd], t2n)
        # The .model directive should contain the edited parameters
        assert "IS=5e-12" in netlist
        assert "N=2.0" in netlist
        assert "RS=10" in netlist
        # Default params should not appear
        assert "IS=1e-14 N=1)" not in netlist

    def test_led_edited_params_in_netlist(self):
        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "D1": make_component("LED", "D1", "IS=1e-20 N=1.8 EG=1.9", (100, 0)),
            "R1": make_component("Resistor", "R1", "330", (200, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
        }
        wires = [
            make_wire("V1", 0, "D1", 0),
            make_wire("D1", 1, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("D1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("D1", 1), ("R1", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        t2n = {
            ("V1", 0): node_a,
            ("D1", 0): node_a,
            ("D1", 1): node_b,
            ("R1", 0): node_b,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }

        # Edit LED parameters
        components["D1"].value = "IS=1e-18 N=2.5 EG=2.1"
        netlist = _generate(components, wires, [node_a, node_b, node_gnd], t2n)
        assert "IS=1e-18" in netlist
        assert "N=2.5" in netlist

    def test_zener_edited_params_in_netlist(self):
        components = {
            "V1": make_component("Voltage Source", "V1", "12V", (0, 0)),
            "D1": make_component("Zener Diode", "D1", "IS=1e-14 N=1 BV=5.1 IBV=1e-3", (100, 0)),
            "R1": make_component("Resistor", "R1", "1k", (200, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "D1", 0),
            make_wire("D1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_b = NodeData(
            terminals={("R1", 1), ("D1", 0)},
            wire_indices={1},
            auto_label="nodeB",
        )
        node_gnd = NodeData(
            terminals={("D1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={2, 3},
            is_ground=True,
            auto_label="0",
        )
        t2n = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_b,
            ("D1", 0): node_b,
            ("D1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }

        # Edit zener breakdown voltage
        components["D1"].value = "IS=1e-14 N=1 BV=3.3 IBV=5e-3"
        netlist = _generate(components, wires, [node_a, node_b, node_gnd], t2n)
        assert "BV=3.3" in netlist
        assert "IBV=5e-3" in netlist


class TestControllerValueSync:
    """Verify that CircuitController.update_component_value() propagates
    changes so the netlist generator sees the new values."""

    def test_controller_update_value_syncs_to_model(self):
        model = CircuitModel()
        ctrl = CircuitController(model)

        comp = ctrl.add_component("Resistor", (0.0, 0.0))
        assert comp.value == "1k"

        ctrl.update_component_value(comp.component_id, "57k")
        assert model.components[comp.component_id].value == "57k"

    def test_controller_update_diode_value_syncs_to_model(self):
        model = CircuitModel()
        ctrl = CircuitController(model)

        comp = ctrl.add_component("Diode", (0.0, 0.0))
        assert comp.value == "IS=1e-14 N=1"

        ctrl.update_component_value(comp.component_id, "IS=5e-12 N=2.0 RS=10")
        assert model.components[comp.component_id].value == "IS=5e-12 N=2.0 RS=10"

    def test_controller_value_change_notifies_observers(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Resistor", (0.0, 0.0))

        events = []
        ctrl.add_observer(lambda event, data: events.append((event, data)))

        ctrl.update_component_value(comp.component_id, "100k")
        value_events = [e for e in events if e[0] == "component_value_changed"]
        assert len(value_events) == 1
        assert value_events[0][1].value == "100k"
