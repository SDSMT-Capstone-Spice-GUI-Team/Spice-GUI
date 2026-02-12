"""Tests for the scripting API (app/scripting/)."""

import csv
import json

import pytest
from models.circuit import CircuitModel
from scripting import Circuit, SimulationResult


class TestCircuitCreation:
    def test_empty_circuit(self):
        circuit = Circuit()
        assert len(circuit.components) == 0
        assert len(circuit.wires) == 0

    def test_add_component_returns_id(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor", "1k")
        assert cid == "R1"

    def test_add_component_default_value(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor")
        assert circuit.components[cid].value == "1k"

    def test_add_component_custom_value(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor", "4.7k")
        assert circuit.components[cid].value == "4.7k"

    def test_add_component_position(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor", position=(100, 200))
        assert circuit.components[cid].position == (100, 200)

    def test_add_component_rotation(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor", rotation=90)
        assert circuit.components[cid].rotation == 90

    def test_add_component_flip(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor", flip_h=True)
        assert circuit.components[cid].flip_h is True

    def test_add_multiple_components_unique_ids(self):
        circuit = Circuit()
        r1 = circuit.add_component("Resistor")
        r2 = circuit.add_component("Resistor")
        v1 = circuit.add_component("Voltage Source")
        assert r1 == "R1"
        assert r2 == "R2"
        assert v1 == "V1"

    def test_add_invalid_component_type(self):
        circuit = Circuit()
        with pytest.raises(ValueError, match="Unknown component type"):
            circuit.add_component("InvalidType")

    def test_remove_component(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor")
        circuit.remove_component(cid)
        assert cid not in circuit.components

    def test_update_value(self):
        circuit = Circuit()
        cid = circuit.add_component("Resistor", "1k")
        circuit.update_value(cid, "2.2k")
        assert circuit.components[cid].value == "2.2k"

    def test_all_component_types_addable(self):
        from models.component import COMPONENT_TYPES

        circuit = Circuit()
        for ctype in COMPONENT_TYPES:
            cid = circuit.add_component(ctype)
            assert cid in circuit.components


class TestWiring:
    def test_add_wire(self):
        circuit = Circuit()
        circuit.add_component("Resistor")
        circuit.add_component("Voltage Source")
        result = circuit.add_wire("R1", 0, "V1", 0)
        assert result is True
        assert len(circuit.wires) == 1

    def test_duplicate_wire_rejected(self):
        circuit = Circuit()
        circuit.add_component("Resistor")
        circuit.add_component("Voltage Source")
        circuit.add_wire("R1", 0, "V1", 0)
        result = circuit.add_wire("R1", 0, "V1", 0)
        assert result is False
        assert len(circuit.wires) == 1

    def test_remove_component_removes_wires(self):
        circuit = Circuit()
        circuit.add_component("Resistor")
        circuit.add_component("Voltage Source")
        circuit.add_wire("R1", 0, "V1", 0)
        circuit.remove_component("R1")
        assert len(circuit.wires) == 0


class TestAnalysis:
    def test_default_analysis(self):
        circuit = Circuit()
        assert circuit.analysis_type == "DC Operating Point"

    def test_set_analysis(self):
        circuit = Circuit()
        circuit.set_analysis("Transient", {"step": 1e-6, "duration": 1e-3})
        assert circuit.analysis_type == "Transient"
        assert circuit.analysis_params["step"] == 1e-6

    def test_validate_empty_circuit(self):
        circuit = Circuit()
        result = circuit.validate()
        assert result.success is False


class TestNetlistGeneration:
    def test_simple_netlist(self):
        circuit = Circuit()
        circuit.add_component("Voltage Source", "5V", position=(0, 0))
        circuit.add_component("Resistor", "1k", position=(200, 0))
        circuit.add_component("Ground", position=(0, 200))
        circuit.add_wire("V1", 0, "R1", 0)
        circuit.add_wire("R1", 1, "V1", 1)
        circuit.add_wire("V1", 1, "GND1", 0)

        netlist = circuit.to_netlist()
        assert "V1" in netlist
        assert "R1" in netlist
        assert ".op" in netlist.lower() or ".OP" in netlist


class TestSaveLoad:
    def test_save_and_load(self, tmp_path):
        circuit = Circuit()
        circuit.add_component("Resistor", "1k", position=(100, 0))
        circuit.add_component("Voltage Source", "5V", position=(0, 0))
        circuit.add_wire("R1", 0, "V1", 0)
        circuit.set_analysis("Transient", {"step": 1e-6, "duration": 1e-3})

        filepath = tmp_path / "test_circuit.json"
        circuit.save(filepath)
        assert filepath.exists()

        loaded = Circuit.load(filepath)
        assert len(loaded.components) == 2
        assert len(loaded.wires) == 1
        assert loaded.components["R1"].value == "1k"
        assert loaded.analysis_type == "Transient"

    def test_save_produces_valid_json(self, tmp_path):
        circuit = Circuit()
        circuit.add_component("Resistor", "1k")
        filepath = tmp_path / "test.json"
        circuit.save(filepath)

        with open(filepath) as f:
            data = json.load(f)
        assert "components" in data
        assert "wires" in data

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            Circuit.load("/nonexistent/path/circuit.json")

    def test_load_invalid_json(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            Circuit.load(filepath)

    def test_load_invalid_structure(self, tmp_path):
        filepath = tmp_path / "bad_structure.json"
        filepath.write_text('{"foo": "bar"}')
        with pytest.raises(ValueError):
            Circuit.load(filepath)


class TestResultExport:
    def test_op_result_to_csv(self, tmp_path):
        result = SimulationResult(
            success=True,
            analysis_type="DC Operating Point",
            data={
                "node_voltages": {"node_a": 5.0, "node_b": 2.5},
                "branch_currents": {"v1#branch": -0.005},
            },
        )
        filepath = tmp_path / "op_results.csv"
        Circuit.result_to_csv(result, filepath)

        with open(filepath) as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[0] == ["name", "value"]
        assert len(rows) == 4  # header + 2 voltages + 1 current

    def test_transient_result_to_csv(self, tmp_path):
        result = SimulationResult(
            success=True,
            analysis_type="Transient",
            data=[
                {"time": 0.0, "v(node_a)": 0.0},
                {"time": 1e-6, "v(node_a)": 2.5},
                {"time": 2e-6, "v(node_a)": 5.0},
            ],
        )
        filepath = tmp_path / "transient_results.csv"
        Circuit.result_to_csv(result, filepath)

        with open(filepath) as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[0] == ["time", "v(node_a)"]
        assert len(rows) == 4  # header + 3 data points

    def test_export_failed_result_raises(self, tmp_path):
        result = SimulationResult(success=False, error="ngspice not found")
        with pytest.raises(ValueError, match="Cannot export"):
            Circuit.result_to_csv(result, tmp_path / "fail.csv")


class TestProperties:
    def test_model_access(self):
        circuit = Circuit()
        assert isinstance(circuit.model, CircuitModel)

    def test_components_property(self):
        circuit = Circuit()
        circuit.add_component("Resistor")
        assert "R1" in circuit.components

    def test_wires_property(self):
        circuit = Circuit()
        circuit.add_component("Resistor")
        circuit.add_component("Voltage Source")
        circuit.add_wire("R1", 0, "V1", 0)
        assert len(circuit.wires) == 1
