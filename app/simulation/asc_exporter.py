"""
simulation/asc_exporter.py

Export a CircuitModel to LTspice .asc schematic format.
Inverse of asc_parser.py — maps Spice-GUI types back to LTspice symbols.

No Qt dependencies.
"""

# Spice-GUI component type -> preferred LTspice symbol name
_TYPE_TO_SYMBOL = {
    "Resistor": "res",
    "Capacitor": "cap",
    "Inductor": "ind",
    "Voltage Source": "voltage",
    "Current Source": "current",
    "Diode": "diode",
    "LED": "LED",
    "Zener Diode": "zener",
    "BJT NPN": "npn",
    "BJT PNP": "pnp",
    "MOSFET NMOS": "nmos",
    "MOSFET PMOS": "pmos",
    "Op-Amp": "opamp",
    "VCVS": "e",
    "CCCS": "f",
    "VCCS": "g",
    "CCVS": "h",
    "Waveform Source": "voltage",
    "Transformer": "ind2",
}

# Pin offsets (same as asc_parser._PIN_OFFSETS, with corrected pin spacing)
_PIN_OFFSETS = {
    "Resistor": [(0, 0), (0, 96)],
    "Capacitor": [(0, 0), (0, 64)],
    "Inductor": [(0, 0), (0, 96)],
    "Voltage Source": [(0, 0), (0, 112)],
    "Current Source": [(0, 0), (0, 112)],
    "Waveform Source": [(0, 0), (0, 112)],
    "Diode": [(0, 0), (0, 64)],
    "LED": [(0, 0), (0, 64)],
    "Zener Diode": [(0, 0), (0, 64)],
    "BJT NPN": [(16, 0), (-16, 32), (16, 64)],
    "BJT PNP": [(16, 64), (-16, 32), (16, 0)],
    "MOSFET NMOS": [(16, 0), (-16, 32), (16, 64)],
    "MOSFET PMOS": [(16, 64), (-16, 32), (16, 0)],
    "Op-Amp": [(-32, 32), (-32, -32), (32, 0)],
    "VCVS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "CCVS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "VCCS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "CCCS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "Transformer": [(-32, -32), (-32, 32), (32, -32), (32, 32)],
    "Ground": [(0, 0)],
}


def _degrees_to_rotation_code(rotation, flip_h=False, is_bipole=True):
    """Convert Spice-GUI rotation + flip to LTspice rotation code.

    For 2-terminal (bipole) components, applies the self-inverse transform
    ``(450 - angle) % 360`` because LTspice R0 is vertical while Spice-GUI
    0° is horizontal, and they rotate in opposite directions.
    """
    prefix = "M" if flip_h else "R"
    angle = int(rotation) % 360
    if is_bipole:
        angle = (450 - angle) % 360
    return f"{prefix}{angle}"


def _center_to_origin(comp_type, rotation, flip_h=False):
    """Convert Spice-GUI center position back to LTspice SYMBOL origin.

    Returns (dx, dy) to subtract from the Spice-GUI center to get the
    LTspice SYMBOL position.
    """
    offsets = _PIN_OFFSETS.get(comp_type)
    if not offsets or len(offsets) < 2:
        return 0, 0
    avg_x = sum(o[0] for o in offsets) / len(offsets)
    avg_y = sum(o[1] for o in offsets) / len(offsets)
    # For bipoles we need the LTspice rotation (reverse of the import transform)
    is_bipole = len(offsets) == 2
    lt_angle = (450 - int(rotation)) % 360 if is_bipole else int(rotation) % 360
    return _transform_pin(avg_x, avg_y, lt_angle, flip_h)


def _transform_pin(dx, dy, rotation, flip_h=False):
    """Transform a pin offset by rotation and flip."""
    if flip_h:
        dx = -dx

    angle = int(rotation) % 360
    if angle == 0:
        return dx, dy
    elif angle == 90:
        return dy, -dx
    elif angle == 180:
        return -dx, -dy
    elif angle == 270:
        return -dy, dx
    return dx, dy


