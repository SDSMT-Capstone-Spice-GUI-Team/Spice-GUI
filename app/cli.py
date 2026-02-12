"""
Command-line interface for Spice-GUI batch operations.

Run simulations, validate circuits, and export netlists without the GUI.

Usage::

    python -m cli simulate circuit.json
    python -m cli simulate circuit.json --format csv --output results.csv
    python -m cli validate circuit.json
    python -m cli export circuit.json --format cir --output circuit.cir
"""

import argparse
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


def load_circuit(filepath: str) -> CircuitModel:
    """Load and validate a circuit JSON file.

    Args:
        filepath: Path to the circuit JSON file.

    Returns:
        A populated CircuitModel.

    Raises:
        SystemExit: On file read or validation errors.
    """
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        validate_circuit_data(data)
    except ValueError as e:
        print(f"Error: invalid circuit file: {e}", file=sys.stderr)
        sys.exit(1)

    return CircuitModel.from_dict(data)


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

    return parser


def main(argv=None) -> int:
    """CLI entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "simulate": cmd_simulate,
        "validate": cmd_validate,
        "export": cmd_export,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
