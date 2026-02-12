"""Tests for SVG metadata injection and extraction."""

import json

import pytest
from simulation.svg_metadata import extract_metadata, has_metadata, inject_metadata

MINIMAL_SVG = """\
<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect x="10" y="10" width="80" height="40" fill="blue"/>
</svg>
"""

CIRCUIT_DATA = {
    "components": [
        {
            "id": "R1",
            "type": "Resistor",
            "value": "1k",
            "pos": {"x": 100, "y": 200},
        }
    ],
    "wires": [],
    "counters": {"Resistor": 1},
}


class TestInjectMetadata:
    def test_injects_into_svg(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), CIRCUIT_DATA)
        content = svg.read_text()
        assert "circuit-data" in content

    def test_svg_still_valid(self, tmp_path):
        import xml.etree.ElementTree as ET

        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), CIRCUIT_DATA)
        tree = ET.parse(str(svg))
        root = tree.getroot()
        assert root.tag.endswith("svg")

    def test_preserves_original_content(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), CIRCUIT_DATA)
        content = svg.read_text()
        assert "rect" in content
        assert 'fill="blue"' in content

    def test_replaces_existing_metadata(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), {"components": [], "wires": []})
        inject_metadata(str(svg), CIRCUIT_DATA)
        data = extract_metadata(str(svg))
        assert len(data["components"]) == 1


class TestExtractMetadata:
    def test_extracts_injected_data(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), CIRCUIT_DATA)
        data = extract_metadata(str(svg))
        assert data is not None
        assert data["components"][0]["id"] == "R1"
        assert data["components"][0]["value"] == "1k"

    def test_returns_none_for_no_metadata(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        data = extract_metadata(str(svg))
        assert data is None

    def test_round_trip_preserves_data(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), CIRCUIT_DATA)
        extracted = extract_metadata(str(svg))
        assert extracted == CIRCUIT_DATA


class TestHasMetadata:
    def test_true_when_present(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        inject_metadata(str(svg), CIRCUIT_DATA)
        assert has_metadata(str(svg)) is True

    def test_false_when_absent(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(MINIMAL_SVG)
        assert has_metadata(str(svg)) is False

    def test_false_for_non_svg(self, tmp_path):
        txt = tmp_path / "not_svg.txt"
        txt.write_text("hello world")
        assert has_metadata(str(txt)) is False


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import simulation.svg_metadata as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
