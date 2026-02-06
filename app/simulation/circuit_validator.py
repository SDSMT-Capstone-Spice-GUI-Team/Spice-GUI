"""
simulation/circuit_validator.py

Pre-simulation circuit validation with no Qt dependencies.
"""


def validate_circuit(components, wires, analysis_type):
    """
    Validate circuit before simulation.

    Args:
        components: Dict[str, ComponentData] keyed by component ID
        wires: List[WireData]
        analysis_type: str (e.g. "DC Operating Point", "DC Sweep", "Transient")

    Returns:
        (is_valid, errors, warnings) where:
            is_valid: bool — False if any errors found
            errors: list[str] — problems that block simulation
            warnings: list[str] — non-blocking issues
    """
    errors = []
    warnings = []

    # 1. Circuit must have components (beyond just Ground)
    non_ground = [c for c in components.values() if c.component_type != 'Ground']
    if not non_ground:
        errors.append("Circuit has no components. Add at least one component to simulate.")
        return False, errors, warnings

    # 2. Must have a ground node
    has_ground = any(c.component_type == 'Ground' for c in components.values())
    if not has_ground:
        errors.append("Circuit has no ground node. Every SPICE circuit requires a ground (node 0).")

    # 3. Build set of connected terminals from wires
    connected_terminals = set()
    for wire in wires:
        connected_terminals.add((wire.start_component_id, wire.start_terminal))
        connected_terminals.add((wire.end_component_id, wire.end_terminal))

    # 4. Check for unconnected terminals
    for comp in components.values():
        if comp.component_type == 'Ground':
            continue
        terminal_count = comp.get_terminal_count()
        comp_connected = []
        comp_unconnected = []
        for i in range(terminal_count):
            if (comp.component_id, i) in connected_terminals:
                comp_connected.append(i)
            else:
                comp_unconnected.append(i)

        if len(comp_unconnected) == terminal_count:
            errors.append(
                f"{comp.component_id} ({comp.component_type}) has no connections. "
                f"Connect its terminals to the circuit."
            )
        elif comp_unconnected:
            warnings.append(
                f"{comp.component_id} ({comp.component_type}) has unconnected "
                f"terminal(s): {comp_unconnected}."
            )

    # 5. Analysis-specific checks
    voltage_sources = [c for c in components.values()
                       if c.component_type in ('Voltage Source', 'Waveform Source')]
    current_sources = [c for c in components.values()
                       if c.component_type == 'Current Source']

    if analysis_type == "DC Sweep":
        dc_sources = [c for c in components.values()
                      if c.component_type == 'Voltage Source']
        if not dc_sources:
            errors.append(
                "DC Sweep requires at least one DC Voltage Source to sweep."
            )

    if not voltage_sources and not current_sources:
        warnings.append(
            "Circuit has no voltage or current sources. "
            "The simulation may not produce meaningful results."
        )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
