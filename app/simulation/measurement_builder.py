"""
Pure-logic builder for ngspice .meas directives.

Extracted from GUI/meas_dialog.py so that measurement directive
generation can be tested and reused without any GUI framework dependency.
"""

# Maps the GUI analysis type name to the .meas domain keyword
ANALYSIS_DOMAIN_MAP = {
    "Transient": "tran",
    "AC Sweep": "ac",
    "DC Sweep": "dc",
}

# Measurement types offered in the GUI
MEAS_TYPES = [
    ("AVG", "Average value over a range"),
    ("RMS", "Root-mean-square over a range"),
    ("MIN", "Minimum value over a range"),
    ("MAX", "Maximum value over a range"),
    ("PP", "Peak-to-peak (max minus min)"),
    ("INTEG", "Integral over a range"),
    ("FIND_AT", "Find value at a specific point"),
    ("FIND_WHEN", "Find value when a condition is met"),
    ("TRIG_TARG", "Timing between trigger and target events"),
]


def build_directive(domain, name, meas_type, params):
    """Build a .meas directive string from structured parameters.

    Args:
        domain: "tran", "ac", or "dc"
        name: measurement name (e.g., "rise_time")
        meas_type: one of the MEAS_TYPES keys
        params: dict with type-specific fields

    Returns:
        str: a complete .meas directive
    """
    variable = params.get("variable", "v(out)")

    if meas_type in ("AVG", "RMS", "MIN", "MAX", "PP", "INTEG"):
        directive = f".meas {domain} {name} {meas_type} {variable}"
        from_val = params.get("from_val", "").strip()
        to_val = params.get("to_val", "").strip()
        if from_val:
            directive += f" FROM={from_val}"
        if to_val:
            directive += f" TO={to_val}"
        return directive

    if meas_type == "FIND_AT":
        at_val = params.get("at_val", "0")
        return f".meas {domain} {name} FIND {variable} AT={at_val}"

    if meas_type == "FIND_WHEN":
        when_var = params.get("when_var", "v(in)")
        when_val = params.get("when_val", "0.5")
        cross = params.get("cross", "")
        directive = f".meas {domain} {name} FIND {variable} WHEN {when_var}={when_val}"
        if cross:
            directive += f" {cross}"
        return directive

    if meas_type == "TRIG_TARG":
        trig_var = params.get("trig_var", "v(in)")
        trig_val = params.get("trig_val", "0.5")
        trig_edge = params.get("trig_edge", "RISE=1")
        targ_var = params.get("targ_var", variable)
        targ_val = params.get("targ_val", "0.5")
        targ_edge = params.get("targ_edge", "RISE=1")
        return (
            f".meas {domain} {name} TRIG {trig_var} VAL={trig_val} {trig_edge} "
            f"TARG {targ_var} VAL={targ_val} {targ_edge}"
        )

    return f".meas {domain} {name} {meas_type} {variable}"
