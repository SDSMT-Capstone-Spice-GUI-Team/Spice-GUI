"""
simulation/asc_parser.py

Parses LTspice .asc schematic files and converts them into CircuitModel
objects for display on the canvas.

LTspice .asc format is a plain-text format with lines like:
    Version 4
    SHEET 1 880 680
    WIRE 192 192 80 192
    FLAG 80 256 0
    SYMBOL res 80 96 R0
    SYMATTR InstName R1
    SYMATTR Value 1k
    TEXT -32 280 Left 2 .tran 10m
"""

import logging
import re

from models.circuit import CircuitModel
from models.component import DEFAULT_VALUES, SPICE_SYMBOLS, ComponentData
from models.wire import WireData

logger = logging.getLogger(__name__)


class AscParseError(ValueError):
    """Raised when an .asc file cannot be parsed."""


# LTspice symbol name -> Spice-GUI component type
_SYMBOL_TO_TYPE = {
    "res": "Resistor",
    "res2": "Resistor",
    "cap": "Capacitor",
    "cap2": "Capacitor",
    "polcap": "Capacitor",
    "ind": "Inductor",
    "ind2": "Inductor",
    "voltage": "Voltage Source",
    "current": "Current Source",
    "diode": "Diode",
    "schottky": "Diode",
    "zener": "Zener Diode",
    "LED": "LED",
    "led": "LED",
    "npn": "BJT NPN",
    "npn2": "BJT NPN",
    "pnp": "BJT PNP",
    "pnp2": "BJT PNP",
    "nmos": "MOSFET NMOS",
    "nmos3": "MOSFET NMOS",
    "pmos": "MOSFET PMOS",
    "pmos3": "MOSFET PMOS",
    "Opamps\\\\opamp": "Op-Amp",
    "Opamps\\\\opamp2": "Op-Amp",
    "opamp": "Op-Amp",
    "e": "VCVS",
    "e2": "VCVS",
    "f": "CCCS",
    "f2": "CCCS",
    "g": "VCCS",
    "g2": "VCCS",
    "h": "CCVS",
    "h2": "CCVS",
}

# Pin offsets (dx, dy) relative to SYMBOL position for each LTspice symbol
# at R0 orientation.  Keyed by LTspice symbol name for accuracy; the
# Spice-GUI component type (used as fallback) may map multiple symbols.
_SYMBOL_PIN_OFFSETS: dict[str, list[tuple[int, int]]] = {
    # --- 2-terminal ---
    "res": [(0, 0), (0, 96)],
    "res2": [(0, 0), (0, 80)],
    "cap": [(0, 0), (0, 64)],
    "cap2": [(0, 0), (0, 64)],
    "polcap": [(0, 0), (0, 64)],
    "ind": [(0, 0), (0, 96)],
    "ind2": [(0, 0), (0, 80)],
    "voltage": [(0, 0), (0, 112)],
    "current": [(0, 0), (0, 112)],
    "diode": [(0, 0), (0, 64)],
    "schottky": [(0, 0), (0, 64)],
    "zener": [(0, 0), (0, 64)],
    "LED": [(0, 0), (0, 64)],
    "led": [(0, 0), (0, 64)],
    # --- 3-terminal ---
    "npn": [(16, 0), (-16, 32), (16, 64)],  # C, B, E
    "npn2": [(16, 0), (-16, 32), (16, 64)],
    "pnp": [(16, 64), (-16, 32), (16, 0)],  # C, B, E
    "pnp2": [(16, 64), (-16, 32), (16, 0)],
    "nmos": [(16, 0), (-16, 32), (16, 64)],  # D, G, S
    "nmos3": [(16, 0), (-16, 32), (16, 64)],
    "pmos": [(16, 64), (-16, 32), (16, 0)],  # D, G, S
    "pmos3": [(16, 64), (-16, 32), (16, 0)],
    "opamp": [(-32, 32), (-32, -32), (32, 0)],  # in+, in-, out
    "Opamps\\\\opamp": [(-32, 32), (-32, -32), (32, 0)],
    "Opamps\\\\opamp2": [(-32, 32), (-32, -32), (32, 0)],
    # --- 4-terminal ---
    "e": [(-32, 32), (-32, -32), (32, -32), (32, 32)],  # VCVS
    "e2": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "f": [(-32, 32), (-32, -32), (32, -32), (32, 32)],  # CCCS
    "f2": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "g": [(-32, 32), (-32, -32), (32, -32), (32, 32)],  # VCCS
    "g2": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "h": [(-32, 32), (-32, -32), (32, -32), (32, 32)],  # CCVS
    "h2": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
}

