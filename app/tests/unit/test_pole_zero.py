"""
Tests for Pole-Zero (.pz) analysis support.

Covers netlist generation, result parsing, and controller wiring.
"""

import math

import pytest
from models.node import NodeData
from simulation.netlist_generator import NetlistGenerator
from simulation.result_parser import ResultParser
from tests.conftest import make_component, make_wire

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rc_circuit():
    """Simple RC lowpass: V1 → R1 → C1 → GND."""
    components = {
        "V1": make_component("Voltage Source", "V1", "1V", (0, 0)),
        "R1": make_component("Resistor", "R1", "1k", (100, 0)),
        "C1": make_component("Capacitor", "C1", "1u", (200, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (200, 100)),
    }
    wires = [
        make_wire("V1", 0, "R1", 0),
        make_wire("R1", 1, "C1", 0),
        make_wire("C1", 1, "GND1", 0),
        make_wire("V1", 1, "GND1", 0),
    ]
    node_in = NodeData(
        terminals={("V1", 0), ("R1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_out = NodeData(
        terminals={("R1", 1), ("C1", 0)},
        wire_indices={1},
        auto_label="nodeB",
    )
    node_gnd = NodeData(
        terminals={("C1", 1), ("GND1", 0), ("V1", 1)},
        wire_indices={2, 3},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_in, node_out, node_gnd]
    t2n = {
        ("V1", 0): node_in,
        ("R1", 0): node_in,
        ("R1", 1): node_out,
        ("C1", 0): node_out,
        ("C1", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }
    return components, wires, nodes, t2n


# ---------------------------------------------------------------------------
# Netlist generation
# ---------------------------------------------------------------------------


class TestPZNetlist:
    def test_pz_directive_generated(self, rc_circuit):
        components, wires, nodes, t2n = rc_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Pole-Zero",
            analysis_params={
                "input_pos": "1",
                "input_neg": "0",
                "output_pos": "2",
                "output_neg": "0",
                "transfer_type": "vol",
                "pz_type": "pz",
            },
        )
        netlist = gen.generate()
        assert ".pz 1 0 2 0 vol pz" in netlist

    def test_pz_default_params(self, rc_circuit):
        components, wires, nodes, t2n = rc_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Pole-Zero",
            analysis_params={},
        )
        netlist = gen.generate()
        assert ".pz 1 0 2 0 vol pz" in netlist

    def test_pz_poles_only(self, rc_circuit):
        components, wires, nodes, t2n = rc_circuit
        gen = NetlistGenerator(
            components=components,
            wires=wires,
            nodes=nodes,
            terminal_to_node=t2n,
            analysis_type="Pole-Zero",
            analysis_params={
                "input_pos": "1",
                "input_neg": "0",
                "output_pos": "3",
                "output_neg": "0",
                "transfer_type": "cur",
                "pz_type": "pol",
            },
        )
        netlist = gen.generate()
        assert ".pz 1 0 3 0 cur pol" in netlist


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


class TestPZParser:
    def test_parse_poles_and_zeros(self):
        output = (
            "pole(1) = -1.00000e+03, 0.00000e+00\n"
            "pole(2) = -5.00000e+05, 3.00000e+05\n"
            "zero(1) = -2.00000e+04, 0.00000e+00\n"
        )
        result = ResultParser.parse_pz_results(output)
        assert result is not None
        assert len(result["poles"]) == 2
        assert len(result["zeros"]) == 1

    def test_pole_values_correct(self):
        output = "pole(1) = -1.00000e+03, 0.00000e+00\n"
        result = ResultParser.parse_pz_results(output)
        pole = result["poles"][0]
        assert pole["real"] == pytest.approx(-1000.0)
        assert pole["imag"] == pytest.approx(0.0)
        assert pole["is_unstable"] is False

    def test_complex_pole_frequency(self):
        output = "pole(1) = -5.00000e+05, 3.00000e+05\n"
        result = ResultParser.parse_pz_results(output)
        pole = result["poles"][0]
        magnitude = math.sqrt(5e5**2 + 3e5**2)
        expected_freq = magnitude / (2 * math.pi)
        assert pole["frequency_hz"] == pytest.approx(expected_freq)

    def test_unstable_pole_detected(self):
        output = "pole(1) = 1.00000e+02, 5.00000e+03\n"
        result = ResultParser.parse_pz_results(output)
        pole = result["poles"][0]
        assert pole["is_unstable"] is True

    def test_empty_output(self):
        result = ResultParser.parse_pz_results("")
        assert result is None

    def test_no_matching_lines(self):
        result = ResultParser.parse_pz_results("random ngspice output\n")
        assert result is None

    def test_poles_only_no_zeros(self):
        output = "pole(1) = -100, 0\npole(2) = -200, 0\n"
        result = ResultParser.parse_pz_results(output)
        assert len(result["poles"]) == 2
        assert len(result["zeros"]) == 0

    def test_zeros_only_no_poles(self):
        output = "zero(1) = -500, 0\n"
        result = ResultParser.parse_pz_results(output)
        assert len(result["poles"]) == 0
        assert len(result["zeros"]) == 1


# ---------------------------------------------------------------------------
# Controller wiring
# ---------------------------------------------------------------------------


class TestPZController:
    def test_parse_results_routes_to_pz_parser(self):
        from unittest.mock import MagicMock

        from controllers.simulation_controller import SimulationController
        from models.circuit import CircuitModel

        model = CircuitModel()
        model.analysis_type = "Pole-Zero"
        ctrl = SimulationController(model=model)

        mock_output = (
            "pole(1) = -1.00000e+03, 0.00000e+00\nzero(1) = -2.00000e+04, 0.00000e+00\n"
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
        assert len(result.data["poles"]) == 1
        assert len(result.data["zeros"]) == 1


# ---------------------------------------------------------------------------
# Analysis dialog
# ---------------------------------------------------------------------------


class TestPZDialog:
    def test_pole_zero_in_configs(self):
        from GUI.analysis_dialog import AnalysisDialog

        assert "Pole-Zero" in AnalysisDialog.ANALYSIS_CONFIGS

    def test_config_has_six_fields(self):
        from GUI.analysis_dialog import AnalysisDialog

        config = AnalysisDialog.ANALYSIS_CONFIGS["Pole-Zero"]
        assert len(config["fields"]) == 6
        field_keys = [f[1] for f in config["fields"]]
        assert "input_pos" in field_keys
        assert "input_neg" in field_keys
        assert "output_pos" in field_keys
        assert "output_neg" in field_keys
        assert "transfer_type" in field_keys
        assert "pz_type" in field_keys
