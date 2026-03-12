"""Tests for shareable SVG export/import (#748).

Verifies that circuit data can be embedded in SVG files and extracted
back, and that the UI wiring for SVG import is in place.
"""

import inspect
import json

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from simulation.svg_shareable import embed_circuit_data, extract_circuit_data, extract_circuit_data_from_string


def _make_simple_circuit():
    """Build a simple circuit for round-trip testing."""
    model = CircuitModel()
    r1 = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 100.0),
        rotation=0,
    )
    v1 = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5",
        position=(0.0, 100.0),
        rotation=0,
    )
    gnd = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 300.0),
    )
    model.add_component(r1)
    model.add_component(v1)
    model.add_component(gnd)
    model.add_wire(
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="R1",
            end_terminal=0,
        )
    )
    model.analysis_type = "Transient"
    model.analysis_params = {"duration": "10m", "step": "10u"}
    return model


_MINIMAL_SVG = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">\n'
    '<rect x="10" y="10" width="100" height="80" fill="none" stroke="black"/>\n'
    "</svg>\n"
)


class TestEmbedCircuitData:
    """Test embedding circuit data into SVG files."""

    def test_embed_creates_metadata(self, tmp_path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        content = svg_file.read_text(encoding="utf-8")
        assert "<metadata" in content
        assert "spice-gui:circuit" in content

    def test_embed_preserves_svg_structure(self, tmp_path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        content = svg_file.read_text(encoding="utf-8")
        # Original SVG content should still be present
        assert "<rect" in content
        assert "</svg>" in content

    def test_embed_is_valid_xml(self, tmp_path):
        import xml.etree.ElementTree as ET

        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        content = svg_file.read_text(encoding="utf-8")
        # Should parse without error
        root = ET.fromstring(content)
        assert root.tag.endswith("svg")


class TestExtractCircuitData:
    """Test extracting circuit data from SVG files."""

    def test_round_trip_preserves_components(self, tmp_path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        data = extract_circuit_data(svg_file)
        assert data is not None
        reimported = CircuitModel.from_dict(data)

        original_ids = set(model.components.keys())
        reimported_ids = set(reimported.components.keys())
        assert original_ids == reimported_ids

    def test_round_trip_preserves_values(self, tmp_path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        data = extract_circuit_data(svg_file)
        reimported = CircuitModel.from_dict(data)

        assert reimported.components["R1"].value == "1k"
        assert reimported.components["V1"].value == "5"

    def test_round_trip_preserves_wires(self, tmp_path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        data = extract_circuit_data(svg_file)
        reimported = CircuitModel.from_dict(data)

        assert len(reimported.wires) == len(model.wires)

    def test_round_trip_preserves_analysis(self, tmp_path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        model = _make_simple_circuit()
        embed_circuit_data(svg_file, model)

        data = extract_circuit_data(svg_file)
        assert data["analysis_type"] == "Transient"
        assert data["analysis_params"]["duration"] == "10m"

    def test_extract_returns_none_for_plain_svg(self, tmp_path):
        svg_file = tmp_path / "plain.svg"
        svg_file.write_text(_MINIMAL_SVG, encoding="utf-8")

        data = extract_circuit_data(svg_file)
        assert data is None

    def test_extract_from_string(self):
        model = _make_simple_circuit()
        circuit_dict = model.to_dict()

        import base64

        json_bytes = json.dumps(circuit_dict, separators=(",", ":")).encode("utf-8")
        b64 = base64.b64encode(json_bytes).decode("ascii")

        svg_with_data = _MINIMAL_SVG.replace(
            "<rect",
            f'<metadata xmlns:spice-gui="https://spice-gui.github.io/schema/circuit">'
            f"<spice-gui:circuit>{b64}</spice-gui:circuit>"
            f"</metadata>\n<rect",
        )

        data = extract_circuit_data_from_string(svg_with_data)
        assert data is not None
        assert "components" in data

    def test_extract_raises_on_corrupt_data(self, tmp_path):
        svg_file = tmp_path / "corrupt.svg"
        corrupt_svg = _MINIMAL_SVG.replace(
            "<rect",
            '<metadata xmlns:spice-gui="https://spice-gui.github.io/schema/circuit">'
            "<spice-gui:circuit>NOT-VALID-BASE64!!!</spice-gui:circuit>"
            "</metadata>\n<rect",
        )
        svg_file.write_text(corrupt_svg, encoding="utf-8")

        with pytest.raises(ValueError, match="Corrupt circuit data"):
            extract_circuit_data(svg_file)


class TestSVGShareableInfrastructure:
    """Structural tests verifying the SVG export embeds data and import menu exists."""

    def test_export_image_calls_embed(self):
        """export_image in ViewOperationsMixin should call embed_circuit_data for SVG."""
        from GUI.main_window_view import ViewOperationsMixin

        source = inspect.getsource(ViewOperationsMixin.export_image)
        assert "embed_circuit_data" in source

    def test_import_svg_menu_exists(self):
        """Menu bar should include an 'Import from SVG' action."""
        from GUI.main_window_menus import MenuBarMixin

        source = inspect.getsource(MenuBarMixin.create_menu_bar)
        assert "Import from" in source
        assert "_on_import_svg" in source

    def test_import_svg_handler_exists(self):
        """FileOperationsMixin should have _on_import_svg method."""
        from GUI.main_window_file_ops import FileOperationsMixin

        assert hasattr(FileOperationsMixin, "_on_import_svg")

    def test_file_controller_has_import_svg(self):
        """FileController should have import_svg method."""
        from controllers.file_controller import FileController

        assert hasattr(FileController, "import_svg")

    def test_svg_viewbox_uses_zero_origin(self):
        """SVG export should use a zero-origin viewBox for correct rendering."""
        from GUI.main_window_view import ViewOperationsMixin

        source = inspect.getsource(ViewOperationsMixin.export_image)
        # Should use QRect(0, 0, ...) not source_rect for viewBox
        assert "QRect(0, 0," in source


class TestNoQtDependencies:
    """Ensure svg_shareable.py has no Qt imports."""

    def test_no_pyqt_imports(self):
        from pathlib import Path

        import simulation.svg_shareable as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "PyQt" not in source
        assert "QtCore" not in source
