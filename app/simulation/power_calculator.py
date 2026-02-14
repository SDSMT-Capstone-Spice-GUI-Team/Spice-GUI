"""
simulation/power_calculator.py

Calculates power dissipation for each component from DC operating point results.
"""

import logging

from GUI.format_utils import parse_value

logger = logging.getLogger(__name__)


def calculate_power(components, nodes, node_voltages, branch_currents=None):
    """Calculate power dissipation for each component.

    Args:
        components: list of ComponentData from the circuit model
        nodes: list of NodeData from the circuit model
        node_voltages: dict mapping node labels to voltage (float)
        branch_currents: optional dict mapping device refs (lowercase) to current (float)

    Returns:
        dict mapping component_id to power in watts (float).
        Positive = dissipating, negative = supplying.
        Components that can't be calculated are omitted.
    """
    if not node_voltages:
        return {}

    branch_currents = branch_currents or {}

    # Build terminal-to-node-label mapping
    term_to_label = {}
    for node in nodes:
        label = node.get_label()
        for comp_id, term_idx in node.terminals:
            term_to_label[(comp_id, term_idx)] = label

    power = {}
    for comp in components:
        cid = comp.component_id
        ctype = comp.component_type

        if ctype == "Ground":
            continue

        try:
            p = _calc_component_power(
                comp, cid, ctype, term_to_label, node_voltages, branch_currents
            )
            if p is not None:
                power[cid] = p
        except (ValueError, KeyError, ZeroDivisionError) as e:
            logger.debug("Could not calculate power for %s: %s", cid, e)

    return power


def _calc_component_power(
    comp, cid, ctype, term_to_label, node_voltages, branch_currents
):
    """Calculate power for a single component. Returns watts or None."""
    # Get node labels for terminal 0 and 1 (2-terminal components)
    label0 = term_to_label.get((cid, 0))
    label1 = term_to_label.get((cid, 1))

    if label0 is None or label1 is None:
        return None

    v0 = node_voltages.get(label0)
    v1 = node_voltages.get(label1)

    if v0 is None or v1 is None:
        return None

    v_across = v0 - v1

    # Check for branch current from simulation
    ref = cid.lower()
    if ref in branch_currents:
        return v_across * branch_currents[ref]

    # Calculate from component value for resistors
    if ctype == "Resistor":
        r = parse_value(comp.value)
        if r > 0:
            return (v_across**2) / r

    # For voltage/current sources without branch current, estimate from node voltages
    if ctype in ("Voltage Source", "Waveform Source"):
        # Can't compute without current; skip
        return None

    if ctype == "Current Source":
        try:
            i = parse_value(comp.value)
            return v_across * i
        except (ValueError, TypeError):
            return None

    # Capacitors/inductors have 0 DC power (ideally)
    if ctype in ("Capacitor", "Inductor"):
        return 0.0

    return None


def total_power(power_dict):
    """Sum of all power dissipations. Should net close to 0 for a valid circuit."""
    return sum(power_dict.values())
