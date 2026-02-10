"""
simulation/circuit_validator.py

Pre-simulation circuit validation with no Qt dependencies.
Error messages are written to be educational and student-friendly,
suggesting how to fix each problem.
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
    non_ground = [c for c in components.values() if c.component_type != "Ground"]
    if not non_ground:
        errors.append(
            "There are no components on the canvas. "
            "Drag components from the palette on the left to start "
            "designing your circuit."
        )
        return False, errors, warnings

    # 2. Must have a ground node
    has_ground = any(c.component_type == "Ground" for c in components.values())
    if not has_ground:
        errors.append(
            "Your circuit needs a ground connection. "
            "Every circuit needs a reference point (0 V). "
            "Drag a Ground component from the palette and connect it "
            "to your circuit."
        )

    # 3. Build set of connected terminals from wires
    connected_terminals = set()
    for wire in wires:
        connected_terminals.add((wire.start_component_id, wire.start_terminal))
        connected_terminals.add((wire.end_component_id, wire.end_terminal))

    # 4. Check for unconnected terminals
    for comp in components.values():
        if comp.component_type == "Ground":
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
                f"Make sure all component terminals (the dots on each end) "
                f"are connected with wires before simulating."
            )
        elif comp_unconnected:
            warnings.append(
                f"{comp.component_id} ({comp.component_type}) has unconnected "
                f"terminals. Make sure all component terminals (the dots on "
                f"each end) are connected with wires before simulating."
            )

    # 5. Analysis-specific checks
    voltage_sources = [c for c in components.values() if c.component_type in ("Voltage Source", "Waveform Source")]
    current_sources = [c for c in components.values() if c.component_type == "Current Source"]

    if analysis_type == "DC Sweep":
        dc_sources = [c for c in components.values() if c.component_type == "Voltage Source"]
        if not dc_sources:
            errors.append(
                "DC Sweep analysis requires a Voltage Source to sweep. "
                "Add a Voltage Source to your circuit and connect it "
                "before running this analysis."
            )

    if not voltage_sources and not current_sources:
        warnings.append(
            "Circuit has no voltage or current sources. "
            "Add a Voltage Source or Current Source to provide power "
            "to the circuit."
        )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
