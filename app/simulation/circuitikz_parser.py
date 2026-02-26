"""
simulation/circuitikz_parser.py

Parses CircuiTikZ LaTeX code and converts it into a CircuitModel.
Reverses the circuitikz_exporter.py output. Pure Python -- no Qt.
"""

import logging
import re
from collections import defaultdict

from models.circuit import CircuitModel
from models.component import DEFAULT_VALUES, ComponentData
from models.wire import WireData

logger = logging.getLogger(__name__)

# Default scale (pixels per TikZ unit), must match circuitikz_exporter.DEFAULT_SCALE
DEFAULT_SCALE = 20.0

# Reverse mapping: CircuiTikZ bipole name -> Spice-GUI component type
_TIKZ_TO_BIPOLE = {
    "R": "Resistor",
    "C": "Capacitor",
    "L": "Inductor",
    "V": "Voltage Source",
    "I": "Current Source",
    "sV": "Waveform Source",
    "D": "Diode",
    "led": "LED",
    "zD": "Zener Diode",
    "closing switch": "VC Switch",
    "american controlled voltage source": "VCVS",
    "american controlled current source": "VCCS",
    # European-style aliases
    "european resistor": "Resistor",
    "european voltage source": "Voltage Source",
    "european current source": "Current Source",
}

# Reverse mapping: CircuiTikZ tripole name -> Spice-GUI component type
_TIKZ_TO_TRIPOLE = {
    "npn": "BJT NPN",
    "pnp": "BJT PNP",
    "nmos": "MOSFET NMOS",
    "pmos": "MOSFET PMOS",
    "op amp": "Op-Amp",
}

# Regex patterns
_RE_COORD = r"\(\s*([\d.eE+-]+)\s*,\s*([\d.eE+-]+)\s*\)"
_RE_DRAW_TO = re.compile(
    r"\\draw\s+" + _RE_COORD + r"\s+to\s*\[([^\]]*)\]\s*" + _RE_COORD + r"\s*;([^\n]*)",
    re.DOTALL,
)
_RE_NODE_COMPONENT = re.compile(
    r"\\node\s*\[([^\]]+)\]\s*\(([^)]*)\)\s*at\s*" + _RE_COORD + r"\s*\{\s*\}\s*;",
)
_RE_NODE_GROUND = re.compile(
    r"\\node\s*\[ground\]\s*at\s*" + _RE_COORD + r"\s*\{\s*\}\s*;",
)
_RE_DRAW_WIRE = re.compile(
    r"\\draw(?:\[dashed\])?\s+" + _RE_COORD + r"(?:\s*--\s*" + _RE_COORD + r")+\s*;",
)
# Matches dashed control-pair draws:  \draw[dashed] (x1,y1) to[short] (x2,y2); % ctrl: <id>
_RE_DASHED_CTRL = re.compile(
    r"\\draw\[dashed\]\s+" + _RE_COORD + r"\s+to\s*\[short\]\s*" + _RE_COORD + r"\s*;\s*%\s*ctrl:\s*(\S+)",
)
_RE_ALL_COORDS = re.compile(_RE_COORD)


class CircuitikzParseError(ValueError):
    """Raised when CircuiTikZ code cannot be parsed."""


def _parse_label(opts_str):
    """Extract component ID from l=$..$ option."""
    m = re.search(r"l\s*=\s*\$([^$]*)\$", opts_str)
    if m:
        # Un-escape LaTeX: \_ -> _
        return m.group(1).replace("\\_", "_").replace("\\", "")
    return None


def _parse_value(opts_str):
    """Extract component value from a={...} option."""
    m = re.search(r"a\s*=\s*\{([^}]*)\}", opts_str)
    if m:
        return m.group(1).replace("\\_", "_").replace("\\", "")
    return None


def _parse_component_name(opts_str):
    """Extract the CircuiTikZ component name from the to[...] options.

    The component name is the first token before any comma-separated option.
    """
    # Remove l=... and a=... options to isolate the component name
    cleaned = re.sub(r"\bl\s*=\s*\$[^$]*\$", "", opts_str)
    cleaned = re.sub(r"\ba\s*=\s*\{[^}]*\}", "", cleaned)
    # Split by comma and take the first non-empty token
    for part in cleaned.split(","):
        part = part.strip()
        if part:
            return part
    return None


