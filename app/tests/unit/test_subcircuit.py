"""Tests for subcircuit support (Phase 1).

Covers:
- parse_subckt() parsing .subckt text
- ComponentData with subcircuit fields (terminal count, positions, serialization)
- NetlistGenerator output for subcircuit components
- CircuitModel JSON round-trip with subcircuit definitions
- NetlistParser import of netlists containing subcircuit instances
- CircuitController.add_subcircuit()
"""

import json

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel
from models.component import ComponentData, _subcircuit_terminal_positions, parse_subckt, subcircuit_body_rect
from models.wire import WireData
from simulation.netlist_generator import NetlistGenerator
from simulation.netlist_parser import import_netlist, parse_netlist

# ── Example subcircuit text ──────────────────────────────────────────

LOWPASS_SUBCKT = """\
.subckt LOWPASS_RC input output gnd_ref
R1 input output 1k
C1 output gnd_ref 1u
.ends"""

BUFFER_SUBCKT = """\
.subckt BUFFER in out
E1 out 0 in 0 1
.ends"""


# ── parse_subckt tests ───────────────────────────────────────────────


class TestParseSubckt:
    def test_basic_parsing(self):
        result = parse_subckt(LOWPASS_SUBCKT)
        assert result["name"] == "LOWPASS_RC"
        assert result["pins"] == ["input", "output", "gnd_ref"]
        assert ".subckt LOWPASS_RC" in result["definition"]
        assert ".ends" in result["definition"]

    def test_two_pin_subcircuit(self):
        result = parse_subckt(BUFFER_SUBCKT)
        assert result["name"] == "BUFFER"
        assert result["pins"] == ["in", "out"]

    def test_with_surrounding_text(self):
        text = "* A comment\n" + LOWPASS_SUBCKT + "\n* Another comment\n"
        result = parse_subckt(text)
        assert result["name"] == "LOWPASS_RC"
        assert result["pins"] == ["input", "output", "gnd_ref"]

    def test_no_subckt_raises(self):
        with pytest.raises(ValueError, match="No .subckt"):
            parse_subckt("R1 1 2 1k\n.end")

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="missing subcircuit name"):
            parse_subckt(".subckt\n.ends")


# ── ComponentData subcircuit fields ──────────────────────────────────


class TestSubcircuitComponentData:
    def _make_subcircuit(self, pins=None):
        pins = pins or ["input", "output", "gnd_ref"]
        return ComponentData(
            component_id="X1",
            component_type="Subcircuit",
            value="LOWPASS_RC",
            position=(100.0, 200.0),
            subcircuit_name="LOWPASS_RC",
            subcircuit_pins=pins,
            subcircuit_definition=LOWPASS_SUBCKT,
        )

    def test_terminal_count_from_pins(self):
        comp = self._make_subcircuit(["a", "b", "c"])
        assert comp.get_terminal_count() == 3

    def test_terminal_count_default_without_pins(self):
        comp = ComponentData(
            component_id="X1",
            component_type="Subcircuit",
            value="test",
            position=(0, 0),
        )
        assert comp.get_terminal_count() == 2

    def test_terminal_positions_3_pin(self):
        comp = self._make_subcircuit(["a", "b", "c"])
        positions = comp.get_base_terminal_positions()
        assert len(positions) == 3
        # Left side: first 2 pins
        assert positions[0][0] < 0
        assert positions[1][0] < 0
        # Right side: 1 pin
        assert positions[2][0] > 0

    def test_terminal_positions_4_pin(self):
        comp = self._make_subcircuit(["a", "b", "c", "d"])
        positions = comp.get_base_terminal_positions()
        assert len(positions) == 4
        # 2 left, 2 right
        assert positions[0][0] < 0
        assert positions[1][0] < 0
        assert positions[2][0] > 0
        assert positions[3][0] > 0

    def test_spice_symbol(self):
        comp = self._make_subcircuit()
        assert comp.get_spice_symbol() == "X"

    def test_to_dict_includes_subcircuit_fields(self):
        comp = self._make_subcircuit()
        d = comp.to_dict()
        assert d["subcircuit_name"] == "LOWPASS_RC"
        assert d["subcircuit_pins"] == ["input", "output", "gnd_ref"]
        assert ".subckt LOWPASS_RC" in d["subcircuit_definition"]
        assert d["type"] == "Subcircuit"

    def test_from_dict_restores_subcircuit_fields(self):
        comp = self._make_subcircuit()
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.component_type == "Subcircuit"
        assert restored.subcircuit_name == "LOWPASS_RC"
        assert restored.subcircuit_pins == ["input", "output", "gnd_ref"]
        assert restored.subcircuit_definition == LOWPASS_SUBCKT
        assert restored.get_terminal_count() == 3

    def test_from_dict_without_subcircuit_fields(self):
        """Non-subcircuit components should not have subcircuit fields."""
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
        )
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.subcircuit_name is None
        assert restored.subcircuit_pins is None


