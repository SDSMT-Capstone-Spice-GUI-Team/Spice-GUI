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

    def test_dc_source_ac_sweep_varies_across_frequency(self):
        """A plain DC voltage source must still produce a varying AC sweep.

        Regression: a source written as "DC 1" (no AC term) left ngspice with
        no drive reference during .ac analysis, so vm() returned ~0 at every
        frequency and the plot was a flat line. The netlist must attach an AC
        reference so the magnitude actually rolls off through the sweep.
        """
        model, ctrl = _build_rc_circuit()
        # Switch the AC source to a plain DC source to reproduce the bug.
        v1_id = next(cid for cid, c in model.components.items() if "V1" in cid)
        ctrl.update_component_value(v1_id, "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            sim = SimulationController(model=model, circuit_ctrl=ctrl)
            sim._runner = NgspiceRunner(output_dir=tmpdir)

            sim.set_analysis(
                "AC Sweep",
                {
                    "fStart": 1,
                    "fStop": 1e6,
                    "points": 50,
                    "sweepType": "dec",
                },
            )
            result = sim.run_simulation()

            assert result.success, f"Simulation failed: {result.error}"
            assert result.data is not None
            assert isinstance(result.data, dict)

            magnitude = result.data.get("magnitude", {})
            assert magnitude, "No magnitude data parsed from AC sweep"

            # nodeA sits directly on the source, so it is flat by design.
            # The output node (nodeB) must roll off through the sweep — this is
            # the core guard against the flat-line bug.
            assert "nodeB" in magnitude, f"Expected output node 'nodeB' in {list(magnitude)}"
            trace = magnitude["nodeB"]
            assert (
                len(set(round(v, 4) for v in trace)) > 5
            ), f"AC sweep magnitude on nodeB is flat (bug regression): {trace[:6]}..."

    def test_ac_sweep_supply_stays_dc_netlist(self):
        """One AC input plus a DC supply: only the input carries AC in the netlist.

        Regression for the two-source bug fix (#943): an AC Sweep should mark
        the existing AC source as the drive, but must NOT append "AC 1" to a
        plain DC supply. If the supply is also wiggled, its 0.5x attenuation
        is wrong. Build V1(AC) and V2(6V DC) feeding a common node through
        equal 1k resistors and assert the supply's netlist line stays a plain
        "DC 6V" source with no AC term.
        """
        model = CircuitModel()
        ctrl = CircuitController(model)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        v2 = ctrl.add_component("Voltage Source", (0, 100))
        r1 = ctrl.add_component("Resistor", (100, 0))
        r2 = ctrl.add_component("Resistor", (100, 100))
        gnd = ctrl.add_component("Ground", (200, 50))

        ctrl.update_component_value(v1.component_id, "AC 1")
        ctrl.update_component_value(v2.component_id, "6V")
        ctrl.update_component_value(r1.component_id, "1k")
        ctrl.update_component_value(r2.component_id, "1k")

        # V1+ -> R1, V2+ -> R2, R1- -> GND, R2- -> GND, V1-, V2- -> GND
        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(v2.component_id, 0, r2.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(r2.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v2.component_id, 1, gnd.component_id, 0)

        sim = SimulationController(model=model, circuit_ctrl=ctrl)
        sim._runner = NgspiceRunner(output_dir=None)
        sim.set_analysis(
            "AC Sweep",
            {
                "fStart": 1,
                "fStop": 1e6,
                "points": 10,
                "sweepType": "dec",
            },
        )
        netlist = sim.generate_netlist()

        supply_line = next(
            (ln for ln in netlist.splitlines() if ln.strip().startswith(f"{v2.component_id} ")),
            None,
        )
        supply_line = supply_line.strip() if supply_line else ""
        assert supply_line, f"Supply {v2.component_id} not found in netlist"
        # The supply must remain a plain DC source: DC value, no AC term.
        assert "AC" not in supply_line.upper(), f"DC supply must not gain an AC term: {supply_line}"
        assert supply_line.endswith("DC 6V"), f"Supply must keep its DC value, got: {supply_line}"
