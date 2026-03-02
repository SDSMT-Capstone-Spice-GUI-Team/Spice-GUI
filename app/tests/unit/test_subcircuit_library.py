"""Tests for the subcircuit library: parsing, persistence, registration, and netlist integration."""

import pytest
from models.subcircuit_library import (
    SubcircuitDefinition,
    SubcircuitLibrary,
    parse_subckt,
    register_subcircuit_component,
)

# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestParseSubckt:
    """Tests for the .subckt parser."""

    def test_parse_simple_subcircuit(self):
        text = ".subckt MYAMP inp inn out\nE1 out 0 inp inn 1e6\n.ends"
        defs = parse_subckt(text)
        assert len(defs) == 1
        assert defs[0].name == "MYAMP"
        assert defs[0].terminals == ["inp", "inn", "out"]
        assert ".subckt MYAMP" in defs[0].spice_definition
        assert ".ends" in defs[0].spice_definition

    def test_parse_multiple_subcircuits(self):
        text = ".subckt SUB1 a b\nR1 a b 1k\n.ends\n\n.subckt SUB2 x y z\nR1 x y 2k\nR2 y z 3k\n.ends\n"
        defs = parse_subckt(text)
        assert len(defs) == 2
        assert defs[0].name == "SUB1"
        assert defs[0].terminals == ["a", "b"]
        assert defs[1].name == "SUB2"
        assert defs[1].terminals == ["x", "y", "z"]

    def test_parse_with_params(self):
        text = ".subckt MYCOMP a b c GAIN=100\nE1 c 0 a b {GAIN}\n.ends"
        defs = parse_subckt(text)
        assert len(defs) == 1
        # GAIN=100 should be excluded from terminals
        assert defs[0].terminals == ["a", "b", "c"]

    def test_parse_case_insensitive(self):
        text = ".SUBCKT UPPER in out\nR1 in out 1k\n.ENDS"
        defs = parse_subckt(text)
        assert len(defs) == 1
        assert defs[0].name == "UPPER"

    def test_parse_with_comments(self):
        text = (
            ".subckt COMMENTED a b\n"
            "* This is a comment describing the subcircuit\n"
            "* Another comment line\n"
            "R1 a b 1k\n"
            ".ends"
        )
        defs = parse_subckt(text)
        assert len(defs) == 1
        assert "comment describing" in defs[0].description

    def test_parse_no_subcircuit_raises(self):
        with pytest.raises(ValueError, match="No valid .subckt"):
            parse_subckt("R1 1 2 1k\n.end")

    def test_parse_empty_text_raises(self):
        with pytest.raises(ValueError, match="No valid .subckt"):
            parse_subckt("")

    def test_parse_mixed_content(self):
        text = "* Some header\n.param VCC=5\n.subckt HIDDEN a b\nR1 a b 1k\n.ends\n* trailing content\n"
        defs = parse_subckt(text)
        assert len(defs) == 1
        assert defs[0].name == "HIDDEN"


# ---------------------------------------------------------------------------
# SubcircuitDefinition tests
# ---------------------------------------------------------------------------


class TestSubcircuitDefinition:
    def test_terminal_count(self):
        d = SubcircuitDefinition(
            name="TEST",
            terminals=["a", "b", "c"],
            spice_definition=".subckt TEST a b c\n.ends",
        )
        assert d.terminal_count == 3

    def test_serialization_roundtrip(self):
        d = SubcircuitDefinition(
            name="TEST",
            terminals=["in", "out", "gnd"],
            spice_definition=".subckt TEST in out gnd\nR1 in out 1k\n.ends",
            description="A test subcircuit",
            builtin=True,
        )
        data = d.to_dict()
        d2 = SubcircuitDefinition.from_dict(data)
        assert d2.name == d.name
        assert d2.terminals == d.terminals
        assert d2.spice_definition == d.spice_definition
        assert d2.description == d.description
        assert d2.builtin == d.builtin


# ---------------------------------------------------------------------------
# SubcircuitLibrary persistence tests
# ---------------------------------------------------------------------------


