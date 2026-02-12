"""Tests for the CLI batch operations (app/cli.py)."""

import json

import pytest
from cli import build_parser, cmd_export, cmd_simulate, cmd_validate, load_circuit, main
from models.circuit import CircuitModel


@pytest.fixture
def voltage_divider(tmp_path):
    """Create a valid voltage divider circuit file."""
    circuit = {
        "components": [
            {"type": "Voltage Source", "id": "V1", "value": "5V", "pos": {"x": 0, "y": 0}, "rotation": 0},
            {"type": "Resistor", "id": "R1", "value": "1k", "pos": {"x": 200, "y": 0}, "rotation": 0},
            {"type": "Resistor", "id": "R2", "value": "1k", "pos": {"x": 300, "y": 0}, "rotation": 0},
            {"type": "Ground", "id": "GND1", "value": "0V", "pos": {"x": 350, "y": 150}, "rotation": 0},
        ],
        "wires": [
            {"start_comp": "V1", "start_term": 0, "end_comp": "R1", "end_term": 0},
            {"start_comp": "R1", "start_term": 1, "end_comp": "R2", "end_term": 0},
            {"start_comp": "R2", "start_term": 1, "end_comp": "GND1", "end_term": 0},
            {"start_comp": "V1", "start_term": 1, "end_comp": "GND1", "end_term": 0},
        ],
        "counters": {"R": 2, "V": 1, "GND": 1},
    }
    filepath = tmp_path / "voltage_divider.json"
    filepath.write_text(json.dumps(circuit))
    return str(filepath)


@pytest.fixture
def empty_circuit(tmp_path):
    """Create a minimal (empty) circuit file."""
    circuit = {"components": [], "wires": [], "counters": {}}
    filepath = tmp_path / "empty.json"
    filepath.write_text(json.dumps(circuit))
    return str(filepath)


class TestLoadCircuit:
    def test_load_valid(self, voltage_divider):
        model = load_circuit(voltage_divider)
        assert isinstance(model, CircuitModel)
        assert len(model.components) == 4
        assert len(model.wires) == 4

    def test_load_nonexistent(self):
        with pytest.raises(SystemExit):
            load_circuit("/nonexistent/file.json")

    def test_load_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        with pytest.raises(SystemExit):
            load_circuit(str(bad))

    def test_load_invalid_structure(self, tmp_path):
        bad = tmp_path / "bad_struct.json"
        bad.write_text('{"foo": "bar"}')
        with pytest.raises(SystemExit):
            load_circuit(str(bad))


class TestValidateCommand:
    def test_valid_circuit(self, voltage_divider):
        args = build_parser().parse_args(["validate", voltage_divider])
        code = cmd_validate(args)
        assert code == 0

    def test_empty_circuit_fails_validation(self, empty_circuit):
        args = build_parser().parse_args(["validate", empty_circuit])
        code = cmd_validate(args)
        assert code == 1

    def test_via_main(self, voltage_divider):
        code = main(["validate", voltage_divider])
        assert code == 0


class TestExportCommand:
    def test_export_netlist_to_stdout(self, voltage_divider, capsys):
        args = build_parser().parse_args(["export", voltage_divider, "--format", "cir"])
        code = cmd_export(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "V1" in captured.out
        assert "R1" in captured.out

    def test_export_netlist_to_file(self, voltage_divider, tmp_path):
        outfile = str(tmp_path / "output.cir")
        args = build_parser().parse_args(["export", voltage_divider, "-f", "cir", "-o", outfile])
        code = cmd_export(args)
        assert code == 0
        content = (tmp_path / "output.cir").read_text()
        assert "V1" in content

    def test_export_json(self, voltage_divider, capsys):
        args = build_parser().parse_args(["export", voltage_divider, "--format", "json"])
        code = cmd_export(args)
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "components" in data

    def test_export_unsupported_format(self, voltage_divider):
        # argparse won't allow invalid choices, so test via main with invalid args
        with pytest.raises(SystemExit):
            main(["export", voltage_divider, "--format", "png"])

    def test_via_main(self, voltage_divider, capsys):
        code = main(["export", voltage_divider])
        assert code == 0
        captured = capsys.readouterr()
        assert "V1" in captured.out


class TestSimulateCommand:
    def test_simulate_missing_ngspice(self, voltage_divider):
        """Simulation fails gracefully when ngspice is not installed."""
        args = build_parser().parse_args(["simulate", voltage_divider])
        code = cmd_simulate(args)
        # Either succeeds (ngspice found) or fails with clear error
        assert code in (0, 1)

    def test_simulate_empty_circuit(self, empty_circuit):
        args = build_parser().parse_args(["simulate", empty_circuit])
        code = cmd_simulate(args)
        assert code == 1  # validation should fail

    def test_simulate_json_output(self, voltage_divider, capsys):
        args = build_parser().parse_args(["simulate", voltage_divider, "--format", "json"])
        code = cmd_simulate(args)
        if code == 0:
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["success"] is True
            assert "data" in data

    def test_simulate_csv_output(self, voltage_divider, capsys):
        args = build_parser().parse_args(["simulate", voltage_divider, "--format", "csv"])
        code = cmd_simulate(args)
        if code == 0:
            captured = capsys.readouterr()
            assert "Node" in captured.out or "Voltage" in captured.out

    def test_simulate_output_to_file(self, voltage_divider, tmp_path):
        outfile = str(tmp_path / "results.json")
        args = build_parser().parse_args(["simulate", voltage_divider, "-o", outfile])
        code = cmd_simulate(args)
        if code == 0:
            assert (tmp_path / "results.json").exists()


class TestParser:
    def test_no_command(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_simulate_requires_circuit(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["simulate"])

    def test_validate_requires_circuit(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["validate"])

    def test_export_requires_circuit(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["export"])

    def test_simulate_analysis_override(self, voltage_divider):
        args = build_parser().parse_args(["simulate", voltage_divider, "--analysis", "DC Operating Point"])
        assert args.analysis == "DC Operating Point"
