"""
Shared test fixtures for the Spice-GUI test suite.

All fixtures build pure-Python model objects (no Qt dependencies).
"""

import sys
from pathlib import Path

# Ensure app/ is on sys.path so bare imports (models, simulation, GUI, controllers)
# work when running individual test files (e.g., python -m pytest app/tests/unit/test_foo.py).
_app_dir = str(Path(__file__).resolve().parent.parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

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