class TestSubcircuitLibrary:
    def test_add_and_get(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        defn = SubcircuitDefinition(
            name="MYCOMP",
            terminals=["a", "b"],
            spice_definition=".subckt MYCOMP a b\nR1 a b 1k\n.ends",
        )
        lib.add(defn)
        assert lib.get("MYCOMP") is defn
        assert "MYCOMP" in lib.names()

    def test_persistence_roundtrip(self, tmp_path):
        lib_dir = tmp_path / "lib"
        lib = SubcircuitLibrary(lib_dir)
        defn = SubcircuitDefinition(
            name="PERSIST",
            terminals=["x", "y"],
            spice_definition=".subckt PERSIST x y\nR1 x y 2k\n.ends",
            description="Persisted",
        )
        lib.add(defn)

        # Verify file was written
        files = list(lib_dir.glob("*.json"))
        assert len(files) == 1

        # Load fresh library from same directory
        lib2 = SubcircuitLibrary(lib_dir)
        loaded = lib2.get("PERSIST")
        assert loaded is not None
        assert loaded.terminals == ["x", "y"]
        assert loaded.description == "Persisted"

    def test_remove(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        defn = SubcircuitDefinition(
            name="REMOVEME",
            terminals=["a", "b"],
            spice_definition=".subckt REMOVEME a b\n.ends",
        )
        lib.add(defn)
        assert lib.remove("REMOVEME") is True
        assert lib.get("REMOVEME") is None

    def test_remove_builtin_fails(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        defn = SubcircuitDefinition(
            name="BUILTIN",
            terminals=["a", "b"],
            spice_definition=".subckt BUILTIN a b\n.ends",
            builtin=True,
        )
        lib.add(defn)
        assert lib.remove("BUILTIN") is False
        assert lib.get("BUILTIN") is not None

    def test_import_file(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        subckt_file = tmp_path / "test.subckt"
        subckt_file.write_text(".subckt FROMFILE a b c\nR1 a b 1k\nR2 b c 2k\n.ends\n")
        imported = lib.import_file(subckt_file)
        assert len(imported) == 1
        assert imported[0].name == "FROMFILE"
        assert lib.get("FROMFILE") is not None

    def test_import_text(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        text = ".subckt FROMTEXT x y\nR1 x y 1k\n.ends"
        imported = lib.import_text(text)
        assert len(imported) == 1
        assert imported[0].name == "FROMTEXT"

    def test_empty_library(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "nonexistent")
        assert lib.names() == []


# ---------------------------------------------------------------------------
# Component registration tests
# ---------------------------------------------------------------------------


class TestSubcircuitRegistration:
    def test_register_adds_to_component_system(self, tmp_path):
        from models.component import (
            COMPONENT_CATEGORIES,
            COMPONENT_TYPES,
            DEFAULT_VALUES,
            SPICE_SYMBOLS,
            TERMINAL_COUNTS,
            TERMINAL_GEOMETRY,
        )

        defn = SubcircuitDefinition(
            name="TEST_REG_237",
            terminals=["in", "out", "gnd"],
            spice_definition=".subckt TEST_REG_237 in out gnd\nR1 in out 1k\n.ends",
        )
        register_subcircuit_component(defn)

        assert "TEST_REG_237" in COMPONENT_TYPES
        assert SPICE_SYMBOLS["TEST_REG_237"] == "X"
        assert TERMINAL_COUNTS["TEST_REG_237"] == 3
        assert DEFAULT_VALUES["TEST_REG_237"] == "TEST_REG_237"
        assert "TEST_REG_237" in TERMINAL_GEOMETRY
        assert "Subcircuits" in COMPONENT_CATEGORIES
        assert "TEST_REG_237" in COMPONENT_CATEGORIES["Subcircuits"]

    def test_register_idempotent(self, tmp_path):
        from models.component import COMPONENT_TYPES

        defn = SubcircuitDefinition(
            name="TEST_IDEMPOTENT_237",
            terminals=["a", "b"],
            spice_definition=".subckt TEST_IDEMPOTENT_237 a b\nR1 a b 1k\n.ends",
        )
        register_subcircuit_component(defn)
        count_before = COMPONENT_TYPES.count("TEST_IDEMPOTENT_237")
        register_subcircuit_component(defn)
        count_after = COMPONENT_TYPES.count("TEST_IDEMPOTENT_237")
        assert count_before == count_after == 1


# ---------------------------------------------------------------------------
# Netlist integration tests
# ---------------------------------------------------------------------------


class TestSubcircuitNetlist:
    def _make_subcircuit_circuit(self, subckt_name, terminal_count):
        """Build a minimal circuit using a subcircuit component."""
        from models.node import NodeData
        from tests.conftest import make_component, make_wire

        # Register the subcircuit so TERMINAL_COUNTS etc. are set
        defn = SubcircuitDefinition(
            name=subckt_name,
            terminals=[f"t{i}" for i in range(terminal_count)],
            spice_definition=f".subckt {subckt_name} "
            + " ".join(f"t{i}" for i in range(terminal_count))
            + "\nR1 t0 t1 1k\n.ends",
        )
        register_subcircuit_component(defn)

        # Build circuit: V1 -- subcircuit -- GND
        v1 = make_component("Voltage Source", "V1", "5V", (0, 0))
        sub = make_component(subckt_name, "X1", subckt_name, (100, 0))
        gnd = make_component("Ground", "GND1", "0V", (200, 0))

        components = {"V1": v1, "X1": sub, "GND1": gnd}

        # Wire V1+ to sub terminal 0
        wires = [make_wire("V1", 0, "X1", 0)]
        # Wire remaining sub terminals to GND
        for i in range(1, terminal_count):
            wires.append(make_wire("X1", i, "GND1", 0))
        # Wire V1- to GND
        wires.append(make_wire("V1", 1, "GND1", 0))

        node_v = NodeData(
            terminals={("V1", 0), ("X1", 0)},
            wire_indices={0},
            auto_label="nodeV",
        )
        gnd_terminals = {("GND1", 0), ("V1", 1)}
        gnd_wires = set()
        for i in range(1, terminal_count):
            gnd_terminals.add(("X1", i))
            gnd_wires.add(i)
        gnd_wires.add(len(wires) - 1)
        node_gnd = NodeData(
            terminals=gnd_terminals,
            wire_indices=gnd_wires,
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_v, node_gnd]

        terminal_to_node = {("V1", 0): node_v, ("X1", 0): node_v}
        for i in range(1, terminal_count):
            terminal_to_node[("X1", i)] = node_gnd
        terminal_to_node[("GND1", 0)] = node_gnd
        terminal_to_node[("V1", 1)] = node_gnd

        return components, wires, nodes, terminal_to_node

    def test_subcircuit_netlist_contains_instance_line(self, tmp_path):
        from simulation.netlist_generator import NetlistGenerator

        components, wires, nodes, t2n = self._make_subcircuit_circuit("NETTEST_237", 3)
        gen = NetlistGenerator(components, wires, nodes, t2n, "DC Operating Point", {})
        netlist = gen.generate()

        # Should contain X-prefixed instance line
        assert "XX1" in netlist
        assert "NETTEST_237" in netlist

    def test_subcircuit_netlist_contains_definition(self, tmp_path):
        from simulation.netlist_generator import NetlistGenerator

        # Ensure subcircuit is in a library the generator can find
        lib = SubcircuitLibrary(tmp_path / "lib")
        defn = SubcircuitDefinition(
            name="DEFTEST_237",
            terminals=["a", "b"],
            spice_definition=".subckt DEFTEST_237 a b\nR1 a b 1k\n.ends",
        )
        lib.add(defn)
        register_subcircuit_component(defn)

        components, wires, nodes, t2n = self._make_subcircuit_circuit("DEFTEST_237", 2)

        # Monkey-patch the library lookup to use our temp library
        import models.subcircuit_library as sl_mod

        orig_default = sl_mod._DEFAULT_LIBRARY_DIR
        sl_mod._DEFAULT_LIBRARY_DIR = tmp_path / "lib"
        try:
            gen = NetlistGenerator(components, wires, nodes, t2n, "DC Operating Point", {})
            netlist = gen.generate()
        finally:
            sl_mod._DEFAULT_LIBRARY_DIR = orig_default

        assert ".subckt DEFTEST_237 a b" in netlist
        assert ".ends" in netlist
