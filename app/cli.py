"""
Command-line interface for Spice-GUI batch operations.

Run simulations, validate circuits, and export netlists without the GUI.

Usage::

    python -m cli simulate circuit.json
    python -m cli simulate circuit.json --format csv --output results.csv
    python -m cli validate circuit.json
    python -m cli export circuit.json --format cir --output circuit.cir
    python -m cli batch circuits/ --output-dir results/
    python -m cli repl
    python -m cli repl --load circuit.json
"""

import argparse
import glob
import json
import sys
from pathlib import Path

from controllers.circuit_controller import CircuitController
from controllers.file_controller import validate_circuit_data
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from simulation.csv_exporter import (
    export_ac_results,
    export_dc_sweep_results,
    export_noise_results,
    export_op_results,
    export_transient_results,
)


def try_load_circuit(filepath: str) -> tuple[CircuitModel | None, str]:
    """Load and validate a circuit JSON file without exiting.

    Args:
        filepath: Path to the circuit JSON file.

    Returns:
        (model, "") on success, or (None, error_message) on failure.
    """
    path = Path(filepath)
    if not path.exists():
        return None, f"file not found: {filepath}"

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in {filepath}: {e}"

    try:
        validate_circuit_data(data)
    except ValueError as e:
        return None, f"invalid circuit file: {e}"

    return CircuitModel.from_dict(data), ""


def load_circuit(filepath: str) -> CircuitModel:
    """Load and validate a circuit JSON file.

    Args:
        filepath: Path to the circuit JSON file.

    Returns:
        A populated CircuitModel.

    Raises:
        SystemExit: On file read or validation errors.
    """
    model, error = try_load_circuit(filepath)
    if model is None:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    return model


