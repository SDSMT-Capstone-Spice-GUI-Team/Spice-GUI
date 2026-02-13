"""
Spice-GUI Scripting API — programmatic circuit creation and simulation.

This package provides a headless Python API for creating, modifying,
and simulating circuits without requiring the GUI or PyQt6.

Usage::

    from scripting import Circuit

    circuit = Circuit()
    circuit.add_component("Voltage Source", "5V", position=(0, 0))
    circuit.add_component("Resistor", "1k", position=(200, 0))
    circuit.add_component("Ground", position=(0, 200))
    circuit.add_wire("V1", 0, "R1", 0)
    circuit.add_wire("R1", 1, "V1", 1)
    circuit.add_wire("V1", 1, "GND1", 0)

    circuit.set_analysis("DC Operating Point")
    result = circuit.simulate()
    print(result.data)

    circuit.save("my_circuit.json")
"""

# Re-export SimulationResult for convenience
from controllers.simulation_controller import SimulationResult
from scripting.circuit import Circuit
from scripting.jupyter import circuit_to_svg, plot_result, register_jupyter_formatters

__all__ = ["Circuit", "SimulationResult", "circuit_to_svg", "plot_result", "register_jupyter_formatters"]
