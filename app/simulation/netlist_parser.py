"""
simulation/netlist_parser.py

Parses SPICE netlist files (.cir, .spice) and converts them into
CircuitModel objects for display on the canvas.
"""

import logging
import re

from models.circuit import CircuitModel
from models.component import DEFAULT_VALUES, SPICE_SYMBOLS, ComponentData
from models.wire import WireData

logger = logging.getLogger(__name__)

# Reverse mapping: SPICE prefix letter -> component display type
# For ambiguous prefixes (D, Q, M), we pick a default
_PREFIX_TO_TYPE = {}
for _display_name, _symbol in SPICE_SYMBOLS.items():
    if _symbol not in _PREFIX_TO_TYPE:
        _PREFIX_TO_TYPE[_symbol] = _display_name

# Override ambiguous ones with sensible defaults
_PREFIX_TO_TYPE["D"] = "Diode"
_PREFIX_TO_TYPE["Q"] = "BJT NPN"
_PREFIX_TO_TYPE["M"] = "MOSFET NMOS"

# Single-letter SPICE prefixes for component lines
_COMPONENT_PREFIXES = set("RCLIVDEFGHQMSXK")

# Grid layout constants
_GRID_SPACING = 150  # pixels between components
_GRID_COLS = 5  # max components per row
_START_X = -300
_START_Y = -200


class NetlistParseError(ValueError):
    """Raised when a netlist cannot be parsed."""


def parse_netlist(text):
    """Parse SPICE netlist text into a structured representation.

    Args:
        text: The full text content of a .cir/.spice file.

    Returns:
        dict with keys:
            title: str - first line (title)
            components: list of dict - parsed component entries
            models: dict of model_name -> model_info
            analysis: dict with type and params (or None)

    Raises:
        NetlistParseError: If the netlist is empty or has no components.
    """
    lines = text.strip().split("\n")
    if not lines:
        raise NetlistParseError("Empty netlist file.")

    title = lines[0].strip()
    models = {}
    analysis = None
    component_lines = []
    in_control_block = False
    in_subckt = False

    subckt_defs = {}  # name -> {name, pins, definition}
    _current_subckt_name = None
    _current_subckt_lines = []

    # Two-pass: first collect models and directives, then parse components
    for line in lines[1:]:
        stripped = line.strip()

        if not stripped or stripped.startswith("*"):
            if in_subckt:
                _current_subckt_lines.append(stripped)
            continue

        if ";" in stripped:
            stripped = stripped[: stripped.index(";")].strip()
            if not stripped:
                continue

        lower = stripped.lower()

        if lower.startswith(".control"):
            in_control_block = True
            continue
        if lower.startswith(".endc"):
            in_control_block = False
            continue
        if in_control_block:
            continue

        if lower.startswith(".subckt"):
            in_subckt = True
            tokens = stripped.split()
            _current_subckt_name = tokens[1] if len(tokens) > 1 else None
            _current_subckt_lines = [stripped]
            continue
        if lower.startswith(".ends"):
            _current_subckt_lines.append(stripped)
            if _current_subckt_name:
                defn = "\n".join(_current_subckt_lines)
                first_line_tokens = _current_subckt_lines[0].split()
                pins = first_line_tokens[2:] if len(first_line_tokens) > 2 else []
                subckt_defs[_current_subckt_name.upper()] = {
                    "name": _current_subckt_name,
                    "pins": pins,
                    "definition": defn,
                }
            _current_subckt_name = None
            _current_subckt_lines = []
            in_subckt = False
            continue
        if in_subckt:
            _current_subckt_lines.append(stripped)
            continue

        if lower == ".end":
            break

        if lower.startswith("."):
            if lower.startswith(".model"):
                model_info = _parse_model_line(stripped)
                if model_info:
                    models[model_info["name"]] = model_info
            elif lower.startswith(".op"):
                analysis = {"type": "DC Operating Point", "params": {}}
            elif lower.startswith(".tran"):
                analysis = _parse_tran_directive(stripped)
            elif lower.startswith(".ac"):
                analysis = _parse_ac_directive(stripped)
            elif lower.startswith(".dc"):
                analysis = _parse_dc_directive(stripped)
            continue

        first_char = stripped[0].upper()
        if first_char in _COMPONENT_PREFIXES:
            component_lines.append(stripped)

    # Second pass: parse component lines with all models available
    components = []
    for comp_line in component_lines:
        comp = _parse_component_line(comp_line, models, subckt_defs)
        if comp:
            components.append(comp)

    if not components:
        raise NetlistParseError("No components found in netlist.")

    return {
        "title": title,
        "components": components,
        "models": models,
        "analysis": analysis,
        "subcircuit_definitions": subckt_defs,
    }


