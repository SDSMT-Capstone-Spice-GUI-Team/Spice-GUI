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
    measurements: Optional[dict] = None


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

    def generate_netlist(
        self,
        wrdata_filepath: Optional[str] = None,
        spice_options: Optional[dict] = None,
        measurements: Optional[list] = None,
    ) -> str:
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
            spice_options=spice_options,
            measurements=measurements,
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

        # 3. Generate netlist (include .meas directives if configured)
        meas_directives = self.model.analysis_params.get("measurements", [])
        try:
            netlist = self.generate_netlist(
                wrdata_filepath=wrdata_filepath,
                measurements=meas_directives,
            )
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
            # Classify the error and attempt retry with relaxed tolerances
            from simulation.convergence import RELAXED_OPTIONS, diagnose_error, format_user_message, is_retriable

            diagnosis = diagnose_error(stderr, stdout)
            friendly_msg = format_user_message(diagnosis)

            if is_retriable(diagnosis.category):
                # Retry with relaxed tolerances
                try:
                    relaxed_netlist = self.generate_netlist(
                        wrdata_filepath=wrdata_filepath,
                        spice_options=RELAXED_OPTIONS,
                    )
                except (ValueError, KeyError, TypeError):
                    relaxed_netlist = None

                if relaxed_netlist:
                    retry_ok, retry_out, retry_stdout, retry_stderr = self.runner.run_simulation(relaxed_netlist)
                    if retry_ok:
                        # Parse retried results, add warning about relaxed tolerances
                        result = self._parse_results(
                            output_file=retry_out,
                            wrdata_filepath=wrdata_filepath,
                            netlist=relaxed_netlist,
                            raw_output=retry_stdout,
                            warnings=validation.warnings
                            + ["Simulation converged with relaxed tolerances (results may be less accurate)."],
                        )
                        if self.circuit_ctrl:
                            self.circuit_ctrl._notify("simulation_completed", result)
                        return result

            result = SimulationResult(
                success=False,
                error=friendly_msg,
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
            elif analysis == "Noise":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_noise_results(output)
            else:
                return SimulationResult(
                    success=False,
                    error=f"Unknown analysis type: {analysis}",
                )

            # Parse any .meas measurement results from stdout
            meas_results = ResultParser.parse_measurement_results(raw_output)

            return SimulationResult(
                success=True,
                analysis_type=analysis,
                data=data,
                netlist=netlist,
                raw_output=raw_output,
                output_file=output_file or "",
                wrdata_filepath=wrdata_filepath,
                warnings=warnings,
                measurements=meas_results,
            )

        except (ValueError, IndexError, KeyError, OSError) as e:
            logger.error("Result parsing failed: %s", e, exc_info=True)
            return SimulationResult(
                success=False,
                error=f"Result parsing failed: {e}",
                netlist=netlist,
                raw_output=raw_output,
            )

    def run_parameter_sweep(self, sweep_config: dict, progress_callback=None) -> SimulationResult:
        """
        Run a parameter sweep: modify a component's value across a range
        and run the base analysis at each step.

        Args:
            sweep_config: dict with keys component_id, start, stop, num_steps,
                          base_analysis_type, base_params
            progress_callback: optional callable(step_index, total_steps) -> bool.
                               Return False to cancel the sweep.

        Returns:
            SimulationResult with analysis_type="Parameter Sweep" and data
            containing sweep results.
        """
        component_id = sweep_config["component_id"]
        start = sweep_config["start"]
        stop = sweep_config["stop"]
        num_steps = sweep_config["num_steps"]
        base_type = sweep_config["base_analysis_type"]
        base_params = sweep_config["base_params"]

        comp = self.model.components.get(component_id)
        if comp is None:
            return SimulationResult(
                success=False,
                error=f"Component {component_id} not found in circuit",
            )

        # Save original state
        original_value = comp.value
        original_analysis = self.model.analysis_type
        original_params = self.model.analysis_params.copy()

        # Set base analysis for netlist generation
        self.set_analysis(base_type, base_params)

        # Validate once
        validation = self.validate_circuit()
        if not validation.success:
            self.set_analysis(original_analysis, original_params)
            return validation

        # Find ngspice once
        ngspice_path = self.runner.find_ngspice()
        if ngspice_path is None:
            self.set_analysis(original_analysis, original_params)
            return SimulationResult(
                success=False,
                error="ngspice executable not found. Please install ngspice.",
            )

        # Calculate sweep values (linear spacing)
        sweep_values = [start + (stop - start) * i / (num_steps - 1) for i in range(num_steps)]

        # Run sweep
        step_results = []
        errors = []
        cancelled = False

        try:
            for i, val in enumerate(sweep_values):
                # Check for cancellation
                if progress_callback and not progress_callback(i, num_steps):
                    cancelled = True
                    break

                comp.value = self._format_sweep_value(val)

                # Generate netlist
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                wrdata_filepath = os.path.join(self.runner.output_dir, f"wrdata_sweep_{i}_{timestamp}.txt")

                try:
                    netlist = self.generate_netlist(wrdata_filepath=wrdata_filepath)
                except (ValueError, KeyError, TypeError) as e:
                    step_results.append(SimulationResult(success=False, error=f"Netlist generation failed: {e}"))
                    errors.append(f"Step {i + 1} ({comp.value}): netlist failed: {e}")
                    continue

                # Run simulation
                success, output_file, stdout, stderr = self.runner.run_simulation(netlist)
                if not success:
                    step_results.append(
                        SimulationResult(
                            success=False,
                            error=stderr or "Simulation failed",
                            netlist=netlist,
                            raw_output=stdout,
                        )
                    )
                    errors.append(f"Step {i + 1} ({comp.value}): {stderr or 'failed'}")
                    continue

                # Parse results
                result = self._parse_results(
                    output_file=output_file,
                    wrdata_filepath=wrdata_filepath,
                    netlist=netlist,
                    raw_output=stdout,
                    warnings=validation.warnings,
                )
                step_results.append(result)

                if not result.success:
                    errors.append(f"Step {i + 1} ({comp.value}): {result.error}")
        finally:
            # Restore original state
            comp.value = original_value
            self.set_analysis(original_analysis, original_params)

        # Trim sweep_values to match actual results if cancelled
        actual_values = sweep_values[: len(step_results)]

        sweep_data = {
            "component_id": component_id,
            "component_type": comp.component_type,
            "sweep_values": actual_values,
            "base_analysis_type": base_type,
            "results": step_results,
            "num_steps": len(step_results),
            "cancelled": cancelled,
        }

        any_success = any(r.success for r in step_results)

        return SimulationResult(
            success=any_success,
            analysis_type="Parameter Sweep",
            data=sweep_data,
            errors=errors,
            warnings=validation.warnings,
        )

    def run_monte_carlo(self, mc_config: dict, progress_callback=None) -> SimulationResult:
        """
        Run Monte Carlo analysis: vary component values randomly and run
        the base analysis N times.

        Args:
            mc_config: dict with keys:
                num_runs, base_analysis_type, base_params, tolerances
            progress_callback: optional callable(step, total) -> bool.

        Returns:
            SimulationResult with analysis_type='Monte Carlo'.
        """
        import numpy as np
        from simulation.monte_carlo import apply_tolerance

        num_runs = mc_config["num_runs"]
        base_type = mc_config["base_analysis_type"]
        base_params = mc_config["base_params"]
        tolerances = mc_config.get("tolerances", {})

        # Save original state
        original_values = {}
        for cid in tolerances:
            comp = self.model.components.get(cid)
            if comp:
                original_values[cid] = comp.value

        original_analysis = self.model.analysis_type
        original_params = self.model.analysis_params.copy()

        self.set_analysis(base_type, base_params)

        validation = self.validate_circuit()
        if not validation.success:
            self.set_analysis(original_analysis, original_params)
            return validation

        ngspice_path = self.runner.find_ngspice()
        if ngspice_path is None:
            self.set_analysis(original_analysis, original_params)
            return SimulationResult(
                success=False,
                error="ngspice executable not found. Please install ngspice.",
            )

        rng = np.random.default_rng()
        step_results = []
        run_values = []
        errors = []
        cancelled = False

        try:
            for i in range(num_runs):
                if progress_callback and not progress_callback(i, num_runs):
                    cancelled = True
                    break

                values_this_run = {}
                for cid, tol_config in tolerances.items():
                    comp = self.model.components.get(cid)
                    if comp is None:
                        continue
                    new_val = apply_tolerance(
                        original_values[cid],
                        tol_config["tolerance_pct"],
                        tol_config.get("distribution", "gaussian"),
                        rng,
                    )
                    comp.value = new_val
                    values_this_run[cid] = new_val

                run_values.append(values_this_run)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                wrdata_filepath = os.path.join(self.runner.output_dir, f"wrdata_mc_{i}_{timestamp}.txt")

                try:
                    netlist = self.generate_netlist(wrdata_filepath=wrdata_filepath)
                except (ValueError, KeyError, TypeError) as e:
                    step_results.append(SimulationResult(success=False, error=f"Netlist generation failed: {e}"))
                    errors.append(f"Run {i + 1}: netlist failed: {e}")
                    continue

                success, output_file, stdout, stderr = self.runner.run_simulation(netlist)
                if not success:
                    step_results.append(
                        SimulationResult(success=False, error=stderr or "Simulation failed", netlist=netlist)
                    )
                    errors.append(f"Run {i + 1}: {stderr or 'failed'}")
                    continue

                result = self._parse_results(
                    output_file=output_file,
                    wrdata_filepath=wrdata_filepath,
                    netlist=netlist,
                    raw_output=stdout,
                    warnings=validation.warnings,
                )
                step_results.append(result)
                if not result.success:
                    errors.append(f"Run {i + 1}: {result.error}")
        finally:
            for cid, orig_val in original_values.items():
                comp = self.model.components.get(cid)
                if comp:
                    comp.value = orig_val
            self.set_analysis(original_analysis, original_params)

        any_success = any(r.success for r in step_results)

        mc_data = {
            "num_runs": len(step_results),
            "base_analysis_type": base_type,
            "tolerances": tolerances,
            "run_values": run_values,
            "results": step_results,
            "cancelled": cancelled,
        }

        return SimulationResult(
            success=any_success,
            analysis_type="Monte Carlo",
            data=mc_data,
            errors=errors,
            warnings=validation.warnings,
        )

    @staticmethod
    def _format_sweep_value(value: float) -> str:
        """Format a float as a SPICE-compatible value string.

        Delegates to the canonical implementation in simulation.monte_carlo.
        """
        from simulation.monte_carlo import format_spice_value

        return format_spice_value(value)
