"""
ComponentData - Pure Python data model for circuit components.

This module contains no Qt dependencies. All positions are represented as
tuples (x, y) rather than QPointF.

Component types use display names as canonical identifiers:
'Resistor', 'Capacitor', 'Inductor', 'Voltage Source', 'Current Source',
'Waveform Source', 'Ground', 'Op-Amp'
"""

import math
from dataclasses import dataclass, field
from typing import Optional

# Component type definitions using display names (canonical)
COMPONENT_TYPES = [
    "Resistor",
    "Capacitor",
    "Inductor",
    "Voltage Source",
    "Current Source",
    "Waveform Source",
    "Ground",
    "Op-Amp",
    "VCVS",
    "CCVS",
    "VCCS",
    "CCCS",
    "BJT NPN",
    "BJT PNP",
    "MOSFET NMOS",
    "MOSFET PMOS",
    "VC Switch",
    "Diode",
    "LED",
    "Zener Diode",
    "Subcircuit",
]

# Mapping of component types to SPICE symbols
SPICE_SYMBOLS = {
    "Resistor": "R",
    "Capacitor": "C",
    "Inductor": "L",
    "Voltage Source": "V",
    "Current Source": "I",
    "Waveform Source": "VW",
    "Ground": "GND",
    "Op-Amp": "OA",
    "VCVS": "E",
    "CCVS": "H",
    "VCCS": "G",
    "CCCS": "F",
    "BJT NPN": "Q",
    "BJT PNP": "Q",
    "MOSFET NMOS": "M",
    "MOSFET PMOS": "M",
    "VC Switch": "S",
    "Diode": "D",
    "LED": "D",
    "Zener Diode": "D",
    "Subcircuit": "X",
}

# Number of terminals per component type (default is 2)
TERMINAL_COUNTS = {
    "Ground": 1,
    "Op-Amp": 3,
    "VCVS": 4,
    "CCVS": 4,
    "VCCS": 4,
    "CCCS": 4,
    "BJT NPN": 3,
    "BJT PNP": 3,
    "MOSFET NMOS": 3,
    "MOSFET PMOS": 3,
    "VC Switch": 4,
}

# Default values per component type
DEFAULT_VALUES = {
    "Resistor": "1k",
    "Capacitor": "1u",
    "Inductor": "1m",
    "Voltage Source": "5V",
    "Current Source": "1A",
    "Waveform Source": "SIN(0 5 1k)",
    "Ground": "0V",
    "Op-Amp": "Ideal",
    "VCVS": "1",
    "CCVS": "1k",
    "VCCS": "1m",
    "CCCS": "1",
    "BJT NPN": "2N3904",
    "BJT PNP": "2N3906",
    "MOSFET NMOS": "NMOS1",
    "MOSFET PMOS": "PMOS1",
    "VC Switch": "VT=2.5 RON=1 ROFF=1e6",
    "Diode": "IS=1e-14 N=1",
    "LED": "IS=1e-20 N=1.8 EG=1.9",
    "Zener Diode": "IS=1e-14 N=1 BV=5.1 IBV=1e-3",
    "Subcircuit": "",
}

# Available op-amp models (value field choices)
OPAMP_MODELS = ["Ideal", "LM741", "TL081", "LM358"]

