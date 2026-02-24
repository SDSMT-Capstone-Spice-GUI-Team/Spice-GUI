"""
simulation/markdown_exporter.py

Export simulation results to Markdown pipe-table format.
No Qt dependencies -- file dialog and clipboard are the view's responsibility.
"""

from datetime import datetime


def _fmt(value):
    """Format a numeric value to 6 significant figures."""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _header_comment(analysis_type, circuit_name=""):
    """Build the metadata comment block."""
    lines = [f"<!-- Analysis: {analysis_type} -->"]
    lines.append(f"<!-- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->")
    if circuit_name:
        lines.append(f"<!-- Circuit: {circuit_name} -->")
    lines.append("")
    return "\n".join(lines)


def _table(headers, rows, alignments=None):
    """Build a Markdown pipe table.

    Args:
        headers: list of column header strings
        rows: list of lists (each inner list = one row of cell values)
        alignments: list of 'l' or 'r' per column (default: first col left, rest right)
    """
    if alignments is None:
        alignments = ["l"] + ["r"] * (len(headers) - 1)

    sep = []
    for a in alignments:
        sep.append("---:" if a == "r" else ":---")

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(sep) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def export_op_results(node_voltages, circuit_name=""):
    """Export DC Operating Point results to Markdown string."""
    out = _header_comment("DC Operating Point", circuit_name)
    out += "## DC Operating Point\n\n"
    rows = [[node, _fmt(v)] for node, v in sorted(node_voltages.items())]
    out += _table(["Node", "Voltage (V)"], rows)
    out += "\n"
    return out


def export_dc_sweep_results(sweep_data, circuit_name=""):
    """Export DC Sweep results to Markdown string."""
    out = _header_comment("DC Sweep", circuit_name)
    out += "## DC Sweep\n\n"
    headers = sweep_data.get("headers", [])
    data = sweep_data.get("data", [])
    rows = [[_fmt(c) for c in row] for row in data]
    alignments = ["r"] * len(headers)
    out += _table(headers, rows, alignments)
    out += "\n"
    return out


def export_ac_results(ac_data, circuit_name=""):
    """Export AC Sweep results to Markdown string."""
    out = _header_comment("AC Sweep", circuit_name)
    out += "## AC Sweep\n\n"

    frequencies = ac_data.get("frequencies", [])
    magnitude = ac_data.get("magnitude", {})
    phase = ac_data.get("phase", {})
    all_nodes = sorted(set(magnitude.keys()) | set(phase.keys()))

    headers = ["Frequency (Hz)"]
    for node in all_nodes:
        if node in magnitude:
            headers.append(f"|V({node})|")
        if node in phase:
            headers.append(f"phase(V({node})) (deg)")

    rows = []
    for i, freq in enumerate(frequencies):
        row = [_fmt(freq)]
        for node in all_nodes:
            if node in magnitude:
                row.append(_fmt(magnitude[node][i]) if i < len(magnitude[node]) else "")
            if node in phase:
                row.append(_fmt(phase[node][i]) if i < len(phase[node]) else "")
        rows.append(row)

    alignments = ["r"] * len(headers)
    out += _table(headers, rows, alignments)
    out += "\n"
    return out


def export_transient_results(tran_data, circuit_name=""):
    """Export Transient analysis results to Markdown string."""
    out = _header_comment("Transient", circuit_name)
    out += "## Transient Analysis\n\n"

    if not tran_data:
        out += "_No data._\n"
        return out

    headers = list(tran_data[0].keys())
    rows = [[_fmt(row[h]) for h in headers] for row in tran_data]
    alignments = ["r"] * len(headers)
    out += _table(headers, rows, alignments)
    out += "\n"
    return out


def export_noise_results(noise_data, circuit_name=""):
    """Export Noise analysis results to Markdown string."""
    out = _header_comment("Noise", circuit_name)
    out += "## Noise Analysis\n\n"

    frequencies = noise_data.get("frequencies", [])
    onoise = noise_data.get("onoise_spectrum", [])
    inoise = noise_data.get("inoise_spectrum", [])

    headers = ["Frequency (Hz)"]
    if onoise:
        headers.append("Output Noise (V/sqrt(Hz))")
    if inoise:
        headers.append("Input Noise (V/sqrt(Hz))")

    rows = []
    for i, freq in enumerate(frequencies):
        row = [_fmt(freq)]
        if onoise:
            row.append(_fmt(onoise[i]) if i < len(onoise) else "")
        if inoise:
            row.append(_fmt(inoise[i]) if i < len(inoise) else "")
        rows.append(row)

    alignments = ["r"] * len(headers)
    out += _table(headers, rows, alignments)
    out += "\n"
    return out


def write_markdown(md_content, filepath):
    """Write Markdown content string to a file."""
    with open(filepath, "w") as f:
        f.write(md_content)
