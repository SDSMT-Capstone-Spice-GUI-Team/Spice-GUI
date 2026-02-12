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
    cmd_diff,
    cmd_export,
    cmd_import,
    cmd_simulate,
    cmd_validate,
    diff_circuits,
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


class TestImportCommand:
    @pytest.fixture
    def simple_netlist(self, tmp_path):
        """Create a simple SPICE netlist file."""
        netlist = """\
* Simple voltage divider
V1 1 0 5
R1 1 2 1k
R2 2 0 1k
.op
.end
"""
        filepath = tmp_path / "divider.cir"
        filepath.write_text(netlist)
        return str(filepath)

    def test_import_basic(self, simple_netlist, tmp_path):
        args = build_parser().parse_args(["import", simple_netlist])
        code = cmd_import(args)
        assert code == 0
        # Default output is same name with .json extension
        out_path = Path(simple_netlist).with_suffix(".json")
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "components" in data

    def test_import_custom_output(self, simple_netlist, tmp_path):
        outfile = str(tmp_path / "imported.json")
        args = build_parser().parse_args(["import", simple_netlist, "-o", outfile])
        code = cmd_import(args)
        assert code == 0
        assert Path(outfile).exists()
        data = json.loads(Path(outfile).read_text())
        assert "components" in data

    def test_import_nonexistent_file(self):
        args = build_parser().parse_args(["import", "/nonexistent/file.cir"])
        code = cmd_import(args)
        assert code == 1

    def test_import_invalid_netlist(self, tmp_path):
        bad = tmp_path / "bad.cir"
        bad.write_text("this is not a valid netlist")
        args = build_parser().parse_args(["import", str(bad)])
        code = cmd_import(args)
        assert code == 1

    def test_import_via_main(self, simple_netlist):
        code = main(["import", simple_netlist])
        assert code == 0

    def test_import_requires_netlist_arg(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["import"])

    def test_import_preserves_analysis(self, simple_netlist, tmp_path):
        """Imported netlist with .op directive should set analysis type."""
        outfile = str(tmp_path / "with_analysis.json")
        args = build_parser().parse_args(["import", simple_netlist, "-o", outfile])
        cmd_import(args)
        data = json.loads(Path(outfile).read_text())
        # The .op directive should result in DC Operating Point analysis
        if "analysis_type" in data:
            assert data["analysis_type"] == "DC Operating Point"


