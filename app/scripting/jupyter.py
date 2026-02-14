"""Jupyter notebook integration for Spice-GUI circuits.

Provides SVG rendering for Circuit objects and matplotlib plotting
for simulation results, enabling inline display in Jupyter notebooks.

No hard dependency on matplotlib — degrades gracefully to text repr.
"""

import xml.etree.ElementTree as ET
from typing import Optional

from models.circuit import CircuitModel

# --- SVG rendering ---


def circuit_to_svg(model: CircuitModel, width: int = 600, height: int = 400) -> str:
    """Render a circuit model as an SVG string.

    Generates a simple box-and-line schematic diagram showing components
    as labeled rectangles and wires as lines between terminal positions.

    Args:
        model: The CircuitModel to render.
        width: SVG viewport width in pixels.
        height: SVG viewport height in pixels.

    Returns:
        An SVG string suitable for Jupyter _repr_svg_().
    """
    if not model.components:
        return _empty_svg(width, height)

    # Compute bounding box of all component positions
    positions = [c.position for c in model.components.values()]
    min_x = min(p[0] for p in positions)
    max_x = max(p[0] for p in positions)
    min_y = min(p[1] for p in positions)
    max_y = max(p[1] for p in positions)

    # Add padding
    padding = 80
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)

    # Scale to fit viewport
    scale_x = (width - 2 * padding) / span_x if span_x > 0 else 1
    scale_y = (height - 2 * padding) / span_y if span_y > 0 else 1
    scale = min(scale_x, scale_y, 3.0)  # cap at 3x

    def to_svg_coords(x, y):
        sx = padding + (x - min_x) * scale
        sy = padding + (y - min_y) * scale
        return sx, sy

    svg = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=str(width),
        height=str(height),
        viewBox=f"0 0 {width} {height}",
    )

    # Background
    ET.SubElement(svg, "rect", width=str(width), height=str(height), fill="white")

    # Style
    style = ET.SubElement(svg, "style")
    style.text = (
        ".comp-box { fill: #f0f4ff; stroke: #336; stroke-width: 1.5; }"
        ".comp-label { font-family: monospace; font-size: 11px; text-anchor: middle; fill: #333; }"
        ".comp-value { font-family: monospace; font-size: 10px; text-anchor: middle; fill: #666; }"
        ".wire { stroke: #333; stroke-width: 1.5; fill: none; }"
        ".terminal { fill: #c33; }"
    )

    # Draw wires first (behind components)
    for wire in model.wires:
        start_comp = model.components.get(wire.start_component_id)
        end_comp = model.components.get(wire.end_component_id)
        if start_comp is None or end_comp is None:
            continue

        start_terminals = start_comp.get_terminal_positions()
        end_terminals = end_comp.get_terminal_positions()

        if wire.start_terminal < len(start_terminals) and wire.end_terminal < len(
            end_terminals
        ):
            sx, sy = to_svg_coords(*start_terminals[wire.start_terminal])
            ex, ey = to_svg_coords(*end_terminals[wire.end_terminal])
            ET.SubElement(
                svg,
                "line",
                x1=str(round(sx, 1)),
                y1=str(round(sy, 1)),
                x2=str(round(ex, 1)),
                y2=str(round(ey, 1)),
                **{"class": "wire"},
            )

    # Draw components
    box_w, box_h = 60, 36
    for comp in model.components.values():
        cx, cy = to_svg_coords(*comp.position)

        # Component box
        ET.SubElement(
            svg,
            "rect",
            x=str(round(cx - box_w / 2, 1)),
            y=str(round(cy - box_h / 2, 1)),
            width=str(box_w),
            height=str(box_h),
            rx="4",
            **{"class": "comp-box"},
        )

        # Component ID label
        label = ET.SubElement(
            svg,
            "text",
            x=str(round(cx, 1)),
            y=str(round(cy - 2, 1)),
            **{"class": "comp-label"},
        )
        label.text = comp.component_id

        # Component value
        val = ET.SubElement(
            svg,
            "text",
            x=str(round(cx, 1)),
            y=str(round(cy + 12, 1)),
            **{"class": "comp-value"},
        )
        val.text = comp.value

        # Terminal dots
        for tx, ty in comp.get_terminal_positions():
            tsx, tsy = to_svg_coords(tx, ty)
            ET.SubElement(
                svg,
                "circle",
                cx=str(round(tsx, 1)),
                cy=str(round(tsy, 1)),
                r="3",
                **{"class": "terminal"},
            )

    return ET.tostring(svg, encoding="unicode")


