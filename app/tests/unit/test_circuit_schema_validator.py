"""Tests for models.circuit_schema_validator.validate_circuit_data."""

import pytest
from models.circuit import SCHEMA_VERSION
from models.circuit_schema_validator import validate_circuit_data


def _valid_circuit():
    return {
        "schema_version": SCHEMA_VERSION,
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


class TestValidateSchemaVersion:
    """Issue #521: circuit JSON must include a schema_version field."""

    def test_valid_version_passes(self):
        data = _valid_circuit()
        validate_circuit_data(data)  # no exception

    def test_missing_version_passes_for_backward_compat(self):
        data = _valid_circuit()
        del data["schema_version"]
        validate_circuit_data(data)  # no exception

    def test_non_integer_version_raises(self):
        data = _valid_circuit()
        data["schema_version"] = "1"
        with pytest.raises(ValueError, match="integer"):
            validate_circuit_data(data)

    def test_future_version_raises(self):
        data = _valid_circuit()
        data["schema_version"] = SCHEMA_VERSION + 1
        with pytest.raises(ValueError, match="update the application"):
            validate_circuit_data(data)

    def test_current_version_passes(self):
        data = _valid_circuit()
        data["schema_version"] = SCHEMA_VERSION
        validate_circuit_data(data)  # no exception

    def test_older_version_passes(self):
        data = _valid_circuit()
        data["schema_version"] = 1
        validate_circuit_data(data)  # no exception


class TestValidateCircuitDataComponents:
    def test_component_missing_id_raises(self):
        data = {
            "components": [{"type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="'id'"):
            validate_circuit_data(data)

    def test_component_missing_type_raises(self):
        data = {
            "components": [{"id": "R1", "value": "1k", "pos": {"x": 0, "y": 0}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="'type'"):
            validate_circuit_data(data)

    def test_component_missing_value_raises(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "pos": {"x": 0, "y": 0}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="'value'"):
            validate_circuit_data(data)

    def test_component_missing_pos_raises(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k"}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="'pos'"):
            validate_circuit_data(data)

    def test_component_pos_missing_x_raises(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"y": 0}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="invalid position"):
            validate_circuit_data(data)

    def test_component_pos_missing_y_raises(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="invalid position"):
            validate_circuit_data(data)

    def test_component_pos_non_numeric_x_raises(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": "a", "y": 0}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="numeric"):
            validate_circuit_data(data)

    def test_component_pos_non_numeric_y_raises(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": "b"}}],
            "wires": [],
        }
        with pytest.raises(ValueError, match="numeric"):
            validate_circuit_data(data)

    def test_component_pos_accepts_float(self):
        data = {
            "components": [
                {
                    "id": "R1",
                    "type": "Resistor",
                    "value": "1k",
                    "pos": {"x": 1.5, "y": 2.5},
                }
            ],
            "wires": [],
        }
        validate_circuit_data(data)  # no exception


class TestValidateComponentTypeAndRotation:
    """Issue #526: validate_circuit_data must check component types and rotation values."""

    def test_unknown_component_type_raises(self):
        data = {
            "components": [
                {
                    "id": "X1",
                    "type": "FakeComponent",
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                }
            ],
            "wires": [],
        }
        with pytest.raises(ValueError, match="unknown type.*FakeComponent"):
            validate_circuit_data(data)

    def test_all_known_types_pass(self):
        from models.component import COMPONENT_TYPES

        for ctype in COMPONENT_TYPES:
            data = {
                "components": [{"id": "X1", "type": ctype, "value": "", "pos": {"x": 0, "y": 0}}],
                "wires": [],
            }
            validate_circuit_data(data)  # no exception

    def test_serialized_class_names_pass(self):
        from models.component import _CLASS_TO_DISPLAY

        for class_name in _CLASS_TO_DISPLAY:
            data = {
                "components": [{"id": "X1", "type": class_name, "value": "", "pos": {"x": 0, "y": 0}}],
                "wires": [],
            }
            validate_circuit_data(data)  # no exception

    def test_valid_rotations_pass(self):
        for rotation in (0, 90, 180, 270):
            data = {
                "components": [
                    {
                        "id": "R1",
                        "type": "Resistor",
                        "value": "1k",
                        "pos": {"x": 0, "y": 0},
                        "rotation": rotation,
                    }
                ],
                "wires": [],
            }
            validate_circuit_data(data)  # no exception

    def test_invalid_rotation_raises(self):
        data = {
            "components": [
                {
                    "id": "R1",
                    "type": "Resistor",
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                    "rotation": 45,
                }
            ],
            "wires": [],
        }
        with pytest.raises(ValueError, match="invalid rotation"):
            validate_circuit_data(data)

    def test_missing_rotation_defaults_to_zero(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}],
            "wires": [],
        }
        validate_circuit_data(data)  # no exception — rotation defaults to 0


class TestValidateCircuitDataWires:
    def _base_circuit(self):
        return {
            "components": [
                {
                    "id": "R1",
                    "type": "Resistor",
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                },
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
        data["wires"] = [
            {
                "start_comp": "UNKNOWN",
                "end_comp": "GND1",
                "start_term": 0,
                "end_term": 0,
            }
        ]
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
