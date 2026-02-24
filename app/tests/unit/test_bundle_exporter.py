"""Tests for ZIP bundle exporter."""

import json
import zipfile

from simulation.bundle_exporter import create_bundle, suggest_bundle_name


class TestCreateBundle:
    def test_creates_valid_zip(self, tmp_path):
        path = tmp_path / "bundle.zip"
        create_bundle(str(path), circuit_json={"components": []})
        assert path.exists()
        assert zipfile.is_zipfile(str(path))

    def test_includes_circuit_json(self, tmp_path):
        path = tmp_path / "bundle.zip"
        circuit = {"components": [{"id": "R1"}], "wires": []}
        included = create_bundle(str(path), circuit_json=circuit)
        assert "circuit.json" in included
        with zipfile.ZipFile(str(path)) as zf:
            data = json.loads(zf.read("circuit.json"))
            assert data["components"][0]["id"] == "R1"

    def test_includes_netlist(self, tmp_path):
        path = tmp_path / "bundle.zip"
        included = create_bundle(str(path), circuit_json={}, netlist="* SPICE netlist\n.end\n")
        assert "netlist.cir" in included
        with zipfile.ZipFile(str(path)) as zf:
            assert b".end" in zf.read("netlist.cir")

    def test_includes_schematic_png(self, tmp_path):
        path = tmp_path / "bundle.zip"
        # Minimal PNG header bytes
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        included = create_bundle(str(path), circuit_json={}, schematic_png=png_bytes)
        assert "schematic.png" in included
        with zipfile.ZipFile(str(path)) as zf:
            assert zf.read("schematic.png").startswith(b"\x89PNG")

    def test_includes_results_csv(self, tmp_path):
        path = tmp_path / "bundle.zip"
        included = create_bundle(str(path), circuit_json={}, results_csv="Node,Voltage\nn1,5.0\n")
        assert "results.csv" in included

    def test_includes_results_xlsx(self, tmp_path):
        path = tmp_path / "bundle.zip"
        # Create a fake xlsx file
        xlsx_path = tmp_path / "temp_results.xlsx"
        xlsx_path.write_bytes(b"PK\x03\x04fake xlsx content")
        included = create_bundle(str(path), circuit_json={}, results_xlsx_path=str(xlsx_path))
        assert "results.xlsx" in included

    def test_includes_report_pdf(self, tmp_path):
        path = tmp_path / "bundle.zip"
        pdf_bytes = b"%PDF-1.4 fake pdf"
        included = create_bundle(str(path), circuit_json={}, report_pdf=pdf_bytes)
        assert "report.pdf" in included

    def test_skips_none_items(self, tmp_path):
        path = tmp_path / "bundle.zip"
        included = create_bundle(
            str(path),
            circuit_json={"components": []},
            netlist=None,
            schematic_png=None,
            results_csv=None,
            results_xlsx_path=None,
            report_pdf=None,
        )
        assert included == ["circuit.json"]

    def test_all_items_together(self, tmp_path):
        path = tmp_path / "bundle.zip"
        xlsx_path = tmp_path / "r.xlsx"
        xlsx_path.write_bytes(b"PK\x03\x04fake")
        included = create_bundle(
            str(path),
            circuit_json={"c": []},
            netlist="* net\n",
            schematic_png=b"\x89PNG...",
            results_csv="a,b\n1,2\n",
            results_xlsx_path=str(xlsx_path),
            report_pdf=b"%PDF",
        )
        assert len(included) == 6
        with zipfile.ZipFile(str(path)) as zf:
            assert set(zf.namelist()) == {
                "circuit.json",
                "netlist.cir",
                "schematic.png",
                "results.csv",
                "results.xlsx",
                "report.pdf",
            }

    def test_circuit_json_as_string(self, tmp_path):
        path = tmp_path / "bundle.zip"
        create_bundle(str(path), circuit_json='{"components":[]}')
        with zipfile.ZipFile(str(path)) as zf:
            data = json.loads(zf.read("circuit.json"))
            assert "components" in data


class TestSuggestBundleName:
    def test_default_name(self):
        name = suggest_bundle_name()
        assert name.startswith("circuit_")
        assert name.endswith(".zip")

    def test_with_circuit_name(self):
        name = suggest_bundle_name("my_circuit.json")
        assert name.startswith("my_circuit_")
        assert name.endswith(".zip")

    def test_sanitizes_special_chars(self):
        name = suggest_bundle_name("my circuit (v2).json")
        assert " " not in name
        assert "(" not in name


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import simulation.bundle_exporter as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