def _empty_svg(width: int, height: int) -> str:
    """Render an empty circuit placeholder SVG."""
    svg = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=str(width),
        height=str(height),
    )
    ET.SubElement(svg, "rect", width=str(width), height=str(height), fill="#fafafa")
    text = ET.SubElement(
        svg,
        "text",
        x=str(width // 2),
        y=str(height // 2),
        **{
            "text-anchor": "middle",
            "fill": "#999",
            "font-family": "sans-serif",
            "font-size": "14",
        },
    )
    text.text = "(empty circuit)"
    return ET.tostring(svg, encoding="unicode")


# --- Matplotlib plotting ---


def plot_result(result, title: Optional[str] = None):
    """Generate a matplotlib figure from a SimulationResult.

    Args:
        result: A SimulationResult from Circuit.simulate().
        title: Optional plot title. Defaults to the analysis type.

    Returns:
        A matplotlib Figure, or None if matplotlib is not available
        or the result has no plottable data.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    if not result.success or result.data is None:
        return None

    analysis = result.analysis_type
    data = result.data
    plot_title = title or analysis

    if analysis == "DC Operating Point":
        return _plot_op(data, plot_title, plt)
    elif analysis == "Transient":
        return _plot_transient(data, plot_title, plt)
    elif analysis == "AC Sweep":
        return _plot_ac(data, plot_title, plt)
    elif analysis == "DC Sweep":
        return _plot_dc_sweep(data, plot_title, plt)
    else:
        return None


def _plot_op(data: dict, title: str, plt):
    """Bar chart of DC operating point node voltages."""
    voltages = data.get("node_voltages", {})
    if not voltages:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    nodes = list(voltages.keys())
    values = [float(v) for v in voltages.values()]
    ax.bar(nodes, values, color="#4488cc")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    return fig


def _plot_transient(data, title: str, plt):
    """Time-series plot for transient analysis."""
    if not isinstance(data, list) or not data:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    time_key = next((k for k in data[0] if k.lower() in ("time", "t")), None)
    if time_key is None:
        return None

    times = [float(row[time_key]) for row in data]
    for key in data[0]:
        if key == time_key:
            continue
        values = [float(row[key]) for row in data]
        ax.plot(times, values, label=key)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    return fig


def _plot_ac(data, title: str, plt):
    """Bode plot for AC analysis (magnitude + phase)."""
    if not isinstance(data, list) or not data:
        return None

    freq_key = next(
        (k for k in data[0] if k.lower() in ("frequency", "freq", "f")), None
    )
    if freq_key is None:
        return None

    fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    freqs = [float(row[freq_key]) for row in data]

    for key in data[0]:
        if key == freq_key:
            continue
        if "phase" in key.lower():
            values = [float(row[key]) for row in data]
            ax_phase.semilogx(freqs, values, label=key)
        else:
            values = [float(row[key]) for row in data]
            ax_mag.semilogx(freqs, values, label=key)

    ax_mag.set_ylabel("Magnitude (dB)")
    ax_mag.set_title(title)
    ax_mag.legend()
    ax_mag.grid(alpha=0.3)
    ax_phase.set_xlabel("Frequency (Hz)")
    ax_phase.set_ylabel("Phase (deg)")
    ax_phase.legend()
    ax_phase.grid(alpha=0.3)
    plt.tight_layout()
    return fig


def _plot_dc_sweep(data, title: str, plt):
    """Plot DC sweep results."""
    if not isinstance(data, list) or not data:
        return None

    # First column is the sweep variable
    keys = list(data[0].keys())
    sweep_key = keys[0]
    sweep_vals = [float(row[sweep_key]) for row in data]

    fig, ax = plt.subplots(figsize=(10, 5))
    for key in keys[1:]:
        values = [float(row[key]) for row in data]
        ax.plot(sweep_vals, values, label=key)

    ax.set_xlabel(sweep_key)
    ax.set_ylabel("Voltage (V)")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    return fig


# --- IPython integration ---


def register_jupyter_formatters():
    """Register IPython display formatters for Circuit and SimulationResult.

    Call this to enable automatic inline rendering in Jupyter notebooks.
    Safe to call outside of IPython — does nothing if IPython is not available.
    """
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is None:
            return
    except ImportError:
        return

    from scripting.circuit import Circuit

    svg_formatter = ip.display_formatter.formatters["image/svg+xml"]
    svg_formatter.for_type(Circuit, lambda c: circuit_to_svg(c.model))
