"""Post-install smoke test suite.

Verifies that the application is correctly installed and functional:

1. **App importable** -- core modules can be loaded.
2. **ngspice found** -- an ngspice executable is available.
3. **Example loads** -- a bundled example circuit loads without error.
4. **Simulation runs** -- a basic DC operating-point simulation completes.

Usage from CLI::

    python -m cli selftest
    python -m main --selftest

Each check prints PASS or FAIL with an actionable error message.
The overall exit code is 0 when all checks pass, 1 otherwise.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckResult:
    """Outcome of a single smoke-test check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class SelftestResult:
    """Aggregate outcome of the full smoke-test suite."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def summary(self) -> str:
        total = len(self.checks)
        ok = sum(1 for c in self.checks if c.passed)
        return f"{ok}/{total} checks passed"


def _find_examples_dir() -> Path | None:
    """Locate the examples directory.

    Works both in development (app/examples/) and in a PyInstaller
    frozen bundle (where files land relative to sys._MEIPASS or the exe).
    """
    # PyInstaller frozen bundle
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = meipass / "examples"
        if candidate.is_dir():
            return candidate

    # Development layout: app/examples/
    app_dir = Path(__file__).resolve().parent.parent
    candidate = app_dir / "examples"
    if candidate.is_dir():
        return candidate

    return None


def check_imports() -> CheckResult:
    """Verify that core application modules can be imported."""
    try:
        import controllers.simulation_controller  # noqa: F401
        import models.circuit  # noqa: F401
        import simulation.ngspice_runner  # noqa: F401

        return CheckResult("Core imports", True, "models, simulation, controllers OK")
    except ImportError as e:
        return CheckResult("Core imports", False, f"Import failed: {e}")


def check_ngspice() -> CheckResult:
    """Verify that an ngspice executable can be found."""
    try:
        from simulation.ngspice_config import resolve_ngspice_path

        path = resolve_ngspice_path()
        if path:
            return CheckResult("ngspice found", True, path)
        return CheckResult("ngspice found", False, "No ngspice executable found on PATH or in bundle")
    except Exception as e:
        return CheckResult("ngspice found", False, str(e))


def check_example_load() -> CheckResult:
    """Verify that an example circuit file can be loaded."""
    examples = _find_examples_dir()
    if examples is None:
        return CheckResult("Example circuit loads", False, "Examples directory not found")

    # Pick the simplest example
    circuit_file = examples / "voltage_divider.json"
    if not circuit_file.is_file():
        # Fall back to any available .json
        json_files = sorted(examples.glob("*.json"))
        if not json_files:
            return CheckResult("Example circuit loads", False, "No .json files in examples/")
        circuit_file = json_files[0]

    try:
        from cli import try_load_circuit

        model, error = try_load_circuit(str(circuit_file))
        if model is None:
            return CheckResult("Example circuit loads", False, f"{circuit_file.name}: {error}")
        n_comp = len(model.components)
        n_wire = len(model.wires)
        return CheckResult("Example circuit loads", True, f"{circuit_file.name}: {n_comp} components, {n_wire} wires")
    except Exception as e:
        return CheckResult("Example circuit loads", False, str(e))


def check_simulation() -> CheckResult:
    """Verify that a basic DC operating-point simulation completes.

    This check requires ngspice to be available. If ngspice is not found
    the check is reported as FAIL with a hint to install ngspice.
    """
    examples = _find_examples_dir()
    if examples is None:
        return CheckResult("Basic simulation runs", False, "Examples directory not found")

    circuit_file = examples / "voltage_divider.json"
    if not circuit_file.is_file():
        json_files = sorted(examples.glob("*.json"))
        if not json_files:
            return CheckResult("Basic simulation runs", False, "No .json files in examples/")
        circuit_file = json_files[0]

    try:
        from cli import try_load_circuit
        from controllers.circuit_controller import CircuitController
        from controllers.simulation_controller import SimulationController

        model, error = try_load_circuit(str(circuit_file))
        if model is None:
            return CheckResult("Basic simulation runs", False, f"Load failed: {error}")

        controller = CircuitController(model)
        sim = SimulationController(model, controller)
        result = sim.run_simulation()

        if result.success:
            return CheckResult("Basic simulation runs", True, f"{result.analysis_type}: OK")
        return CheckResult("Basic simulation runs", False, result.error or "Simulation returned failure")
    except Exception as e:
        return CheckResult("Basic simulation runs", False, str(e))


def run_selftest() -> SelftestResult:
    """Execute all smoke-test checks and return the aggregate result."""
    result = SelftestResult()
    result.checks.append(check_imports())
    result.checks.append(check_ngspice())
    result.checks.append(check_example_load())
    result.checks.append(check_simulation())
    return result


def print_selftest(result: SelftestResult) -> None:
    """Print the selftest results to stdout in a human-readable format."""
    print("Spice GUI Self-Test")
    print("=" * 40)
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name}")
        if check.detail:
            print(f"         {check.detail}")
    print("-" * 40)
    print(result.summary)
    if not result.passed:
        print("\nSome checks failed. See details above for actionable errors.")
