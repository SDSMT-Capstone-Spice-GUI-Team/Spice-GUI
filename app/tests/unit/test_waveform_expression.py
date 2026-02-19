"""
Tests for waveform math expression support (issue #236).

Covers:
- WaveformExpression model (create, serialize, reference extraction)
- WaveformExpressionManager (add, remove, validate, let directives)
- Expression presets
- CircuitModel integration (persistence)
- NetlistGenerator integration (let directives in .control block)
"""

import importlib
import sys

import pytest
from models.circuit import CircuitModel
from models.waveform_expression import (
    EXPRESSION_PRESETS,
    WaveformExpression,
    WaveformExpressionManager,
    get_preset,
    get_preset_names,
)
from tests.conftest import make_component, make_wire


# ---------------------------------------------------------------------------
# Import simulation submodules without triggering Qt via simulation/__init__.py
# ---------------------------------------------------------------------------
def _import_simulation_module(module_name, filename):
    from pathlib import Path

    app_dir = Path(__file__).resolve().parent.parent.parent
    module_path = app_dir / "simulation" / filename
    fq_name = f"simulation.{module_name}"
    if fq_name in sys.modules:
        return sys.modules[fq_name]
    spec = importlib.util.spec_from_file_location(fq_name, str(module_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fq_name] = mod
    spec.loader.exec_module(mod)
    return mod


netlist_mod = _import_simulation_module("netlist_generator", "netlist_generator.py")
NetlistGenerator = netlist_mod.NetlistGenerator


# ===================================================================
# WaveformExpression dataclass tests
# ===================================================================
class TestWaveformExpression:
    def test_create_basic(self):
        expr = WaveformExpression(name="gain", expression="v(out)/v(in)")
        assert expr.name == "gain"
        assert expr.expression == "v(out)/v(in)"
        assert expr.description == ""

    def test_create_with_description(self):
        expr = WaveformExpression(
            name="gain_db",
            expression="db(v(out)/v(in))",
            description="Voltage gain in dB",
        )
        assert expr.description == "Voltage gain in dB"

    def test_to_dict_minimal(self):
        expr = WaveformExpression(name="diff", expression="v(a) - v(b)")
        d = expr.to_dict()
        assert d == {"name": "diff", "expression": "v(a) - v(b)"}
        assert "description" not in d

    def test_to_dict_with_description(self):
        expr = WaveformExpression(name="diff", expression="v(a) - v(b)", description="Difference")
        d = expr.to_dict()
        assert d["description"] == "Difference"

    def test_from_dict(self):
        d = {"name": "gain", "expression": "v(out)/v(in)", "description": "Linear gain"}
        expr = WaveformExpression.from_dict(d)
        assert expr.name == "gain"
        assert expr.expression == "v(out)/v(in)"
        assert expr.description == "Linear gain"

    def test_from_dict_no_description(self):
        d = {"name": "x", "expression": "v(a)"}
        expr = WaveformExpression.from_dict(d)
        assert expr.description == ""

    def test_roundtrip(self):
        original = WaveformExpression(name="power", expression="v(out) * i(R1)", description="Power")
        restored = WaveformExpression.from_dict(original.to_dict())
        assert restored.name == original.name
        assert restored.expression == original.expression
        assert restored.description == original.description


# ===================================================================
# Reference extraction tests
# ===================================================================
class TestReferenceExtraction:
    def test_node_references_single(self):
        expr = WaveformExpression(name="x", expression="v(out)")
        assert expr.get_node_references() == {"out"}

    def test_node_references_multiple(self):
        expr = WaveformExpression(name="x", expression="v(out) - v(in)")
        assert expr.get_node_references() == {"out", "in"}

    def test_node_references_case_insensitive(self):
        expr = WaveformExpression(name="x", expression="V(OUT) + v(in)")
        assert expr.get_node_references() == {"OUT", "in"}

    def test_current_references(self):
        expr = WaveformExpression(name="x", expression="i(R1)")
        assert expr.get_current_references() == {"R1"}

    def test_current_references_case(self):
        expr = WaveformExpression(name="x", expression="I(V1) + i(R2)")
        assert expr.get_current_references() == {"V1", "R2"}

    def test_mixed_references(self):
        expr = WaveformExpression(name="x", expression="v(out) * i(R1)")
        assert expr.get_node_references() == {"out"}
        assert expr.get_current_references() == {"R1"}
        assert expr.get_all_references() == {"out", "R1"}

    def test_no_references(self):
        expr = WaveformExpression(name="x", expression="1 + 2")
        assert expr.get_node_references() == set()
        assert expr.get_current_references() == set()

    def test_nested_function(self):
        expr = WaveformExpression(name="x", expression="db(v(out)/v(in))")
        assert expr.get_node_references() == {"out", "in"}


# ===================================================================
# WaveformExpressionManager tests
# ===================================================================
class TestExpressionManager:
    def test_add_expression(self):
        mgr = WaveformExpressionManager()
        expr = mgr.add_expression("gain", "v(out)/v(in)")
        assert expr.name == "gain"
        assert len(mgr.get_all()) == 1

    def test_add_expression_with_description(self):
        mgr = WaveformExpressionManager()
        expr = mgr.add_expression("gain", "v(out)/v(in)", "Linear voltage gain")
        assert expr.description == "Linear voltage gain"

    def test_add_duplicate_name_raises(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        with pytest.raises(ValueError, match="already exists"):
            mgr.add_expression("gain", "v(a)/v(b)")

    def test_add_empty_name_raises(self):
        mgr = WaveformExpressionManager()
        with pytest.raises(ValueError, match="cannot be empty"):
            mgr.add_expression("", "v(out)")

    def test_add_invalid_name_raises(self):
        mgr = WaveformExpressionManager()
        with pytest.raises(ValueError, match="must be a valid identifier"):
            mgr.add_expression("my-expr", "v(out)")

    def test_add_name_with_spaces_raises(self):
        mgr = WaveformExpressionManager()
        with pytest.raises(ValueError, match="must be a valid identifier"):
            mgr.add_expression("my expr", "v(out)")

    def test_valid_identifier_names(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain_db", "db(v(out)/v(in))")
        mgr.add_expression("_private", "v(a)")
        mgr.add_expression("V2", "v(b)")
        assert len(mgr.get_all()) == 3

    def test_remove_expression(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        removed = mgr.remove_expression("gain")
        assert removed.name == "gain"
        assert len(mgr.get_all()) == 0

    def test_remove_nonexistent_raises(self):
        mgr = WaveformExpressionManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.remove_expression("nope")

    def test_get_expression(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        expr = mgr.get_expression("gain")
        assert expr is not None
        assert expr.name == "gain"

    def test_get_expression_not_found(self):
        mgr = WaveformExpressionManager()
        assert mgr.get_expression("nope") is None

    def test_get_all_preserves_order(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("a", "v(x)")
        mgr.add_expression("b", "v(y)")
        mgr.add_expression("c", "v(z)")
        names = [e.name for e in mgr.get_all()]
        assert names == ["a", "b", "c"]

    def test_clear(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("a", "v(x)")
        mgr.add_expression("b", "v(y)")
        mgr.clear()
        assert len(mgr.get_all()) == 0


# ===================================================================
# Let directive generation
# ===================================================================
class TestLetDirectiveGeneration:
    def test_single_directive(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        directives = mgr.generate_let_directives()
        assert directives == ["let gain = v(out)/v(in)"]

    def test_multiple_directives(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        mgr.add_expression("gain_db", "db(v(out)/v(in))")
        directives = mgr.generate_let_directives()
        assert len(directives) == 2
        assert "let gain = v(out)/v(in)" in directives
        assert "let gain_db = db(v(out)/v(in))" in directives

    def test_empty_manager(self):
        mgr = WaveformExpressionManager()
        assert mgr.generate_let_directives() == []

    def test_print_variables(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        mgr.add_expression("power", "v(out) * i(R1)")
        assert mgr.get_print_variables() == ["gain", "power"]


# ===================================================================
# Reference validation
# ===================================================================
class TestReferenceValidation:
    def test_valid_references(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        errors = mgr.validate_references({"out", "in"}, set())
        assert errors == []

    def test_invalid_node_reference(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)")
        errors = mgr.validate_references({"out"}, set())
        assert len(errors) == 1
        assert "unknown node 'in'" in errors[0]

    def test_invalid_current_reference(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("power", "v(out) * i(R1)")
        errors = mgr.validate_references({"out"}, set())
        assert len(errors) == 1
        assert "unknown component 'R1'" in errors[0]

    def test_multiple_errors(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("bad", "v(missing1) + i(missing2)")
        errors = mgr.validate_references(set(), set())
        assert len(errors) == 2

    def test_valid_with_components(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("power", "v(out) * i(R1)")
        errors = mgr.validate_references({"out"}, {"R1"})
        assert errors == []


# ===================================================================
# Serialization
# ===================================================================
class TestExpressionSerialization:
    def test_manager_to_dict(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)", "Gain")
        data = mgr.to_dict()
        assert len(data) == 1
        assert data[0]["name"] == "gain"
        assert data[0]["expression"] == "v(out)/v(in)"

    def test_manager_from_dict(self):
        data = [
            {"name": "gain", "expression": "v(out)/v(in)"},
            {"name": "power", "expression": "v(a)*i(R1)", "description": "P"},
        ]
        mgr = WaveformExpressionManager.from_dict(data)
        assert len(mgr.get_all()) == 2
        assert mgr.get_expression("gain") is not None
        assert mgr.get_expression("power").description == "P"

    def test_manager_roundtrip(self):
        mgr = WaveformExpressionManager()
        mgr.add_expression("gain", "v(out)/v(in)", "Linear gain")
        mgr.add_expression("power", "v(out)*i(R1)")
        data = mgr.to_dict()
        restored = WaveformExpressionManager.from_dict(data)
        assert len(restored.get_all()) == 2
        assert restored.get_expression("gain").description == "Linear gain"
        assert restored.get_expression("power").expression == "v(out)*i(R1)"

    def test_empty_manager_to_dict(self):
        mgr = WaveformExpressionManager()
        assert mgr.to_dict() == []


# ===================================================================
# Preset expressions
# ===================================================================
class TestExpressionPresets:
    def test_presets_exist(self):
        assert len(EXPRESSION_PRESETS) >= 4

    def test_preset_names(self):
        names = get_preset_names()
        assert "differential" in names
        assert "gain" in names
        assert "gain_db" in names
        assert "power" in names

    def test_get_preset_returns_copy(self):
        preset = get_preset("gain")
        assert preset is not None
        assert preset.name == "gain"
        # Should be a copy, not the original
        original = None
        for p in EXPRESSION_PRESETS:
            if p.name == "gain":
                original = p
                break
        assert preset is not original

    def test_get_preset_not_found(self):
        assert get_preset("nonexistent") is None

    def test_preset_templates_have_placeholders(self):
        gain = get_preset("gain")
        assert "{output}" in gain.expression
        assert "{input}" in gain.expression

    def test_preset_differential(self):
        diff = get_preset("differential")
        assert "{node_p}" in diff.expression
        assert "{node_n}" in diff.expression


# ===================================================================
# CircuitModel integration
# ===================================================================
class TestCircuitModelExpressionIntegration:
    def test_circuit_model_has_expression_manager(self):
        model = CircuitModel()
        assert isinstance(model.expression_manager, WaveformExpressionManager)

    def test_circuit_model_clear_clears_expressions(self):
        model = CircuitModel()
        model.expression_manager.add_expression("gain", "v(out)/v(in)")
        model.clear()
        assert len(model.expression_manager.get_all()) == 0

    def test_circuit_model_to_dict_includes_expressions(self):
        model = CircuitModel()
        model.expression_manager.add_expression("gain", "v(out)/v(in)")
        data = model.to_dict()
        assert "expressions" in data
        assert len(data["expressions"]) == 1

    def test_circuit_model_to_dict_no_expressions(self):
        model = CircuitModel()
        data = model.to_dict()
        assert "expressions" not in data

    def test_circuit_model_from_dict_with_expressions(self):
        data = {
            "components": [],
            "wires": [],
            "counters": {},
            "expressions": [
                {"name": "gain", "expression": "v(out)/v(in)"},
            ],
        }
        model = CircuitModel.from_dict(data)
        assert len(model.expression_manager.get_all()) == 1
        assert model.expression_manager.get_expression("gain") is not None

    def test_circuit_model_from_dict_without_expressions(self):
        data = {"components": [], "wires": [], "counters": {}}
        model = CircuitModel.from_dict(data)
        assert len(model.expression_manager.get_all()) == 0

    def test_circuit_model_roundtrip_with_expressions(self):
        model = CircuitModel()
        model.expression_manager.add_expression("gain_db", "db(v(out)/v(in))", "Gain in dB")
        model.expression_manager.add_expression("diff", "v(a) - v(b)")
        data = model.to_dict()
        restored = CircuitModel.from_dict(data)
        assert len(restored.expression_manager.get_all()) == 2
        assert restored.expression_manager.get_expression("gain_db").description == "Gain in dB"


# ===================================================================
# NetlistGenerator integration
# ===================================================================
class TestNetlistExpressionIntegration:
    """Test that expressions produce let directives and print variables in netlists."""

    def _build_simple_circuit(self):
        """Build a minimal V1-R1-GND circuit for netlist generation."""
        from models.node import NodeData

        components = {
            "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
            "R1": make_component("Resistor", "R1", "1k", (100, 0)),
            "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        node_a = NodeData(
            terminals={("V1", 0), ("R1", 0)},
            wire_indices={0},
            auto_label="nodeA",
        )
        node_gnd = NodeData(
            terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
            wire_indices={1, 2},
            is_ground=True,
            auto_label="0",
        )
        nodes = [node_a, node_gnd]
        terminal_to_node = {
            ("V1", 0): node_a,
            ("R1", 0): node_a,
            ("R1", 1): node_gnd,
            ("GND1", 0): node_gnd,
            ("V1", 1): node_gnd,
        }
        return components, wires, nodes, terminal_to_node

    def test_no_expressions_no_let_directives(self):
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
        )
        netlist = gen.generate()
        assert "User-defined waveform expressions" not in netlist

    def test_expressions_generate_let_directives(self):
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
            expressions=["let gain = v(nodeA)/v(nodeA)"],
        )
        netlist = gen.generate()
        assert "let gain = v(nodeA)/v(nodeA)" in netlist
        assert "User-defined waveform expressions" in netlist

    def test_expressions_added_to_print(self):
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
            expressions=["let mygain = v(nodeA)"],
        )
        netlist = gen.generate()
        # The print command should include the expression variable
        lines = netlist.split("\n")
        print_lines = [l for l in lines if l.strip().startswith("print ")]
        assert any("mygain" in l for l in print_lines), f"Expected 'mygain' in print commands: {print_lines}"

    def test_expressions_added_to_wrdata(self):
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
            expressions=["let mygain = v(nodeA)"],
        )
        netlist = gen.generate()
        lines = netlist.split("\n")
        wrdata_lines = [l for l in lines if l.strip().startswith("wrdata ")]
        assert any("mygain" in l for l in wrdata_lines), f"Expected 'mygain' in wrdata commands: {wrdata_lines}"

    def test_multiple_expressions_in_netlist(self):
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
            expressions=[
                "let gain = v(nodeA)",
                "let gain_db = db(v(nodeA))",
            ],
        )
        netlist = gen.generate()
        assert "let gain = v(nodeA)" in netlist
        assert "let gain_db = db(v(nodeA))" in netlist
        # Both should appear in print
        lines = netlist.split("\n")
        print_lines = [l for l in lines if l.strip().startswith("print ")]
        assert any("gain" in l and "gain_db" in l for l in print_lines)

    def test_expression_let_prefix_not_duplicated(self):
        """If the expression already starts with 'let', don't add another."""
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
            expressions=["let gain = v(nodeA)"],
        )
        netlist = gen.generate()
        # Should have exactly one "let gain" not "let let gain"
        assert "let let" not in netlist

    def test_expression_without_let_prefix(self):
        """Expressions without 'let' prefix should get it added."""
        comps, wires, nodes, t2n = self._build_simple_circuit()
        gen = NetlistGenerator(
            components=comps,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="DC Operating Point",
            analysis_params={},
            expressions=["gain = v(nodeA)"],
        )
        netlist = gen.generate()
        assert "let gain = v(nodeA)" in netlist


# ===================================================================
# Controller integration
# ===================================================================
class TestControllerExpressionIntegration:
    """Test that SimulationController passes expressions to NetlistGenerator.

    Since SimulationController.generate_netlist() uses ``from simulation import
    NetlistGenerator`` which triggers the Qt import chain in headless environments,
    we pre-load the simulation.netlist_generator module via importlib and patch
    ``simulation.__init__`` to make the import succeed.
    """

    def test_controller_passes_expressions(self):
        """Verify expressions from circuit model appear in generated netlist."""
        # Ensure simulation.netlist_generator is already in sys.modules so that
        # ``from simulation import NetlistGenerator`` can resolve without
        # importing the full simulation package (which triggers Qt).
        _import_simulation_module("netlist_generator", "netlist_generator.py")

        # Create a minimal simulation package stub if needed
        if "simulation" not in sys.modules:
            import types

            sim_pkg = types.ModuleType("simulation")
            sim_pkg.__path__ = []
            sys.modules["simulation"] = sim_pkg

        sim_pkg = sys.modules["simulation"]
        if not hasattr(sim_pkg, "NetlistGenerator"):
            sim_pkg.NetlistGenerator = NetlistGenerator

        from controllers.simulation_controller import SimulationController

        model = CircuitModel()

        # Build a minimal circuit
        model.add_component(make_component("Voltage Source", "V1", "5V", (0, 0)))
        model.add_component(make_component("Resistor", "R1", "1k", (100, 0)))
        model.add_component(make_component("Ground", "GND1", "0V", (100, 100)))
        model.add_wire(make_wire("V1", 0, "R1", 0))
        model.add_wire(make_wire("R1", 1, "GND1", 0))
        model.add_wire(make_wire("V1", 1, "GND1", 0))

        # Add an expression
        model.expression_manager.add_expression("test_expr", "v(nodeA) * 2")

        ctrl = SimulationController(model=model)
        netlist = ctrl.generate_netlist()

        assert "let test_expr = v(nodeA) * 2" in netlist
        # Variable should also appear in print/wrdata
        assert "test_expr" in netlist