# ── Terminal position helper ─────────────────────────────────────────


class TestSubcircuitTerminalPositions:
    def test_2_pins(self):
        pos = _subcircuit_terminal_positions(2)
        assert len(pos) == 2
        assert pos[0][0] < 0  # left
        assert pos[1][0] > 0  # right

    def test_5_pins(self):
        pos = _subcircuit_terminal_positions(5)
        assert len(pos) == 5
        # 3 left, 2 right
        left = [p for p in pos if p[0] < 0]
        right = [p for p in pos if p[0] > 0]
        assert len(left) == 3
        assert len(right) == 2

    def test_1_pin(self):
        pos = _subcircuit_terminal_positions(1)
        assert len(pos) == 1

    def test_body_rect_scales_with_pins(self):
        r2 = subcircuit_body_rect(2)
        r6 = subcircuit_body_rect(6)
        # Height should increase with more pins
        assert r6[3] >= r2[3]


# ── CircuitModel round-trip ──────────────────────────────────────────


class TestSubcircuitCircuitModel:
    def test_to_dict_includes_subcircuit_definitions(self):
        model = CircuitModel()
        model.subcircuit_definitions["LOWPASS_RC"] = LOWPASS_SUBCKT
        comp = ComponentData(
            component_id="X1",
            component_type="Subcircuit",
            value="LOWPASS_RC",
            position=(0, 0),
            subcircuit_name="LOWPASS_RC",
            subcircuit_pins=["input", "output", "gnd_ref"],
            subcircuit_definition=LOWPASS_SUBCKT,
        )
        model.components["X1"] = comp
        d = model.to_dict()
        assert "subcircuit_definitions" in d
        assert "LOWPASS_RC" in d["subcircuit_definitions"]

    def test_from_dict_restores_subcircuit_definitions(self):
        model = CircuitModel()
        model.subcircuit_definitions["LOWPASS_RC"] = LOWPASS_SUBCKT
        comp = ComponentData(
            component_id="X1",
            component_type="Subcircuit",
            value="LOWPASS_RC",
            position=(0, 0),
            subcircuit_name="LOWPASS_RC",
            subcircuit_pins=["input", "output", "gnd_ref"],
            subcircuit_definition=LOWPASS_SUBCKT,
        )
        model.components["X1"] = comp
        d = model.to_dict()

        restored = CircuitModel.from_dict(d)
        assert "LOWPASS_RC" in restored.subcircuit_definitions
        assert "X1" in restored.components
        r_comp = restored.components["X1"]
        assert r_comp.subcircuit_name == "LOWPASS_RC"
        assert r_comp.get_terminal_count() == 3

    def test_json_round_trip(self, tmp_path):
        model = CircuitModel()
        model.subcircuit_definitions["LOWPASS_RC"] = LOWPASS_SUBCKT
        comp = ComponentData(
            component_id="X1",
            component_type="Subcircuit",
            value="LOWPASS_RC",
            position=(100, 200),
            subcircuit_name="LOWPASS_RC",
            subcircuit_pins=["input", "output", "gnd_ref"],
            subcircuit_definition=LOWPASS_SUBCKT,
        )
        model.components["X1"] = comp
        model.component_counter["X"] = 1

        filepath = tmp_path / "test_subcircuit.json"
        filepath.write_text(json.dumps(model.to_dict(), indent=2))

        data = json.loads(filepath.read_text())
        restored = CircuitModel.from_dict(data)
        assert restored.components["X1"].subcircuit_name == "LOWPASS_RC"
        assert restored.subcircuit_definitions["LOWPASS_RC"] == LOWPASS_SUBCKT

    def test_clear_removes_subcircuit_definitions(self):
        model = CircuitModel()
        model.subcircuit_definitions["test"] = "..."
        model.clear()
        assert len(model.subcircuit_definitions) == 0