# Fallback offsets keyed by Spice-GUI type (used when LTspice symbol is unknown)
_PIN_OFFSETS = {
    "Resistor": [(0, 0), (0, 96)],
    "Capacitor": [(0, 0), (0, 64)],
    "Inductor": [(0, 0), (0, 96)],
    "Voltage Source": [(0, 0), (0, 112)],
    "Current Source": [(0, 0), (0, 112)],
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
}

# Coordinate scale factor: LTspice units -> Spice-GUI scene coordinates
_SCALE = 1.0


def _point_on_segment(pt, seg_a, seg_b):
    """Return True if integer point *pt* lies strictly between *seg_a* and *seg_b*.

    Only checks axis-aligned segments (horizontal or vertical), which is
    all LTspice wires produce.  The endpoints themselves are already
    handled by the normal union-find, so this only matches interior points.
    """
    px, py = pt
    ax, ay = seg_a
    bx, by = seg_b

    if ax == bx == px:  # vertical segment
        lo, hi = (min(ay, by), max(ay, by))
        return lo < py < hi
    if ay == by == py:  # horizontal segment
        lo, hi = (min(ax, bx), max(ax, bx))
        return lo < px < hi
    return False


def _transform_pin(dx, dy, rotation_code):
    """Transform a pin offset by the LTspice rotation code.

    LTspice rotation codes:
        R0: no rotation (default)
        R90: 90 degrees CW
        R180: 180 degrees
        R270: 270 degrees CW (= 90 CCW)
        M0: horizontal mirror
        M90: mirror + 90 CW
        M180: mirror + 180
        M270: mirror + 270 CW
    """
    code = rotation_code.upper() if rotation_code else "R0"
    mirrored = code.startswith("M")
    angle = int(code[1:]) if len(code) > 1 else 0

    if mirrored:
        dx = -dx

    if angle == 0:
        return dx, dy
    elif angle == 90:
        return dy, -dx
    elif angle == 180:
        return -dx, -dy
    elif angle == 270:
        return -dy, dx
    return dx, dy


def _rotation_to_degrees(rotation_code, is_bipole=True):
    """Convert LTspice rotation code to Spice-GUI rotation degrees and flip state.

    Args:
        rotation_code: LTspice rotation code (R0, R90, R180, R270, M0, etc.)
        is_bipole: True for 2-terminal components where LTspice R0=vertical
                   but Spice-GUI 0°=horizontal, requiring a 90° offset.

    Returns (rotation_degrees, flip_h).
    """
    code = rotation_code.upper() if rotation_code else "R0"
    mirrored = code.startswith("M")
    angle = int(code[1:]) if len(code) > 1 else 0

    if is_bipole:
        # LTspice R0 is vertical, Spice-GUI 0° is horizontal, and they
        # rotate in opposite directions (LTspice CW increments map to
        # Spice-GUI CCW).  The self-inverse transform is:
        angle = (450 - angle) % 360

    return angle, mirrored


