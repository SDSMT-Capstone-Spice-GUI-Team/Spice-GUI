"""Tests for built-in voltage regulator subcircuit components (7805, LM317, LM7812)."""

import pytest
from models.builtin_subcircuits import BUILTIN_SUBCIRCUITS, register_builtin_subcircuits
from models.component import (
    COMPONENT_CATEGORIES,
    COMPONENT_TYPES,
    DEFAULT_VALUES,
    SPICE_SYMBOLS,
    TERMINAL_COUNTS,
    TERMINAL_GEOMETRY,
)
from models.subcircuit_library import SubcircuitLibrary, register_subcircuit_component
from simulation.netlist_generator import NetlistGenerator
from tests.conftest import make_component, make_wire


class TestBuiltinDefinitions:
    """Test that built-in subcircuit definitions are correct."""

    def test_three_builtins_defined(self):
        assert len(BUILTIN_SUBCIRCUITS) == 3

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_builtin_has_three_terminals(self, name):
        defn = next(d for d in BUILTIN_SUBCIRCUITS if d.name == name)
        assert defn.terminal_count == 3

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_builtin_is_marked_builtin(self, name):
        defn = next(d for d in BUILTIN_SUBCIRCUITS if d.name == name)
        assert defn.builtin is True

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_builtin_has_valid_spice_definition(self, name):
        defn = next(d for d in BUILTIN_SUBCIRCUITS if d.name == name)
        assert f".subckt {name}" in defn.spice_definition
        assert ".ends" in defn.spice_definition

    def test_7805_terminals(self):
        defn = next(d for d in BUILTIN_SUBCIRCUITS if d.name == "7805")
        assert defn.terminals == ["IN", "OUT", "GND"]

    def test_lm317_terminals(self):
        defn = next(d for d in BUILTIN_SUBCIRCUITS if d.name == "LM317")
        assert defn.terminals == ["IN", "OUT", "ADJ"]

    def test_lm7812_terminals(self):
        defn = next(d for d in BUILTIN_SUBCIRCUITS if d.name == "LM7812")
        assert defn.terminals == ["IN", "OUT", "GND"]


class TestRegistration:
    """Test that voltage regulators are registered in the component system."""

    @classmethod
    def setup_class(cls):
        register_builtin_subcircuits()

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_in_component_types(self, name):
        assert name in COMPONENT_TYPES

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_spice_symbol_is_X(self, name):
        assert SPICE_SYMBOLS[name] == "X"

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_terminal_count_is_3(self, name):
        assert TERMINAL_COUNTS[name] == 3

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_has_terminal_geometry(self, name):
        assert name in TERMINAL_GEOMETRY

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_default_value_is_name(self, name):
        assert DEFAULT_VALUES[name] == name

    def test_subcircuits_category_exists(self):
        assert "Subcircuits" in COMPONENT_CATEGORIES

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_in_subcircuits_category(self, name):
        assert name in COMPONENT_CATEGORIES["Subcircuits"]


class TestLibraryIntegration:
    """Test that builtins appear in SubcircuitLibrary."""

    def test_builtins_in_default_library(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        assert lib.get("7805") is not None
        assert lib.get("LM317") is not None
        assert lib.get("LM7812") is not None

    def test_builtins_cannot_be_deleted(self, tmp_path):
        lib = SubcircuitLibrary(tmp_path / "lib")
        assert lib.remove("7805") is False
        assert lib.get("7805") is not None


class TestNetlistGeneration:
    """Test that voltage regulators generate correct netlist lines."""

    @classmethod
    def setup_class(cls):
        register_builtin_subcircuits()

    def _build_regulator_circuit(self, name, tmp_path):
        """Build: Vin -- regulator -- GND, with output floating."""
        from models.node import NodeData

        v1 = make_component("Voltage Source", "V1", "12V", (0, 0))
        reg = make_component(name, "X1", name, (100, 0))
        gnd = make_component("Ground", "GND1", "0V", (200, 100))

        components = {"V1": v1, "X1": reg, "GND1": gnd}

        # Wire V1+ to regulator IN (terminal 0)
        wires = [
            make_wire("V1", 0, "X1", 0),
            # Wire regulator GND (terminal 1 for output, terminal 2 for GND)
            # Terminal order: IN=0, OUT=1, GND=2  (based on 3-terminal layout)
            make_wire("X1", 1, "GND1", 0),  # OUT to GND (load)
            make_wire("X1", 2, "GND1", 0),  # GND pin to GND
            make_wire("V1", 1, "GND1", 0),  # V1- to GND
        ]

        node_in = NodeData(
            terminals={("V1", 0), ("X1", 0)},
            wire_indices={0},
            auto_label="nodeIN",
        )
        node_gnd = NodeData(
            terminals={("X1", 1), ("X1", 2), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 2, 3},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_in, node_gnd]

        terminal_to_node = {
            ("V1", 0): node_in,
            ("X1", 0): node_in,
            ("X1", 1): node_gnd,
            ("X1", 2): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }

        return components, wires, nodes, terminal_to_node

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_netlist_has_x_prefix_instance(self, name, tmp_path):
        components, wires, nodes, t2n = self._build_regulator_circuit(name, tmp_path)
        gen = NetlistGenerator(components, wires, nodes, t2n, "DC Operating Point", {})
        netlist = gen.generate()
        # Should have XX1 ... <name>
        assert "XX1" in netlist
        assert name in netlist

    @pytest.mark.parametrize("name", ["7805", "LM317", "LM7812"])
    def test_netlist_has_subckt_definition(self, name, tmp_path):
        import models.subcircuit_library as sl_mod

        # Create a library with builtins (side effect: populates lib_dir)
        lib_dir = tmp_path / "lib"
        SubcircuitLibrary(lib_dir)

        components, wires, nodes, t2n = self._build_regulator_circuit(name, tmp_path)

        orig_default = sl_mod._DEFAULT_LIBRARY_DIR
        sl_mod._DEFAULT_LIBRARY_DIR = lib_dir
        try:
            gen = NetlistGenerator(components, wires, nodes, t2n, "DC Operating Point", {})
            netlist = gen.generate()
        finally:
            sl_mod._DEFAULT_LIBRARY_DIR = orig_default

        assert f".subckt {name}" in netlist
        assert ".ends" in netlist

    def test_component_data_spice_symbol(self):
        comp = make_component("7805", "X1", "7805", (0, 0))
        assert comp.get_spice_symbol() == "X"

    def test_component_data_terminal_count(self):
        comp = make_component("7805", "X1", "7805", (0, 0))
        assert comp.get_terminal_count() == 3
