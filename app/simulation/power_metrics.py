"""
simulation/power_metrics.py

Computes RMS voltage/current and average/peak power from transient simulation data.
"""

import math

from GUI.format_utils import parse_value


def compute_rms(values):
    """Compute the RMS (root-mean-square) of a list of numeric values.

    Args:
        values: list of float values

    Returns:
        RMS value as float, or 0.0 if empty.
    """
    if not values:
        return 0.0
    mean_sq = sum(v * v for v in values) / len(values)
    return math.sqrt(mean_sq)


def compute_transient_power_metrics(tran_data, components):
    """Compute power metrics from transient simulation data.

    For each resistor, computes:
    - Vrms: RMS voltage across the component
    - Irms: RMS current through the component
    - Pavg: average power dissipated
    - Ppeak: peak instantaneous power

    Args:
        tran_data: list[dict] — time-series data from parse_transient_results.
            Each dict has keys like "time", node labels, and "v_r1" for resistor voltages.
        components: dict mapping component_id -> ComponentData

    Returns:
        list[dict] with keys: component_id, component_type, value, vrms, irms, pavg, ppeak.
        Only includes components for which metrics could be computed.
    """
    if not tran_data or not components:
        return []

    results = []

    for comp_id, comp in components.items():
        if comp.component_type == "Ground":
            continue

        # Look for voltage-across vector in the transient data
        v_key = f"v_{comp_id.lower()}"
        if v_key not in tran_data[0]:
            continue

        voltage_series = [row[v_key] for row in tran_data if v_key in row]
        if not voltage_series:
            continue

        vrms = compute_rms(voltage_series)

        if comp.component_type == "Resistor":
            try:
                resistance = parse_value(comp.value)
                if resistance <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            irms = vrms / resistance
            # Instantaneous power at each time point: P(t) = V(t)^2 / R
            power_series = [v * v / resistance for v in voltage_series]
            pavg = sum(power_series) / len(power_series)
            ppeak = max(abs(p) for p in power_series)

            results.append(
                {
                    "component_id": comp_id,
                    "component_type": comp.component_type,
                    "value": comp.value,
                    "vrms": vrms,
                    "irms": irms,
                    "pavg": pavg,
                    "ppeak": ppeak,
                }
            )

    return results


def format_power_summary(metrics):
    """Format power metrics as a text table for display.

    Args:
        metrics: list of dicts from compute_transient_power_metrics

    Returns:
        Formatted string with power summary table.
    """
    if not metrics:
        return ""

    lines = []
    lines.append("")
    lines.append("POWER SUMMARY")
    lines.append("=" * 70)
    lines.append(
        f"  {'Component':<12s} {'Value':>8s} {'Vrms':>12s} {'Irms':>12s} {'Pavg':>12s} {'Ppeak':>12s}"
    )
    lines.append("-" * 70)

    total_pavg = 0.0
    for m in metrics:
        total_pavg += m["pavg"]
        lines.append(
            f"  {m['component_id']:<12s} {m['value']:>8s}"
            f" {_fmt_eng(m['vrms'], 'V'):>12s}"
            f" {_fmt_eng(m['irms'], 'A'):>12s}"
            f" {_fmt_eng(m['pavg'], 'W'):>12s}"
            f" {_fmt_eng(m['ppeak'], 'W'):>12s}"
        )

    lines.append("-" * 70)
    lines.append(
        f"  {'Total Pavg':<12s} {'':>8s} {'':>12s} {'':>12s} {_fmt_eng(total_pavg, 'W'):>12s}"
    )
    lines.append("=" * 70)

    return "\n".join(lines)


def _fmt_eng(value, unit):
    """Format a value in engineering notation with SI prefix."""
    if value == 0:
        return f"0 {unit}"

    abs_val = abs(value)
    prefixes = [
        (1e12, "T"),
        (1e9, "G"),
        (1e6, "M"),
        (1e3, "k"),
        (1, ""),
        (1e-3, "m"),
        (1e-6, "u"),
        (1e-9, "n"),
        (1e-12, "p"),
    ]

    for mult, prefix in prefixes:
        if abs_val >= mult:
            scaled = value / mult
            return f"{scaled:.3g} {prefix}{unit}"

    return f"{value:.3e} {unit}"