def cmd_simulate(args: argparse.Namespace) -> int:
    """Run simulation and output results."""
    model = load_circuit(args.circuit)
    controller = CircuitController(model)
    sim = SimulationController(model, controller)

    # Override analysis if specified
    if args.analysis:
        sim.set_analysis(args.analysis)

    result = sim.run_simulation()

    if not result.success:
        print(f"Simulation failed: {result.error}", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    output_text = _format_result(result, args.format, Path(args.circuit).stem)

    if args.output:
        Path(args.output).write_text(output_text)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output_text)

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a circuit without simulating."""
    model = load_circuit(args.circuit)
    sim = SimulationController(model)

    result = sim.validate_circuit()

    if result.success:
        print(f"Circuit is valid: {args.circuit}")
        for warning in result.warnings:
            print(f"  Warning: {warning}")
        return 0
    else:
        print(f"Circuit has errors: {args.circuit}", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """Export circuit in the specified format."""
    model = load_circuit(args.circuit)

    fmt = args.format
    if fmt == "cir":
        controller = CircuitController(model)
        sim = SimulationController(model, controller)
        try:
            netlist = sim.generate_netlist()
        except (ValueError, KeyError, TypeError) as e:
            print(f"Error generating netlist: {e}", file=sys.stderr)
            return 1

        if args.output:
            Path(args.output).write_text(netlist)
            print(f"Netlist written to {args.output}", file=sys.stderr)
        else:
            print(netlist)
        return 0

    elif fmt == "json":
        data = model.to_dict()
        output_text = json.dumps(data, indent=2)
        if args.output:
            Path(args.output).write_text(output_text)
            print(f"JSON written to {args.output}", file=sys.stderr)
        else:
            print(output_text)
        return 0

    else:
        print(f"Error: unsupported export format '{fmt}'", file=sys.stderr)
        print("Supported formats: cir, json", file=sys.stderr)
        return 1


def _format_result(result, fmt: str, circuit_name: str = "") -> str:
    """Format simulation result as text."""
    if fmt == "json":
        return _result_to_json(result)
    elif fmt == "csv":
        return _result_to_csv(result, circuit_name)
    else:
        return _result_to_json(result)


def _result_to_json(result) -> str:
    """Format simulation result as JSON."""
    output = {
        "success": result.success,
        "analysis_type": result.analysis_type,
        "data": result.data,
    }
    if result.warnings:
        output["warnings"] = result.warnings
    if result.netlist:
        output["netlist"] = result.netlist
    return json.dumps(output, indent=2, default=str)


def _result_to_csv(result, circuit_name: str = "") -> str:
    """Format simulation result as CSV using existing exporters."""
    analysis = result.analysis_type
    data = result.data

    if analysis == "DC Operating Point":
        voltages = data.get("node_voltages", {})
        return export_op_results(voltages, circuit_name)
    elif analysis == "DC Sweep":
        return export_dc_sweep_results(data, circuit_name)
    elif analysis == "AC Sweep":
        return export_ac_results(data, circuit_name)
    elif analysis == "Transient":
        return export_transient_results(data, circuit_name)
    elif analysis == "Noise":
        return export_noise_results(data, circuit_name)
    else:
        # Fall back to JSON for unsupported analysis types
        return _result_to_json(result)


def cmd_batch(args: argparse.Namespace) -> int:
    """Run simulations on multiple circuit files."""
    # Resolve input files
    pattern = args.path
    path = Path(pattern)
    if path.is_dir():
        files = sorted(path.glob("*.json"))
    elif "*" in pattern or "?" in pattern:
        files = sorted(Path(p) for p in glob.glob(pattern))
    else:
        print(f"Error: {pattern} is not a directory or glob pattern", file=sys.stderr)
        return 1

    if not files:
        print(f"No .json circuit files found matching: {pattern}", file=sys.stderr)
        return 1

    # Create output directory if specified
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    fmt = args.format
    results_summary = []
    any_failed = False

    for filepath in files:
        name = filepath.stem
        model, error = try_load_circuit(str(filepath))

        if model is None:
            results_summary.append({"file": filepath.name, "status": "LOAD_ERROR", "error": error})
            any_failed = True
            if args.fail_fast:
                break
            continue

        controller = CircuitController(model)
        sim = SimulationController(model, controller)

        if args.analysis:
            sim.set_analysis(args.analysis)

        result = sim.run_simulation()

        if not result.success:
            results_summary.append({"file": filepath.name, "status": "FAIL", "error": result.error})
            any_failed = True
            if args.fail_fast:
                break
            continue

        results_summary.append(
            {
                "file": filepath.name,
                "status": "OK",
                "analysis": result.analysis_type,
            }
        )

        # Write per-file results if output directory specified
        if output_dir:
            ext = "csv" if fmt == "csv" else "json"
            out_path = output_dir / f"{name}.{ext}"
            out_path.write_text(_format_result(result, fmt, name))

    # Print summary table
    print(f"\n{'File':<40} {'Status':<12} {'Details'}")
    print("-" * 70)
    for entry in results_summary:
        status = entry["status"]
        details = entry.get("analysis", entry.get("error", ""))
        print(f"{entry['file']:<40} {status:<12} {details}")

    total = len(results_summary)
    passed = sum(1 for e in results_summary if e["status"] == "OK")
    failed = total - passed
    print(f"\n{passed}/{total} succeeded, {failed} failed")

    return 1 if any_failed else 0


REPL_BANNER = """\
Spice-GUI Interactive REPL
==========================

Available objects:
  Circuit          - create and manipulate circuits
  SimulationResult - simulation result type
  COMPONENT_TYPES  - list of all supported component types

Quick start:
  c = Circuit()
  c.add_component("Voltage Source", "5V")
  c.add_component("Resistor", "1k")
  c.add_component("Ground")
  c.add_wire("V1", 0, "R1", 0)
  c.add_wire("R1", 1, "V1", 1)
  c.add_wire("V1", 1, "GND1", 0)
  result = c.simulate()
  print(result.data)