# SPICE subcircuit definitions for each op-amp model.
# Keys match OPAMP_MODELS entries; "Ideal" is the built-in high-gain model.
OPAMP_SUBCIRCUITS = {
    "Ideal": (".subckt OPAMP_IDEAL inp inn out\nE_amp out 0 inp inn 1e6\nR_out out 0 1e-3\n.ends"),
    "LM741": (
        ".subckt LM741 inp inn out\n"
        "* Simplified LM741 behavioral model\n"
        "* GBW ~1 MHz, DC gain ~200k, Rout ~75 ohm\n"
        "Rin inp inn 2e6\n"
        "E1 int1 0 inp inn 2e5\n"
        "R1 int1 int2 1e6\n"
        "C1 int2 0 159e-12\n"
        "E2 int3 0 int2 0 1\n"
        "Rout int3 out 75\n"
        ".ends"
    ),
    "TL081": (
        ".subckt TL081 inp inn out\n"
        "* Simplified TL081 JFET-input behavioral model\n"
        "* GBW ~4 MHz, DC gain ~200k, Rout ~50 ohm\n"
        "Rin inp inn 1e12\n"
        "E1 int1 0 inp inn 2e5\n"
        "R1 int1 int2 1e6\n"
        "C1 int2 0 39.8e-12\n"
        "E2 int3 0 int2 0 1\n"
        "Rout int3 out 50\n"
        ".ends"
    ),
    "LM358": (
        ".subckt LM358 inp inn out\n"
        "* Simplified LM358 behavioral model\n"
        "* GBW ~1 MHz, DC gain ~100k, Rout ~50 ohm\n"
        "Rin inp inn 2e6\n"
        "E1 int1 0 inp inn 1e5\n"
        "R1 int1 int2 1e6\n"
        "C1 int2 0 159e-12\n"
        "E2 int3 0 int2 0 1\n"
        "Rout int3 out 50\n"
        ".ends"
    ),
}

# Component colors (hex strings)
COMPONENT_COLORS = {
    "Resistor": "#2196F3",
    "Capacitor": "#4CAF50",
    "Inductor": "#FF9800",
    "Voltage Source": "#F44336",
    "Current Source": "#9C27B0",
    "Waveform Source": "#E91E63",
    "Ground": "#000000",
    "Op-Amp": "#FFC107",
    "VCVS": "#00897B",
    "CCVS": "#00ACC1",
    "VCCS": "#26A69A",
    "CCCS": "#0097A7",
    "BJT NPN": "#FF6B6B",
    "BJT PNP": "#4ECDC4",
    "MOSFET NMOS": "#7B1FA2",
    "MOSFET PMOS": "#512DA8",
    "VC Switch": "#795548",
    "Diode": "#607D8B",
    "LED": "#FFEB3B",
    "Zener Diode": "#8D6E63",
    "Subcircuit": "#78909C",
}

# Terminal geometry configuration per component type
# Format: (body_extent_x, terminal_padding, base_terminals)
# base_terminals is None for standard 2-terminal horizontal layout,
# or a list of (x, y) tuples for custom terminal positions
TERMINAL_GEOMETRY = {
    "Resistor": (15, 15, None),
    "Capacitor": (5, 25, None),
    "Inductor": (20, 10, None),
    "Voltage Source": (15, 15, None),
    "Current Source": (15, 15, None),
    "Waveform Source": (15, 15, None),
    "Ground": (15, 0, [(0, -10)]),
    "Op-Amp": (20, 10, [(-30, -10), (-30, 10), (30, 0)]),
    "VCVS": (20, 10, [(-30, -10), (-30, 10), (30, -10), (30, 10)]),
    "CCVS": (20, 10, [(-30, -10), (-30, 10), (30, -10), (30, 10)]),
    "VCCS": (20, 10, [(-30, -10), (-30, 10), (30, -10), (30, 10)]),
    "CCCS": (20, 10, [(-30, -10), (-30, 10), (30, -10), (30, 10)]),
    "BJT NPN": (20, 10, [(20, -20), (-20, 0), (20, 20)]),  # Collector, Base, Emitter
    "BJT PNP": (20, 10, [(20, -20), (-20, 0), (20, 20)]),  # Collector, Base, Emitter
    "MOSFET NMOS": (20, 10, [(20, -20), (-20, 0), (20, 20)]),
    "MOSFET PMOS": (20, 10, [(20, -20), (-20, 0), (20, 20)]),
    "VC Switch": (20, 10, [(-30, -10), (-30, 10), (30, -10), (30, 10)]),
    "Diode": (10, 20, None),
    "LED": (10, 20, None),
    "Zener Diode": (10, 20, None),
}

