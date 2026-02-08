"""
GUI/format_utils.py

Provides utility functions for parsing and formatting numbers with SI unit prefixes.
"""
import re

# Dictionary of SI prefixes and their multipliers
# Includes common variations like 'u' for 'µ' and 'MEG' for 'M'
SI_PREFIX_MULTIPLIERS = {
    'f': 1e-15,  # Femto
    'p': 1e-12,  # Pico
    'n': 1e-9,   # Nano
    'u': 1e-6,   # Micro
    'µ': 1e-6,   # Micro
    'm': 1e-3,   # Milli
    'k': 1e3,    # Kilo
    'M': 1e6,    # Mega
    'MEG': 1e6,  # Mega (SPICE variant)
    'G': 1e9,    # Giga
    'T': 1e12,   # Tera
}

# For formatting, we iterate to find the best fit
# We sort by value to handle this correctly.
# Using a list of tuples: (multiplier, prefix)
FORMATTING_PREFIXES = sorted(
    [(1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'k'),
     (1, ''), (1e-3, 'm'), (1e-6, 'µ'), (1e-9, 'n'), (1e-12, 'p'), (1e-15, 'f')],
    key=lambda x: x[0], reverse=True
)

def parse_value(s: str) -> float:
    """
    Parses a string with an optional SI prefix into a float.
    Examples: "10k" -> 10000.0, "25m" -> 0.025, "10u" -> 1e-5
    """
    if not isinstance(s, str):
        return float(s)

    s = s.strip()
    
    # Check for SPICE 'MEG' variant first
    if 'MEG' in s.upper():
        num_part = s[:-3]
        multiplier = SI_PREFIX_MULTIPLIERS['MEG']
        try:
            return float(num_part) * multiplier
        except ValueError:
            raise ValueError(f"Invalid number format: {s}")

    # Use regex to separate the number from the potential prefix/unit
    match = re.match(r'^(-?\d+\.?\d*e?[-+]?\d*)([a-zA-Zµ]*)', s)
    if not match:
        raise ValueError(f"Invalid number format: {s}")

    num_str, unit_str = match.groups()
    
    if not unit_str:
        return float(num_str)

    # Find the first character that is a known prefix
    for i, char in enumerate(unit_str):
        if char in SI_PREFIX_MULTIPLIERS:
            multiplier = SI_PREFIX_MULTIPLIERS[char]
            return float(num_str) * multiplier

    # If no known prefix is found in the unit string, just return the number
    return float(num_str)


def format_value(value: float, unit: str = "") -> str:
    """
    Formats a float into a string with the most appropriate SI prefix.
    Examples: 0.015 -> "15.00m", 15000 -> "15.00k"
    """
    if value == 0:
        return f"0.00 {unit}"
    
    abs_val = abs(value)

    for mult, prefix in FORMATTING_PREFIXES:
        if abs_val >= mult:
            scaled_val = value / mult
            # Format to 2 decimal places, but avoid trailing ".00" for integers
            if scaled_val == int(scaled_val):
                 return f"{int(scaled_val)} {prefix}{unit}"
            else:
                 return f"{scaled_val:.2f} {prefix}{unit}"

    # If value is smaller than the smallest prefix, use scientific notation
    return f"{value:.2e} {unit}"


# Component types that require positive values
_POSITIVE_ONLY_TYPES = {'Resistor', 'Capacitor', 'Inductor'}

# Component types that don't need value validation
_SKIP_VALIDATION_TYPES = {'Ground', 'Op-Amp', 'Waveform Source', 'BJT NPN', 'BJT PNP'}


def validate_component_value(value: str, component_type: str) -> tuple[bool, str]:
    """
    Validate a component value string for the given component type.

    Returns:
        (is_valid, error_message) — error_message is empty when valid.
    """
    if component_type in _SKIP_VALIDATION_TYPES:
        return True, ""

    value = value.strip()
    if not value:
        return False, "Value cannot be empty."

    try:
        numeric = parse_value(value)
    except (ValueError, TypeError):
        return False, f"Invalid value '{value}'. Use a number with optional suffix (e.g. 10k, 100n, 4.7M)."

    if component_type in _POSITIVE_ONLY_TYPES and numeric <= 0:
        return False, f"{component_type} value must be positive (got {value})."

    return True, ""
