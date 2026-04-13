"""Tests for narrowed exception catches (issue #770).

Verify that unexpected exceptions (e.g. RuntimeError, AttributeError) propagate
instead of being silently swallowed by overly broad except clauses.
"""

import json

import pytest
from models.circuit import CircuitModel


class TestCircuitFromDictPropagatesUnexpected:
    """CircuitModel.from_dict should only catch data-corruption exceptions."""

    def test_corrupt_component_caught(self):
        """ValueError/KeyError/TypeError from bad component data is caught."""
        data = {"components": [None], "wires": [], "counters": {}}
        model = CircuitModel.from_dict(data)
        assert len(model.components) == 0  # skipped, not crashed

    def test_corrupt_wire_caught(self):
        """ValueError/KeyError/TypeError from bad wire data is caught."""
        data = {"components": [], "wires": ["not-a-dict"], "counters": {}}
        model = CircuitModel.from_dict(data)
        assert len(model.wires) == 0

    def test_corrupt_annotation_caught(self):
        """ValueError/TypeError/AttributeError from bad annotation data is caught."""
        data = {"components": [], "wires": [], "annotations": [None], "counters": {}}
        model = CircuitModel.from_dict(data)
        assert len(model.annotations) == 0


class TestSvgShareablePropagatesUnexpected:
    """svg_shareable should only catch base64/JSON decode errors."""

    def test_corrupt_base64_raises_valueerror(self):
        """Invalid base64 in SVG raises ValueError, not silently ignored."""
        from simulation.svg_shareable import extract_circuit_data_from_string

        svg = '<svg><metadata xmlns:spice-gui="urn:spice-gui"><spice-gui:circuit>!!!not-base64!!!</spice-gui:circuit></metadata></svg>'
        with pytest.raises(ValueError, match="Corrupt circuit data"):
            extract_circuit_data_from_string(svg)

    def test_corrupt_json_raises_valueerror(self):
        """Valid base64 but invalid JSON raises ValueError."""
        import base64

        from simulation.svg_shareable import extract_circuit_data_from_string

        bad_json = base64.b64encode(b"not json").decode()
        svg = f'<svg><metadata xmlns:spice-gui="urn:spice-gui"><spice-gui:circuit>{bad_json}</spice-gui:circuit></metadata></svg>'
        with pytest.raises(ValueError, match="Corrupt circuit data"):
            extract_circuit_data_from_string(svg)


class TestSubcircuitLibraryLoadPropagatesUnexpected:
    """SubcircuitLibrary._load should only catch JSON/OS/value errors."""

    def test_invalid_json_file_skipped(self, tmp_path):
        """A .json file with invalid JSON is skipped, not crashed."""
        from models.subcircuit_library import SubcircuitLibrary

        lib_dir = tmp_path / "subcircuits"
        lib_dir.mkdir()
        (lib_dir / "bad.json").write_text("not valid json", encoding="utf-8")

        lib = SubcircuitLibrary(library_dir=lib_dir)
        # bad.json was skipped; only built-in subcircuits should be present
        assert "bad" not in [n.lower() for n in lib.names()]
