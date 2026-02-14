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

__version__ = "0.1.0"
from simulation.csv_exporter import (export_ac_results,
                                     export_dc_sweep_results,
                                     export_noise_results, export_op_results,
                                     export_transient_results)


def try_load_circuit(filepath: str) -> tuple[CircuitModel | None, str]:
    """Load and validate a circuit JSON file without exiting.

    Args:
        filepath: Path to the circuit JSON file, or "-" to read from stdin.

    Returns:
        (model, "") on success, or (None, error_message) on failure.
    """
    if filepath == "-":
        return _load_circuit_from_text(sys.stdin.read(), "<stdin>")

    path = Path(filepath)
    if not path.exists():
        return None, f"file not found: {filepath}"

    try:
        with open(path, "r") as f:
            text = f.read()
    except OSError as e:
        return None, f"error reading {filepath}: {e}"

    return _load_circuit_from_text(text, filepath)


def _load_circuit_from_text(text: str, source: str) -> tuple[CircuitModel | None, str]:
    """Parse and validate circuit JSON text.

    Args:
        text: Raw JSON text.
        source: Source name for error messages.

    Returns:
        (model, "") on success, or (None, error_message) on failure.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in {source}: {e}"

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
            results_summary.append(
                {"file": filepath.name, "status": "LOAD_ERROR", "error": error}
            )
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
            results_summary.append(
                {"file": filepath.name, "status": "FAIL", "error": result.error}
            )
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


def diff_circuits(model_a: CircuitModel, model_b: CircuitModel) -> dict:
    """Compare two circuit models and return a structured diff.

    Args:
        model_a: The reference (baseline) circuit.
        model_b: The circuit to compare against the reference.

    Returns:
        Dict with keys: components, wires, analysis. Each contains
        lists of added/removed/changed items. Empty if identical.
    """
    diff: dict = {"components": {}, "wires": {}, "analysis": {}}

    # --- Components ---
    ids_a = set(model_a.components.keys())
    ids_b = set(model_b.components.keys())

    added = sorted(ids_b - ids_a)
    removed = sorted(ids_a - ids_b)
    changed = []

    for cid in sorted(ids_a & ids_b):
        ca = model_a.components[cid]
        cb = model_b.components[cid]
        changes = {}
        if ca.component_type != cb.component_type:
            changes["type"] = {"from": ca.component_type, "to": cb.component_type}
        if ca.value != cb.value:
            changes["value"] = {"from": ca.value, "to": cb.value}
        if ca.rotation != cb.rotation:
            changes["rotation"] = {"from": ca.rotation, "to": cb.rotation}
        if ca.position != cb.position:
            changes["position"] = {"from": list(ca.position), "to": list(cb.position)}
        if changes:
            changed.append({"id": cid, "changes": changes})

    comp_diff = {}
    if added:
        comp_diff["added"] = [
            {"id": cid, "type": model_b.components[cid].component_type} for cid in added
        ]
    if removed:
        comp_diff["removed"] = [
            {"id": cid, "type": model_a.components[cid].component_type}
            for cid in removed
        ]
    if changed:
        comp_diff["changed"] = changed
    diff["components"] = comp_diff

    # --- Wires ---
    def wire_key(w):
        return (
            w.start_component_id,
            w.start_terminal,
            w.end_component_id,
            w.end_terminal,
        )

    wires_a = {wire_key(w) for w in model_a.wires}
    wires_b = {wire_key(w) for w in model_b.wires}

    wire_added = sorted(wires_b - wires_a)
    wire_removed = sorted(wires_a - wires_b)

    wire_diff = {}
    if wire_added:
        wire_diff["added"] = [
            {"start": f"{k[0]}:{k[1]}", "end": f"{k[2]}:{k[3]}"} for k in wire_added
        ]
    if wire_removed:
        wire_diff["removed"] = [
            {"start": f"{k[0]}:{k[1]}", "end": f"{k[2]}:{k[3]}"} for k in wire_removed
        ]
    diff["wires"] = wire_diff

    # --- Analysis ---
    analysis_diff = {}
    if model_a.analysis_type != model_b.analysis_type:
        analysis_diff["type"] = {
            "from": model_a.analysis_type,
            "to": model_b.analysis_type,
        }
    if model_a.analysis_params != model_b.analysis_params:
        analysis_diff["params"] = {
            "from": model_a.analysis_params,
            "to": model_b.analysis_params,
        }
    diff["analysis"] = analysis_diff

    return diff


def _is_empty_diff(diff: dict) -> bool:
    """Check if a diff result represents identical circuits."""
    return not diff["components"] and not diff["wires"] and not diff["analysis"]


def _format_diff_text(diff: dict, name_a: str, name_b: str) -> str:
    """Format a circuit diff as human-readable text."""
    lines = [f"Comparing {name_a} vs {name_b}", ""]

    if _is_empty_diff(diff):
        lines.append("Circuits are identical.")
        return "\n".join(lines)

    # Components
    comp = diff["components"]
    if comp:
        lines.append("Components:")
        for item in comp.get("added", []):
            lines.append(f"  + {item['id']} ({item['type']})")
        for item in comp.get("removed", []):
            lines.append(f"  - {item['id']} ({item['type']})")
        for item in comp.get("changed", []):
            lines.append(f"  ~ {item['id']}:")
            for field, vals in item["changes"].items():
                lines.append(f"      {field}: {vals['from']} -> {vals['to']}")
        lines.append("")

    # Wires
    wire = diff["wires"]
    if wire:
        lines.append("Wires:")
        for item in wire.get("added", []):
            lines.append(f"  + {item['start']} -- {item['end']}")
        for item in wire.get("removed", []):
            lines.append(f"  - {item['start']} -- {item['end']}")
        lines.append("")

    # Analysis
    analysis = diff["analysis"]
    if analysis:
        lines.append("Analysis:")
        if "type" in analysis:
            lines.append(
                f"  type: {analysis['type']['from']} -> {analysis['type']['to']}"
            )
        if "params" in analysis:
            lines.append(
                f"  params: {analysis['params']['from']} -> {analysis['params']['to']}"
            )
        lines.append("")

    return "\n".join(lines)


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare two circuit files and report differences."""
    model_a = load_circuit(args.circuit_a)
    model_b = load_circuit(args.circuit_b)

    diff = diff_circuits(model_a, model_b)
    identical = _is_empty_diff(diff)

    fmt = args.format
    if fmt == "json":
        print(json.dumps(diff, indent=2, default=str))
    else:
        print(
            _format_diff_text(
                diff, Path(args.circuit_a).name, Path(args.circuit_b).name
            )
        )

    return 0 if identical else 1


