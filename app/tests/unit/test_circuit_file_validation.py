"""
Tests for CircuitCanvasView._validate_circuit_data — JSON schema validation.
"""

import pytest
from GUI.circuit_canvas import CircuitCanvasView


def _valid_data():
    """Return minimal valid circuit data dict."""
    return {
        "components": [
            {"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0.0, "y": 0.0}},
            {"id": "GND1", "type": "Ground", "value": "0V", "pos": {"x": 100.0, "y": 100.0}},
        ],
        "wires": [
            {"start_comp": "R1", "start_term": 0, "end_comp": "GND1", "end_term": 0},
        ],
    }


class TestValidCircuitData:
    def test_valid_data_passes(self):
        CircuitCanvasView._validate_circuit_data(_valid_data())

    def test_empty_components_and_wires_passes(self):
        CircuitCanvasView._validate_circuit_data({"components": [], "wires": []})


class TestMissingTopLevelKeys:
    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="valid circuit object"):
            CircuitCanvasView._validate_circuit_data([])

    def test_missing_components(self):
        with pytest.raises(ValueError, match="components"):
            CircuitCanvasView._validate_circuit_data({"wires": []})

    def test_missing_wires(self):
        with pytest.raises(ValueError, match="wires"):
            CircuitCanvasView._validate_circuit_data({"components": []})

    def test_components_not_list(self):
        with pytest.raises(ValueError, match="components"):
            CircuitCanvasView._validate_circuit_data({"components": "bad", "wires": []})


class TestComponentValidation:
    def test_missing_id(self):
        data = _valid_data()
        del data["components"][0]["id"]
        with pytest.raises(ValueError, match="'id'"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_missing_type(self):
        data = _valid_data()
        del data["components"][0]["type"]
        with pytest.raises(ValueError, match="'type'"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_missing_value(self):
        data = _valid_data()
        del data["components"][0]["value"]
        with pytest.raises(ValueError, match="'value'"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_missing_pos(self):
        data = _valid_data()
        del data["components"][0]["pos"]
        with pytest.raises(ValueError, match="'pos'"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_pos_missing_x(self):
        data = _valid_data()
        data["components"][0]["pos"] = {"y": 0}
        with pytest.raises(ValueError, match="invalid position"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_pos_not_dict(self):
        data = _valid_data()
        data["components"][0]["pos"] = [0, 0]
        with pytest.raises(ValueError, match="invalid position"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_pos_non_numeric(self):
        data = _valid_data()
        data["components"][0]["pos"] = {"x": "abc", "y": 0}
        with pytest.raises(ValueError, match="numeric"):
            CircuitCanvasView._validate_circuit_data(data)


class TestWireValidation:
    def test_missing_start_comp(self):
        data = _valid_data()
        del data["wires"][0]["start_comp"]
        with pytest.raises(ValueError, match="'start_comp'"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_missing_end_term(self):
        data = _valid_data()
        del data["wires"][0]["end_term"]
        with pytest.raises(ValueError, match="'end_term'"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_wire_references_unknown_start(self):
        data = _valid_data()
        data["wires"][0]["start_comp"] = "NONEXISTENT"
        with pytest.raises(ValueError, match="unknown component"):
            CircuitCanvasView._validate_circuit_data(data)

    def test_wire_references_unknown_end(self):
        data = _valid_data()
        data["wires"][0]["end_comp"] = "NONEXISTENT"
        with pytest.raises(ValueError, match="unknown component"):
            CircuitCanvasView._validate_circuit_data(data)
