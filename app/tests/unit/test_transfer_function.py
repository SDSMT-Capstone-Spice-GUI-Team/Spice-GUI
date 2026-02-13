"""
Tests for Transfer Function (.tf) analysis support.

Covers netlist generation, result parsing, and controller wiring.
"""

import pytest
from models.component import ComponentData
from models.node import NodeData
from simulation.netlist_generator import NetlistGenerator
from simulation.result_parser import ResultParser
from tests.conftest import make_component, make_wire

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def divider_circuit():
    """
    Simple resistor divider: V1 → R1 → R2 → GND
    Used for transfer function testing (output at mid-node).
    """
    components = {
        "V1": make_component("Voltage Source", "V1", "10V", (0, 0)),
        "R1": make_component("Resistor", "R1", "1k", (100, 0)),
        "R2": make_component("Resistor", "R2", "1k", (200, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
    }
    wires = [
        make_wire("V1", 0, "R1", 0),
        make_wire("R1", 1, "R2", 0),
        make_wire("R2", 1, "GND1", 0),
        make_wire("V1", 1, "GND1", 0),
    ]
    node_top = NodeData(
        terminals={("V1", 0), ("R1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_mid = NodeData(
        terminals={("R1", 1), ("R2", 0)},
        wire_indices={1},
        auto_label="nodeB",
    )
    node_gnd = NodeData(
        terminals={("R2", 1), ("GND1", 0), ("V1", 1)},
        wire_indices={2, 3},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_top, node_mid, node_gnd]
    t2n = {
        ("V1", 0): node_top,
        ("R1", 0): node_top,
        ("R1", 1): node_mid,
        ("R2", 0): node_mid,
        ("R2", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, nodes, t2n


# ---------------------------------------------------------------------------
# Netlist generation
# ---------------------------------------------------------------------------


class TestTFNetlist:
    def test_tf_directive_generated(self, divider_circuit):
        components, wires, nodes, t2n = divider_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Transfer Function",
            analysis_params={"output_var": "v(nodeB)", "input_source": "V1"},
        )
        netlist = gen.generate()
        assert ".tf v(nodeB) V1" in netlist

    def test_tf_default_params(self, divider_circuit):
        components, wires, nodes, t2n = divider_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Transfer Function",
            analysis_params={},
        )
        netlist = gen.generate()
        assert ".tf v(out) V1" in netlist

    def test_tf_with_current_output(self, divider_circuit):
        components, wires, nodes, t2n = divider_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Transfer Function",
            analysis_params={"output_var": "i(V1)", "input_source": "V1"},
        )
        netlist = gen.generate()
        assert ".tf i(V1) V1" in netlist


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


class TestTFParser:
    def test_parse_standard_output(self):
        output = (
            "Transfer function, output/input = 5.000000e-01\n"
            "Output impedance at v(nodeB) = 5.000000e+02\n"
            "v1#Input impedance = 1.000000e+03\n"
        )
        result = ResultParser.parse_tf_results(output)
        assert result is not None
        assert result["transfer_function"] == pytest.approx(0.5)
        assert result["output_impedance"] == pytest.approx(500.0)
        assert result["input_impedance"] == pytest.approx(1000.0)

    def test_parse_negative_gain(self):
        output = (
            "Transfer function, output/input = -2.500000e+00\n"
            "Output impedance at v(out) = 7.500000e+01\n"
            "v1#Input impedance = 2.000000e+06\n"
        )
        result = ResultParser.parse_tf_results(output)
        assert result is not None
        assert result["transfer_function"] == pytest.approx(-2.5)

    def test_parse_partial_output(self):
        """Only transfer function line present."""
        output = "Transfer function, output/input = 1.000000e+00\n"
        result = ResultParser.parse_tf_results(output)
        assert result is not None
        assert result["transfer_function"] == pytest.approx(1.0)
        assert "output_impedance" not in result
        assert "input_impedance" not in result

    def test_parse_empty_output(self):
        result = ResultParser.parse_tf_results("")
        assert result is None

    def test_parse_no_matching_lines(self):
        output = "Some random ngspice output\nno transfer data here\n"
        result = ResultParser.parse_tf_results(output)
        assert result is None

    def test_parse_scientific_notation_variants(self):
        output = (
            "transfer function, output/input = 3.14159e+00\n"
            "output impedance at v(2) = 1.5e+03\n"
            "V1#input impedance = 2e+06\n"
        )
        result = ResultParser.parse_tf_results(output)
        assert result is not None
        assert result["transfer_function"] == pytest.approx(3.14159)
        assert result["output_impedance"] == pytest.approx(1500.0)
        assert result["input_impedance"] == pytest.approx(2e6)


# ---------------------------------------------------------------------------
# Controller wiring
# ---------------------------------------------------------------------------


class TestTFController:
    def test_parse_results_routes_to_tf_parser(self, divider_circuit):
        """Verify the controller dispatches Transfer Function to parse_tf_results."""
        from unittest.mock import MagicMock, patch

        from controllers.simulation_controller import SimulationController
        from models.circuit import CircuitModel

        model = CircuitModel()
        model.analysis_type = "Transfer Function"
        ctrl = SimulationController(model=model)

        mock_output = (
            "Transfer function, output/input = 5.000000e-01\n"
            "Output impedance at v(nodeB) = 5.000000e+02\n"
            "v1#Input impedance = 1.000000e+03\n"
        )
        ctrl._runner = MagicMock()
        ctrl._runner.read_output.return_value = mock_output

        result = ctrl._parse_results(
            output_file="fake.txt",
            wrdata_filepath="",
            netlist="",
            raw_output="",
            warnings=[],
        )

        assert result.success is True
        assert result.data["transfer_function"] == pytest.approx(0.5)
        assert result.data["output_impedance"] == pytest.approx(500.0)
        assert result.data["input_impedance"] == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Analysis dialog
# ---------------------------------------------------------------------------


class TestTFDialog:
    def test_transfer_function_in_configs(self):
        from GUI.analysis_dialog import AnalysisDialog

        assert "Transfer Function" in AnalysisDialog.ANALYSIS_CONFIGS

    def test_config_has_two_fields(self):
        from GUI.analysis_dialog import AnalysisDialog

        config = AnalysisDialog.ANALYSIS_CONFIGS["Transfer Function"]
        assert len(config["fields"]) == 2
        field_keys = [f[1] for f in config["fields"]]
        assert "output_var" in field_keys
        assert "input_source" in field_keys
