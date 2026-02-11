"""Tests for simulation/circuitikz_exporter.py — CircuiTikZ LaTeX export."""

import math

from models.circuit import CircuitModel
from models.component import ComponentData
from models.node import NodeData
from models.wire import WireData
from simulation.circuitikz_exporter import (
    CIRCUITIKZ_BIPOLES,
    CIRCUITIKZ_TRIPOLES,
    _coord,
    _escape_latex,
    _fmt,
    _transform_coords,
    generate,
)


def _simple_circuit():
    """Build a minimal R-C series circuit for testing."""
    model = CircuitModel()
    model.add_component(
        ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100, 100),
        )
    )
    model.add_component(
        ComponentData(
            component_id="C1",
            component_type="Capacitor",
            value="100n",
            position=(200, 100),
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
    model.rebuild_nodes()
    return model


class TestFormatHelpers:
    def test_fmt_integer(self):
        assert _fmt(3.0) == "3"

    def test_fmt_float(self):
        assert _fmt(2.5) == "2.5"

    def test_fmt_trailing_zeros(self):
        assert _fmt(1.10) == "1.1"

    def test_coord(self):
        assert _coord(1, 2) == "(1, 2)"

    def test_escape_latex_special_chars(self):
        assert _escape_latex("R_1") == "R\\_1"
        assert _escape_latex("100%") == "100\\%"
        assert _escape_latex("a&b") == "a\\&b"


class TestCoordinateTransform:
    def test_transform_normalizes_origin(self):
        comps = {
            "R1": ComponentData("R1", "Resistor", "1k", position=(100, 200)),
            "R2": ComponentData("R2", "Resistor", "2k", position=(200, 100)),
        }
        transform = _transform_coords(comps, scale=20.0)
        # R1 at (100,200): tx = (100-100)/20 = 0, ty = (200-200)/20 = 0
        assert transform(100, 200) == (0.0, 0.0)
        # R2 at (200,100): tx = (200-100)/20 = 5, ty = (200-100)/20 = 5
        assert transform(200, 100) == (5.0, 5.0)

    def test_transform_flips_y(self):
        comps = {
            "R1": ComponentData("R1", "Resistor", "1k", position=(0, 0)),
            "R2": ComponentData("R2", "Resistor", "2k", position=(0, 40)),
        }
        transform = _transform_coords(comps, scale=20.0)
        # Top point (0,0) should be at TikZ y=2 (highest), bottom (0,40) at y=0
        assert transform(0, 0) == (0.0, 2.0)
        assert transform(0, 40) == (0.0, 0.0)

    def test_transform_empty_components(self):
        transform = _transform_coords({}, scale=20.0)
        assert transform(100, 100) == (0.0, 0.0)


class TestStandaloneOutput:
    def test_standalone_has_documentclass(self):
        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            standalone=True,
        )
        assert r"\documentclass" in output
        assert r"\usepackage" in output
        assert r"\begin{document}" in output
        assert r"\end{document}" in output

    def test_non_standalone_omits_preamble(self):
        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            standalone=False,
        )
        assert r"\documentclass" not in output
        assert r"\begin{circuitikz}" in output
        assert r"\end{circuitikz}" in output

    def test_circuit_name_in_comment(self):
        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            circuit_name="test.circ",
        )
        assert "% Circuit: test.circ" in output