def circuit_stats(model: CircuitModel) -> dict:
    """Compute circuit complexity statistics.

    Args:
        model: The CircuitModel to analyze.

    Returns:
        Dict with component counts, wire count, node count, etc.
    """
    type_counts = {}
    for comp in model.components.values():
        type_counts[comp.component_type] = type_counts.get(comp.component_type, 0) + 1

    has_ground = any(c.component_type == "Ground" for c in model.components.values())

    return {
        "components": {
            "total": len(model.components),
            "by_type": type_counts,
        },
        "wires": len(model.wires),
        "nodes": len(model.nodes),
        "has_ground": has_ground,
        "analysis_type": model.analysis_type,
        "analysis_params": model.analysis_params if model.analysis_params else {},
    }


def _format_stats_text(stats: dict, filename: str) -> str:
    """Format circuit stats as human-readable text."""
    lines = [f"Circuit: {filename}", ""]

    lines.append(f"Components: {stats['components']['total']}")
    for ctype, count in sorted(stats["components"]["by_type"].items()):
        lines.append(f"  {ctype}: {count}")

    lines.append(f"Wires: {stats['wires']}")
    lines.append(f"Nodes: {stats['nodes']}")
    lines.append(f"Ground: {'yes' if stats['has_ground'] else 'no'}")
    lines.append(f"Analysis: {stats['analysis_type']}")

    if stats["analysis_params"]:
        for key, val in stats["analysis_params"].items():
            lines.append(f"  {key}: {val}")

    return "\n".join(lines)