# Mapping from serialized class names to canonical display names
# Used for backwards compatibility when loading saved circuits
_CLASS_TO_DISPLAY = {
    "VoltageSource": "Voltage Source",
    "CurrentSource": "Current Source",
    "WaveformVoltageSource": "Waveform Source",
    "OpAmp": "Op-Amp",
    "VoltageControlledVoltageSource": "VCVS",
    "CurrentControlledVoltageSource": "CCVS",
    "VoltageControlledCurrentSource": "VCCS",
    "CurrentControlledCurrentSource": "CCCS",
    "BJTNPN": "BJT NPN",
    "BJTPNP": "BJT PNP",
    "MOSFETNMOS": "MOSFET NMOS",
    "MOSFETPMOS": "MOSFET PMOS",
    "VCSwitch": "VC Switch",
    "ZenerDiode": "Zener Diode",
    "Subcircuit": "Subcircuit",
}

# Mapping from display names to Python class names (for serialization)
_DISPLAY_TO_CLASS = {
    "Voltage Source": "VoltageSource",
    "Current Source": "CurrentSource",
    "Waveform Source": "WaveformVoltageSource",
    "Op-Amp": "OpAmp",
    "VCVS": "VoltageControlledVoltageSource",
    "CCVS": "CurrentControlledVoltageSource",
    "VCCS": "VoltageControlledCurrentSource",
    "CCCS": "CurrentControlledCurrentSource",
    "BJT NPN": "BJTNPN",
    "BJT PNP": "BJTPNP",
    "MOSFET NMOS": "MOSFETNMOS",
    "MOSFET PMOS": "MOSFETPMOS",
    "VC Switch": "VCSwitch",
    "Zener Diode": "ZenerDiode",
}


