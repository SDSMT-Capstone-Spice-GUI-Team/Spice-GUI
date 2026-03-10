"""Tests for clipboard JSON copy/paste circuit functionality."""

import json

import pytest
from controllers.file_controller import validate_circuit_data
from models.circuit import CircuitModel
from models.component import ComponentData


def _make_circuit():
    """Build a simple circuit model for testing."""
    model = CircuitModel()
    model.components = {
        "R1": ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100.0, 200.0),
            rotation=0,
        ),
        "V1": ComponentData(
            component_id="V1",
            component_type="VoltageSource",
            value="5",
            position=(300.0, 200.0),
            rotation=0,
        ),
    }
    model.component_counter = {"Resistor": 1, "VoltageSource": 1}
    model.analysis_type = "DC Operating Point"
    model.analysis_params = {"test": True}
    return model


class TestJsonRoundTrip:
    def test_to_dict_produces_valid_json(self):
        model = _make_circuit()
        data = model.to_dict()
        json_str = json.dumps(data, indent=2)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "components" in parsed
        assert "wires" in parsed

    def test_round_trip_preserves_components(self):
        model = _make_circuit()
        data = model.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        validate_circuit_data(parsed)
        restored = CircuitModel.from_dict(parsed)
        assert set(restored.components.keys()) == {"R1", "V1"}

    def test_round_trip_preserves_values(self):
        model = _make_circuit()
        data = model.to_dict()
        json_str = json.dumps(data)
        restored = CircuitModel.from_dict(json.loads(json_str))
        assert restored.components["R1"].value == "1k"
        assert restored.components["V1"].value == "5"

    def test_round_trip_preserves_analysis_type(self):
        model = _make_circuit()
        data = model.to_dict()
        json_str = json.dumps(data)
        restored = CircuitModel.from_dict(json.loads(json_str))
        assert restored.analysis_type == "DC Operating Point"

    def test_empty_circuit_round_trip(self):
        model = CircuitModel()
        data = model.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        validate_circuit_data(parsed)
        restored = CircuitModel.from_dict(parsed)
        assert len(restored.components) == 0
        assert len(restored.wires) == 0


class TestValidateCircuitData:
    def test_valid_data_passes(self):
        model = _make_circuit()
        data = model.to_dict()
        validate_circuit_data(data)  # should not raise

    def test_not_dict_raises(self):
        with pytest.raises(ValueError, match="valid circuit"):
            validate_circuit_data("not a dict")

    def test_missing_components_raises(self):
        with pytest.raises(ValueError, match="components"):
            validate_circuit_data({"wires": []})

    def test_missing_wires_raises(self):
        with pytest.raises(ValueError, match="wires"):
            validate_circuit_data({"components": []})

    def test_invalid_component_raises(self):
        with pytest.raises(ValueError, match="missing required field"):
            validate_circuit_data({"components": [{"id": "R1"}], "wires": []})


class TestLoadFromDict:
    def test_load_from_dict_updates_model(self):
        from controllers.circuit_controller import CircuitController

        model = CircuitModel()
        ctrl = CircuitController(model)
        file_ctrl = _make_file_ctrl(model, ctrl)

        source = _make_circuit()
        data = source.to_dict()
        file_ctrl.load_from_dict(data)

        assert "R1" in model.components
        assert "V1" in model.components

    def test_load_from_dict_clears_previous(self):
        from controllers.circuit_controller import CircuitController

        model = _make_circuit()
        ctrl = CircuitController(model)
        file_ctrl = _make_file_ctrl(model, ctrl)

        empty = CircuitModel()
        file_ctrl.load_from_dict(empty.to_dict())

        assert len(model.components) == 0


def _make_file_ctrl(model, circuit_ctrl):
    """Create a FileController wired to a model and circuit controller."""
    from controllers.file_controller import FileController

    fc = FileController(model)
    fc.circuit_ctrl = circuit_ctrl
    return fc