class TestDiffCommand:
    @pytest.fixture
    def base_circuit_data(self):
        return {
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

    @pytest.fixture
    def circuit_a(self, tmp_path, base_circuit_data):
        filepath = tmp_path / "circuit_a.json"
        filepath.write_text(json.dumps(base_circuit_data))
        return str(filepath)

    @pytest.fixture
    def circuit_b_identical(self, tmp_path, base_circuit_data):
        filepath = tmp_path / "circuit_b.json"
        filepath.write_text(json.dumps(base_circuit_data))
        return str(filepath)

    @pytest.fixture
    def circuit_b_value_changed(self, tmp_path, base_circuit_data):
        data = json.loads(json.dumps(base_circuit_data))
        data["components"][1]["value"] = "2.2k"
        filepath = tmp_path / "circuit_b_changed.json"
        filepath.write_text(json.dumps(data))
        return str(filepath)

    @pytest.fixture
    def circuit_b_component_added(self, tmp_path, base_circuit_data):
        data = json.loads(json.dumps(base_circuit_data))
        data["components"].append(
            {"type": "Resistor", "id": "R2", "value": "4.7k", "pos": {"x": 300, "y": 0}, "rotation": 0}
        )
        data["counters"]["R"] = 2
        filepath = tmp_path / "circuit_b_added.json"
        filepath.write_text(json.dumps(data))
        return str(filepath)

    @pytest.fixture
    def circuit_b_wire_changed(self, tmp_path, base_circuit_data):
        data = json.loads(json.dumps(base_circuit_data))
        # Remove one wire and add a different one
        data["wires"] = data["wires"][:2]
        data["wires"].append({"start_comp": "V1", "start_term": 1, "end_comp": "R1", "end_term": 1})
        filepath = tmp_path / "circuit_b_wire.json"
        filepath.write_text(json.dumps(data))
        return str(filepath)

    @pytest.fixture
    def circuit_b_analysis_changed(self, tmp_path, base_circuit_data):
        data = json.loads(json.dumps(base_circuit_data))
        data["analysis_type"] = "AC Sweep"
        data["analysis_params"] = {"start_freq": "1", "stop_freq": "1MEG", "points": "100"}
        filepath = tmp_path / "circuit_b_analysis.json"
        filepath.write_text(json.dumps(data))
        return str(filepath)

    def test_identical_circuits(self, circuit_a, circuit_b_identical):
        model_a = load_circuit(circuit_a)
        model_b = load_circuit(circuit_b_identical)
        diff = diff_circuits(model_a, model_b)
        assert diff["components"] == {}
        assert diff["wires"] == {}
        assert diff["analysis"] == {}

    def test_identical_returns_zero(self, circuit_a, circuit_b_identical):
        args = build_parser().parse_args(["diff", circuit_a, circuit_b_identical])
        code = cmd_diff(args)
        assert code == 0

    def test_different_returns_one(self, circuit_a, circuit_b_value_changed):
        args = build_parser().parse_args(["diff", circuit_a, circuit_b_value_changed])
        code = cmd_diff(args)
        assert code == 1

    def test_component_value_change(self, circuit_a, circuit_b_value_changed):
        model_a = load_circuit(circuit_a)
        model_b = load_circuit(circuit_b_value_changed)
        diff = diff_circuits(model_a, model_b)
        assert len(diff["components"]["changed"]) == 1
        change = diff["components"]["changed"][0]
        assert change["id"] == "R1"
        assert change["changes"]["value"] == {"from": "1k", "to": "2.2k"}

    def test_component_added(self, circuit_a, circuit_b_component_added):
        model_a = load_circuit(circuit_a)
        model_b = load_circuit(circuit_b_component_added)
        diff = diff_circuits(model_a, model_b)
        assert len(diff["components"]["added"]) == 1
        assert diff["components"]["added"][0]["id"] == "R2"

    def test_component_removed(self, circuit_a, circuit_b_component_added):
        # Swap a and b to test removal
        model_a = load_circuit(circuit_b_component_added)
        model_b = load_circuit(circuit_a)
        diff = diff_circuits(model_a, model_b)
        assert len(diff["components"]["removed"]) == 1
        assert diff["components"]["removed"][0]["id"] == "R2"

    def test_wire_changes(self, circuit_a, circuit_b_wire_changed):
        model_a = load_circuit(circuit_a)
        model_b = load_circuit(circuit_b_wire_changed)
        diff = diff_circuits(model_a, model_b)
        assert "added" in diff["wires"]
        assert "removed" in diff["wires"]

    def test_analysis_change(self, circuit_a, circuit_b_analysis_changed):
        model_a = load_circuit(circuit_a)
        model_b = load_circuit(circuit_b_analysis_changed)
        diff = diff_circuits(model_a, model_b)
        assert diff["analysis"]["type"] == {"from": "DC Operating Point", "to": "AC Sweep"}
        assert "params" in diff["analysis"]

    def test_text_format(self, circuit_a, circuit_b_value_changed, capsys):
        args = build_parser().parse_args(["diff", circuit_a, circuit_b_value_changed])
        cmd_diff(args)
        captured = capsys.readouterr()
        assert "R1" in captured.out
        assert "1k" in captured.out
        assert "2.2k" in captured.out

    def test_json_format(self, circuit_a, circuit_b_value_changed, capsys):
        args = build_parser().parse_args(["diff", circuit_a, circuit_b_value_changed, "-f", "json"])
        cmd_diff(args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "components" in data
        assert "wires" in data
        assert "analysis" in data

    def test_identical_text_output(self, circuit_a, circuit_b_identical, capsys):
        args = build_parser().parse_args(["diff", circuit_a, circuit_b_identical])
        cmd_diff(args)
        captured = capsys.readouterr()
        assert "identical" in captured.out

    def test_via_main(self, circuit_a, circuit_b_value_changed):
        code = main(["diff", circuit_a, circuit_b_value_changed])
        assert code == 1

    def test_parser_requires_two_files(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["diff"])