@dataclass
class ComponentData:
    """
    Pure Python data class representing a circuit component.

    This class stores all component data without any Qt dependencies.
    Positions are stored as (x, y) tuples.
    """

    component_id: str
    component_type: str
    value: str
    position: tuple[float, float]  # (x, y) in scene coordinates
    rotation: int = 0  # degrees: 0, 90, 180, 270
    flip_h: bool = False  # horizontal mirror (negate x before rotation)
    flip_v: bool = False  # vertical mirror (negate y before rotation)

    # Waveform source parameters (only used for Waveform Source)
    waveform_type: Optional[str] = None
    waveform_params: Optional[dict] = field(default_factory=lambda: None)

    # Subcircuit parameters (only used for Subcircuit type)
    subcircuit_name: Optional[str] = None
    subcircuit_pins: Optional[list[str]] = None
    subcircuit_definition: Optional[str] = None

    def __post_init__(self):
        """Initialize waveform parameters for waveform sources."""
        if self.component_type == "Waveform Source" and self.waveform_params is None:
            self.waveform_type = "SIN"
            self.waveform_params = self._default_waveform_params()

    @staticmethod
    def _default_waveform_params() -> dict:
        """Return default waveform parameters for all waveform types."""
        return {
            "SIN": {
                "offset": "0",
                "amplitude": "5",
                "frequency": "1k",
                "delay": "0",
                "theta": "0",
                "phase": "0",
            },
            "PULSE": {
                "v1": "0",
                "v2": "5",
                "td": "0",
                "tr": "1n",
                "tf": "1n",
                "pw": "500u",
                "per": "1m",
            },
            "EXP": {
                "v1": "0",
                "v2": "5",
                "td1": "0",
                "tau1": "1u",
                "td2": "2u",
                "tau2": "2u",
            },
        }

    def get_terminal_count(self) -> int:
        """Return number of terminals for this component type."""
        if self.component_type == "Subcircuit" and self.subcircuit_pins:
            return len(self.subcircuit_pins)
        return TERMINAL_COUNTS.get(self.component_type, 2)

    def get_base_terminal_positions(self) -> list[tuple[float, float]]:
        """
        Return base terminal positions in local coordinates (before rotation).

        Returns:
            List of (x, y) tuples representing terminal positions relative to component center.
        """
        if self.component_type == "Subcircuit" and self.subcircuit_pins:
            return _subcircuit_terminal_positions(len(self.subcircuit_pins))

        geom = TERMINAL_GEOMETRY.get(self.component_type)
        if geom is None:
            # Default: 2 terminals at +/-30 on x-axis
            return [(-30.0, 0.0), (30.0, 0.0)]

        body_extent_x, terminal_padding, base_terminals = geom

        if base_terminals is not None:
            # Custom terminal positions
            return [(float(x), float(y)) for x, y in base_terminals]
        else:
            # Standard 2-terminal horizontal layout
            terminal_x = body_extent_x + terminal_padding
            return [(-terminal_x, 0.0), (terminal_x, 0.0)]

    def get_terminal_positions(self) -> list[tuple[float, float]]:
        """
        Return terminal positions in world coordinates (after flip, rotation, and translation).

        Returns:
            List of (x, y) tuples representing terminal positions in scene coordinates.
        """
        base_terminals = self.get_base_terminal_positions()

        # Apply flip before rotation
        rad = math.radians(self.rotation)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        rotated = []
        for tx, ty in base_terminals:
            if self.flip_h:
                tx = -tx
            if self.flip_v:
                ty = -ty
            new_x = tx * cos_a - ty * sin_a
            new_y = tx * sin_a + ty * cos_a
            world_x = self.position[0] + new_x
            world_y = self.position[1] + new_y
            rotated.append((world_x, world_y))

        return rotated

    def get_spice_symbol(self) -> str:
        """Return the SPICE symbol for this component type."""
        return SPICE_SYMBOLS.get(self.component_type, "X")

    def get_spice_value(self) -> str:
        """
        Return the SPICE value string for this component.

        For waveform sources, generates the full waveform specification.
        For other components, returns the value as-is.
        """
        if self.component_type != "Waveform Source" or self.waveform_params is None:
            return self.value

        wtype = self.waveform_type or "SIN"
        params = self.waveform_params.get(wtype, {})

        if wtype == "SIN":
            return (
                f"SIN({params.get('offset', '0')} {params.get('amplitude', '5')} "
                f"{params.get('frequency', '1k')} {params.get('delay', '0')} "
                f"{params.get('theta', '0')} {params.get('phase', '0')})"
            )
        elif wtype == "PULSE":
            return (
                f"PULSE({params.get('v1', '0')} {params.get('v2', '5')} "
                f"{params.get('td', '0')} {params.get('tr', '1n')} "
                f"{params.get('tf', '1n')} {params.get('pw', '500u')} "
                f"{params.get('per', '1m')})"
            )
        elif wtype == "EXP":
            return (
                f"EXP({params.get('v1', '0')} {params.get('v2', '5')} "
                f"{params.get('td1', '0')} {params.get('tau1', '1u')} "
                f"{params.get('td2', '2u')} {params.get('tau2', '2u')})"
            )
        else:
            return self.value

    def to_dict(self) -> dict:
        """
        Serialize component to dictionary.

        Uses Python class names for the 'type' field to maintain backwards
        compatibility with existing saved circuit files.
        """
        # Use class name for serialization (backwards compatible)
        class_name = _DISPLAY_TO_CLASS.get(self.component_type, self.component_type)

        data = {
            "type": class_name,
            "id": self.component_id,
            "value": self.value,
            "pos": {"x": self.position[0], "y": self.position[1]},
            "rotation": self.rotation,
            "flip_h": self.flip_h,
            "flip_v": self.flip_v,
        }

        # Add waveform parameters for waveform sources
        if self.component_type == "Waveform Source":
            data["waveform_type"] = self.waveform_type
            data["waveform_params"] = self.waveform_params

        # Add subcircuit parameters
        if self.component_type == "Subcircuit":
            if self.subcircuit_name:
                data["subcircuit_name"] = self.subcircuit_name
            if self.subcircuit_pins:
                data["subcircuit_pins"] = list(self.subcircuit_pins)
            if self.subcircuit_definition:
                data["subcircuit_definition"] = self.subcircuit_definition

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ComponentData":
        """
        Deserialize component from dictionary.

        Handles both old-style class names (VoltageSource, OpAmp) and
        display names (Voltage Source, Op-Amp) in the 'type' field.
        """
        raw_type = data["type"]
        # Normalize to display name
        component_type = _CLASS_TO_DISPLAY.get(raw_type, raw_type)

        component = cls(
            component_id=data["id"],
            component_type=component_type,
            value=data["value"],
            position=(data["pos"]["x"], data["pos"]["y"]),
            rotation=data.get("rotation", 0),
            flip_h=data.get("flip_h", False),
            flip_v=data.get("flip_v", False),
        )

        # Load waveform parameters if present
        if "waveform_type" in data:
            component.waveform_type = data["waveform_type"]
        if "waveform_params" in data:
            component.waveform_params = data["waveform_params"]

        # Load subcircuit parameters if present
        if "subcircuit_name" in data:
            component.subcircuit_name = data["subcircuit_name"]
        if "subcircuit_pins" in data:
            component.subcircuit_pins = list(data["subcircuit_pins"])
        if "subcircuit_definition" in data:
            component.subcircuit_definition = data["subcircuit_definition"]

        return component

    def __repr__(self) -> str:
        return (
            f"ComponentData(id={self.component_id!r}, type={self.component_type!r}, "
            f"value={self.value!r}, pos={self.position}, rot={self.rotation})"
        )