def _center_offset_from_pins(pin_offsets, rotation_code):
    """Compute the offset from LTspice SYMBOL origin to Spice-GUI center.

    LTspice positions the SYMBOL origin at pin 1.  Spice-GUI uses the
    component center.  Returns (dx, dy) to add to the LTspice SYMBOL
    position to get the Spice-GUI center position.
    """
    if not pin_offsets or len(pin_offsets) < 2:
        return 0, 0
    # Center = average of all pin offsets (in LTspice space, before rotation)
    avg_x = sum(o[0] for o in pin_offsets) / len(pin_offsets)
    avg_y = sum(o[1] for o in pin_offsets) / len(pin_offsets)
    # Transform the center offset by the LTspice rotation
    return _transform_pin(avg_x, avg_y, rotation_code)


def parse_asc(text):
    """Parse LTspice .asc schematic text into a structured representation.

    Args:
        text: The full text content of a .asc file.

    Returns:
        dict with keys:
            components: list of parsed component dicts
            wires: list of (x1, y1, x2, y2) wire segments
            flags: list of (x, y, label) flag entries
            analysis: dict with type and params, or None
            warnings: list of warning messages

    Raises:
        AscParseError: If the file is empty or has no recognizable content.
    """
    lines = text.strip().replace("\r\n", "\n").split("\n")
    if not lines:
        raise AscParseError("Empty .asc file.")

    components = []
    wires = []
    flags = []
    analysis = None
    warnings = []

    current_symbol = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("WIRE "):
            parts = stripped.split()
            if len(parts) >= 5:
                try:
                    x1, y1, x2, y2 = (
                        int(parts[1]),
                        int(parts[2]),
                        int(parts[3]),
                        int(parts[4]),
                    )
                    wires.append((x1, y1, x2, y2))
                except ValueError:
                    logger.debug("Skipping WIRE with invalid coordinates: %s", stripped)

        elif stripped.startswith("FLAG "):
            parts = stripped.split()
            if len(parts) >= 4:
                try:
                    x, y = int(parts[1]), int(parts[2])
                    label = parts[3]
                    flags.append((x, y, label))
                except ValueError:
                    logger.debug("Skipping FLAG with invalid coordinates: %s", stripped)

        elif stripped.startswith("SYMBOL "):
            # Save any previous symbol
            if current_symbol is not None:
                components.append(current_symbol)

            parts = stripped.split()
            if len(parts) >= 5:
                try:
                    sym_name = parts[1]
                    x, y = int(parts[2]), int(parts[3])
                    rotation = parts[4] if len(parts) > 4 else "R0"
                    current_symbol = {
                        "ltspice_name": sym_name,
                        "x": x,
                        "y": y,
                        "rotation": rotation,
                        "inst_name": None,
                        "value": None,
                        "value2": None,
                        "spice_model": None,
                    }
                except ValueError:
                    logger.debug("Skipping SYMBOL with invalid coordinates: %s", stripped)
                    current_symbol = None

        elif stripped.startswith("SYMATTR "):
            if current_symbol is not None:
                # Split only into 3 parts: SYMATTR key value
                parts = stripped.split(None, 2)
                if len(parts) >= 3:
                    attr_name = parts[1]
                    attr_value = parts[2]
                    if attr_name == "InstName":
                        current_symbol["inst_name"] = attr_value
                    elif attr_name == "Value":
                        current_symbol["value"] = attr_value
                    elif attr_name == "Value2":
                        current_symbol["value2"] = attr_value
                    elif attr_name == "SpiceModel":
                        current_symbol["spice_model"] = attr_value

        elif stripped.startswith("TEXT "):
            # TEXT format: TEXT x y alignment size text_content
            # SPICE directives are preceded by !
            parts = stripped.split(None, 5)
            if len(parts) >= 6:
                text_content = parts[5]
                if text_content.startswith("!"):
                    directive = text_content[1:].strip()
                    parsed_analysis = _parse_directive(directive)
                    if parsed_analysis is not None:
                        analysis = parsed_analysis

    # Don't forget the last symbol
    if current_symbol is not None:
        components.append(current_symbol)

    if not components and not wires and not flags:
        raise AscParseError("No components, wires, or flags found in .asc file.")

    return {
        "components": components,
        "wires": wires,
        "flags": flags,
        "analysis": analysis,
        "warnings": warnings,
    }