def _parse_component_line(line, models, subckt_defs=None):
    """Parse a single SPICE component line.

    Returns a dict with: id, prefix, type, nodes, value, model
    or None if the line cannot be parsed.
    """
    if subckt_defs is None:
        subckt_defs = {}

    tokens = _tokenize_spice_line(line)
    if len(tokens) < 3:
        return None

    comp_id = tokens[0]
    prefix = comp_id[0].upper()

    if prefix == "X":
        # Subcircuit instance: X<name> node1 node2 ... subckt_name
        subckt_name = tokens[-1].upper()
        node_names = tokens[1:-1]
        if "OPAMP" in subckt_name:
            return {
                "id": comp_id,
                "prefix": prefix,
                "type": "Op-Amp",
                "nodes": node_names,
                "value": DEFAULT_VALUES.get("Op-Amp", "Ideal"),
                "model": subckt_name,
            }
        # Generic subcircuit
        subckt_info = subckt_defs.get(subckt_name)
        result = {
            "id": comp_id,
            "prefix": prefix,
            "type": "Subcircuit",
            "nodes": node_names,
            "value": subckt_name,
            "model": subckt_name,
        }
        if subckt_info:
            result["subcircuit_name"] = subckt_info["name"]
            result["subcircuit_pins"] = subckt_info["pins"]
            result["subcircuit_definition"] = subckt_info["definition"]
        else:
            # No definition found; use node names as pin labels
            result["subcircuit_name"] = subckt_name
            result["subcircuit_pins"] = [f"p{i}" for i in range(len(node_names))]
        return result

    # Determine component type from prefix
    comp_type = _PREFIX_TO_TYPE.get(prefix)
    if comp_type is None:
        logger.warning("Unknown SPICE prefix '%s' - skipping %s", prefix, comp_id)
        return None

    # Determine number of nodes based on SPICE syntax
    if prefix in ("Q",):
        num_nodes = 3
    elif prefix in ("M",):
        num_nodes = 4
    elif prefix in ("E", "G"):
        num_nodes = 4
    elif prefix in ("H", "F"):
        num_nodes = 2
    elif prefix in ("S",):
        num_nodes = 4
    else:
        num_nodes = 2

    if len(tokens) < num_nodes + 2:
        logger.warning("Not enough tokens for %s: %s", comp_id, line)
        return None

    node_names = tokens[1 : 1 + num_nodes]
    rest = tokens[1 + num_nodes :]

    # Extract value and/or model
    value = ""
    model_name = None

    if prefix in ("R", "C", "L"):
        value = rest[0] if rest else DEFAULT_VALUES.get(comp_type, "1")
    elif prefix in ("V", "I"):
        value, comp_type = _parse_source_value(rest, prefix)
    elif prefix in ("D",):
        model_name = rest[0] if rest else None
        value = _resolve_model_value(model_name, models, comp_type)
    elif prefix in ("Q",):
        if len(tokens) >= 6:
            model_name = rest[-1] if rest else None
        else:
            model_name = rest[0] if rest else None
        comp_type = _resolve_bjt_type(model_name, models)
        value = model_name or DEFAULT_VALUES.get(comp_type, "2N3904")
    elif prefix in ("M",):
        model_name = rest[0] if rest else None
        comp_type = _resolve_mosfet_type(model_name, models)
        value = model_name or DEFAULT_VALUES.get(comp_type, "NMOS1")
    elif prefix in ("E", "G"):
        value = rest[0] if rest else "1"
    elif prefix in ("H", "F"):
        value = rest[1] if len(rest) > 1 else "1"
    elif prefix in ("S",):
        model_name = rest[0] if rest else None
        value = _resolve_model_value(model_name, models, comp_type)

    return {
        "id": comp_id,
        "prefix": prefix,
        "type": comp_type,
        "nodes": node_names,
        "value": value,
        "model": model_name,
    }


