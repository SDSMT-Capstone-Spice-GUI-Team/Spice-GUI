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

# Pin offsets (dx, dy) relative to SYMBOL position for each type (at R0 orientation)
# LTspice convention: R0 = vertical, pin 1 at top
_PIN_OFFSETS = {
    "Resistor": [(0, 0), (0, 80)],
    "Capacitor": [(0, 0), (0, 64)],
    "Inductor": [(0, 0), (0, 80)],
    "Voltage Source": [(0, 0), (0, 112)],
    "Current Source": [(0, 0), (0, 112)],
    "Diode": [(0, 0), (0, 64)],
    "LED": [(0, 0), (0, 64)],
    "Zener Diode": [(0, 0), (0, 64)],
    "BJT NPN": [(16, 0), (-16, 32), (16, 64)],  # C, B, E
    "BJT PNP": [(16, 64), (-16, 32), (16, 0)],  # C, B, E
    "MOSFET NMOS": [(16, 0), (-16, 32), (16, 64)],  # D, G, S
    "MOSFET PMOS": [(16, 64), (-16, 32), (16, 0)],  # D, G, S
    "Op-Amp": [(-32, 32), (-32, -32), (32, 0)],  # in+, in-, out
    "VCVS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "CCVS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "VCCS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
    "CCCS": [(-32, 32), (-32, -32), (32, -32), (32, 32)],
}

# Coordinate scale factor: LTspice units -> Spice-GUI scene coordinates
_SCALE = 1.0


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


def _rotation_to_degrees(rotation_code):
    """Convert LTspice rotation code to Spice-GUI rotation degrees and flip state.

    Returns (rotation_degrees, flip_h).
    """
    code = rotation_code.upper() if rotation_code else "R0"
    mirrored = code.startswith("M")
    angle = int(code[1:]) if len(code) > 1 else 0

    # LTspice R0 is vertical, Spice-GUI 0 is horizontal
    # We use rotation 90 to convert from LTspice vertical to Spice-GUI horizontal
    # for 2-terminal components. For multi-terminal, keep as-is.
    return angle, mirrored


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
                    x1, y1, x2, y2 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                    wires.append((x1, y1, x2, y2))
                except ValueError:
                    pass

        elif stripped.startswith("FLAG "):
            parts = stripped.split()
            if len(parts) >= 4:
                try:
                    x, y = int(parts[1]), int(parts[2])
                    label = parts[3]
                    flags.append((x, y, label))
                except ValueError:
                    pass

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

        # Convert position: scale LTspice coords to scene coords
        pos_x = sym["x"] * _SCALE
        pos_y = sym["y"] * _SCALE

        # Convert rotation
        rotation_deg, flip_h = _rotation_to_degrees(sym["rotation"])

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
        pin_offsets = _PIN_OFFSETS.get(comp_type, [(0, 0), (0, 80)])
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

    # Phase 5: Create wires between component terminals sharing the same net
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