# ── NetlistGenerator ─────────────────────────────────────────────────


class TestSubcircuitNetlistGeneration:
    def _build_model(self):
        """Build a circuit with a subcircuit instance wired to V1 and GND."""
        model = CircuitModel()

        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (0, 100))
        sub = ComponentData(
            "X1",
            "Subcircuit",
            "LOWPASS_RC",
            (200, 0),
            subcircuit_name="LOWPASS_RC",
            subcircuit_pins=["input", "output", "gnd_ref"],
            subcircuit_definition=LOWPASS_SUBCKT,
        )

        model.components["V1"] = v1
        model.components["GND1"] = gnd
        model.components["X1"] = sub
        model.subcircuit_definitions["LOWPASS_RC"] = LOWPASS_SUBCKT

        # V1 terminal 0 -> subcircuit input (terminal 0)
        model.add_wire(WireData("V1", 0, "X1", 0))
        # V1 terminal 1 -> GND
        model.add_wire(WireData("V1", 1, "GND1", 0))
        # Subcircuit gnd_ref (terminal 2) -> GND
        model.add_wire(WireData("X1", 2, "GND1", 0))

        return model

    def test_netlist_contains_subcircuit_definition(self):
        model = self._build_model()
        gen = NetlistGenerator(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            "DC Operating Point",
            {},
        )
        netlist = gen.generate()
        assert ".subckt LOWPASS_RC input output gnd_ref" in netlist
        assert ".ends" in netlist

    def test_netlist_contains_x_instance_line(self):
        model = self._build_model()
        gen = NetlistGenerator(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            "DC Operating Point",
            {},
        )
        netlist = gen.generate()
        # Should have X1 <nodes> LOWPASS_RC
        lines = netlist.split("\n")
        x_lines = [l for l in lines if l.startswith("X1 ")]
        assert len(x_lines) == 1
        assert "LOWPASS_RC" in x_lines[0]

    def test_deduplicates_subcircuit_definitions(self):
        """Multiple instances of the same subcircuit should only emit definition once."""
        model = self._build_model()
        sub2 = ComponentData(
            "X2",
            "Subcircuit",
            "LOWPASS_RC",
            (400, 0),
            subcircuit_name="LOWPASS_RC",
            subcircuit_pins=["input", "output", "gnd_ref"],
            subcircuit_definition=LOWPASS_SUBCKT,
        )
        model.components["X2"] = sub2

        gen = NetlistGenerator(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            "DC Operating Point",
            {},
        )
        netlist = gen.generate()
        # Definition should appear exactly once
        assert netlist.count(".subckt LOWPASS_RC") == 1


# ── NetlistParser (import) ───────────────────────────────────────────


