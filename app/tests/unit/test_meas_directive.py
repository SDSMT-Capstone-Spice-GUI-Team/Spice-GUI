"""Tests for .meas measurement directive support — netlist generation and result parsing."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from simulation import NetlistGenerator, ResultParser


def _build_transient_circuit():
    """Build a simple circuit with transient analysis for .meas testing."""
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
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
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
    model.analysis_type = "Transient"
    model.analysis_params = {"step": "1u", "duration": "10m"}
    model.rebuild_nodes()
    return model


class TestMeasNetlistGeneration:
    """Test .meas directive generation in netlists."""

    def test_single_meas_directive(self):
        model = _build_transient_circuit()
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
            measurements=[".meas tran avg_out AVG V(1) FROM=1m TO=10m"],
        )
        netlist = gen.generate()
        assert ".meas tran avg_out AVG V(1) FROM=1m TO=10m" in netlist
        assert "* Measurement Directives" in netlist

    def test_multiple_meas_directives(self):
        model = _build_transient_circuit()
        measurements = [
            ".meas tran max_v MAX V(1)",
            ".meas tran min_v MIN V(1)",
            ".meas tran avg_v AVG V(1)",
        ]
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
            measurements=measurements,
        )
        netlist = gen.generate()
        for meas in measurements:
            assert meas in netlist

    def test_no_meas_directives(self):
        model = _build_transient_circuit()
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
        )
        netlist = gen.generate()
        assert "* Measurement Directives" not in netlist

    def test_auto_prefix_meas(self):
        """If the directive doesn't start with .meas, it should be auto-prefixed."""
        model = _build_transient_circuit()
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
            measurements=["tran avg_out AVG V(1)"],
        )
        netlist = gen.generate()
        assert ".meas tran avg_out AVG V(1)" in netlist

    def test_meas_appears_before_control_block(self):
        model = _build_transient_circuit()
        gen = NetlistGenerator(
            components=model.components,
            wires=model.wires,
            nodes=model.nodes,
            terminal_to_node=model.terminal_to_node,
            analysis_type=model.analysis_type,
            analysis_params=model.analysis_params,
            measurements=[".meas tran avg_out AVG V(1)"],
        )
        netlist = gen.generate()
        meas_pos = netlist.find(".meas")
        control_pos = netlist.find(".control")
        assert meas_pos < control_pos


class TestParseMeasurementResults:
    """Test parsing .meas output from ngspice stdout."""

    def test_parse_single_measurement(self):
        stdout = "avg_out  =  2.50000e+00\n"
        results = ResultParser.parse_measurement_results(stdout)
        assert results is not None
        assert "avg_out" in results
        assert results["avg_out"] == pytest.approx(2.5)

    def test_parse_multiple_measurements(self):
        stdout = "max_v  =  5.00000e+00\nmin_v  =  0.00000e+00\navg_v  =  2.50000e+00\n"
        results = ResultParser.parse_measurement_results(stdout)
        assert results is not None
        assert len(results) == 3
        assert results["max_v"] == pytest.approx(5.0)
        assert results["min_v"] == pytest.approx(0.0)
        assert results["avg_v"] == pytest.approx(2.5)

    def test_parse_failed_measurement(self):
        stdout = "rise_time  =  failed\n"
        results = ResultParser.parse_measurement_results(stdout)
        assert results is not None
        assert results["rise_time"] is None

    def test_parse_mixed_success_and_failure(self):
        stdout = "avg_v  =  2.50000e+00\nrise_time  =  failed\n"
        results = ResultParser.parse_measurement_results(stdout)
        assert results is not None
        assert results["avg_v"] == pytest.approx(2.5)
        assert results["rise_time"] is None

    def test_empty_stdout_returns_none(self):
        assert ResultParser.parse_measurement_results("") is None

    def test_no_measurements_returns_none(self):
        stdout = "some random ngspice output\nno measurements here\n"
        assert ResultParser.parse_measurement_results(stdout) is None

    def test_negative_value(self):
        stdout = "delay  =  -1.23456e-06\n"
        results = ResultParser.parse_measurement_results(stdout)
        assert results is not None
        assert results["delay"] == pytest.approx(-1.23456e-6)

    def test_ignores_non_measurement_lines(self):
        stdout = "Circuit: My Test Circuit\nDoing transient analysis...\navg_v  =  2.50000e+00\nNo. of Data Rows : 100\n"
        results = ResultParser.parse_measurement_results(stdout)
        assert results is not None
        assert len(results) == 1
        assert "avg_v" in results


class TestMeasControllerIntegration:
    """Test measurement directives flow through the controller."""

    def test_measurements_in_analysis_params_generate_directives(self):
        from controllers.simulation_controller import SimulationController

        model = _build_transient_circuit()
        model.analysis_params["measurements"] = [".meas tran avg_v AVG V(1)"]
        ctrl = SimulationController(model)
        netlist = ctrl.generate_netlist(
            measurements=model.analysis_params.get("measurements")
        )
        assert ".meas tran avg_v AVG V(1)" in netlist