"""


def build_repl_namespace(load_path: str | None = None) -> dict:
    """Build the namespace dict for the interactive REPL.

    Args:
        load_path: Optional path to a circuit JSON file to pre-load.

    Returns:
        Dict of names to inject into the REPL namespace.
    """
    from controllers.simulation_controller import SimulationResult
    from models.component import COMPONENT_TYPES
    from scripting.circuit import Circuit

    namespace = {
        "Circuit": Circuit,
        "SimulationResult": SimulationResult,
        "COMPONENT_TYPES": COMPONENT_TYPES,
    }

    if load_path:
        model, error = try_load_circuit(load_path)
        if model is None:
            print(f"Warning: could not load {load_path}: {error}", file=sys.stderr)
        else:
            namespace["circuit"] = Circuit(model)
            print(f"Loaded circuit from {load_path} as 'circuit'", file=sys.stderr)

    return namespace


def cmd_repl(args: argparse.Namespace) -> int:
    """Launch an interactive Python REPL with the scripting API."""
    namespace = build_repl_namespace(getattr(args, "load", None))

    try:
        from IPython import start_ipython

        start_ipython(argv=[], user_ns=namespace, display_banner=False)
        return 0
    except ImportError:
        pass

    import code

    code.interact(banner=REPL_BANNER, local=namespace)
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Import a SPICE netlist and convert to circuit JSON."""
    from simulation.netlist_parser import NetlistParseError, import_netlist

    filepath = Path(args.netlist)
    if not filepath.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        return 1

    try:
        text = filepath.read_text()
    except OSError as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return 1

    try:
        model, analysis = import_netlist(text)
    except NetlistParseError as e:
        print(f"Error parsing netlist: {e}", file=sys.stderr)
        return 1

    if analysis:
        model.analysis_type = analysis["type"]
        model.analysis_params = analysis["params"]

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = filepath.with_suffix(".json")

    data = model.to_dict()
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Imported {filepath.name} -> {out_path}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="spice-gui-cli",
        description="Spice-GUI batch operations — simulate, validate, and export circuits from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Run simulation and output results")
    sim_parser.add_argument("circuit", help="Path to circuit JSON file")
    sim_parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")
    sim_parser.add_argument("--output", "-o", help="Write results to file instead of stdout")
    sim_parser.add_argument(
        "--analysis",
        choices=["DC Operating Point", "DC Sweep", "AC Sweep", "Transient", "Temperature Sweep", "Noise"],
        help="Override the analysis type configured in the circuit file",
    )

    # validate
    val_parser = subparsers.add_parser("validate", help="Check circuit for errors without simulating")
    val_parser.add_argument("circuit", help="Path to circuit JSON file")

    # export
    exp_parser = subparsers.add_parser("export", help="Export circuit in specified format")
    exp_parser.add_argument("circuit", help="Path to circuit JSON file")
    exp_parser.add_argument(
        "--format", "-f", choices=["cir", "json"], default="cir", help="Export format (default: cir)"
    )
    exp_parser.add_argument("--output", "-o", help="Write output to file instead of stdout")

    # batch
    batch_parser = subparsers.add_parser("batch", help="Run simulations on multiple circuit files")
    batch_parser.add_argument("path", help="Directory or glob pattern matching circuit JSON files")
    batch_parser.add_argument(
        "--format", choices=["json", "csv"], default="json", help="Output format for per-file results (default: json)"
    )
    batch_parser.add_argument("--output-dir", help="Write per-file results to this directory")
    batch_parser.add_argument(
        "--analysis",
        choices=["DC Operating Point", "DC Sweep", "AC Sweep", "Transient", "Temperature Sweep", "Noise"],
        help="Override the analysis type for all circuits",
    )
    batch_parser.add_argument("--fail-fast", action="store_true", help="Stop on first error")

    # repl
    repl_parser = subparsers.add_parser("repl", help="Launch interactive Python REPL with scripting API")
    repl_parser.add_argument("--load", help="Pre-load a circuit JSON file as 'circuit' variable")

    # import
    import_parser = subparsers.add_parser("import", help="Import a SPICE netlist to circuit JSON")
    import_parser.add_argument("netlist", help="Path to SPICE netlist file (.cir, .spice, .sp)")
    import_parser.add_argument("--output", "-o", help="Output JSON file path (default: same name with .json extension)")

    return parser


def main(argv=None) -> int:
    """CLI entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "simulate": cmd_simulate,
        "validate": cmd_validate,
        "export": cmd_export,
        "batch": cmd_batch,
        "repl": cmd_repl,
        "import": cmd_import,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