def _parse_directive(directive):
    """Parse a SPICE directive from a TEXT line."""
    lower = directive.lower()
    if lower.startswith(".tran"):
        return _parse_tran(directive)
    elif lower.startswith(".ac"):
        return _parse_ac(directive)
    elif lower.startswith(".dc"):
        return _parse_dc(directive)
    elif lower.startswith(".op"):
        return {"type": "DC Operating Point", "params": {}}
    return None


def _parse_tran(directive):
    tokens = directive.split()
    params = {}
    if len(tokens) >= 2:
        params["duration"] = tokens[1]
    if len(tokens) >= 3:
        params["step"] = tokens[2]
    elif len(tokens) >= 2:
        params["step"] = tokens[1]
    return {"type": "Transient", "params": params}


def _parse_ac(directive):
    tokens = directive.split()
    params = {}
    if len(tokens) >= 5:
        params["sweep_type"] = tokens[1]
        params["points"] = tokens[2]
        params["fStart"] = tokens[3]
        params["fStop"] = tokens[4]
    return {"type": "AC Sweep", "params": params}


def _parse_dc(directive):
    tokens = directive.split()
    params = {}
    if len(tokens) >= 5:
        params["source"] = tokens[1]
        params["min"] = tokens[2]
        params["max"] = tokens[3]
        params["step"] = tokens[4]
    return {"type": "DC Sweep", "params": params}


