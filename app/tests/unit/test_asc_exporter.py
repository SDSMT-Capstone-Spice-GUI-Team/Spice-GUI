"""Tests for LTspice .asc schematic export."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from simulation.asc_exporter import export_asc, write_asc


def _make_rc_circuit():
    """Build a simple RC circuit for testing."""
    model = CircuitModel()
    r1 = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 100.0),
        rotation=0,
    )
    c1 = ComponentData(
        component_id="C1",
        component_type="Capacitor",
        value="1u",
        position=(250.0, 100.0),
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
    model.add_component(c1)
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
    model.add_wire(
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="C1",
            end_terminal=0,
        )
    )
    model.add_wire(
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        )
    )
    model.analysis_type = "Transient"
    model.analysis_params = {"duration": "10m", "step": "10u"}
    return model


class TestExportAsc:
    def test_header(self):
        model = CircuitModel()
        content = export_asc(model)
        assert content.startswith("Version 4")
        assert "SHEET 1" in content

    def test_component_symbols(self):
        model = _make_rc_circuit()
        content = export_asc(model)
        assert "SYMBOL res" in content
        assert "SYMBOL cap" in content
        assert "SYMBOL voltage" in content

    def test_component_names(self):
        model = _make_rc_circuit()
        content = export_asc(model)
        assert "SYMATTR InstName R1" in content
        assert "SYMATTR InstName C1" in content
        assert "SYMATTR InstName V1" in content

    def test_component_values(self):
        model = _make_rc_circuit()
        content = export_asc(model)
        assert "SYMATTR Value 1k" in content
        assert "SYMATTR Value 1u" in content
        assert "SYMATTR Value 5" in content

    def test_wires(self):
        model = _make_rc_circuit()
        content = export_asc(model)
        wire_lines = [l for l in content.split("\n") if l.startswith("WIRE")]
        assert len(wire_lines) >= 3

    def test_ground_as_flag(self):
        model = _make_rc_circuit()
        content = export_asc(model)
        assert "FLAG" in content
        # Ground should not appear as SYMBOL
        lines = content.split("\n")
        symbol_lines = [l for l in lines if l.startswith("SYMBOL")]
        for sl in symbol_lines:
            assert "Ground" not in sl

    def test_analysis_directive(self):
        model = _make_rc_circuit()
        content = export_asc(model)
        assert ".tran 10m" in content

    def test_dc_op_directive(self):
        model = CircuitModel()
        model.analysis_type = "DC Operating Point"
        model.analysis_params = {}
        content = export_asc(model)
        assert ".op" in content

    def test_ac_sweep_directive(self):
        model = CircuitModel()
        model.analysis_type = "AC Sweep"
        model.analysis_params = {
            "sweep_type": "dec",
            "points": "100",
            "fStart": "1",
            "fStop": "1Meg",
        }
        content = export_asc(model)
        assert ".ac dec 100 1 1Meg" in content

    def test_dc_sweep_directive(self):
        model = CircuitModel()
        model.analysis_type = "DC Sweep"
        model.analysis_params = {
            "source": "V1",
            "min": "0",
            "max": "5",
            "step": "0.1",
        }
        content = export_asc(model)
        assert ".dc V1 0 5 0.1" in content

    def test_empty_model(self):
        model = CircuitModel()
        content = export_asc(model)
        assert "Version 4" in content

    def test_rotation_code(self):
        model = CircuitModel()
        r1 = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100.0, 100.0),
            rotation=90,
        )
        model.add_component(r1)
        content = export_asc(model)
        assert "R90" in content

    def test_flip_produces_mirror_code(self):
        model = CircuitModel()
        r1 = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100.0, 100.0),
            rotation=0,
            flip_h=True,
        )
        model.add_component(r1)
        content = export_asc(model)
        assert "M0" in content


class TestWriteAsc:
    def test_writes_file(self, tmp_path):
        path = tmp_path / "circuit.asc"
        write_asc("Version 4\nSHEET 1 880 680\n", str(path))
        assert path.exists()
        content = path.read_text()
        assert "Version 4" in content

    def test_round_trip_to_file(self, tmp_path):
        model = _make_rc_circuit()
        content = export_asc(model)
        path = tmp_path / "test.asc"
        write_asc(content, str(path))
        assert path.stat().st_size > 0
        text = path.read_text()
        assert "SYMBOL res" in text
        assert "WIRE" in text


class TestImportExportRoundTrip:
    def test_basic_round_trip(self):
        """Export → re-import should preserve component names and types."""
        from simulation.asc_parser import import_asc

        model = _make_rc_circuit()
        asc_text = export_asc(model)

        reimported, _analysis, _warnings = import_asc(asc_text)

        # Check component names are preserved
        original_ids = {cid for cid in model.components if model.components[cid].component_type != "Ground"}
        reimported_ids = {cid for cid in reimported.components if reimported.components[cid].component_type != "Ground"}
        assert original_ids == reimported_ids

    def test_values_preserved(self):
        from simulation.asc_parser import import_asc

        model = _make_rc_circuit()
        asc_text = export_asc(model)
        reimported, _, _ = import_asc(asc_text)

        assert reimported.components["R1"].value == "1k"
        assert reimported.components["C1"].value == "1u"

    def test_analysis_preserved(self):
        from simulation.asc_parser import import_asc

        model = _make_rc_circuit()
        asc_text = export_asc(model)
        _, analysis, _ = import_asc(asc_text)

        assert analysis is not None
        assert analysis["type"] == "Transient"


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import simulation.asc_exporter as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source
