"""
simulation/ngspice_runner.py

Handles execution of ngspice simulations
"""

import os
import subprocess
from datetime import datetime

from simulation.ngspice_config import resolve_ngspice_path
from simulation.spice_sanitizer import validate_output_dir
from utils.constants import SIMULATION_TIMEOUT


class NgspiceRunner:
    """Runs ngspice simulations and manages output files"""

    #: Environment variable that, when set to a truthy value (1/true/yes),
    #: suppresses automatic cleanup of temp simulation files.  Useful for
    #: debugging ngspice output by hand.
    KEEP_FILES_ENV_VAR = "SPICE_KEEP_SIM_OUTPUT"

    def __init__(self, output_dir="simulation_output", settings=None):
        self.output_dir = validate_output_dir(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.ngspice_cmd = None
        self._settings = settings
        # When True, temp files are never deleted (controlled by env var).
        self._keep_files: bool = os.environ.get(self.KEEP_FILES_ENV_VAR, "").lower() in (
            "1",
            "true",
            "yes",
        )
        # Paths written during the most-recently completed run; cleaned up at
        # the start of the next run so that results remain readable until then.
        self._prev_run_files: list[str] = []

    def _cleanup_prev_run(self) -> None:
        """Remove temp files written by the previous simulation run.

        Skipped when *SPICE_KEEP_SIM_OUTPUT* is set.  Uses best-effort
        deletion: missing or un-deletable files are silently ignored so that
        a stale path never prevents a new simulation from starting.
        """
        if self._keep_files:
            return
        for path in self._prev_run_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._prev_run_files = []

    def find_ngspice(self):
        """Find ngspice executable on the system.

        Delegates to :func:`simulation.ngspice_config.resolve_ngspice_path`
        which checks (in order): stored user preference, bundled copy,
        system PATH and well-known install directories.
        """
        result = resolve_ngspice_path(self._settings)
        if result:
            self.ngspice_cmd = result
        return result

    def run_simulation(self, netlist_content):
        """
        Run ngspice simulation with the given netlist

        Returns:
            tuple: (success: bool, output_file: str, stdout: str, stderr: str)
        """
        # Clean up temp files from the previous run before starting a new one.
        self._cleanup_prev_run()

        # Find ngspice if not already found
        if self.ngspice_cmd is None:
            ngspice_path = self.find_ngspice()
            if ngspice_path is None:
                return False, None, "", "ngspice executable not found"

        # Create timestamped filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        netlist_filename = os.path.join(self.output_dir, f"netlist_{timestamp}.cir")
        output_filename = os.path.join(self.output_dir, f"output_{timestamp}.txt")

        # Write netlist to file
        try:
            with open(netlist_filename, "w") as f:
                f.write(netlist_content)
        except OSError as e:
            return False, None, "", f"Failed to write netlist: {str(e)}"

        # Run ngspice
        try:
            result = subprocess.run(
                [self.ngspice_cmd, "-b", netlist_filename, "-o", output_filename],
                capture_output=True,
                text=True,
                timeout=SIMULATION_TIMEOUT,
            )

            # Check if output file was created and is non-empty
            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                # Track both files so the next run can clean them up.
                self._prev_run_files = [netlist_filename, output_filename]

                # Check exit code first — a non-zero return code means
                # ngspice encountered an error even if it wrote output (#508).
                if result.returncode != 0:
                    return False, output_filename, result.stdout, result.stderr

                # Detect convergence failures even when ngspice produces output.
                # ngspice may write partial output before aborting, so check
                # stderr and stdout for error patterns (#858).
                from simulation.convergence import ErrorCategory, classify_error

                error_category = classify_error(result.stderr or "", result.stdout or "")
                if error_category != ErrorCategory.UNKNOWN:
                    return False, output_filename, result.stdout, result.stderr
                return True, output_filename, result.stdout, result.stderr
            else:
                # Track the netlist for cleanup; output was not produced.
                self._prev_run_files = [netlist_filename]
                return (
                    False,
                    None,
                    result.stdout,
                    result.stderr or "Simulation produced no output",
                )

        except subprocess.TimeoutExpired:
            self._prev_run_files = [netlist_filename]
            return (
                False,
                None,
                "",
                f"Simulation timed out (>{SIMULATION_TIMEOUT} seconds)",
            )
        except (OSError, subprocess.SubprocessError) as e:
            self._prev_run_files = [netlist_filename]
            return False, None, "", f"Simulation error: {str(e)}"

    def read_output(self, output_filename):
        """Read simulation output file"""
        try:
            with open(output_filename, "r") as f:
                return f.read()
        except OSError as e:
            return f"Error reading output: {str(e)}"
