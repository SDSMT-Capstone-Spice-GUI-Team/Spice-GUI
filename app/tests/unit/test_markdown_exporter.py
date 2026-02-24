"""Tests for Markdown table export of simulation results."""

from simulation.markdown_exporter import (
    export_ac_results,
    export_dc_sweep_results,
    export_noise_results,
    export_op_results,
    export_transient_results,
    write_markdown,
)


class TestExportOpResults:
    def test_contains_table_header(self):
        md = export_op_results({"nodeA": 5.0})
        assert "| Node | Voltage (V) |" in md

    def test_contains_node_data(self):
        md = export_op_results({"nodeA": 5.0, "nodeB": 3.3})
        assert "nodeA" in md
        assert "nodeB" in md
        assert "5" in md
        assert "3.3" in md

    def test_sorted_by_node_name(self):
        md = export_op_results({"nodeC": 1.0, "nodeA": 2.0, "nodeB": 3.0})
        pos_a = md.index("nodeA")
        pos_b = md.index("nodeB")
        pos_c = md.index("nodeC")
        assert pos_a < pos_b < pos_c

    def test_metadata_comment(self):
        md = export_op_results({}, circuit_name="test.json")
        assert "<!-- Analysis: DC Operating Point -->" in md
        assert "<!-- Circuit: test.json -->" in md

    def test_pipe_table_format(self):
        md = export_op_results({"n1": 1.0})
        lines = md.strip().split("\n")
        table_lines = [l for l in lines if l.startswith("|")]
        assert len(table_lines) >= 3  # header, separator, data row
        assert ":---" in table_lines[1] or "---:" in table_lines[1]

    def test_significant_figures(self):
        md = export_op_results({"n1": 1.23456789})
        assert "1.23457" in md  # 6 significant figures

    def test_empty_results(self):
        md = export_op_results({})
        assert "| Node | Voltage (V) |" in md


class TestExportDcSweepResults:
    def test_contains_headers(self):
        data = {"headers": ["V1", "V(out)"], "data": [[1.0, 2.0]]}
        md = export_dc_sweep_results(data)
        assert "| V1 | V(out) |" in md

    def test_contains_data_rows(self):
        data = {"headers": ["V1", "V(out)"], "data": [[1.0, 2.5], [2.0, 3.5]]}
        md = export_dc_sweep_results(data)
        assert "2.5" in md
        assert "3.5" in md

    def test_right_aligned_numeric(self):
        data = {"headers": ["V1"], "data": [[1.0]]}
        md = export_dc_sweep_results(data)
        assert "---:" in md

    def test_empty_data(self):
        data = {"headers": ["V1"], "data": []}
        md = export_dc_sweep_results(data)
        assert "| V1 |" in md


class TestExportAcResults:
    def test_contains_frequency_header(self):
        data = {"frequencies": [100.0], "magnitude": {"out": [1.0]}, "phase": {"out": [45.0]}}
        md = export_ac_results(data)
        assert "Frequency (Hz)" in md

    def test_contains_mag_and_phase(self):
        data = {"frequencies": [100.0], "magnitude": {"out": [1.0]}, "phase": {"out": [45.0]}}
        md = export_ac_results(data)
        assert "|V(out)|" in md
        assert "phase(V(out))" in md

    def test_data_values(self):
        data = {"frequencies": [1000.0], "magnitude": {"out": [0.707]}, "phase": {"out": [-45.0]}}
        md = export_ac_results(data)
        assert "1000" in md
        assert "0.707" in md
        assert "-45" in md


class TestExportTransientResults:
    def test_contains_time_header(self):
        data = [{"time": 0.0, "V(out)": 1.0}]
        md = export_transient_results(data)
        assert "time" in md
        assert "V(out)" in md

    def test_data_rows(self):
        data = [{"time": 0.001, "V(out)": 2.5}, {"time": 0.002, "V(out)": 3.0}]
        md = export_transient_results(data)
        assert "0.001" in md
        assert "2.5" in md

    def test_empty_data(self):
        md = export_transient_results([])
        assert "_No data._" in md


class TestExportNoiseResults:
    def test_contains_headers(self):
        data = {"frequencies": [100.0], "onoise_spectrum": [1e-6], "inoise_spectrum": [2e-6]}
        md = export_noise_results(data)
        assert "Frequency (Hz)" in md
        assert "Output Noise" in md
        assert "Input Noise" in md

    def test_data_values(self):
        data = {"frequencies": [1000.0], "onoise_spectrum": [1.5e-6], "inoise_spectrum": []}
        md = export_noise_results(data)
        assert "1000" in md
        assert "1.5e-06" in md

    def test_omits_empty_columns(self):
        data = {"frequencies": [100.0], "onoise_spectrum": [1e-6], "inoise_spectrum": []}
        md = export_noise_results(data)
        assert "Output Noise" in md
        assert "Input Noise" not in md


class TestWriteMarkdown:
    def test_writes_file(self, tmp_path):
        path = tmp_path / "results.md"
        write_markdown("# Test\n\n| A |\n", str(path))
        assert path.exists()
        assert path.read_text() == "# Test\n\n| A |\n"


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import simulation.markdown_exporter as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
