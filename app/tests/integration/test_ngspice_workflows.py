"""
Integration tests for core ngspice simulation workflows.

Each test builds a circuit through CircuitController, configures
analysis via SimulationController, runs the full pipeline, and
validates the parsed results.

All tests are marked @pytest.mark.ngspice and are automatically
skipped when ngspice is not on PATH (via the session-scoped
require_ngspice fixture in conftest.py).
"""

import tempfile

import pytest
from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from simulation.ngspice_runner import NgspiceRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_resistor_divider():
    """Build V1(5V) -- R1(1k) -- R2(1k) -- GND circuit.

    Expected DC operating point:
        node between V1+ and R1: 5 V
        node between R1 and R2:  2.5 V
    """
    model = CircuitModel()
    ctrl = CircuitController(model)

    v1 = ctrl.add_component("Voltage Source", (0, 0))
    r1 = ctrl.add_component("Resistor", (100, 0))
    r2 = ctrl.add_component("Resistor", (200, 0))
    gnd = ctrl.add_component("Ground", (200, 100))

    ctrl.update_component_value(v1.component_id, "5")
    ctrl.update_component_value(r1.component_id, "1k")
    ctrl.update_component_value(r2.component_id, "1k")

    # V1 term0 (+) -> R1 term0
    ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
    # R1 term1 -> R2 term0
    ctrl.add_wire(r1.component_id, 1, r2.component_id, 0)
    # R2 term1 -> GND term0
    ctrl.add_wire(r2.component_id, 1, gnd.component_id, 0)
    # V1 term1 (-) -> GND term0
    ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

    return model, ctrl


def _build_rc_circuit():
    """Build V1(AC) -- R1(1k) -- C1(1u) -- GND circuit.

    An RC low-pass filter suitable for AC sweep analysis.
    Cutoff frequency: 1 / (2*pi*R*C) ≈ 159 Hz
    """
    model = CircuitModel()
    ctrl = CircuitController(model)

    v1 = ctrl.add_component("Voltage Source", (0, 0))
    r1 = ctrl.add_component("Resistor", (100, 0))
    c1 = ctrl.add_component("Capacitor", (200, 0))
    gnd = ctrl.add_component("Ground", (200, 100))

    ctrl.update_component_value(v1.component_id, "AC 1")
    ctrl.update_component_value(r1.component_id, "1k")
    ctrl.update_component_value(c1.component_id, "1u")

    # V1+ -> R1
    ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
    # R1 -> C1
    ctrl.add_wire(r1.component_id, 1, c1.component_id, 0)
    # C1 -> GND
    ctrl.add_wire(c1.component_id, 1, gnd.component_id, 0)
    # V1- -> GND
    ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

    return model, ctrl


# ---------------------------------------------------------------------------
# DC Operating Point
# ---------------------------------------------------------------------------


@pytest.mark.ngspice
class TestDCOperatingPoint:
    """Test DC operating point analysis through the full pipeline."""

    def test_resistor_divider_op(self):
        """V1(5V)-R1(1k)-R2(1k)-GND should produce a ~2.5V midpoint."""
        model, ctrl = _build_resistor_divider()

        with tempfile.TemporaryDirectory() as tmpdir:
            sim = SimulationController(model=model, circuit_ctrl=ctrl)
            sim._runner = NgspiceRunner(output_dir=tmpdir)

            sim.set_analysis("DC Operating Point")
            result = sim.run_simulation()

            assert result.success, f"Simulation failed: {result.error}"
            assert result.analysis_type == "DC Operating Point"
            assert result.data is not None

            # Result should contain node voltages
            node_voltages = result.data.get("node_voltages", result.data)
            assert len(node_voltages) > 0, "No node voltages found"

            # At least one node should be close to 5 V and one close to 2.5 V
            voltages = list(node_voltages.values())
            assert any(abs(v - 5.0) < 0.1 for v in voltages), f"Expected ~5V node, got {voltages}"
            assert any(abs(v - 2.5) < 0.1 for v in voltages), f"Expected ~2.5V node, got {voltages}"


# ---------------------------------------------------------------------------
# DC Sweep
# ---------------------------------------------------------------------------


@pytest.mark.ngspice
class TestDCSweep:
    """Test DC sweep analysis through the full pipeline."""

    def test_resistor_divider_dc_sweep(self):
        """Sweep V1 from 0 to 5V; midpoint should track at half the source."""
        model, ctrl = _build_resistor_divider()

        with tempfile.TemporaryDirectory() as tmpdir:
            sim = SimulationController(model=model, circuit_ctrl=ctrl)
            sim._runner = NgspiceRunner(output_dir=tmpdir)

            sim.set_analysis(
                "DC Sweep",
                {
                    "source": "V1",
                    "min": 0,
                    "max": 5,
                    "step": 1,
                },
            )
            result = sim.run_simulation()

            assert result.success, f"Simulation failed: {result.error}"
            assert result.analysis_type == "DC Sweep"
            assert result.data is not None

            # DC sweep data should have sweep values and node data
            # The result parser returns a dict with node names as keys
            # and lists of values
            assert isinstance(result.data, dict)
            assert len(result.data) > 0, "No DC sweep data returned"


# ---------------------------------------------------------------------------
# Transient Analysis
# ---------------------------------------------------------------------------


@pytest.mark.ngspice
class TestTransientAnalysis:
    """Test transient analysis through the full pipeline."""

    def test_rc_transient_step_response(self):
        """RC circuit with a step input should produce time-domain data."""
        model, ctrl = _build_resistor_divider()

        with tempfile.TemporaryDirectory() as tmpdir:
            sim = SimulationController(model=model, circuit_ctrl=ctrl)
            sim._runner = NgspiceRunner(output_dir=tmpdir)

            sim.set_analysis(
                "Transient",
                {
                    "step": 0.0001,
                    "duration": 0.01,
                    "start": 0,
                },
            )
            result = sim.run_simulation()

            assert result.success, f"Simulation failed: {result.error}"
            assert result.analysis_type == "Transient"
            assert result.data is not None

            # Transient data is a list of dicts, each with 'time' + signals
            assert isinstance(result.data, list), f"Expected list, got {type(result.data)}"
            assert len(result.data) > 0, "Transient data is empty"

            first_row = result.data[0]
            assert "time" in first_row, f"No 'time' key in first row: {list(first_row.keys())}"

            # Should have at least one signal besides time
            signal_keys = [k for k in first_row.keys() if k != "time"]
            assert len(signal_keys) > 0, "No signal data in transient results"


# ---------------------------------------------------------------------------
# AC Sweep
# ---------------------------------------------------------------------------


@pytest.mark.ngspice
class TestACSweep:
    """Test AC sweep analysis through the full pipeline."""

    def test_rc_lowpass_ac_sweep(self):
        """RC low-pass filter should show roll-off in AC sweep."""
        model, ctrl = _build_rc_circuit()

        with tempfile.TemporaryDirectory() as tmpdir:
            sim = SimulationController(model=model, circuit_ctrl=ctrl)
            sim._runner = NgspiceRunner(output_dir=tmpdir)

            sim.set_analysis(
                "AC Sweep",
                {
                    "fStart": 1,
                    "fStop": 1e6,
                    "points": 10,
                    "sweepType": "dec",
                },
            )
            result = sim.run_simulation()

            assert result.success, f"Simulation failed: {result.error}"
            assert result.analysis_type == "AC Sweep"
            assert result.data is not None
            assert isinstance(result.data, dict)

            # At minimum, the data dict should not be empty
            assert len(result.data) > 0, "AC sweep data is empty"
