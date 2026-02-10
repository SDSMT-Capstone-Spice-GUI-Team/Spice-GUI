"""
SimulationController - Orchestrates the simulation pipeline.

This module contains no Qt dependencies. It coordinates analysis
configuration, circuit validation, netlist generation, ngspice
execution, and result parsing.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from models.circuit import CircuitModel

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of a simulation run."""

    success: bool
    analysis_type: str = ""
    data: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    netlist: str = ""
    raw_output: str = ""
    output_file: str = ""
    wrdata_filepath: str = ""


class SimulationController:
    """
    Controller for the simulation pipeline.

    Coordinates: validate -> generate netlist -> run ngspice -> parse results
    """

    def __init__(self, model: Optional[CircuitModel] = None, circuit_ctrl=None):
        self.model = model or CircuitModel()
        self.circuit_ctrl = circuit_ctrl  # Phase 5: For observer notifications
        self._runner = None

    @property
    def runner(self):
        """Lazy initialization of NgspiceRunner."""
        if self._runner is None:
            from simulation import NgspiceRunner

            self._runner = NgspiceRunner()
        return self._runner

    def set_analysis(self, analysis_type: str, params: Optional[dict] = None) -> None:
        """Set the analysis type and parameters on the model."""
        self.model.analysis_type = analysis_type
        self.model.analysis_params = (params or {}).copy()

    def validate_circuit(self) -> SimulationResult:
        """
        Validate the circuit before simulation.

        Returns a SimulationResult with success=False and errors if invalid.
        """
        from simulation import validate_circuit

        is_valid, errors, warnings = validate_circuit(
            self.model.components,
            [w for w in self.model.wires],
            self.model.analysis_type,
        )
        return SimulationResult(
            success=is_valid,
            errors=errors,
            warnings=warnings,
            error="; ".join(errors) if errors else "",
        )

    def generate_netlist(self, wrdata_filepath: Optional[str] = None) -> str:
        """Generate a SPICE netlist from the current circuit model."""
        from simulation import NetlistGenerator

        self.model.rebuild_nodes()
        generator = NetlistGenerator(
            components=self.model.components,
            wires=self.model.wires,
            nodes=self.model.nodes,
            terminal_to_node=self.model.terminal_to_node,
            analysis_type=self.model.analysis_type,
            analysis_params=self.model.analysis_params,
            wrdata_filepath=wrdata_filepath or "transient_data.txt",
        )
        return generator.generate()

    def run_simulation(self) -> SimulationResult:
        """
        Run the full simulation pipeline.

        Steps: validate -> generate netlist -> find ngspice -> run -> parse
        """
        # Phase 5: Notify simulation started
        if self.circuit_ctrl:
            self.circuit_ctrl._notify("simulation_started", None)

        # 1. Validate
        validation = self.validate_circuit()
        if not validation.success:
            # Phase 5: Notify even on failure
            if self.circuit_ctrl:
                self.circuit_ctrl._notify("simulation_completed", validation)
            return validation

        # 2. Generate wrdata path for transient
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wrdata_filepath = os.path.join(self.runner.output_dir, f"wrdata_{timestamp}.txt")

        # 3. Generate netlist
        try:
            netlist = self.generate_netlist(wrdata_filepath=wrdata_filepath)
        except (ValueError, KeyError, TypeError) as e:
            result = SimulationResult(
                success=False,
                error=f"Netlist generation failed: {e}",
            )
            # Phase 5: Notify even on failure
            if self.circuit_ctrl:
                self.circuit_ctrl._notify("simulation_completed", result)
            return result

        # 4. Find ngspice
        ngspice_path = self.runner.find_ngspice()
        if ngspice_path is None:
            result = SimulationResult(
                success=False,
                error="ngspice executable not found. Please install ngspice.",
                netlist=netlist,
            )
            # Phase 5: Notify even on failure
            if self.circuit_ctrl:
                self.circuit_ctrl._notify("simulation_completed", result)
            return result

        # 5. Run simulation
        success, output_file, stdout, stderr = self.runner.run_simulation(netlist)
        if not success:
            result = SimulationResult(
                success=False,
                error=stderr or "Simulation failed",
                netlist=netlist,
                raw_output=stdout,
            )
            # Phase 5: Notify even on failure
            if self.circuit_ctrl:
                self.circuit_ctrl._notify("simulation_completed", result)
            return result

        # 6. Parse results
        result = self._parse_results(
            output_file=output_file,
            wrdata_filepath=wrdata_filepath,
            netlist=netlist,
            raw_output=stdout,
            warnings=validation.warnings,
        )

        # Phase 5: Notify simulation completed
        if self.circuit_ctrl:
            self.circuit_ctrl._notify("simulation_completed", result)

        return result

    def _parse_results(
        self,
        output_file: str,
        wrdata_filepath: str,
        netlist: str,
        raw_output: str,
        warnings: list[str],
    ) -> SimulationResult:
        """Parse simulation results based on analysis type."""
        from simulation import ResultParser

        analysis = self.model.analysis_type

        try:
            if analysis == "DC Operating Point":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_op_results(output)
            elif analysis == "DC Sweep":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_dc_results(output)
            elif analysis == "AC Sweep":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_ac_results(output)
            elif analysis == "Transient":
                data = ResultParser.parse_transient_results(wrdata_filepath)
            elif analysis == "Temperature Sweep":
                # Temperature sweep runs DC OP at each temp; parse as OP
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_op_results(output)
            else:
                return SimulationResult(
                    success=False,
                    error=f"Unknown analysis type: {analysis}",
                )

            return SimulationResult(
                success=True,
                analysis_type=analysis,
                data=data,
                netlist=netlist,
                raw_output=raw_output,
                output_file=output_file or "",
                wrdata_filepath=wrdata_filepath,
                warnings=warnings,
            )

        except (ValueError, IndexError, KeyError, OSError) as e:
            logger.error("Result parsing failed: %s", e, exc_info=True)
            return SimulationResult(
                success=False,
                error=f"Result parsing failed: {e}",
                netlist=netlist,
                raw_output=raw_output,
            )
