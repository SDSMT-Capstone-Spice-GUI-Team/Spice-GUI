"""Tests for circuit_semantic_validator.validate_circuit."""

from simulation.circuit_semantic_validator import validate_circuit
from tests.conftest import make_component, make_wire


def _comp(ctype, cid, value="1"):
    return make_component(ctype, cid, value)


class TestValidateCircuitEmpty:
    def test_empty_components_returns_error(self):
        valid, errors, warnings = validate_circuit({}, [], "DC Operating Point")
        assert not valid
        assert any("no components" in e.lower() for e in errors)

    def test_only_ground_returns_error(self):
        components = {"GND1": _comp("Ground", "GND1")}
        valid, errors, _ = validate_circuit(components, [], "DC Operating Point")
        assert not valid
        assert any("no components" in e.lower() for e in errors)


class TestValidateCircuitNoGround:
    def test_missing_ground_is_an_error(self):
        components = {
            "R1": _comp("Resistor", "R1", "1k"),
            "V1": _comp("Voltage Source", "V1", "5"),
        }
        valid, errors, _ = validate_circuit(components, [], "DC Operating Point")
        assert not valid
        assert any("ground" in e.lower() for e in errors)


class TestValidateCircuitUnconnected:
    def test_fully_unconnected_component_is_error(self):
        components = {
            "R1": _comp("Resistor", "R1", "1k"),
            "GND1": _comp("Ground", "GND1"),
        }
        valid, errors, _ = validate_circuit(components, [], "DC Operating Point")
        assert not valid
        assert any("R1" in e for e in errors)

    def test_partially_unconnected_component_is_warning(self):
        # R1 has 2 terminals (0 and 1); connect only terminal 0
        components = {
            "R1": _comp("Resistor", "R1", "1k"),
            "GND1": _comp("Ground", "GND1"),
        }
        # Wire from R1 terminal 0 to GND1 terminal 0 (Ground has 1 terminal)
        wires = [make_wire("R1", 0, "GND1", 0)]
        _, errors, warnings = validate_circuit(components, wires, "DC Operating Point")
        assert any("R1" in w for w in warnings)


class TestValidateCircuitDCSweep:
    def test_dc_sweep_without_voltage_source_is_error(self):
        components = {
            "R1": _comp("Resistor", "R1", "1k"),
            "GND1": _comp("Ground", "GND1"),
        }
        wires = [make_wire("R1", 0, "GND1", 0), make_wire("R1", 1, "GND1", 0)]
        valid, errors, _ = validate_circuit(components, wires, "DC Sweep")
        assert not valid
        assert any("voltage source" in e.lower() for e in errors)

    def test_dc_sweep_with_voltage_source_passes_that_check(self):
        components = {
            "V1": _comp("Voltage Source", "V1", "5"),
            "R1": _comp("Resistor", "R1", "1k"),
            "GND1": _comp("Ground", "GND1"),
        }
        # Fully connect
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        _, errors, _ = validate_circuit(components, wires, "DC Sweep")
        assert not any("voltage source" in e.lower() for e in errors)


class TestValidateCircuitNoSources:
    def test_no_sources_generates_warning(self):
        components = {
            "R1": _comp("Resistor", "R1", "1k"),
            "GND1": _comp("Ground", "GND1"),
        }
        wires = [make_wire("R1", 0, "GND1", 0), make_wire("R1", 1, "GND1", 0)]
        _, _, warnings = validate_circuit(components, wires, "DC Operating Point")
        assert any("source" in w.lower() for w in warnings)


class TestValidateCircuitValid:
    def test_valid_resistor_circuit_no_errors(self):
        components = {
            "V1": _comp("Voltage Source", "V1", "5"),
            "R1": _comp("Resistor", "R1", "1k"),
            "GND1": _comp("Ground", "GND1"),
        }
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        valid, errors, _ = validate_circuit(components, wires, "DC Operating Point")
        assert valid
        assert errors == []

    def test_returns_tuple_of_three(self):
        result = validate_circuit({}, [], "Transient")
        assert len(result) == 3
        assert isinstance(result[1], list)
        assert isinstance(result[2], list)