def import_asc(text):
    """Parse an LTspice .asc schematic and build a CircuitModel.

    Args:
        text: The full text content of a .asc file.

    Returns:
        tuple of (CircuitModel, analysis_dict_or_None, warnings_list)

    Raises:
        AscParseError: If the .asc file cannot be parsed.
    """
    parsed = parse_asc(text)
    raw_components = parsed["components"]
    raw_wires = parsed["wires"]
    raw_flags = parsed["flags"]
    analysis = parsed["analysis"]
    warnings = list(parsed["warnings"])

    model = CircuitModel()

    # Phase 1: Convert parsed symbols to ComponentData
    # Build a map of (x, y) -> [(comp_id, terminal_index)] for wire matching
    pin_map = {}  # (x, y) -> [(comp_id, terminal_index)]
    comp_info_list = []

    for sym in raw_components:
        lt_name = sym["ltspice_name"]

        # Normalize: strip path prefixes for matching
        lookup_name = lt_name
        comp_type = _SYMBOL_TO_TYPE.get(lookup_name)

        if comp_type is None:
            # Try lowercase
            comp_type = _SYMBOL_TO_TYPE.get(lookup_name.lower())

        if comp_type is None:
            # Try just the last path component
            base_name = lt_name.rsplit("\\", 1)[-1] if "\\" in lt_name else lt_name
            comp_type = _SYMBOL_TO_TYPE.get(base_name)
            if comp_type is None:
                comp_type = _SYMBOL_TO_TYPE.get(base_name.lower())

        if comp_type is None:
            warnings.append(f"Unsupported LTspice component '{lt_name}' — skipped")
            continue

        comp_id = sym["inst_name"]
        if comp_id is None:
            warnings.append(f"Component '{lt_name}' has no InstName — skipped")
            continue

        # Determine value
        value = sym["value"]
        if value is None:
            value = DEFAULT_VALUES.get(comp_type, "1")

        # Handle waveform sources
        if comp_type == "Voltage Source" and value:
            upper_val = value.upper()
            for func in ("SIN", "PULSE", "EXP", "PWL"):
                if func in upper_val:
                    comp_type = "Waveform Source"
                    break

        # Also check Value2 for AC sources
        if comp_type == "Voltage Source" and sym.get("value2"):
            val2_upper = sym["value2"].upper()
            for func in ("SIN", "PULSE", "EXP", "PWL"):
                if func in val2_upper:
                    comp_type = "Waveform Source"
                    value = sym["value2"]
                    break

        # Look up pin offsets: prefer LTspice symbol name, fall back to type
        lt_name_lower = lt_name.lower() if lt_name else ""
        pin_offsets = (
            _SYMBOL_PIN_OFFSETS.get(lt_name)
            or _SYMBOL_PIN_OFFSETS.get(lt_name_lower)
            or _PIN_OFFSETS.get(comp_type, [(0, 0), (0, 96)])
        )
        is_bipole = len(pin_offsets) == 2

        # Convert position: LTspice SYMBOL origin → Spice-GUI center
        cx, cy = _center_offset_from_pins(pin_offsets, sym["rotation"])
        pos_x = (sym["x"] + cx) * _SCALE
        pos_y = (sym["y"] + cy) * _SCALE

        # Convert rotation (bipoles need +90° offset)
        rotation_deg, flip_h = _rotation_to_degrees(sym["rotation"], is_bipole=is_bipole)

        component = ComponentData(
            component_id=comp_id,
            component_type=comp_type,
            value=value,
            position=(pos_x, pos_y),
            rotation=rotation_deg,
            flip_h=flip_h,
        )

        # Set up waveform params if applicable
        if comp_type == "Waveform Source":
            _setup_waveform_params(component, value)

        model.add_component(component)

        # Update component counter
        symbol = SPICE_SYMBOLS.get(comp_type, "X")
        num_match = re.search(r"(\d+)$", comp_id)
        if num_match:
            num = int(num_match.group(1))
            current = model.component_counter.get(symbol, 0)
            model.component_counter[symbol] = max(current, num)

        # Calculate absolute pin positions for this component
        # (pin_offsets was already resolved above via symbol/type lookup)
        for term_idx, (dx, dy) in enumerate(pin_offsets):
            tx, ty = _transform_pin(dx, dy, sym["rotation"])
            abs_x = sym["x"] + tx
            abs_y = sym["y"] + ty
            key = (abs_x, abs_y)
            if key not in pin_map:
                pin_map[key] = []
            pin_map[key].append((comp_id, term_idx))

        comp_info_list.append({"id": comp_id, "type": comp_type})

    # Phase 2: Build connectivity from wire segments
    # Use union-find to group connected wire endpoints + pin positions
    all_points = set()
    for x1, y1, x2, y2 in raw_wires:
        all_points.add((x1, y1))
        all_points.add((x2, y2))
    for key in pin_map:
        all_points.add(key)

    parent = {p: p for p in all_points}

    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Union wire segment endpoints
    for x1, y1, x2, y2 in raw_wires:
        union((x1, y1), (x2, y2))

    # Phase 3: Handle FLAG entries
    # FLAG x y 0 = ground, FLAG x y name = net label
    ground_points = set()
    for fx, fy, label in raw_flags:
        flag_pt = (fx, fy)
        if flag_pt not in parent:
            parent[flag_pt] = flag_pt
            all_points.add(flag_pt)

        if label == "0":
            ground_points.add(find(flag_pt))

    # Phase 4: Create ground components
    # Find all terminals connected to ground nets
    gnd_count = 0
    for pt in list(all_points):
        root = find(pt)
        if root in ground_points or find(pt) in ground_points:
            # Check if any component terminal is at this point
            if pt in pin_map:
                for comp_id, term_idx in pin_map[pt]:
                    gnd_count += 1
                    gnd_id = f"GND{gnd_count}"

                    gnd_x = pt[0] * _SCALE
                    gnd_y = (pt[1] + 48) * _SCALE

                    gnd_component = ComponentData(
                        component_id=gnd_id,
                        component_type="Ground",
                        value="0V",
                        position=(gnd_x, gnd_y),
                    )
                    model.add_component(gnd_component)
                    model.component_counter["GND"] = gnd_count

                    wire = WireData(
                        start_component_id=comp_id,
                        start_terminal=term_idx,
                        end_component_id=gnd_id,
                        end_terminal=0,
                    )
                    model.add_wire(wire)

    # Also update ground_points to include all points in ground nets
    # (for excluding from normal wire creation below)
    ground_roots = set()
    for pt in all_points:
        root = find(pt)
        if root in ground_points:
            ground_roots.add(root)

    # Group terminals by their net (union-find root)
    net_to_terminals = {}
    for pt, terminal_list in pin_map.items():
        root = find(pt)
        if root in ground_roots:
            continue  # Already handled by ground wires
        if root not in net_to_terminals:
            net_to_terminals[root] = []
        net_to_terminals[root].extend(terminal_list)

    for _net_root, terminals in net_to_terminals.items():
        if len(terminals) < 2:
            continue
        # Chain terminals together
        for j in range(len(terminals) - 1):
            comp_a, term_a = terminals[j]
            comp_b, term_b = terminals[j + 1]
            # Skip if either component was skipped
            if comp_a not in model.components or comp_b not in model.components:
                continue
            wire = WireData(
                start_component_id=comp_a,
                start_terminal=term_a,
                end_component_id=comp_b,
                end_terminal=term_b,
            )
            model.add_wire(wire)

    # Phase 6: Rebuild node graph and set analysis
    model.rebuild_nodes()

    if analysis:
        model.analysis_type = analysis["type"]
        model.analysis_params = analysis["params"]

    return model, analysis, warnings