class TestSubcircuitNetlistParser:
    NETLIST_WITH_SUBCIRCUIT = """\
Test Circuit with Subcircuit
.subckt LOWPASS_RC input output gnd_ref
R1 input output 1k
C1 output gnd_ref 1u
.ends

V1 1 0 5V
X1 1 2 0 LOWPASS_RC
R2 2 0 10k

.op
.end"""

    def test_parse_netlist_finds_subcircuit_defs(self):
        parsed = parse_netlist(self.NETLIST_WITH_SUBCIRCUIT)
        assert "subcircuit_definitions" in parsed
        assert "LOWPASS_RC" in parsed["subcircuit_definitions"]
        defn = parsed["subcircuit_definitions"]["LOWPASS_RC"]
        assert defn["name"] == "LOWPASS_RC"
        assert defn["pins"] == ["input", "output", "gnd_ref"]

    def test_parse_netlist_identifies_subcircuit_component(self):
        parsed = parse_netlist(self.NETLIST_WITH_SUBCIRCUIT)
        subcircuit_comps = [c for c in parsed["components"] if c["type"] == "Subcircuit"]
        assert len(subcircuit_comps) == 1
        sc = subcircuit_comps[0]
        assert sc["id"] == "X1"
        assert sc["subcircuit_name"] == "LOWPASS_RC"
        assert sc["subcircuit_pins"] == ["input", "output", "gnd_ref"]

    def test_import_netlist_creates_subcircuit_component(self):
        model, analysis = import_netlist(self.NETLIST_WITH_SUBCIRCUIT)
        x1 = model.components.get("X1")
        assert x1 is not None
        assert x1.component_type == "Subcircuit"
        assert x1.subcircuit_name == "LOWPASS_RC"
        assert x1.subcircuit_pins == ["input", "output", "gnd_ref"]
        assert x1.get_terminal_count() == 3

    def test_import_netlist_stores_subcircuit_definition(self):
        model, _ = import_netlist(self.NETLIST_WITH_SUBCIRCUIT)
        assert "LOWPASS_RC" in model.subcircuit_definitions

    def test_opamp_still_parses_as_opamp(self):
        """Ensure op-amp subcircuits are still recognized as Op-Amp type."""
        netlist = """\
Test Op-Amp
.subckt OPAMP_IDEAL inp inn out
E_amp out 0 inp inn 1e6
.ends

XOA1 1 2 3 OPAMP_IDEAL
V1 1 0 5V
R1 2 0 1k

.op
.end"""
        parsed = parse_netlist(netlist)
        opamp_comps = [c for c in parsed["components"] if c["type"] == "Op-Amp"]
        assert len(opamp_comps) == 1


# ── CircuitController.add_subcircuit ─────────────────────────────────


class TestCircuitControllerAddSubcircuit:
    def test_add_subcircuit(self):
        ctrl = CircuitController()
        comp = ctrl.add_subcircuit(LOWPASS_SUBCKT, (100.0, 200.0))
        assert comp.component_id == "X1"
        assert comp.component_type == "Subcircuit"
        assert comp.subcircuit_name == "LOWPASS_RC"
        assert comp.subcircuit_pins == ["input", "output", "gnd_ref"]
        assert comp.get_terminal_count() == 3
        assert "X1" in ctrl.model.components
        assert "LOWPASS_RC" in ctrl.model.subcircuit_definitions

    def test_add_multiple_subcircuits(self):
        ctrl = CircuitController()
        c1 = ctrl.add_subcircuit(LOWPASS_SUBCKT, (100, 100))
        c2 = ctrl.add_subcircuit(BUFFER_SUBCKT, (300, 100))
        assert c1.component_id == "X1"
        assert c2.component_id == "X2"
        assert ctrl.model.component_counter["X"] == 2

    def test_add_subcircuit_invalid_text(self):
        ctrl = CircuitController()
        with pytest.raises(ValueError):
            ctrl.add_subcircuit("not a subcircuit", (0, 0))

    def test_add_subcircuit_notifies_observer(self):
        ctrl = CircuitController()
        events = []
        ctrl.add_observer(lambda event, data: events.append((event, data)))
        ctrl.add_subcircuit(LOWPASS_SUBCKT, (0, 0))
        assert any(e == "component_added" for e, _ in events)
