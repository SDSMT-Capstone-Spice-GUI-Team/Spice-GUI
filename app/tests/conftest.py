"""
Shared test fixtures for the Spice-GUI test suite.

All fixtures build pure-Python model objects (no Qt dependencies).
"""

import os
import sys
from pathlib import Path

# Prevent matplotlib.use("QtAgg") from failing in headless environments.
# The monte_carlo_results_dialog module calls matplotlib.use("QtAgg") at
# import time which raises ImportError when Qt's offscreen platform is active.
# Patching here ensures the entire test suite can collect and run.
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    import matplotlib

    _orig_mpl_use = matplotlib.use

    def _safe_mpl_use(backend, **kwargs):
        if backend == "QtAgg":
            return  # silently skip in headless mode
        return _orig_mpl_use(backend, **kwargs)

    matplotlib.use = _safe_mpl_use

# Ensure app/ is on sys.path so bare imports (models, simulation, GUI, controllers)
# work when running individual test files (e.g., python -m pytest app/tests/unit/test_foo.py).
_app_dir = str(Path(__file__).resolve().parent.parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

# Create QApplication before any matplotlib import so the QtAgg backend works.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication as _QApp

if _QApp.instance() is None:
    _qapp_instance = _QApp([])

import pytest
from models.component import ComponentData
from models.node import NodeData, reset_node_counter
from models.wire import WireData


@pytest.fixture(autouse=True)
def _reset_nodes():
    """Reset the node counter before each test."""
    reset_node_counter()


def make_component(component_type, component_id, value, position=(0.0, 0.0)):
    """Helper to create a ComponentData with minimal boilerplate."""
    return ComponentData(
        component_id=component_id,
        component_type=component_type,
        value=value,
        position=position,
    )


def make_wire(start_id, start_term, end_id, end_term):
    """Helper to create a WireData."""
    return WireData(
        start_component_id=start_id,
        start_terminal=start_term,
        end_component_id=end_id,
        end_terminal=end_term,
    )


@pytest.fixture
def simple_resistor_circuit():
    """
    V1 -- R1 -- GND

    V1 terminal 0 (positive) connects to R1 terminal 0
    R1 terminal 1 connects to GND terminal 0
    V1 terminal 1 (negative) connects to GND terminal 0
    """
    components = {
        "V1": make_component("Voltage Source", "V1", "5V", (0, 0)),
        "R1": make_component("Resistor", "R1", "1k", (100, 0)),
        "GND1": make_component("Ground", "GND1", "0V", (100, 100)),
    }
    wires = [
        make_wire("V1", 0, "R1", 0),
        make_wire("R1", 1, "GND1", 0),
        make_wire("V1", 1, "GND1", 0),
    ]

    # Build nodes
    node_a = NodeData(
        terminals={("V1", 0), ("R1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_gnd = NodeData(
        terminals={("R1", 1), ("GND1", 0), ("V1", 1)},
        wire_indices={1, 2},
        is_ground=True,
        auto_label="0",
    )
    nodes = [node_a, node_gnd]

    terminal_to_node = {
        ("V1", 0): node_a,
        ("R1", 0): node_a,
        ("R1", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }

    return components, wires, nodes, terminal_to_node


@pytest.fixture
def resistor_divider_circuit():
    """
    V1+ -- R1 -- R2 -- GND
    V1- connected to GND

    Nodes: nodeA (V1+, R1 term0), nodeB (R1 term1, R2 term0), 0 (R2 term1, V1-, GND)
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

    node_a = NodeData(
        terminals={("V1", 0), ("R1", 0)},
        wire_indices={0},
        auto_label="nodeA",
    )
    node_b = NodeData(
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
    nodes = [node_a, node_b, node_gnd]

    terminal_to_node = {
        ("V1", 0): node_a,
        ("R1", 0): node_a,
        ("R1", 1): node_b,
        ("R2", 0): node_b,
        ("R2", 1): node_gnd,
        ("GND1", 0): node_gnd,
        ("V1", 1): node_gnd,
    }

    return components, wires, nodes, terminal_to_node


# ---------------------------------------------------------------------------
# Shared circuit-model builder
# ---------------------------------------------------------------------------


def build_simple_circuit():
    """Build a simple V1-R1-GND CircuitModel.

    Creates the canonical 3-component, 3-wire test circuit used across the
    test suite.  Returns a fully-initialised ``CircuitModel`` with nodes
    built and ``component_counter`` set.

    Tests that additionally need ``model.analysis_type`` can set it after
    calling this helper.
    """
    from models.circuit import CircuitModel

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
    model.component_counter = {"V": 1, "R": 1, "GND": 1}
    model.rebuild_nodes()
    return model


# ---------------------------------------------------------------------------
# Shared simulation-controller factory
# ---------------------------------------------------------------------------


def make_simulation_controller(model=None, circuit_ctrl=None):
    """Create a SimulationController with a mocked NgspiceRunner.

    Returns ``(ctrl, runner)`` where ``runner`` is a ``MagicMock`` with
    ``output_dir`` and ``find_ngspice`` pre-configured.

    Args:
        model: Optional ``CircuitModel``.  Defaults to an empty model.
        circuit_ctrl: Optional ``CircuitController`` to pass through.
    """
    from unittest.mock import MagicMock

    from controllers.simulation_controller import SimulationController
    from models.circuit import CircuitModel

    ctrl = SimulationController(model=model or CircuitModel(), circuit_ctrl=circuit_ctrl)
    runner = MagicMock()
    runner.output_dir = "/tmp/test_output"
    runner.find_ngspice.return_value = "/usr/bin/ngspice"
    ctrl._runner = runner
    return ctrl, runner
