"""
Controllers for Spice-GUI.

This package contains Qt-free controller classes that orchestrate
operations between models and views using an observer pattern.
"""

from .circuit_controller import CircuitController

# AUDIT(architecture): validate_circuit_data is re-exported from controllers but its canonical location is models.circuit_schema_validator — consumers should import from the canonical location to avoid confusion
from .file_controller import FileController, validate_circuit_data
from .simulation_controller import SimulationController, SimulationResult

__all__ = [
    "CircuitController",
    "SimulationController",
    "SimulationResult",
    "FileController",
    "validate_circuit_data",
]