class TestBipoleExport:
    def test_resistor_draw(self):
        model = CircuitModel()
        model.add_component(ComponentData("R1", "Resistor", "1k", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert "to[R" in output
        assert "R1" in output
        assert "1k" in output

    def test_capacitor_draw(self):
        model = CircuitModel()
        model.add_component(ComponentData("C1", "Capacitor", "100n", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert "to[C" in output

    def test_voltage_source_draw(self):
        model = CircuitModel()
        model.add_component(ComponentData("V1", "Voltage Source", "5", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert "to[V" in output

    def test_diode_draw(self):
        model = CircuitModel()
        model.add_component(ComponentData("D1", "Diode", "1N4148", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert "to[D" in output

    def test_all_bipole_types_mapped(self):
        """Ensure every bipole type has a CircuiTikZ mapping."""
        expected_bipoles = {
            "Resistor",
            "Capacitor",
            "Inductor",
            "Voltage Source",
            "Current Source",
            "Waveform Source",
            "Diode",
            "LED",
            "Zener Diode",
            "VC Switch",
            "VCVS",
            "VCCS",
            "CCVS",
            "CCCS",
        }
        assert set(CIRCUITIKZ_BIPOLES.keys()) == expected_bipoles


class TestTripoleExport:
    def test_npn_node(self):
        model = CircuitModel()
        model.add_component(ComponentData("Q1", "BJT NPN", "2N3904", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert r"\node[npn" in output
        assert "(Q1)" in output
        assert "Q1.C" in output
        assert "Q1.B" in output
        assert "Q1.E" in output

    def test_opamp_node(self):
        model = CircuitModel()
        model.add_component(ComponentData("OA1", "Op-Amp", "Ideal", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert r"\node[op amp" in output
        assert "OA1.-" in output or "OA1.+" in output

    def test_all_tripole_types_mapped(self):
        """Ensure every tripole type has a CircuiTikZ mapping."""
        expected_tripoles = {
            "BJT NPN",
            "BJT PNP",
            "MOSFET NMOS",
            "MOSFET PMOS",
            "Op-Amp",
        }
        assert set(CIRCUITIKZ_TRIPOLES.keys()) == expected_tripoles


class TestGroundExport:
    def test_ground_symbol(self):
        model = CircuitModel()
        model.add_component(ComponentData("GND1", "Ground", "", position=(100, 200)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert r"\node[ground]" in output


class TestWireExport:
    def test_wire_draw(self):
        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        # Should have a wire section
        assert "% Wires" in output
        assert "\\draw" in output

    def test_wire_with_waypoints(self):
        model = CircuitModel()
        model.add_component(ComponentData("R1", "Resistor", "1k", position=(100, 100)))
        model.add_component(ComponentData("R2", "Resistor", "2k", position=(100, 200)))
        model.add_wire(
            WireData(
                start_component_id="R1",
                start_terminal=1,
                end_component_id="R2",
                end_terminal=0,
                waypoints=[(130, 100), (130, 200)],
            )
        )
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert " -- " in output  # waypoint segments


class TestNetLabels:
    def test_custom_label_exported(self):
        model = _simple_circuit()
        # Set a custom label on the node between R1 and C1
        for node in model.nodes:
            if ("R1", 1) in node.terminals:
                node.set_custom_label("Vmid")
                break
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            include_net_labels=True,
        )
        assert "Vmid" in output
        assert "% Net labels" in output

    def test_no_labels_when_disabled(self):
        model = _simple_circuit()
        for node in model.nodes:
            if ("R1", 1) in node.terminals:
                node.set_custom_label("Vmid")
                break
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            include_net_labels=False,
        )
        assert "Vmid" not in output


class TestLabelOptions:
    def test_no_ids_when_disabled(self):
        model = CircuitModel()
        model.add_component(ComponentData("R1", "Resistor", "1k", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            include_ids=False,
        )
        assert "l=$R1$" not in output

    def test_no_values_when_disabled(self):
        model = CircuitModel()
        model.add_component(ComponentData("R1", "Resistor", "1k", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            include_values=False,
        )
        assert "1k" not in output


class TestEuropeanStyle:
    def test_european_ctikzset(self):
        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            style="european",
        )
        assert r"\ctikzset{european}" in output

    def test_american_no_ctikzset(self):
        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            style="american",
        )
        assert r"\ctikzset{european}" not in output


class TestFourTerminalExport:
    def test_vcvs_exports_output_and_control(self):
        model = CircuitModel()
        model.add_component(ComponentData("E1", "VCVS", "10", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert "american controlled voltage source" in output
        assert "dashed" in output  # control pair drawn dashed

    def test_vc_switch_exports(self):
        model = CircuitModel()
        model.add_component(ComponentData("S1", "VC Switch", "VON=1 VOFF=0", position=(100, 100)))
        model.rebuild_nodes()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )
        assert "closing switch" in output


class TestCompleteCircuit:
    def test_voltage_divider_compiles_structure(self):
        """Full voltage divider: V1, R1, R2, GND with wires."""
        model = CircuitModel()
        model.add_component(ComponentData("V1", "Voltage Source", "5", position=(0, 100)))
        model.add_component(ComponentData("R1", "Resistor", "1k", position=(100, 0)))
        model.add_component(ComponentData("R2", "Resistor", "2k", position=(100, 200)))
        model.add_component(ComponentData("GND1", "Ground", "", position=(0, 300)))
        # Wire V1:1 -> R1:0
        model.add_wire(WireData("V1", 1, "R1", 0))
        # Wire R1:1 -> R2:0
        model.add_wire(WireData("R1", 1, "R2", 0))
        # Wire R2:1 -> GND1:0
        model.add_wire(WireData("R2", 1, "GND1", 0))
        # Wire GND1:0 -> V1:0
        model.add_wire(WireData("GND1", 0, "V1", 0))
        model.rebuild_nodes()

        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
        )

        # Should contain all components
        assert "to[V" in output
        assert "to[R" in output
        assert r"\node[ground]" in output
        # Should have valid structure
        assert r"\begin{circuitikz}" in output
        assert r"\end{circuitikz}" in output
        # Should have wire connections
        assert "% Wires" in output


class TestScaleParameter:
    def test_custom_scale(self):
        model = CircuitModel()
        model.add_component(ComponentData("R1", "Resistor", "1k", position=(0, 0)))
        model.add_component(ComponentData("R2", "Resistor", "2k", position=(40, 0)))
        model.rebuild_nodes()

        output_20 = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            scale=20.0,
        )
        output_40 = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            scale=40.0,
        )
        # With scale=40, coordinates should be half of scale=20
        # Both should generate valid output
        assert r"\begin{circuitikz}" in output_20
        assert r"\begin{circuitikz}" in output_40


class TestOptionsDialog:
    """Tests for CircuiTikZOptionsDialog (requires Qt offscreen)."""

    def test_default_options(self, qtbot):
        from GUI.circuitikz_options_dialog import CircuiTikZOptionsDialog

        dialog = CircuiTikZOptionsDialog()
        qtbot.addWidget(dialog)
        opts = dialog.get_options()
        assert opts["style"] == "american"
        assert opts["scale"] == 20.0
        assert opts["include_ids"] is True
        assert opts["include_values"] is True
        assert opts["include_net_labels"] is True
        assert opts["standalone"] is True

    def test_european_style_option(self, qtbot):
        from GUI.circuitikz_options_dialog import CircuiTikZOptionsDialog

        dialog = CircuiTikZOptionsDialog()
        qtbot.addWidget(dialog)
        dialog.style_combo.setCurrentIndex(1)  # European
        opts = dialog.get_options()
        assert opts["style"] == "european"

    def test_scale_option(self, qtbot):
        from GUI.circuitikz_options_dialog import CircuiTikZOptionsDialog

        dialog = CircuiTikZOptionsDialog()
        qtbot.addWidget(dialog)
        dialog.scale_spin.setValue(40.0)
        opts = dialog.get_options()
        assert opts["scale"] == 40.0

    def test_uncheck_labels(self, qtbot):
        from GUI.circuitikz_options_dialog import CircuiTikZOptionsDialog

        dialog = CircuiTikZOptionsDialog()
        qtbot.addWidget(dialog)
        dialog.include_ids_cb.setChecked(False)
        dialog.include_values_cb.setChecked(False)
        dialog.include_net_labels_cb.setChecked(False)
        opts = dialog.get_options()
        assert opts["include_ids"] is False
        assert opts["include_values"] is False
        assert opts["include_net_labels"] is False

    def test_non_standalone_option(self, qtbot):
        from GUI.circuitikz_options_dialog import CircuiTikZOptionsDialog

        dialog = CircuiTikZOptionsDialog()
        qtbot.addWidget(dialog)
        dialog.standalone_cb.setChecked(False)
        opts = dialog.get_options()
        assert opts["standalone"] is False

    def test_options_round_trip_through_generate(self, qtbot):
        """Verify that options from the dialog produce correct output when passed to generate()."""
        from GUI.circuitikz_options_dialog import CircuiTikZOptionsDialog

        dialog = CircuiTikZOptionsDialog()
        qtbot.addWidget(dialog)
        dialog.style_combo.setCurrentIndex(1)  # European
        dialog.include_ids_cb.setChecked(False)
        dialog.standalone_cb.setChecked(False)
        opts = dialog.get_options()

        model = _simple_circuit()
        output = generate(
            model.components,
            model.wires,
            model.nodes,
            model.terminal_to_node,
            **opts,
        )
        assert r"\ctikzset{european}" not in output  # non-standalone has no preamble
        assert r"\documentclass" not in output
        assert "l=$R1$" not in output