def _tikz_to_pixel(tx, ty, scale, offset_x=0.0, offset_y=0.0, max_ty=0.0):
    """Convert TikZ coordinates back to pixel coordinates.

    Reverses: tx = (px - min_x) / scale, ty = (max_y - py) / scale
    =>  px = tx * scale + offset_x,  py = max_ty_pixels - ty * scale
    """
    px = tx * scale + offset_x
    py = (max_ty - ty) * scale + offset_y
    return (round(px, 1), round(py, 1))


def _extract_circuitikz_body(text):
    """Extract the content inside \\begin{circuitikz}...\\end{circuitikz}."""
    m = re.search(r"\\begin\{circuitikz\}(.*?)\\end\{circuitikz\}", text, re.DOTALL)
    if m:
        return m.group(1)
    # Fallback: try the whole text (bare TikZ without document wrapper)
    return text


def import_circuitikz(text):
    """Parse CircuiTikZ LaTeX code and build a CircuitModel.

    Args:
        text: LaTeX source code (standalone document or bare environment).

    Returns:
        (CircuitModel, list[str]): The circuit model and a list of warnings.

    Raises:
        CircuitikzParseError: If the input cannot be parsed at all.
    """
    warnings = []
    body = _extract_circuitikz_body(text)

    # --- Step 1: Parse all elements ---
    bipoles = []
    tripoles = []
    grounds = []
    wires = []

    # Parse bipoles: \draw (x1,y1) to[opts] (x2,y2); [% spice: <type>]
    for m in _RE_DRAW_TO.finditer(body):
        x1, y1, opts, x2, y2, trailing = (
            m.group(1),
            m.group(2),
            m.group(3),
            m.group(4),
            m.group(5),
            m.group(6),
        )
        # Check for a % spice: <type> override (disambiguates CCVS/CCCS)
        spice_type = None
        type_m = re.search(r"%\s*spice:\s*(\S+)", trailing)
        if type_m:
            spice_type = type_m.group(1)
        bipoles.append(
            {
                "x1": float(x1),
                "y1": float(y1),
                "opts": opts,
                "x2": float(x2),
                "y2": float(y2),
                "spice_type": spice_type,
            }
        )

    # Parse tripoles: \node[type, opts] (id) at (x,y) {};
    for m in _RE_NODE_COMPONENT.finditer(body):
        opts, node_id, x, y = m.group(1), m.group(2), m.group(3), m.group(4)
        # Skip ground nodes (handled separately)
        if "ground" in opts:
            continue
        tripoles.append(
            {
                "opts": opts,
                "node_id": node_id,
                "x": float(x),
                "y": float(y),
            }
        )

    # Parse ground: \node[ground] at (x,y) {};
    for m in _RE_NODE_GROUND.finditer(body):
        x, y = m.group(1), m.group(2)
        grounds.append({"x": float(x), "y": float(y)})

    # Parse dashed control pairs: \draw[dashed] (x1,y1) to[short] (x2,y2); % ctrl: <id>
    ctrl_pairs = {}  # comp_id -> (x1, y1, x2, y2) in TikZ coords
    for m in _RE_DASHED_CTRL.finditer(body):
        x1, y1, x2, y2, ctrl_id = (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
            float(m.group(4)),
            m.group(5),
        )
        ctrl_pairs[ctrl_id] = (x1, y1, x2, y2)

    # Parse wires: \draw (x1,y1) -- (x2,y2) [-- ...];
    for m in _RE_DRAW_WIRE.finditer(body):
        segment_text = m.group(0)
        # Skip if this is a bipole draw (has 'to[' in it)
        if "to[" in segment_text:
            continue
        coords = _RE_ALL_COORDS.findall(segment_text)
        if len(coords) >= 2:
            points = [(float(x), float(y)) for x, y in coords]
            wires.append(points)

    if not bipoles and not tripoles and not grounds:
        raise CircuitikzParseError("No circuit elements found in the CircuiTikZ code.")

    # --- Step 2: Determine coordinate bounds for reverse transform ---
    all_tikz_coords = []
    for b in bipoles:
        all_tikz_coords.extend([(b["x1"], b["y1"]), (b["x2"], b["y2"])])
    for t in tripoles:
        all_tikz_coords.append((t["x"], t["y"]))
    for g in grounds:
        all_tikz_coords.append((g["x"], g["y"]))
    for w in wires:
        all_tikz_coords.extend(w)
    for x1, y1, x2, y2 in ctrl_pairs.values():
        all_tikz_coords.extend([(x1, y1), (x2, y2)])

    if not all_tikz_coords:
        return CircuitModel(), warnings

    max_ty = max(y for _, y in all_tikz_coords)

    def to_pixel(tx, ty):
        return _tikz_to_pixel(tx, ty, DEFAULT_SCALE, offset_x=0.0, offset_y=0.0, max_ty=max_ty)

    # --- Step 3: Build components ---
    model = CircuitModel()
    counters = defaultdict(int)
    # Track terminal positions for wire matching
    terminal_positions = {}  # (comp_id, term_idx) -> pixel position

    for bp in bipoles:
        comp_name = _parse_component_name(bp["opts"])
        if comp_name is None:
            warnings.append(f"Could not parse component name from: {bp['opts']}")
            continue

        comp_type = _TIKZ_TO_BIPOLE.get(comp_name)
        if comp_type is None:
            warnings.append(f"Unsupported CircuiTikZ component: {comp_name}")
            continue

        # Override type when a % spice: <type> comment is present
        # (distinguishes CCVS from VCVS, CCCS from VCCS)
        if bp.get("spice_type") and bp["spice_type"] in ("CCVS", "CCCS"):
            comp_type = bp["spice_type"]

        comp_id = _parse_label(bp["opts"])
        value = _parse_value(bp["opts"])

        # Generate ID if not found in label
        if not comp_id:
            from models.component import SPICE_SYMBOLS

            prefix = SPICE_SYMBOLS.get(comp_type, comp_type[0])
            counters[prefix] += 1
            comp_id = f"{prefix}{counters[prefix]}"

        # Default value if not found
        if not value:
            value = DEFAULT_VALUES.get(comp_type, "")

        # Convert bipole endpoints to pixel coords
        p1 = to_pixel(bp["x1"], bp["y1"])
        p2 = to_pixel(bp["x2"], bp["y2"])

        # For 4-terminal devices the bipole draw represents the output pair
        # (terminals 2,3) and a separate dashed draw holds the control pair
        # (terminals 0,1).
        from models.component import TERMINAL_COUNTS

        is_four_terminal = TERMINAL_COUNTS.get(comp_type, 2) == 4
        ctrl_pair = ctrl_pairs.get(comp_id) if is_four_terminal else None

        if ctrl_pair is not None:
            cp1 = to_pixel(ctrl_pair[0], ctrl_pair[1])
            cp2 = to_pixel(ctrl_pair[2], ctrl_pair[3])
            all_x = [p1[0], p2[0], cp1[0], cp2[0]]
            all_y = [p1[1], p2[1], cp1[1], cp2[1]]
            pos = (round(sum(all_x) / 4, 1), round(sum(all_y) / 4, 1))
        else:
            pos = (round((p1[0] + p2[0]) / 2, 1), round((p1[1] + p2[1]) / 2, 1))

        comp = ComponentData(
            component_id=comp_id,
            component_type=comp_type,
            value=value,
            position=pos,
        )
        model.add_component(comp)

        # Update counter
        from models.component import SPICE_SYMBOLS

        prefix = SPICE_SYMBOLS.get(comp_type, comp_type[0])
        # Extract number from comp_id
        num_match = re.search(r"(\d+)$", comp_id)
        if num_match:
            num = int(num_match.group(1))
            if num > counters.get(prefix, 0):
                counters[prefix] = num

        # Record terminal positions
        if ctrl_pair is not None:
            # 4-terminal: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
            terminal_positions[(comp_id, 0)] = cp1
            terminal_positions[(comp_id, 1)] = cp2
            terminal_positions[(comp_id, 2)] = p1
            terminal_positions[(comp_id, 3)] = p2
        else:
            terminal_positions[(comp_id, 0)] = p1
            terminal_positions[(comp_id, 1)] = p2

    for tp in tripoles:
        opts = tp["opts"]
        # Parse the component type from opts (first token)
        opts_parts = [p.strip() for p in opts.split(",")]
        tikz_type = opts_parts[0]

        comp_type = _TIKZ_TO_TRIPOLE.get(tikz_type)
        if comp_type is None:
            warnings.append(f"Unsupported CircuiTikZ tripole: {tikz_type}")
            continue

        comp_id = tp["node_id"].replace("_", " ") if tp["node_id"] else None

        # Parse rotation and flip from opts
        rotation = 0
        flip_h = False
        for part in opts_parts[1:]:
            part = part.strip()
            rot_m = re.match(r"rotate\s*=\s*(-?\d+)", part)
            if rot_m:
                rotation = int(rot_m.group(1))
            if "xscale=-1" in part:
                flip_h = True

        if not comp_id:
            from models.component import SPICE_SYMBOLS

            prefix = SPICE_SYMBOLS.get(comp_type, comp_type[0])
            counters[prefix] += 1
            comp_id = f"{prefix}{counters[prefix]}"

        pos = to_pixel(tp["x"], tp["y"])
        comp = ComponentData(
            component_id=comp_id,
            component_type=comp_type,
            value=DEFAULT_VALUES.get(comp_type, ""),
            position=pos,
            rotation=rotation,
            flip_h=flip_h,
        )
        model.add_component(comp)

        from models.component import SPICE_SYMBOLS

        prefix = SPICE_SYMBOLS.get(comp_type, comp_type[0])
        num_match = re.search(r"(\d+)$", comp_id)
        if num_match:
            num = int(num_match.group(1))
            if num > counters.get(prefix, 0):
                counters[prefix] = num

        # Record terminal positions from the component's calculated positions
        terminals = comp.get_terminal_positions()
        for i, tpos in enumerate(terminals):
            terminal_positions[(comp_id, i)] = tpos

    for i, gnd in enumerate(grounds):
        gnd_id = f"GND{i + 1}"
        pos = to_pixel(gnd["x"], gnd["y"])
        comp = ComponentData(
            component_id=gnd_id,
            component_type="Ground",
            value="0V",
            position=pos,
        )
        model.add_component(comp)
        terminals = comp.get_terminal_positions()
        if terminals:
            terminal_positions[(gnd_id, 0)] = terminals[0]

    # Update model counters
    for prefix, count in counters.items():
        model.component_counter[prefix] = count

    # --- Step 4: Build wires by matching endpoints to nearest terminals ---
    snap_tolerance = DEFAULT_SCALE * 0.6  # ~12 pixels

    def _find_nearest_terminal(px, py):
        """Find the closest terminal within snap tolerance."""
        best = None
        best_dist = snap_tolerance
        for (cid, tidx), (tx, ty) in terminal_positions.items():
            dist = ((px - tx) ** 2 + (py - ty) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = (cid, tidx)
        return best

    for wire_points in wires:
        start = to_pixel(*wire_points[0])
        end = to_pixel(*wire_points[-1])

        start_term = _find_nearest_terminal(*start)
        end_term = _find_nearest_terminal(*end)

        if start_term and end_term and start_term != end_term:
            waypoints = []
            if len(wire_points) > 2:
                waypoints = [to_pixel(*wp) for wp in wire_points[1:-1]]

            wire = WireData(
                start_component_id=start_term[0],
                start_terminal=start_term[1],
                end_component_id=end_term[0],
                end_terminal=end_term[1],
                waypoints=waypoints,
            )
            model.wires.append(wire)

    model.rebuild_nodes()
    return model, warnings