def _tokenize_spice_line(line):
    """Tokenize a SPICE line, keeping parenthesized expressions as single tokens.

    E.g. 'Vin 1 0 SIN(0 5 1k)' -> ['Vin', '1', '0', 'SIN(0 5 1k)']
    """
    tokens = []
    current = ""
    paren_depth = 0

    for ch in line:
        if ch == "(":
            paren_depth += 1
            current += ch
        elif ch == ")":
            paren_depth -= 1
            current += ch
        elif ch in (" ", "\t") and paren_depth == 0:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += ch

    if current:
        tokens.append(current)

    return tokens


def _parse_source_value(rest_tokens, prefix):
    """Parse voltage/current source value from remaining tokens.

    Returns (value_str, component_type).
    """
    if not rest_tokens:
        comp_type = "Voltage Source" if prefix == "V" else "Current Source"
        return DEFAULT_VALUES.get(comp_type, "5V"), comp_type

    combined = " ".join(rest_tokens).strip()
    upper = combined.upper()

    # Check for waveform functions
    for func in ("SIN", "PULSE", "PWL", "EXP"):
        if func in upper:
            idx = upper.index(func)
            waveform_str = combined[idx:]
            return waveform_str, "Waveform Source"

    # Check for AC specification with waveform
    if upper.startswith("AC"):
        after_ac = combined[2:].strip()
        upper_after = after_ac.upper()
        for func in ("SIN", "PULSE", "PWL", "EXP"):
            if func in upper_after:
                idx = upper_after.index(func)
                waveform_str = after_ac[idx:]
                return waveform_str, "Waveform Source"
        value = after_ac if after_ac else "1"
        comp_type = "Voltage Source" if prefix == "V" else "Current Source"
        return value, comp_type

    # DC value: "DC 5" or just "5"
    if upper.startswith("DC"):
        value = combined[2:].strip()
    else:
        value = combined

    comp_type = "Voltage Source" if prefix == "V" else "Current Source"
    return value if value else DEFAULT_VALUES.get(comp_type, "5V"), comp_type


def _parse_model_line(line):
    """Parse a .model directive line."""
    tokens = _tokenize_spice_line(line)
    if len(tokens) < 3:
        return None

    name = tokens[1]
    model_type = tokens[2].upper()
    params = ""
    if len(tokens) > 3:
        params = " ".join(tokens[3:])
        if params.startswith("(") and params.endswith(")"):
            params = params[1:-1]

    return {"name": name, "type": model_type, "params": params}


def _resolve_model_value(model_name, models, comp_type):
    """Get a component value from model info, or use default."""
    if model_name and model_name in models:
        model = models[model_name]
        if model.get("params"):
            return model["params"]
    return DEFAULT_VALUES.get(comp_type, "1")


def _resolve_bjt_type(model_name, models):
    """Determine BJT NPN vs PNP from model definition."""
    if model_name and model_name in models:
        model_type = models[model_name].get("type", "").upper()
        if "PNP" in model_type:
            return "BJT PNP"
    return "BJT NPN"


def _resolve_mosfet_type(model_name, models):
    """Determine MOSFET NMOS vs PMOS from model definition."""
    if model_name and model_name in models:
        model_type = models[model_name].get("type", "").upper()
        if "PMOS" in model_type:
            return "MOSFET PMOS"
    return "MOSFET NMOS"


def _parse_tran_directive(line):
    """Parse .tran step duration [start] directive."""
    tokens = line.split()
    params = {}
    if len(tokens) >= 3:
        params["step"] = tokens[1]
        params["duration"] = tokens[2]
    if len(tokens) >= 4:
        params["start"] = tokens[3]
    return {"type": "Transient", "params": params}