def _subcircuit_terminal_positions(pin_count: int) -> list[tuple[float, float]]:
    """Calculate terminal positions for a subcircuit block.

    Distributes pins along left and right sides of a rectangle.
    First half of pins on the left, second half on the right.
    """
    if pin_count <= 0:
        return [(-50.0, 0.0), (50.0, 0.0)]

    left_count = (pin_count + 1) // 2
    right_count = pin_count - left_count
    pin_spacing = 20.0
    body_x = 50.0

    positions = []

    # Left-side pins
    left_height = (left_count - 1) * pin_spacing
    for i in range(left_count):
        y = -left_height / 2.0 + i * pin_spacing
        positions.append((-body_x, y))

    # Right-side pins
    right_height = (right_count - 1) * pin_spacing if right_count > 0 else 0
    for i in range(right_count):
        y = -right_height / 2.0 + i * pin_spacing
        positions.append((body_x, y))

    return positions


def subcircuit_body_rect(pin_count: int) -> tuple[float, float, float, float]:
    """Return (x, y, width, height) of the subcircuit rectangular body."""
    left_count = (pin_count + 1) // 2
    right_count = pin_count - left_count
    max_side = max(left_count, right_count, 1)
    pin_spacing = 20.0
    body_half_w = 40.0
    body_half_h = max(max_side * pin_spacing / 2.0 + 5.0, 15.0)
    return (-body_half_w, -body_half_h, body_half_w * 2, body_half_h * 2)


def parse_subckt(text: str) -> dict:
    """Parse a .subckt definition from text.

    Accepts either the full .subckt block or a file containing one.

    Returns:
        dict with keys: name (str), pins (list[str]), definition (str)

    Raises:
        ValueError: If no valid .subckt block is found.
    """
    lines = text.strip().split("\n")
    subckt_name = None
    subckt_pins = []
    block_lines = []
    in_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(".subckt"):
            tokens = stripped.split()
            if len(tokens) < 2:
                raise ValueError("Invalid .subckt line: missing subcircuit name.")
            subckt_name = tokens[1]
            subckt_pins = tokens[2:]
            in_block = True
            block_lines.append(stripped)
        elif stripped.lower().startswith(".ends"):
            block_lines.append(stripped)
            in_block = False
            break
        elif in_block:
            block_lines.append(stripped)

    if subckt_name is None:
        raise ValueError("No .subckt definition found in text.")

    definition = "\n".join(block_lines)
    return {"name": subckt_name, "pins": subckt_pins, "definition": definition}
