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

    def __init__(
        self,
        model: Optional[CircuitModel] = None,
        circuit_ctrl=None,
        preset_manager=None,
    ):
        self.model = model or CircuitModel()
        self.circuit_ctrl = circuit_ctrl  # Phase 5: For observer notifications
        self._runner = None
        self._preset_manager = preset_manager

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

    # --- Read-only query methods ---
    # Views should use these instead of accessing self.model directly.

    def get_analysis_type(self) -> str:
        """Return the current analysis type."""
        return self.model.analysis_type

    def get_analysis_params(self) -> dict:
        """Return a copy of the current analysis parameters."""
        return self.model.analysis_params.copy()

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
        from simulation.result_parser import ResultParseError

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
            elif analysis == "Sensitivity":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_sensitivity_results(output)
            elif analysis == "Transfer Function":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_tf_results(output)
            elif analysis == "Pole-Zero":
                output = self.runner.read_output(output_file)
                data = ResultParser.parse_pz_results(output)
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

        except (ResultParseError, ValueError, IndexError, KeyError, OSError) as e:
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
        if num_steps <= 1:
            sweep_values = [start]
        else:
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

        # Validate component IDs and save original state
        invalid_ids = [cid for cid in tolerances if cid not in self.model.components]
        if invalid_ids:
            logger.warning("Monte Carlo: ignoring unknown component IDs: %s", invalid_ids)
            tolerances = {cid: t for cid, t in tolerances.items() if cid not in invalid_ids}

        original_values = {}
        for cid in tolerances:
            original_values[cid] = self.model.components[cid].value

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
                        SimulationResult(
                            success=False,
                            error=stderr or "Simulation failed",
                            netlist=netlist,
                        )
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

    # --- Result analysis helpers ---

    @staticmethod
    def format_results_table(tran_data: dict) -> str:
        """Format transient data as a text table."""
        from simulation import ResultParser

        return ResultParser.format_results_as_table(tran_data)

    @staticmethod
    def compute_power_metrics(tran_data: dict, components: dict) -> tuple:
        """Compute transient power metrics for resistors.

        Returns:
            (power_metrics, summary_text) where *power_metrics* is a list of
            per-component metrics and *summary_text* is a pre-formatted string.
            If no metrics are available, returns ``([], "")``.
        """
        from simulation.power_metrics import compute_transient_power_metrics, format_power_summary

        metrics = compute_transient_power_metrics(tran_data, components)
        if metrics:
            return metrics, format_power_summary(metrics)
        return [], ""

    @staticmethod
    def compute_power(components, nodes, node_voltages) -> tuple:
        """Calculate power dissipation for all components.

        Returns:
            (power_data, total) — *power_data* is a dict mapping component ID
            to power value; *total* is the summed total power.
        """
        from simulation.power_calculator import calculate_power, total_power

        power_data = calculate_power(components, nodes, node_voltages)
        if power_data:
            return power_data, total_power(power_data)
        return {}, 0.0

    @staticmethod
    def compute_frequency_markers(frequencies, magnitude, phase=None) -> dict:
        """Compute frequency response markers from AC sweep data."""
        from simulation.freq_markers import compute_markers

        return compute_markers(frequencies, magnitude, phase)

    @staticmethod
    def compute_signal_fft(time, signal, signal_name, window_type="hamming"):
        """Compute FFT spectrum for a transient signal."""
        from simulation.fft_analysis import analyze_signal_spectrum

        return analyze_signal_spectrum(time, signal, signal_name, window_type)

    @staticmethod
    def compute_mc_statistics(values) -> dict:
        """Compute Monte Carlo statistics for a set of values."""
        from simulation.monte_carlo import compute_mc_statistics

        return compute_mc_statistics(values)

    @staticmethod
    def _format_sweep_value(value: float) -> str:
        """Format a float as a SPICE-compatible value string.

        Delegates to the canonical implementation in simulation.monte_carlo.
        """
        from simulation.monte_carlo import format_spice_value

        return format_spice_value(value)

    # --- Preset management ---

    @property
    def preset_manager(self):
        """Lazy initialization of PresetManager."""
        if self._preset_manager is None:
            from simulation.preset_manager import PresetManager

            self._preset_manager = PresetManager()
        return self._preset_manager

    def get_presets(self, analysis_type=None):
        """Return presets, optionally filtered by analysis type."""
        return self.preset_manager.get_presets(analysis_type)

    def get_preset_by_name(self, name, analysis_type=None):
        """Look up a preset by name (and optionally analysis type)."""
        return self.preset_manager.get_preset_by_name(name, analysis_type)

    def save_preset(self, name, analysis_type, params):
        """Save a user preset. Raises ValueError for built-in presets."""
        return self.preset_manager.save_preset(name, analysis_type, params)

    def delete_preset(self, name, analysis_type=None):
        """Delete a user preset. Returns True if deleted."""
        return self.preset_manager.delete_preset(name, analysis_type)

    @staticmethod
    def generate_analysis_command(analysis_type: str, params: dict) -> str:
        """Generate a SPICE analysis directive from type and parameters."""
        from simulation.netlist_generator import generate_analysis_command

        return generate_analysis_command(analysis_type, params)

    # --- Measurement / analysis metadata ---

    @staticmethod
    def get_analysis_domain_map() -> dict:
        """Return mapping of analysis types to measurement domains."""
        from simulation.measurement_builder import ANALYSIS_DOMAIN_MAP

        return ANALYSIS_DOMAIN_MAP

    @staticmethod
    def get_meas_types() -> dict:
        """Return the measurement type definitions."""
        from simulation.measurement_builder import MEAS_TYPES

        return MEAS_TYPES

    @staticmethod
    def build_meas_directive(domain: str, name: str, meas_type: str, params: dict) -> str:
        """Build a .meas directive string."""
        from simulation.measurement_builder import build_directive

        return build_directive(domain, name, meas_type, params)

    # --- Monte Carlo metadata ---

    @staticmethod
    def get_mc_eligible_types() -> set:
        """Return the set of component types eligible for Monte Carlo analysis."""
        from simulation.monte_carlo import MC_ELIGIBLE_TYPES

        return MC_ELIGIBLE_TYPES

    @staticmethod
    def get_mc_default_tolerance(component_type: str) -> float:
        """Return the default tolerance percentage for a component type."""
        from simulation.monte_carlo import DEFAULT_TOLERANCES

        return DEFAULT_TOLERANCES.get(component_type, 5.0)

    # --- Export helpers ---

    def export_netlist(self, filepath: str) -> None:
        """Generate a SPICE netlist and write it to a file.

        Raises:
            ValueError, KeyError, TypeError: If netlist generation fails.
            OSError: If the file cannot be written.
        """
        netlist = self.generate_netlist()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(netlist)

    def generate_results_csv(self, results, results_type: str, circuit_name: str = "") -> Optional[str]:
        """Generate CSV content from simulation results.

        Returns None if the results type is not supported for CSV export.
        """
        from simulation.csv_exporter import (
            export_ac_results,
            export_dc_sweep_results,
            export_noise_results,
            export_op_results,
            export_transient_results,
        )

        dispatch = {
            "DC Operating Point": export_op_results,
            "DC Sweep": export_dc_sweep_results,
            "AC Sweep": export_ac_results,
            "Transient": export_transient_results,
            "Noise": export_noise_results,
        }
        func = dispatch.get(results_type)
        if func is None:
            return None
        return func(results, circuit_name)

    def export_results_csv(self, results, results_type: str, filepath: str, circuit_name: str = "") -> None:
        """Export simulation results to a CSV file.

        Raises:
            OSError: If the file cannot be written.
        """
        from simulation.csv_exporter import write_csv

        content = self.generate_results_csv(results, results_type, circuit_name)
        if content is not None:
            write_csv(content, filepath)

    def export_results_excel(self, results, results_type: str, filepath: str, circuit_name: str = "") -> None:
        """Export simulation results to an Excel (.xlsx) file.

        Raises:
            OSError: If the file cannot be written.
        """
        from simulation.excel_exporter import export_to_excel

        export_to_excel(results, results_type, filepath, circuit_name)

    def generate_results_markdown(self, results, results_type: str, circuit_name: str = "") -> Optional[str]:
        """Generate Markdown content from simulation results.

        Returns None if the results type is not supported.
        """
        from simulation.markdown_exporter import (
            export_ac_results,
            export_dc_sweep_results,
            export_noise_results,
            export_op_results,
            export_transient_results,
        )

        dispatch = {
            "DC Operating Point": export_op_results,
            "DC Sweep": export_dc_sweep_results,
            "AC Sweep": export_ac_results,
            "Transient": export_transient_results,
            "Noise": export_noise_results,
        }
        func = dispatch.get(results_type)
        if func is None:
            return None
        return func(results, circuit_name)

    def export_results_markdown(self, results, results_type: str, filepath: str, circuit_name: str = "") -> None:
        """Export simulation results to a Markdown file.

        Raises:
            OSError: If the file cannot be written.
        """
        from simulation.markdown_exporter import write_markdown

        content = self.generate_results_markdown(results, results_type, circuit_name)
        if content is not None:
            write_markdown(content, filepath)

    def generate_circuitikz(self, **kwargs) -> str:
        """Generate CircuiTikZ LaTeX code from the current circuit model."""
        from simulation.circuitikz_exporter import generate

        self.model.rebuild_nodes()
        return generate(
            components=self.model.components,
            wires=self.model.wires,
            nodes=self.model.nodes,
            terminal_to_node=self.model.terminal_to_node,
            **kwargs,
        )

    @staticmethod
    def suggest_bundle_name(circuit_name: str) -> str:
        """Suggest a filename for a lab bundle export."""
        from simulation.bundle_exporter import suggest_bundle_name

        return suggest_bundle_name(circuit_name)

    @staticmethod
    def create_bundle(filepath: str, **kwargs) -> str:
        """Create a ZIP bundle of circuit artifacts for lab submission.

        Delegates to ``simulation.bundle_exporter.create_bundle``.
        Accepts the same keyword arguments (circuit_json, netlist,
        schematic_png, results_csv, etc.).
        """
        from simulation.bundle_exporter import create_bundle

        return create_bundle(filepath, **kwargs)
