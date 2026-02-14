"""
Tests for simulation/circuit_validator.py — pre-simulation validation.
"""

import pytest
from simulation.circuit_validator import validate_circuit
from tests.conftest import make_component, make_wire


class TestValidCircuit:
    def test_simple_valid_circuit(self, simple_resistor_circuit):
        components, wires, _, _ = simple_resistor_circuit
        is_valid, errors, warnings = validate_circuit(
            components, wires, "DC Operating Point"
        )
        assert is_valid
        assert len(errors) == 0

    def test_resistor_divider_valid(self, resistor_divider_circuit):
        components, wires, _, _ = resistor_divider_circuit
        is_valid, errors, warnings = validate_circuit(
            components, wires, "DC Operating Point"
        )
        assert is_valid


class TestNoComponents:
    def test_only_ground(self):
        components = {
            "GND1": make_component("Ground", "GND1", "0V"),
        }
        is_valid, errors, warnings = validate_circuit(
            components, [], "DC Operating Point"
        )
        assert not is_valid
        assert any("no components" in e.lower() for e in errors)

    def test_empty_circuit(self):
        is_valid, errors, warnings = validate_circuit({}, [], "DC Operating Point")
        assert not is_valid


class TestNoGround:
    def test_missing_ground(self):
        components = {
            "R1": make_component("Resistor", "R1", "1k"),
            "V1": make_component("Voltage Source", "V1", "5V"),
        }
        wires = [make_wire("V1", 0, "R1", 0)]
        is_valid, errors, warnings = validate_circuit(
            components, wires, "DC Operating Point"
        )
        assert not is_valid
        assert any("ground" in e.lower() for e in errors)


class TestUnconnectedTerminals:
    def test_fully_unconnected_component(self):
        components = {
            "R1": make_component("Resistor", "R1", "1k"),
            "V1": make_component("Voltage Source", "V1", "5V"),
            "GND1": make_component("Ground", "GND1", "0V"),
        }
        # Only V1 and GND connected; R1 has no wires
        wires = [make_wire("V1", 0, "GND1", 0)]
        is_valid, errors, warnings = validate_circuit(
            components, wires, "DC Operating Point"
        )
        assert not is_valid
        assert any("R1" in e and "no connections" in e.lower() for e in errors)

    def test_partially_unconnected_is_warning(self):
        components = {
            "R1": make_component("Resistor", "R1", "1k"),
            "V1": make_component("Voltage Source", "V1", "5V"),
            "GND1": make_component("Ground", "GND1", "0V"),
        }
        # R1 has terminal 0 connected but terminal 1 not
        wires = [
            make_wire("V1", 0, "R1", 0),
            make_wire("V1", 1, "GND1", 0),
        ]
        is_valid, errors, warnings = validate_circuit(
            components, wires, "DC Operating Point"
        )
        assert any("R1" in w and "unconnected" in w.lower() for w in warnings)


class TestAnalysisSpecific:
    def test_dc_sweep_no_voltage_source(self):
        components = {
            "R1": make_component("Resistor", "R1", "1k"),
            "I1": make_component("Current Source", "I1", "1A"),
            "GND1": make_component("Ground", "GND1", "0V"),
        }
        wires = [
            make_wire("I1", 0, "R1", 0),
            make_wire("R1", 1, "GND1", 0),
            make_wire("I1", 1, "GND1", 0),
        ]
        is_valid, errors, warnings = validate_circuit(components, wires, "DC Sweep")
        assert not is_valid
        assert any("dc sweep" in e.lower() for e in errors)


class TestNoSources:
    def test_no_sources_warning(self):
        components = {
            "R1": make_component("Resistor", "R1", "1k"),
            "GND1": make_component("Ground", "GND1", "0V"),
        }
        wires = [make_wire("R1", 0, "GND1", 0)]
        is_valid, errors, warnings = validate_circuit(
            components, wires, "DC Operating Point"
        )
        assert any("no voltage or current" in w.lower() for w in warnings)