def _format_analysis_directive(analysis_type, params):
    """Convert analysis type and params to an LTspice TEXT directive."""
    if analysis_type == "DC Operating Point":
        return ".op"
    elif analysis_type == "Transient":
        duration = params.get("duration", "10m")
        step = params.get("step", "")
        if step:
            return f".tran {duration} {step}"
        return f".tran {duration}"
    elif analysis_type == "AC Sweep":
        sweep_type = params.get("sweep_type", "dec")
        points = params.get("points", "100")
        fstart = params.get("fStart", "1")
        fstop = params.get("fStop", "1Meg")
        return f".ac {sweep_type} {points} {fstart} {fstop}"
    elif analysis_type == "DC Sweep":
        source = params.get("source", "V1")
        vmin = params.get("min", "0")
        vmax = params.get("max", "5")
        step = params.get("step", "0.1")
        return f".dc {source} {vmin} {vmax} {step}"
    return None


def export_asc(model):
    """Export a CircuitModel to LTspice .asc format text.

    Args:
        model: CircuitModel instance

    Returns:
        str: .asc file content
    """
    lines = []
    lines.append("Version 4")
    lines.append("SHEET 1 880 680")

    # Build pin position map for wire generation
    pin_positions = {}  # (comp_id, terminal_idx) -> (x, y)

    # Export components (skip Ground — handled as FLAG)
    for comp_id, comp in sorted(model.components.items()):
        if comp.component_type == "Ground":
            continue

        symbol = _TYPE_TO_SYMBOL.get(comp.component_type)
        if symbol is None:
            continue

        offsets = _PIN_OFFSETS.get(comp.component_type, [(0, 0), (0, 80)])
        is_bipole = len(offsets) == 2

        # Convert Spice-GUI center back to LTspice SYMBOL origin
        cx, cy = _center_to_origin(comp.component_type, comp.rotation, comp.flip_h)
        x = int(comp.position[0] - cx)
        y = int(comp.position[1] - cy)
        rot_code = _degrees_to_rotation_code(comp.rotation, comp.flip_h, is_bipole=is_bipole)

        lines.append(f"SYMBOL {symbol} {x} {y} {rot_code}")
        lines.append(f"SYMATTR InstName {comp_id}")
        if comp.value:
            lines.append(f"SYMATTR Value {comp.value}")

        # Compute pin positions using LTspice rotation/flip
        lt_angle = int(rot_code[1:])
        lt_flip = rot_code.startswith("M")
        for term_idx, (dx, dy) in enumerate(offsets):
            tx, ty = _transform_pin(dx, dy, lt_angle, lt_flip)
            pin_positions[(comp_id, term_idx)] = (x + tx, y + ty)

    # Export Ground components as FLAG entries
    for comp_id, comp in sorted(model.components.items()):
        if comp.component_type != "Ground":
            continue
        gx = int(comp.position[0])
        gy = int(comp.position[1])
        lines.append(f"FLAG {gx} {gy} 0")

        # Ground has a single pin at its position
        pin_positions[(comp_id, 0)] = (gx, gy)

    # Export wires
    for wire in model.wires:
        start_key = (wire.start_component_id, wire.start_terminal)
        end_key = (wire.end_component_id, wire.end_terminal)
        if start_key in pin_positions and end_key in pin_positions:
            x1, y1 = pin_positions[start_key]
            x2, y2 = pin_positions[end_key]
            if (x1, y1) != (x2, y2):  # skip zero-length wires
                lines.append(f"WIRE {x1} {y1} {x2} {y2}")

    # Export analysis directive
    if model.analysis_type:
        directive = _format_analysis_directive(model.analysis_type, model.analysis_params)
        if directive:
            lines.append(f"TEXT -32 280 Left 2 !{directive}")

    lines.append("")  # trailing newline
    return "\n".join(lines)


def write_asc(content, filepath):
    """Write .asc content to a file.

    Args:
        content: str from export_asc()
        filepath: output file path
    """
    from utils.atomic_write import atomic_write_text

    atomic_write_text(filepath, content)
