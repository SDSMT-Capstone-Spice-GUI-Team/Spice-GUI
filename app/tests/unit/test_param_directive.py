"""Tests for .param directive support (issue #242).

Covers: parameter definition, reference extraction, validation,
netlist generation, and persistence through CircuitModel.
"""

import importlib
import sys

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel
from models.parameter import Parameter, ParameterManager


def _import_simulation_module(module_name, filename):
    """Import a simulation submodule without triggering simulation/__init__.py.

    The simulation package __init__.py imports NgspiceRunner which pulls
    in Qt/matplotlib, breaking headless test environments. We import
    individual modules directly via importlib to bypass the package init.
    """
    from pathlib import Path

    # tests/unit/test_xxx.py -> tests/unit/ -> tests/ -> app/
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


_ng_mod = _import_simulation_module("netlist_generator", "netlist_generator.py")
NetlistGenerator = _ng_mod.NetlistGenerator

_cv_mod = _import_simulation_module("circuit_validator", "circuit_validator.py")
validate_circuit = _cv_mod.validate_circuit

# ---------------------------------------------------------------------------
# ParameterManager model tests
# ---------------------------------------------------------------------------


class TestParameterModel:
    """Test the Parameter and ParameterManager data classes."""

    def test_create_parameter(self):
        p = Parameter(name="R_load", value="1k")
        assert p.name == "R_load"
        assert p.value == "1k"

    def test_parameter_to_dict(self):
        p = Parameter(name="Vdd", value="5")
        d = p.to_dict()
        assert d == {"name": "Vdd", "value": "5"}

    def test_parameter_from_dict(self):
        p = Parameter.from_dict({"name": "gain", "value": "{R_fb / R_in}"})
        assert p.name == "gain"
        assert p.value == "{R_fb / R_in}"

    def test_add_parameter(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_load", "1k")
        assert mgr.get_parameter("R_load") is not None
        assert mgr.get_parameter("R_load").value == "1k"

    def test_add_parameter_invalid_name(self):
        mgr = ParameterManager()
        with pytest.raises(ValueError, match="Invalid parameter name"):
            mgr.add_parameter("123bad", "1k")

    def test_add_parameter_invalid_name_spaces(self):
        mgr = ParameterManager()
        with pytest.raises(ValueError, match="Invalid parameter name"):
            mgr.add_parameter("bad name", "1k")

    def test_add_parameter_underscore_start(self):
        mgr = ParameterManager()
        mgr.add_parameter("_private", "42")
        assert mgr.get_parameter("_private").value == "42"

    def test_update_parameter(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_load", "1k")
        mgr.add_parameter("R_load", "2k")
        assert mgr.get_parameter("R_load").value == "2k"
        assert len(mgr.get_all_parameters()) == 1

    def test_remove_parameter(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_load", "1k")
        mgr.remove_parameter("R_load")
        assert mgr.get_parameter("R_load") is None

    def test_remove_nonexistent_parameter(self):
        mgr = ParameterManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.remove_parameter("nonexistent")

    def test_get_all_parameters(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_fb", "10k")
        mgr.add_parameter("R_in", "1k")
        params = mgr.get_all_parameters()
        assert len(params) == 2
        assert params[0].name == "R_fb"
        assert params[1].name == "R_in"

    def test_clear(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_fb", "10k")
        mgr.add_parameter("R_in", "1k")
        mgr.clear()
        assert len(mgr.get_all_parameters()) == 0


# ---------------------------------------------------------------------------
# Directive generation
# ---------------------------------------------------------------------------


class TestDirectiveGeneration:
    """Test .param directive generation for netlists."""

    def test_generate_directives_empty(self):
        mgr = ParameterManager()
        assert mgr.generate_directives() == []

    def test_generate_directives_simple(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_load", "1k")
        mgr.add_parameter("Vdd", "5")
        directives = mgr.generate_directives()
        assert directives == [".param R_load = 1k", ".param Vdd = 5"]

    def test_generate_directives_expression(self):
        mgr = ParameterManager()
        mgr.add_parameter("gain", "{R_fb / R_in}")
        directives = mgr.generate_directives()
        assert directives == [".param gain = {R_fb / R_in}"]


# ---------------------------------------------------------------------------
# Reference extraction and validation
# ---------------------------------------------------------------------------


class TestReferenceExtraction:
    """Test parameter reference detection and extraction."""

    def test_find_references_simple(self):
        mgr = ParameterManager()
        refs = mgr.find_references("{R_load}")
        assert refs == ["R_load"]

    def test_find_references_expression(self):
        mgr = ParameterManager()
        refs = mgr.find_references("{R_fb / R_in}")
        assert refs == ["R_fb / R_in"]

    def test_find_references_none(self):
        mgr = ParameterManager()
        refs = mgr.find_references("1k")
        assert refs == []

    def test_find_references_multiple(self):
        mgr = ParameterManager()
        refs = mgr.find_references("{Vdd} and {R_load}")
        assert refs == ["Vdd", "R_load"]

    def test_extract_param_names(self):
        mgr = ParameterManager()
        names = mgr.extract_param_names("{R_fb / R_in}")
        assert names == {"R_fb", "R_in"}

    def test_extract_param_names_simple(self):
        mgr = ParameterManager()
        names = mgr.extract_param_names("{R_load}")
        assert names == {"R_load"}

    def test_has_param_reference_true(self):
        mgr = ParameterManager()
        assert mgr.has_param_reference("{R_load}") is True

    def test_has_param_reference_false(self):
        mgr = ParameterManager()
        assert mgr.has_param_reference("1k") is False


class TestReferenceValidation:
    """Test validation of undefined parameter references."""

    def test_validate_all_defined(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_load", "1k")
        errors = mgr.validate_references({"R1": "{R_load}"})
        assert errors == []

    def test_validate_undefined_reference(self):
        mgr = ParameterManager()
        errors = mgr.validate_references({"R1": "{R_load}"})
        assert len(errors) == 1
        assert "R_load" in errors[0]
        assert "R1" in errors[0]

    def test_validate_partial_definition(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_fb", "10k")
        errors = mgr.validate_references({"R1": "{R_fb / R_in}"})
        assert len(errors) == 1
        assert "R_in" in errors[0]

    def test_validate_no_references(self):
        mgr = ParameterManager()
        errors = mgr.validate_references({"R1": "1k", "V1": "5V"})
        assert errors == []

    def test_validate_multiple_components(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_load", "1k")
        errors = mgr.validate_references(
            {
                "R1": "{R_load}",
                "R2": "{R_unknown}",
            }
        )
        assert len(errors) == 1
        assert "R_unknown" in errors[0]


# ---------------------------------------------------------------------------
# Serialization / persistence
# ---------------------------------------------------------------------------


class TestParameterSerialization:
    """Test ParameterManager serialization and deserialization."""

    def test_to_dict(self):
        mgr = ParameterManager()
        mgr.add_parameter("R_fb", "10k")
        mgr.add_parameter("R_in", "1k")
        d = mgr.to_dict()
        assert d == [
            {"name": "R_fb", "value": "10k"},
            {"name": "R_in", "value": "1k"},
        ]

    def test_from_dict(self):
        data = [
            {"name": "R_fb", "value": "10k"},
            {"name": "R_in", "value": "1k"},
        ]
        mgr = ParameterManager.from_dict(data)
        assert len(mgr.get_all_parameters()) == 2
        assert mgr.get_parameter("R_fb").value == "10k"

    def test_to_dict_empty(self):
        mgr = ParameterManager()
        assert mgr.to_dict() == []

    def test_from_dict_empty(self):
        mgr = ParameterManager.from_dict([])
        assert len(mgr.get_all_parameters()) == 0


# ---------------------------------------------------------------------------
# CircuitModel integration
# ---------------------------------------------------------------------------


class TestCircuitModelParameterIntegration:
    """Test parameters persist through CircuitModel serialization."""

    def test_circuit_model_has_param_manager(self):
        model = CircuitModel()
        assert hasattr(model, "param_manager")
        assert isinstance(model.param_manager, ParameterManager)

    def test_circuit_model_to_dict_with_params(self):
        model = CircuitModel()
        model.param_manager.add_parameter("R_load", "1k")
        d = model.to_dict()
        assert "parameters" in d
        assert d["parameters"] == [{"name": "R_load", "value": "1k"}]

    def test_circuit_model_to_dict_without_params(self):
        model = CircuitModel()
        d = model.to_dict()
        assert "parameters" not in d

    def test_circuit_model_from_dict_with_params(self):
        data = {
            "components": [],
            "wires": [],
            "counters": {},
            "parameters": [
                {"name": "R_fb", "value": "10k"},
                {"name": "R_in", "value": "1k"},
            ],
        }
        model = CircuitModel.from_dict(data)
        assert len(model.param_manager.get_all_parameters()) == 2
        assert model.param_manager.get_parameter("R_fb").value == "10k"

    def test_circuit_model_from_dict_without_params(self):
        data = {"components": [], "wires": [], "counters": {}}
        model = CircuitModel.from_dict(data)
        assert len(model.param_manager.get_all_parameters()) == 0

    def test_circuit_model_clear_resets_params(self):
        model = CircuitModel()
        model.param_manager.add_parameter("R_load", "1k")
        model.clear()
        assert len(model.param_manager.get_all_parameters()) == 0

    def test_roundtrip_serialization(self):
        model = CircuitModel()
        model.param_manager.add_parameter("R_fb", "10k")
        model.param_manager.add_parameter("R_in", "1k")
        model.param_manager.add_parameter("gain", "{R_fb / R_in}")

        d = model.to_dict()
        restored = CircuitModel.from_dict(d)

        assert len(restored.param_manager.get_all_parameters()) == 3
        assert restored.param_manager.get_parameter("gain").value == "{R_fb / R_in}"


# ---------------------------------------------------------------------------
# Netlist generation
# ---------------------------------------------------------------------------


class TestNetlistParameterGeneration:
    """Test .param directives appear correctly in generated netlists.

    Uses NetlistGenerator directly (no Qt dependency) for pure model tests.
    """

    def _make_simple_circuit(self):
        """Create a simple V1-R1-GND circuit and return generator inputs."""
        model = CircuitModel()
        ctrl = CircuitController(model)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))

        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        model.rebuild_nodes()
        return model

    def _generate(self, model):
        """Build a netlist via NetlistGenerator (no Qt imports)."""
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
            parameters=model.param_manager.generate_directives(),
        )
        return gen.generate()

    def test_netlist_contains_param_directives(self):
        model = self._make_simple_circuit()
        model.param_manager.add_parameter("R_load", "1k")
        model.param_manager.add_parameter("Vdd", "5")

        netlist = self._generate(model)
        assert ".param R_load = 1k" in netlist
        assert ".param Vdd = 5" in netlist

    def test_netlist_param_section_header(self):
        model = self._make_simple_circuit()
        model.param_manager.add_parameter("R_load", "1k")

        netlist = self._generate(model)
        assert "* Parameter Definitions" in netlist

    def test_netlist_no_param_section_when_empty(self):
        model = self._make_simple_circuit()
        netlist = self._generate(model)
        assert "* Parameter Definitions" not in netlist
        assert ".param" not in netlist

    def test_netlist_param_with_expression(self):
        model = self._make_simple_circuit()
        model.param_manager.add_parameter("gain", "{R_fb / R_in}")

        netlist = self._generate(model)
        assert ".param gain = {R_fb / R_in}" in netlist

    def test_component_value_with_param_reference(self):
        """Component values using {param} syntax appear in netlist as-is."""
        model = self._make_simple_circuit()

        # Find the resistor and set its value to a parameter reference
        r1 = next(c for c in model.components.values() if c.component_type == "Resistor")
        r1.value = "{R_load}"
        model.param_manager.add_parameter("R_load", "1k")

        netlist = self._generate(model)
        assert "{R_load}" in netlist
        assert ".param R_load = 1k" in netlist


# ---------------------------------------------------------------------------
# Validation integration
# ---------------------------------------------------------------------------


class TestParameterValidationIntegration:
    """Test parameter validation through the circuit validator."""

    def test_validation_passes_with_defined_params(self):
        model = CircuitModel()
        ctrl = CircuitController(model)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))

        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        r1.value = "{R_load}"
        model.param_manager.add_parameter("R_load", "1k")

        is_valid, errors, warnings = validate_circuit(
            model.components,
            model.wires,
            model.analysis_type,
            param_manager=model.param_manager,
        )
        assert is_valid is True

    def test_validation_fails_with_undefined_params(self):
        model = CircuitModel()
        ctrl = CircuitController(model)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))

        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        r1.value = "{R_undefined}"

        is_valid, errors, warnings = validate_circuit(
            model.components,
            model.wires,
            model.analysis_type,
            param_manager=model.param_manager,
        )
        assert is_valid is False
        assert any("R_undefined" in e for e in errors)
