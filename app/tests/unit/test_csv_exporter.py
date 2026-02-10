"""Tests for CSV export functionality."""

import csv
import io

import pytest
from simulation.csv_exporter import (
    export_ac_results,
    export_dc_sweep_results,
    export_op_results,
    export_transient_results,
    write_csv,
)


class TestExportOpResults:
    def test_basic_export(self):
        voltages = {"1": 5.0, "2": 3.3}
        result = export_op_results(voltages)
        assert "DC Operating Point" in result
        assert "Node" in result
        assert "Voltage" in result

    def test_contains_all_nodes(self):
        voltages = {"1": 5.0, "2": 3.3, "out": 2.5}
        result = export_op_results(voltages)
        assert "1" in result
        assert "2" in result
        assert "out" in result
        assert "5.0" in result
        assert "3.3" in result

    def test_sorted_by_node_name(self):
        voltages = {"z_node": 1.0, "a_node": 2.0}
        result = export_op_results(voltages)
        lines = result.strip().split("\n")
        data_lines = [l for l in lines if not l.startswith("#") and l.strip() and "Node" not in l]
        assert "a_node" in data_lines[0]
        assert "z_node" in data_lines[1]

    def test_circuit_name_included(self):
        result = export_op_results({"1": 5.0}, circuit_name="my_circuit.json")
        assert "my_circuit.json" in result

    def test_parseable_as_csv(self):
        voltages = {"1": 5.0, "2": 3.3}
        result = export_op_results(voltages)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) >= 5  # metadata + header + data

    def test_empty_voltages(self):
        result = export_op_results({})
        assert "DC Operating Point" in result
        assert "Node" in result


class TestExportDcSweepResults:
    def test_basic_export(self):
        data = {
            "headers": ["Index", "v-sweep", "v(1)"],
            "data": [[0, 0.0, 0.0], [1, 1.0, 0.5], [2, 2.0, 1.0]],
        }
        result = export_dc_sweep_results(data)
        assert "DC Sweep" in result
        assert "v-sweep" in result

    def test_all_data_rows_present(self):
        data = {"headers": ["Index", "v-sweep"], "data": [[0, 0.0], [1, 1.0], [2, 2.0]]}
        result = export_dc_sweep_results(data)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        # metadata (3) + blank + header + 3 data = 8
        data_rows = [r for r in rows if r and not r[0].startswith("#") and r[0] != "Index"]
        assert len(data_rows) == 3

    def test_empty_data(self):
        data = {"headers": ["Index"], "data": []}
        result = export_dc_sweep_results(data)
        assert "DC Sweep" in result


class TestExportAcResults:
    def test_basic_export(self):
        data = {
            "frequencies": [100.0, 1000.0],
            "magnitude": {"1": [0.5, 0.3]},
            "phase": {"1": [-45.0, -90.0]},
        }
        result = export_ac_results(data)
        assert "AC Sweep" in result
        assert "Frequency" in result

    def test_magnitude_and_phase_columns(self):
        data = {
            "frequencies": [100.0],
            "magnitude": {"out": [0.5]},
            "phase": {"out": [-45.0]},
        }
        result = export_ac_results(data)
        assert "|V(out)|" in result
        assert "phase(V(out))" in result

    def test_multiple_nodes(self):
        data = {
            "frequencies": [100.0],
            "magnitude": {"1": [0.5], "2": [0.3]},
            "phase": {"1": [-45.0], "2": [-90.0]},
        }
        result = export_ac_results(data)
        assert "|V(1)|" in result
        assert "|V(2)|" in result

    def test_empty_frequencies(self):
        data = {"frequencies": [], "magnitude": {}, "phase": {}}
        result = export_ac_results(data)
        assert "AC Sweep" in result


class TestExportTransientResults:
    def test_basic_export(self):
        data = [
            {"time": 0.0, "out": 0.0, "in": 5.0},
            {"time": 0.001, "out": 2.5, "in": 5.0},
        ]
        result = export_transient_results(data)
        assert "Transient" in result
        assert "time" in result
        assert "out" in result

    def test_all_rows_present(self):
        data = [{"time": i * 0.001, "v1": float(i)} for i in range(10)]
        result = export_transient_results(data)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        data_rows = [r for r in rows if r and not r[0].startswith("#") and r[0] != "time"]
        assert len(data_rows) == 10

    def test_empty_data(self):
        result = export_transient_results([])
        assert "Transient" in result

    def test_parseable_by_pandas_style(self):
        """Verify CSV can be parsed: skip comment rows, read header + data."""
        data = [
            {"time": 0.0, "node1": 1.0},
            {"time": 0.001, "node1": 2.0},
        ]
        result = export_transient_results(data, circuit_name="test.json")
        reader = csv.reader(io.StringIO(result))
        rows = [r for r in reader if r and not r[0].startswith("#")]
        # First non-comment, non-empty row should be header
        assert rows[0] == ["time", "node1"]
        assert rows[1] == ["0.0", "1.0"]
        assert rows[2] == ["0.001", "2.0"]


class TestWriteCsv:
    def test_writes_file(self, tmp_path):
        filepath = tmp_path / "test.csv"
        write_csv("a,b\n1,2\n", str(filepath))
        assert filepath.exists()
        assert filepath.read_text() == "a,b\n1,2\n"

    def test_round_trip(self, tmp_path):
        data = [{"time": 0.0, "v1": 5.0}]
        csv_content = export_transient_results(data)
        filepath = tmp_path / "export.csv"
        write_csv(csv_content, str(filepath))
        content = filepath.read_text()
        assert "time" in content
        assert "5.0" in content


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import simulation.csv_exporter as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
