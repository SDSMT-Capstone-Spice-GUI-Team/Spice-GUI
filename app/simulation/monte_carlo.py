"""
Monte Carlo simulation engine.

Applies random component tolerances and collects results across N runs.
No Qt dependencies — pure computation module.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Default tolerances by component type (percentage)
DEFAULT_TOLERANCES = {
    "Resistor": 5.0,
    "Capacitor": 10.0,
    "Inductor": 5.0,
}

# Component types eligible for Monte Carlo variation
MC_ELIGIBLE_TYPES = {
    "Resistor",
    "Capacitor",
    "Inductor",
    "Voltage Source",
    "Current Source",
}


def parse_spice_value(value_str):
    """Parse a SPICE value string (e.g. '1k', '100n', '4.7MEG') to float.

    Returns None if the value cannot be parsed (e.g. waveform specs).
    """
    s = value_str.strip()
    if not s:
        return None

    # Map of SPICE suffix → multiplier
    suffixes = [
        ("MEG", 1e6),
        ("meg", 1e6),
        ("T", 1e12),
        ("G", 1e9),
        ("k", 1e3),
        ("K", 1e3),
        ("m", 1e-3),
        ("u", 1e-6),
        ("n", 1e-9),
        ("p", 1e-12),
        ("f", 1e-15),
    ]

    for suffix, mult in suffixes:
        if s.endswith(suffix):
            num_part = s[: -len(suffix)]
            try:
                return float(num_part) * mult
            except ValueError:
                return None

    # Strip trailing unit letters (V, A, H, F, etc.)
    stripped = s.rstrip("VAHFhvaf")
    try:
        return float(stripped)
    except ValueError:
        return None


def format_spice_value(value):
    """Format a float as a SPICE-compatible value string with SI prefix."""
    if value == 0:
        return "0"

    abs_val = abs(value)
    prefixes = [
        (1e12, "T"),
        (1e9, "G"),
        (1e6, "MEG"),
        (1e3, "k"),
        (1, ""),
        (1e-3, "m"),
        (1e-6, "u"),
        (1e-9, "n"),
        (1e-12, "p"),
        (1e-15, "f"),
    ]

    for mult, prefix in prefixes:
        if abs_val >= mult:
            scaled = value / mult
            if scaled == int(scaled):
                return f"{int(scaled)}{prefix}"
            return f"{scaled:.6g}{prefix}"

    return f"{value:.6g}"


def apply_tolerance(value_str, tolerance_pct, distribution="gaussian", rng=None):
    """Apply a random tolerance to a SPICE value string.

    Args:
        value_str: Original SPICE value (e.g. '1k')
        tolerance_pct: Tolerance percentage (e.g. 5.0 for ±5%)
        distribution: 'gaussian' or 'uniform'
        rng: numpy random Generator (default: numpy default_rng)

    Returns:
        New SPICE value string with tolerance applied, or the original
        if the value cannot be parsed.
    """
    if rng is None:
        rng = np.random.default_rng()

    base_value = parse_spice_value(value_str)
    if base_value is None or base_value == 0:
        return value_str

    fraction = tolerance_pct / 100.0
    if distribution == "gaussian":
        # 3-sigma = tolerance range, so sigma = fraction/3
        factor = 1.0 + rng.normal(0, fraction / 3.0)
    else:  # uniform
        factor = 1.0 + rng.uniform(-fraction, fraction)

    new_value = base_value * factor
    return format_spice_value(new_value)


def compute_mc_statistics(values):
    """Compute statistics for a list of numeric values.

    Args:
        values: list of float values

    Returns:
        dict with mean, std, min, max, median, count
    """
    arr = np.array(values)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
        "count": len(arr),
    }
