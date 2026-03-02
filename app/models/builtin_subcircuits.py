"""Built-in subcircuit definitions for common voltage regulators.

Provides 7805, LM317, and LM7812 as built-in subcircuit components that are
automatically registered into the component system on first import.

Each has 3 terminals: IN, OUT, GND — matching real-world IC pinouts.
"""

from models.subcircuit_library import SubcircuitDefinition, register_subcircuit_component

# ---------------------------------------------------------------------------
# SPICE subcircuit definitions
# ---------------------------------------------------------------------------

_7805_SUBCKT = """\
.subckt 7805 IN OUT GND
* 7805 Fixed +5V voltage regulator (behavioral model)
* Pins: IN=input, OUT=output (+5V), GND=ground
Rin IN GND 1e6
E_reg int_out GND IN GND 1
R_limit int_out OUT 0.1
V_ref ref GND 5.0
B_clamp OUT GND V=min(V(int_out, GND), V(ref))
R_out OUT GND 1e6
.ends"""

_LM317_SUBCKT = """\
.subckt LM317 IN OUT ADJ
* LM317 Adjustable positive voltage regulator (behavioral model)
* Pins: IN=input, OUT=output, ADJ=adjust
* Vout = 1.25 * (1 + R2/R1) where R1 is between OUT and ADJ
* This model provides a 1.25V reference between OUT and ADJ
Rin IN ADJ 1e6
V_ref OUT ADJ 1.25
R_in IN int1 0.1
E_buf int1 ADJ OUT ADJ 1
R_out OUT ADJ 1e6
.ends"""

_LM7812_SUBCKT = """\
.subckt LM7812 IN OUT GND
* LM7812 Fixed +12V voltage regulator (behavioral model)
* Pins: IN=input, OUT=output (+12V), GND=ground
Rin IN GND 1e6
E_reg int_out GND IN GND 1
R_limit int_out OUT 0.1
V_ref ref GND 12.0
B_clamp OUT GND V=min(V(int_out, GND), V(ref))
R_out OUT GND 1e6
.ends"""

# ---------------------------------------------------------------------------
# Built-in definitions
# ---------------------------------------------------------------------------

BUILTIN_SUBCIRCUITS: list[SubcircuitDefinition] = [
    SubcircuitDefinition(
        name="7805",
        terminals=["IN", "OUT", "GND"],
        spice_definition=_7805_SUBCKT,
        description="Fixed +5V voltage regulator",
        builtin=True,
    ),
    SubcircuitDefinition(
        name="LM317",
        terminals=["IN", "OUT", "ADJ"],
        spice_definition=_LM317_SUBCKT,
        description="Adjustable positive voltage regulator (1.25V ref)",
        builtin=True,
    ),
    SubcircuitDefinition(
        name="LM7812",
        terminals=["IN", "OUT", "GND"],
        spice_definition=_LM7812_SUBCKT,
        description="Fixed +12V voltage regulator",
        builtin=True,
    ),
]


def register_builtin_subcircuits() -> None:
    """Register all built-in subcircuit components into the component system.

    Safe to call multiple times — already-registered components are skipped.
    """
    for defn in BUILTIN_SUBCIRCUITS:
        register_subcircuit_component(defn)


def load_builtin_subcircuits_into_library(library) -> None:
    """Add built-in subcircuits to a SubcircuitLibrary instance.

    Built-in definitions are marked ``builtin=True`` so they cannot be
    deleted by users.
    """
    for defn in BUILTIN_SUBCIRCUITS:
        library.add(defn, persist=True)
