"""Tests for models.circuit_schema_validator.validate_circuit_data."""

import pytest
from models.circuit_schema_validator import validate_circuit_data


def _valid_circuit():
    return {
        "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}],
        "wires": [],
    }


class TestValidateCircuitDataStructure:
    def test_valid_circuit_passes(self):
        validate_circuit_data(_valid_circuit())  # no exception

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="valid circuit object"):
            validate_circuit_data([])

    def test_string_raises(self):
        with pytest.raises(ValueError):
            validate_circuit_data("not a dict")

    def test_missing_components_key_raises(self):
        with pytest.raises(ValueError, match="components"):
            validate_circuit_data({"wires": []})

    def test_missing_wires_key_raises(self):
        with pytest.raises(ValueError, match="wires"):
            validate_circuit_data({"components": []})

    def test_components_not_list_raises(self):
        with pytest.raises(ValueError, match="components"):
            validate_circuit_data({"components": {}, "wires": []})

    def test_wires_not_list_raises(self):
        with pytest.raises(ValueError, match="wires"):
            validate_circuit_data({"components": [], "wires": {}})


class TestValidateCircuitDataComponents:
    def test_component_missing_id_raises(self):
        data = {"components": [{"type": "R", "value": "1k", "pos": {"x": 0, "y": 0}}], "wires": []}
        with pytest.raises(ValueError, match="'id'"):
            validate_circuit_data(data)

    def test_component_missing_type_raises(self):
        data = {"components": [{"id": "R1", "value": "1k", "pos": {"x": 0, "y": 0}}], "wires": []}
        with pytest.raises(ValueError, match="'type'"):
            validate_circuit_data(data)

    def test_component_missing_value_raises(self):
        data = {"components": [{"id": "R1", "type": "Resistor", "pos": {"x": 0, "y": 0}}], "wires": []}
        with pytest.raises(ValueError, match="'value'"):
            validate_circuit_data(data)

    def test_component_missing_pos_raises(self):
        data = {"components": [{"id": "R1", "type": "Resistor", "value": "1k"}], "wires": []}
        with pytest.raises(ValueError, match="'pos'"):
            validate_circuit_data(data)

    def test_component_pos_missing_x_raises(self):
        data = {"components": [{"id": "R1", "type": "R", "value": "1k", "pos": {"y": 0}}], "wires": []}
        with pytest.raises(ValueError, match="invalid position"):
            validate_circuit_data(data)

    def test_component_pos_missing_y_raises(self):
        data = {"components": [{"id": "R1", "type": "R", "value": "1k", "pos": {"x": 0}}], "wires": []}
        with pytest.raises(ValueError, match="invalid position"):
            validate_circuit_data(data)

    def test_component_pos_non_numeric_x_raises(self):
        data = {"components": [{"id": "R1", "type": "R", "value": "1k", "pos": {"x": "a", "y": 0}}], "wires": []}
        with pytest.raises(ValueError, match="numeric"):
            validate_circuit_data(data)

    def test_component_pos_non_numeric_y_raises(self):
        data = {"components": [{"id": "R1", "type": "R", "value": "1k", "pos": {"x": 0, "y": "b"}}], "wires": []}
        with pytest.raises(ValueError, match="numeric"):
            validate_circuit_data(data)

    def test_component_pos_accepts_float(self):
        data = {"components": [{"id": "R1", "type": "R", "value": "1k", "pos": {"x": 1.5, "y": 2.5}}], "wires": []}
        validate_circuit_data(data)  # no exception


class TestValidateCircuitDataWires:
    def _base_circuit(self):
        return {
            "components": [
                {"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}},
                {"id": "GND1", "type": "Ground", "value": "0", "pos": {"x": 1, "y": 0}},
            ],
            "wires": [],
        }

    def test_valid_wire_passes(self):
        data = self._base_circuit()
        data["wires"] = [{"start_comp": "R1", "end_comp": "GND1", "start_term": 0, "end_term": 0}]
        validate_circuit_data(data)  # no exception

    def test_wire_missing_start_comp_raises(self):
        data = self._base_circuit()
        data["wires"] = [{"end_comp": "GND1", "start_term": 0, "end_term": 0}]
        with pytest.raises(ValueError, match="start_comp"):
            validate_circuit_data(data)

    def test_wire_missing_end_comp_raises(self):
        data = self._base_circuit()
        data["wires"] = [{"start_comp": "R1", "start_term": 0, "end_term": 0}]
        with pytest.raises(ValueError, match="end_comp"):
            validate_circuit_data(data)

    def test_wire_unknown_start_comp_raises(self):
        data = self._base_circuit()
        data["wires"] = [{"start_comp": "UNKNOWN", "end_comp": "GND1", "start_term": 0, "end_term": 0}]
        with pytest.raises(ValueError, match="unknown component"):
            validate_circuit_data(data)

    def test_wire_unknown_end_comp_raises(self):
        data = self._base_circuit()
        data["wires"] = [{"start_comp": "R1", "end_comp": "UNKNOWN", "start_term": 0, "end_term": 0}]
        with pytest.raises(ValueError, match="unknown component"):
            validate_circuit_data(data)

    def test_empty_wires_list_passes(self):
        data = {"components": [], "wires": []}
        validate_circuit_data(data)  # no exception
