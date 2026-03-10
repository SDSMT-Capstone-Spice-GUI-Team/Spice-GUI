"""Tests for sensitivity analysis — netlist generation and result parsing."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from simulation import NetlistGenerator, ResultParser


def _build_divider_model(analysis_type="Sensitivity", analysis_params=None):
    """Build a simple V1-R1-R2-GND resistor divider for testing."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5V",
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 0.0),
    )
    model.components["R2"] = ComponentData(
        component_id="R2",
        component_type="Resistor",
        value="1k",
        position=(100.0, 100.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 200.0),
    )
    model.wires = [
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="R1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="R2",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R2",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="GND1",
            end_terminal=0,
        ),
    ]
    model.analysis_type = analysis_type
    model.analysis_params = analysis_params or {"output_node": "2"}
    model.rebuild_nodes()
    return model


class TestSensitivityNetlist:
    """Netlist snapshot tests for .sens directive generation."""

    def test_sens_directive_present(self):
        model = _build_divider_model()
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        assert ".sens v(2)" in netlist.lower()

    def test_sens_directive_with_named_node(self):
        model = _build_divider_model(analysis_params={"output_node": "out"})
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        assert ".sens v(out)" in netlist.lower()

    def test_sens_netlist_has_control_block(self):
        model = _build_divider_model()
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        assert ".control" in netlist
        assert "run" in netlist
        assert ".endc" in netlist
        assert ".end" in netlist


class TestParseSensitivityResults:
    """Test parsing of ngspice .sens output."""

    SAMPLE_OUTPUT = """
No. of Data Rows : 7

dc sensitivity of node voltage v(2)

dc sensitivities of output v(2)

element              element       element       normalized
name                 value         sensitivity   sensitivity
                                   (volts/unit)  (volts/percent)

r1                   1.000e+03    -2.500e-04    -2.500e-01
r2                   1.000e+03     2.500e-04     2.500e-01
v1                   5.000e+00     5.000e-01     2.500e+00
"""

    def test_parses_three_elements(self):
        results = ResultParser.parse_sensitivity_results(self.SAMPLE_OUTPUT)
        assert results is not None
        assert len(results) == 3

    def test_element_names(self):
        results = ResultParser.parse_sensitivity_results(self.SAMPLE_OUTPUT)
        names = [r["element"] for r in results]
        assert "r1" in names
        assert "r2" in names
        assert "v1" in names

    def test_sensitivity_values(self):
        results = ResultParser.parse_sensitivity_results(self.SAMPLE_OUTPUT)
        r1 = next(r for r in results if r["element"] == "r1")
        assert r1["value"] == pytest.approx(1000.0)
        assert r1["sensitivity"] == pytest.approx(-2.5e-4)
        assert r1["normalized_sensitivity"] == pytest.approx(-0.25)

    def test_empty_output_returns_none(self):
        assert ResultParser.parse_sensitivity_results("") is None

    def test_no_sensitivity_section_returns_none(self):
        output = "some random ngspice output\nv(1) = 5.0\n"
        assert ResultParser.parse_sensitivity_results(output) is None

    def test_single_element(self):
        output = """
dc sensitivities of output v(out)

element              element       element       normalized
name                 value         sensitivity   sensitivity
                                   (volts/unit)  (volts/percent)

r1                   1.000e+03     1.000e-03     1.000e+00
"""
        results = ResultParser.parse_sensitivity_results(output)
        assert results is not None
        assert len(results) == 1
        assert results[0]["element"] == "r1"


class TestSensitivityControllerWiring:
    """Test that the controller correctly routes Sensitivity analysis."""

    def test_controller_generates_sensitivity_netlist(self):
        from controllers.simulation_controller import SimulationController

        model = _build_divider_model()
        ctrl = SimulationController(model)
        netlist = ctrl.generate_netlist()
        assert ".sens v(2)" in netlist.lower()
