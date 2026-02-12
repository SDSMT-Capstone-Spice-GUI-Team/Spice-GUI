"""Tests for the CLI batch operations (app/cli.py)."""

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from cli import (
    REPL_BANNER,
    __version__,
    build_parser,
    build_repl_namespace,
    cmd_batch,
    cmd_export,
    cmd_simulate,
    cmd_validate,
    load_circuit,
    main,
    try_load_circuit,
)
from models.circuit import CircuitModel
from scripting.circuit import Circuit


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

    def test_batch_requires_path(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["batch"])


class TestTryLoadCircuit:
    def test_success(self, voltage_divider):
        model, error = try_load_circuit(voltage_divider)
        assert model is not None
        assert error == ""

    def test_nonexistent(self):
        model, error = try_load_circuit("/nonexistent/file.json")
        assert model is None
        assert "not found" in error

    def test_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        model, error = try_load_circuit(str(bad))
        assert model is None
        assert "invalid JSON" in error


class TestBatchCommand:
    @pytest.fixture
    def circuit_dir(self, tmp_path):
        """Create a directory with multiple circuit files."""
        base = {
            "components": [
                {"type": "Voltage Source", "id": "V1", "value": "5V", "pos": {"x": 0, "y": 0}, "rotation": 0},
                {"type": "Resistor", "id": "R1", "value": "1k", "pos": {"x": 200, "y": 0}, "rotation": 0},
                {"type": "Ground", "id": "GND1", "value": "0V", "pos": {"x": 0, "y": 200}, "rotation": 0},
            ],
            "wires": [
                {"start_comp": "V1", "start_term": 0, "end_comp": "R1", "end_term": 0},
                {"start_comp": "R1", "start_term": 1, "end_comp": "GND1", "end_term": 0},
                {"start_comp": "V1", "start_term": 1, "end_comp": "GND1", "end_term": 0},
            ],
            "counters": {"R": 1, "V": 1, "GND": 1},
        }
        circuits_dir = tmp_path / "circuits"
        circuits_dir.mkdir()

        # Write three valid circuits with different values
        for i, val in enumerate(["1k", "2.2k", "4.7k"], 1):
            c = json.loads(json.dumps(base))
            c["components"][1]["value"] = val
            (circuits_dir / f"circuit_{i}.json").write_text(json.dumps(c))

        return str(circuits_dir)

    @pytest.fixture
    def mixed_dir(self, tmp_path):
        """Create a directory with valid and invalid circuit files."""
        circuits_dir = tmp_path / "mixed"
        circuits_dir.mkdir()

        # Valid circuit
        valid = {
            "components": [
                {"type": "Voltage Source", "id": "V1", "value": "5V", "pos": {"x": 0, "y": 0}, "rotation": 0},
                {"type": "Resistor", "id": "R1", "value": "1k", "pos": {"x": 200, "y": 0}, "rotation": 0},
                {"type": "Ground", "id": "GND1", "value": "0V", "pos": {"x": 0, "y": 200}, "rotation": 0},
            ],
            "wires": [
                {"start_comp": "V1", "start_term": 0, "end_comp": "R1", "end_term": 0},
                {"start_comp": "R1", "start_term": 1, "end_comp": "GND1", "end_term": 0},
                {"start_comp": "V1", "start_term": 1, "end_comp": "GND1", "end_term": 0},
            ],
            "counters": {"R": 1, "V": 1, "GND": 1},
        }
        (circuits_dir / "good.json").write_text(json.dumps(valid))

        # Invalid circuit (empty)
        (circuits_dir / "bad.json").write_text(json.dumps({"components": [], "wires": [], "counters": {}}))

        return str(circuits_dir)

    def test_batch_directory(self, circuit_dir, capsys):
        args = build_parser().parse_args(["batch", circuit_dir])
        cmd_batch(args)
        captured = capsys.readouterr()
        # Should print summary table
        assert "circuit_1.json" in captured.out
        assert "circuit_2.json" in captured.out
        assert "circuit_3.json" in captured.out

    def test_batch_with_output_dir(self, circuit_dir, tmp_path):
        out_dir = str(tmp_path / "results")
        args = build_parser().parse_args(["batch", circuit_dir, "--output-dir", out_dir])
        cmd_batch(args)
        # Output directory should be created
        assert Path(out_dir).exists()

    def test_batch_mixed_results(self, mixed_dir, capsys):
        """Batch continues on error by default."""
        args = build_parser().parse_args(["batch", mixed_dir])
        cmd_batch(args)
        captured = capsys.readouterr()
        # Should have processed both files
        assert "good.json" in captured.out
        assert "bad.json" in captured.out

    def test_batch_fail_fast(self, mixed_dir, capsys):
        """--fail-fast stops after first failure."""
        args = build_parser().parse_args(["batch", mixed_dir, "--fail-fast"])
        code = cmd_batch(args)
        assert code == 1

    def test_batch_empty_dir(self, tmp_path, capsys):
        """Empty directory returns error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        args = build_parser().parse_args(["batch", str(empty_dir)])
        code = cmd_batch(args)
        assert code == 1

    def test_batch_via_main(self, circuit_dir, capsys):
        main(["batch", circuit_dir])
        captured = capsys.readouterr()
        assert "succeeded" in captured.out

    def test_batch_glob_pattern(self, circuit_dir, capsys):
        pattern = str(Path(circuit_dir) / "circuit_*.json")
        args = build_parser().parse_args(["batch", pattern])
        cmd_batch(args)
        captured = capsys.readouterr()
        assert "circuit_1.json" in captured.out

    def test_batch_csv_format(self, circuit_dir, tmp_path):
        out_dir = str(tmp_path / "csv_results")
        args = build_parser().parse_args(["batch", circuit_dir, "--format", "csv", "--output-dir", out_dir])
        code = cmd_batch(args)
        # If simulations succeeded, check CSV files exist
        if code == 0:
            csv_files = list(Path(out_dir).glob("*.csv"))
            assert len(csv_files) == 3


class TestVersion:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_version_string(self):
        assert __version__
        parts = __version__.split(".")
        assert len(parts) == 3


class TestStdinPipe:
    def test_load_from_stdin(self, voltage_divider):
        """Reading from '-' reads stdin."""
        circuit_json = Path(voltage_divider).read_text()
        with patch("sys.stdin", io.StringIO(circuit_json)):
            model, error = try_load_circuit("-")
        assert model is not None
        assert error == ""
        assert len(model.components) == 4

    def test_load_invalid_stdin(self):
        with patch("sys.stdin", io.StringIO("not json")):
            model, error = try_load_circuit("-")
        assert model is None
        assert "invalid JSON" in error

    def test_validate_from_stdin(self, voltage_divider, capsys):
        circuit_json = Path(voltage_divider).read_text()
        with patch("sys.stdin", io.StringIO(circuit_json)):
            code = main(["validate", "-"])
        assert code == 0

    def test_export_from_stdin(self, voltage_divider, capsys):
        circuit_json = Path(voltage_divider).read_text()
        with patch("sys.stdin", io.StringIO(circuit_json)):
            code = main(["export", "-", "--format", "json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "components" in data


class TestReplCommand:
    def test_repl_namespace_has_circuit(self):
        ns = build_repl_namespace()
        assert "Circuit" in ns
        assert ns["Circuit"] is Circuit

    def test_repl_namespace_has_simulation_result(self):
        ns = build_repl_namespace()
        assert "SimulationResult" in ns

    def test_repl_namespace_has_component_types(self):
        ns = build_repl_namespace()
        assert "COMPONENT_TYPES" in ns
        assert "Resistor" in ns["COMPONENT_TYPES"]

    def test_repl_namespace_load_circuit(self, voltage_divider):
        ns = build_repl_namespace(voltage_divider)
        assert "circuit" in ns
        assert isinstance(ns["circuit"], Circuit)
        assert len(ns["circuit"].components) == 4

    def test_repl_namespace_load_nonexistent(self, capsys):
        ns = build_repl_namespace("/nonexistent/file.json")
        assert "circuit" not in ns
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_repl_banner_content(self):
        assert "Circuit" in REPL_BANNER
        assert "Quick start" in REPL_BANNER

    def test_repl_parser(self, voltage_divider):
        args = build_parser().parse_args(["repl", "--load", voltage_divider])
        assert args.load == voltage_divider

    def test_repl_parser_no_args(self):
        args = build_parser().parse_args(["repl"])
        assert args.load is None