def cmd_stats(args: argparse.Namespace) -> int:
    """Display circuit complexity statistics."""
    model = load_circuit(args.circuit)
    stats = circuit_stats(model)

    if args.format == "json":
        print(json.dumps(stats, indent=2, default=str))
    else:
        print(_format_stats_text(stats, Path(args.circuit).name))

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="spice-gui-cli",
        description="Spice-GUI batch operations — simulate, validate, and export circuits from the command line.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # simulate
    sim_parser = subparsers.add_parser(
        "simulate", help="Run simulation and output results"
    )
    sim_parser.add_argument(
        "circuit", help="Path to circuit JSON file (use '-' for stdin)"
    )
    sim_parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)",
    )
    sim_parser.add_argument(
        "--output", "-o", help="Write results to file instead of stdout"
    )
    sim_parser.add_argument(
        "--analysis",
        choices=[
            "DC Operating Point",
            "DC Sweep",
            "AC Sweep",
            "Transient",
            "Temperature Sweep",
            "Noise",
        ],
        help="Override the analysis type configured in the circuit file",
    )

    # validate
    val_parser = subparsers.add_parser(
        "validate", help="Check circuit for errors without simulating"
    )
    val_parser.add_argument(
        "circuit", help="Path to circuit JSON file (use '-' for stdin)"
    )

    # export
    exp_parser = subparsers.add_parser(
        "export", help="Export circuit in specified format"
    )
    exp_parser.add_argument(
        "circuit", help="Path to circuit JSON file (use '-' for stdin)"
    )
    exp_parser.add_argument(
        "--format",
        "-f",
        choices=["cir", "json"],
        default="cir",
        help="Export format (default: cir)",
    )
    exp_parser.add_argument(
        "--output", "-o", help="Write output to file instead of stdout"
    )

    # batch
    batch_parser = subparsers.add_parser(
        "batch", help="Run simulations on multiple circuit files"
    )
    batch_parser.add_argument(
        "path", help="Directory or glob pattern matching circuit JSON files"
    )
    batch_parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format for per-file results (default: json)",
    )
    batch_parser.add_argument(
        "--output-dir", help="Write per-file results to this directory"
    )
    batch_parser.add_argument(
        "--analysis",
        choices=[
            "DC Operating Point",
            "DC Sweep",
            "AC Sweep",
            "Transient",
            "Temperature Sweep",
            "Noise",
        ],
        help="Override the analysis type for all circuits",
    )
    batch_parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first error"
    )

    # repl
    repl_parser = subparsers.add_parser(
        "repl", help="Launch interactive Python REPL with scripting API"
    )
    repl_parser.add_argument(
        "--load", help="Pre-load a circuit JSON file as 'circuit' variable"
    )

    # import
    import_parser = subparsers.add_parser(
        "import", help="Import a SPICE netlist to circuit JSON"
    )
    import_parser.add_argument(
        "netlist", help="Path to SPICE netlist file (.cir, .spice, .sp)"
    )
    import_parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file path (default: same name with .json extension)",
    )

    # diff
    diff_parser = subparsers.add_parser(
        "diff", help="Compare two circuit files and report differences"
    )
    diff_parser.add_argument("circuit_a", help="Path to reference circuit JSON file")
    diff_parser.add_argument("circuit_b", help="Path to circuit JSON file to compare")
    diff_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # stats
    stats_parser = subparsers.add_parser(
        "stats", help="Display circuit complexity statistics"
    )
    stats_parser.add_argument("circuit", help="Path to circuit JSON file")
    stats_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

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
        "diff": cmd_diff,
        "stats": cmd_stats,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