def _setup_waveform_params(component, value_str):
    """Set up waveform parameters on a Waveform Source component."""
    upper = value_str.upper().strip()

    if "SIN" in upper:
        component.waveform_type = "SIN"
        params = _extract_paren_params(value_str)
        if len(params) >= 2:
            sin_params = {
                "offset": params[0] if len(params) > 0 else "0",
                "amplitude": params[1] if len(params) > 1 else "5",
                "frequency": params[2] if len(params) > 2 else "1k",
                "delay": params[3] if len(params) > 3 else "0",
                "theta": params[4] if len(params) > 4 else "0",
                "phase": params[5] if len(params) > 5 else "0",
            }
            component.waveform_params = {"SIN": sin_params}
    elif "PULSE" in upper:
        component.waveform_type = "PULSE"
        params = _extract_paren_params(value_str)
        if len(params) >= 2:
            pulse_params = {
                "v1": params[0] if len(params) > 0 else "0",
                "v2": params[1] if len(params) > 1 else "5",
                "td": params[2] if len(params) > 2 else "0",
                "tr": params[3] if len(params) > 3 else "1n",
                "tf": params[4] if len(params) > 4 else "1n",
                "pw": params[5] if len(params) > 5 else "500u",
                "per": params[6] if len(params) > 6 else "1m",
            }
            component.waveform_params = {"PULSE": pulse_params}
    elif "EXP" in upper:
        component.waveform_type = "EXP"
        params = _extract_paren_params(value_str)
        if len(params) >= 2:
            exp_params = {
                "v1": params[0] if len(params) > 0 else "0",
                "v2": params[1] if len(params) > 1 else "5",
                "td1": params[2] if len(params) > 2 else "0",
                "tau1": params[3] if len(params) > 3 else "1u",
                "td2": params[4] if len(params) > 4 else "2u",
                "tau2": params[5] if len(params) > 5 else "2u",
            }
            component.waveform_params = {"EXP": exp_params}


def _extract_paren_params(text):
    """Extract whitespace-separated parameters from inside parentheses."""
    match = re.search(r"\(([^)]*)\)", text)
    if match:
        return match.group(1).split()
    return []