def _parse_ac_directive(line):
    """Parse .ac sweep_type points fstart fstop directive."""
    tokens = line.split()
    params = {}
    if len(tokens) >= 5:
        params["sweep_type"] = tokens[1]
        params["points"] = tokens[2]
        params["fStart"] = tokens[3]
        params["fStop"] = tokens[4]
    return {"type": "AC Sweep", "params": params}


def _parse_dc_directive(line):
    """Parse .dc source start stop step directive."""
    tokens = line.split()
    params = {}
    if len(tokens) >= 5:
        params["source"] = tokens[1]
        params["min"] = tokens[2]
        params["max"] = tokens[3]
        params["step"] = tokens[4]
    return {"type": "DC Sweep", "params": params}


def import_netlist(text):
    """Parse a SPICE netlist and build a CircuitModel.

    Args:
        text: The full text content of a .cir/.spice file.

    Returns:
        tuple of (CircuitModel, analysis_dict_or_None)

    Raises:
        NetlistParseError: If the netlist cannot be parsed.
    """
    parsed = parse_netlist(text)
    components_data = parsed["components"]
    analysis = parsed["analysis"]

    model = CircuitModel()

    # Build node-to-terminals map: netlist_node_name -> [(comp_id, terminal_index)]
    node_to_terminals = {}

    # Phase 1: Create ComponentData objects and track node connections
    positions = _compute_layout(components_data)

    for comp_info in components_data:
        comp_id = comp_info["id"]
        comp_type = comp_info["type"]
        value = comp_info["value"]
        position = positions.get(comp_id, (0.0, 0.0))

        component = ComponentData(
            component_id=comp_id,
            component_type=comp_type,
            value=value,
            position=position,
        )

        # Handle waveform source parameters
        if comp_type == "Waveform Source":
            _setup_waveform_params(component, value)

        # Handle subcircuit parameters
        if comp_type == "Subcircuit":
            component.subcircuit_name = comp_info.get("subcircuit_name")
            component.subcircuit_pins = comp_info.get("subcircuit_pins")
            component.subcircuit_definition = comp_info.get("subcircuit_definition")
            if component.subcircuit_name and component.subcircuit_definition:
                model.subcircuit_definitions[component.subcircuit_name] = component.subcircuit_definition

        model.add_component(component)

        # Update component counter
        symbol = SPICE_SYMBOLS.get(comp_type, "X")
        num_match = re.search(r"(\d+)$", comp_id)
        if num_match:
            num = int(num_match.group(1))
            current = model.component_counter.get(symbol, 0)
            model.component_counter[symbol] = max(current, num)

        # Map netlist nodes to component terminals
        nodes = comp_info["nodes"]

        if comp_type == "Op-Amp":
            # Subcircuit: X<name> inp(non-inv) inn(inv) out
            # Our terminals: 0=inv, 1=non-inv, 2=out
            terminal_map = [1, 0, 2]
            for spice_idx, node_name in enumerate(nodes):
                if spice_idx < len(terminal_map):
                    term_idx = terminal_map[spice_idx]
                    _add_node_terminal(node_to_terminals, node_name, comp_id, term_idx)
        elif comp_info["prefix"] in ("E", "G"):
            # VCVS/VCCS: SPICE order out+ out- ctrl+ ctrl-
            # Our terminals: 0=ctrl+ 1=ctrl- 2=out+ 3=out-
            terminal_map = [2, 3, 0, 1]
            for spice_idx, node_name in enumerate(nodes):
                if spice_idx < len(terminal_map):
                    term_idx = terminal_map[spice_idx]
                    _add_node_terminal(node_to_terminals, node_name, comp_id, term_idx)
        elif comp_info["prefix"] in ("S",):
            # VC Switch: SPICE order switch+ switch- ctrl+ ctrl-
            # Our terminals: 0=ctrl+ 1=ctrl- 2=switch+ 3=switch-
            terminal_map = [2, 3, 0, 1]
            for spice_idx, node_name in enumerate(nodes):
                if spice_idx < len(terminal_map):
                    term_idx = terminal_map[spice_idx]
                    _add_node_terminal(node_to_terminals, node_name, comp_id, term_idx)
        elif comp_info["prefix"] == "M":
            # MOSFET: SPICE order drain gate source bulk
            # Our terminals: 0=drain 1=gate 2=source (ignore bulk)
            for spice_idx, node_name in enumerate(nodes[:3]):
                _add_node_terminal(node_to_terminals, node_name, comp_id, spice_idx)
        else:
            # Standard terminal ordering
            for term_idx, node_name in enumerate(nodes):
                _add_node_terminal(node_to_terminals, node_name, comp_id, term_idx)

    # Phase 2: Add Ground components for node "0"
    ground_terminals = node_to_terminals.pop("0", [])
    if ground_terminals:
        for gnd_idx, (comp_id, term_idx) in enumerate(ground_terminals):
            gnd_id = f"GND{gnd_idx + 1}"
            comp = model.components.get(comp_id)
            if comp:
                gnd_pos = (comp.position[0], comp.position[1] + _GRID_SPACING)
            else:
                gnd_pos = (_START_X + gnd_idx * 80, _START_Y + 3 * _GRID_SPACING)

            gnd_component = ComponentData(
                component_id=gnd_id,
                component_type="Ground",
                value="0V",
                position=gnd_pos,
            )
            model.add_component(gnd_component)

            current = model.component_counter.get("GND", 0)
            model.component_counter["GND"] = max(current, gnd_idx + 1)

            wire = WireData(
                start_component_id=comp_id,
                start_terminal=term_idx,
                end_component_id=gnd_id,
                end_terminal=0,
            )
            model.add_wire(wire)

    # Phase 3: Create wires between components sharing the same netlist node
    for node_name, terminals in node_to_terminals.items():
        if len(terminals) < 2:
            continue

        for j in range(len(terminals) - 1):
            comp_a, term_a = terminals[j]
            comp_b, term_b = terminals[j + 1]
            wire = WireData(
                start_component_id=comp_a,
                start_terminal=term_a,
                end_component_id=comp_b,
                end_terminal=term_b,
            )
            model.add_wire(wire)

    # Phase 4: Rebuild node graph
    model.rebuild_nodes()

    # Phase 5: Set analysis type if parsed
    if analysis:
        model.analysis_type = analysis["type"]
        model.analysis_params = analysis["params"]

    return model, analysis


