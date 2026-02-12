"""
Circuit — high-level scripting API for programmatic circuit manipulation.

No GUI or PyQt6 dependency. Wraps the existing model/controller/simulation
layers behind a user-friendly interface.
"""

import csv
import json
from pathlib import Path
from typing import Optional, Union

from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController, SimulationResult
from models.circuit import CircuitModel
from models.component import COMPONENT_TYPES, ComponentData


class Circuit:
    """A scriptable circuit that can be built, simulated, and saved programmatically.

    Wraps CircuitModel, CircuitController, and SimulationController to provide
    a clean API for headless circuit workflows.

    Args:
        model: An existing CircuitModel to wrap. If None, creates an empty circuit.
    """

    def __init__(self, model: Optional[CircuitModel] = None):
        self._model = model or CircuitModel()
        self._controller = CircuitController(self._model)
        self._sim = SimulationController(self._model, self._controller)

    # --- Factory methods ---

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Circuit":
        """Load a circuit from a JSON file.

        Args:
            path: Path to the circuit JSON file.

        Returns:
            A new Circuit instance populated from the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValueError: If the JSON structure is invalid.
        """
        path = Path(path)
        with open(path, "r") as f:
            data = json.load(f)

        from controllers.file_controller import validate_circuit_data

        validate_circuit_data(data)
        model = CircuitModel.from_dict(data)
        return cls(model)

    @classmethod
    def from_netlist(cls, path: Union[str, Path]) -> "Circuit":
        """Import a circuit from a SPICE netlist file (.cir, .spice).

        Args:
            path: Path to the netlist file.

        Returns:
            A new Circuit instance built from the netlist.

        Raises:
            FileNotFoundError: If the file does not exist.
            simulation.netlist_parser.NetlistParseError: If parsing fails.
        """
        from simulation.netlist_parser import import_netlist

        path = Path(path)
        with open(path, "r") as f:
            text = f.read()

        model, analysis = import_netlist(text)
        if analysis:
            model.analysis_type = analysis["type"]
            model.analysis_params = analysis["params"]
        return cls(model)

    # --- Component operations ---

    def add_component(
        self,
        component_type: str,
        value: Optional[str] = None,
        position: tuple[float, float] = (0.0, 0.0),
        rotation: int = 0,
        flip_h: bool = False,
        flip_v: bool = False,
    ) -> str:
        """Add a component to the circuit.

        Args:
            component_type: One of the supported types (e.g. "Resistor",
                "Voltage Source", "Ground"). See ``Circuit.component_types``
                for the full list.
            value: Component value (e.g. "1k", "5V"). If None, uses the
                default value for the component type.
            position: (x, y) position on the canvas.
            rotation: Rotation in degrees (0, 90, 180, 270).
            flip_h: Horizontal flip.
            flip_v: Vertical flip.

        Returns:
            The auto-generated component ID (e.g. "R1", "V1", "GND1").

        Raises:
            ValueError: If the component_type is not recognized.
        """
        if component_type not in COMPONENT_TYPES:
            raise ValueError(f"Unknown component type '{component_type}'. Valid types: {', '.join(COMPONENT_TYPES)}")

        comp = self._controller.add_component(component_type, position)

        if value is not None:
            self._controller.update_component_value(comp.component_id, value)

        if rotation:
            comp.rotation = rotation % 360

        if flip_h:
            comp.flip_h = True
        if flip_v:
            comp.flip_v = True

        return comp.component_id

    def remove_component(self, component_id: str) -> None:
        """Remove a component and its connected wires.

        Args:
            component_id: The ID of the component to remove (e.g. "R1").
        """
        self._controller.remove_component(component_id)

    def update_value(self, component_id: str, value: str) -> None:
        """Update a component's value.

        Args:
            component_id: The component to update (e.g. "R1").
            value: The new value (e.g. "2.2k").
        """
        self._controller.update_component_value(component_id, value)

    # --- Wire operations ---

    def add_wire(
        self,
        start_component: str,
        start_terminal: int,
        end_component: str,
        end_terminal: int,
    ) -> bool:
        """Connect two component terminals with a wire.

        Args:
            start_component: ID of the first component (e.g. "V1").
            start_terminal: Terminal index on the first component (0-based).
            end_component: ID of the second component (e.g. "R1").
            end_terminal: Terminal index on the second component (0-based).

        Returns:
            True if the wire was added, False if a duplicate wire exists.
        """
        wire = self._controller.add_wire(start_component, start_terminal, end_component, end_terminal)
        return wire is not None

    # --- Analysis ---

    def set_analysis(self, analysis_type: str, params: Optional[dict] = None) -> None:
        """Configure the simulation analysis type.

        Args:
            analysis_type: One of "DC Operating Point", "DC Sweep",
                "AC Sweep", "Transient", "Temperature Sweep", "Noise".
            params: Analysis-specific parameters. Examples:
                - DC Sweep: {"min": 0, "max": 10, "step": 0.1}
                - AC Sweep: {"sweep_type": "dec", "points": 10,
                             "fStart": 1, "fStop": 1e6}
                - Transient: {"step": 1e-6, "duration": 1e-3, "start": 0}
        """
        self._sim.set_analysis(analysis_type, params)

    def simulate(self) -> SimulationResult:
        """Run the configured simulation.

        Returns:
            A SimulationResult with success status, parsed data, and any errors.
            On success, result.data contains the parsed simulation output.

        Raises:
            No exceptions — errors are reported via SimulationResult.success
            and SimulationResult.error.
        """
        return self._sim.run_simulation()

    def validate(self) -> SimulationResult:
        """Validate the circuit without running a simulation.

        Returns:
            SimulationResult with success=True if valid, or errors/warnings.
        """
        return self._sim.validate_circuit()

    # --- Netlist ---

    def to_netlist(self) -> str:
        """Generate a SPICE netlist from the current circuit.

        Returns:
            The netlist as a string.
        """
        return self._sim.generate_netlist()

    # --- Persistence ---

    def save(self, path: Union[str, Path]) -> None:
        """Save the circuit to a JSON file.

        Args:
            path: Destination file path.
        """
        path = Path(path)
        data = self._model.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # --- Properties ---

    @property
    def components(self) -> dict[str, ComponentData]:
        """All components in the circuit, keyed by ID."""
        return self._model.components

    @property
    def wires(self) -> list:
        """All wires in the circuit."""
        return self._model.wires

    @property
    def analysis_type(self) -> str:
        """The currently configured analysis type."""
        return self._model.analysis_type

    @property
    def analysis_params(self) -> dict:
        """The currently configured analysis parameters."""
        return self._model.analysis_params

    @property
    def model(self) -> CircuitModel:
        """Direct access to the underlying CircuitModel."""
        return self._model

    @property
    def component_types(self) -> list[str]:
        """List of all supported component types."""
        return list(COMPONENT_TYPES)

    # --- Display integration ---

    def _repr_svg_(self) -> str:
        """Jupyter notebook SVG representation."""
        from scripting.jupyter import circuit_to_svg

        return circuit_to_svg(self._model)

    def plot_result(self, result: SimulationResult, title: Optional[str] = None):
        """Generate a matplotlib figure from a simulation result.

        Args:
            result: A SimulationResult from simulate().
            title: Optional plot title.

        Returns:
            A matplotlib Figure, or None if matplotlib is unavailable.
        """
        from scripting.jupyter import plot_result

        return plot_result(result, title)

    # --- Result export ---

    @staticmethod
    def result_to_csv(result: SimulationResult, path: Union[str, Path]) -> None:
        """Export simulation results to a CSV file.

        Supports DC Operating Point (node voltages + branch currents),
        DC Sweep, AC Sweep, and Transient results.

        Args:
            result: A successful SimulationResult from simulate().
            path: Destination CSV file path.

        Raises:
            ValueError: If the result has no data or is a failure.
        """
        if not result.success or result.data is None:
            raise ValueError(f"Cannot export failed or empty result: {result.error}")

        path = Path(path)
        data = result.data

        if result.analysis_type == "DC Operating Point":
            _write_op_csv(data, path)
        elif result.analysis_type == "Transient":
            _write_tabular_csv(data, path)
        elif result.analysis_type in ("DC Sweep", "AC Sweep", "Noise"):
            _write_tabular_csv(data, path)
        else:
            _write_generic_csv(data, path)


def _write_op_csv(data: dict, path: Path) -> None:
    """Write DC Operating Point results as name,value rows."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "value"])
        for name, value in data.get("node_voltages", {}).items():
            writer.writerow([name, value])
        for name, value in data.get("branch_currents", {}).items():
            writer.writerow([name, value])


def _write_tabular_csv(data, path: Path) -> None:
    """Write list-of-dicts data as a CSV table."""
    if isinstance(data, list) and data:
        keys = list(data[0].keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
    elif isinstance(data, dict):
        _write_generic_csv(data, path)


def _write_generic_csv(data, path: Path) -> None:
    """Fallback: write dict data as key,value rows."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "value"])
        if isinstance(data, dict):
            for key, value in data.items():
                writer.writerow([key, value])