def _add_node_terminal(node_to_terminals, node_name, comp_id, term_idx):
    """Add a (comp_id, terminal_index) entry to the node map."""
    node_key = node_name.lower() if node_name != "0" else "0"
    if node_key not in node_to_terminals:
        node_to_terminals[node_key] = []
    node_to_terminals[node_key].append((comp_id, term_idx))


def _compute_layout(components_data):
    """Compute grid positions for imported components.

    Returns dict of comp_id -> (x, y).
    """
    positions = {}
    for i, comp in enumerate(components_data):
        row = i // _GRID_COLS
        col = i % _GRID_COLS
        x = _START_X + col * _GRID_SPACING
        y = _START_Y + row * _GRID_SPACING
        positions[comp["id"]] = (float(x), float(y))
    return positions


def _setup_waveform_params(component, value_str):
    """Set up waveform parameters on a Waveform Source component."""
    upper = value_str.upper().strip()

    if upper.startswith("SIN"):
        component.waveform_type = "SIN"
        params = _extract_paren_params(value_str)
        if len(params) >= 3:
            sin_params = {
                "offset": params[0] if len(params) > 0 else "0",
                "amplitude": params[1] if len(params) > 1 else "5",
                "frequency": params[2] if len(params) > 2 else "1k",
                "delay": params[3] if len(params) > 3 else "0",
                "theta": params[4] if len(params) > 4 else "0",
                "phase": params[5] if len(params) > 5 else "0",
            }
            component.waveform_params = {"SIN": sin_params}
    elif upper.startswith("PULSE"):
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
    elif upper.startswith("EXP"):
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
    """Extract whitespace-separated parameters from inside parentheses.

    E.g. 'SIN(0 5 1k)' -> ['0', '5', '1k']
    """
    match = re.search(r"\(([^)]*)\)", text)
    if match:
        return match.group(1).split()
    return []
