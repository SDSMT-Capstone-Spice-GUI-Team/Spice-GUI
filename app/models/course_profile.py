"""
CourseProfile - Data model for adaptive GUI course profiles.

Defines which components, analyses, and UI panels are available
for a given course or usage context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class CourseProfile:
    """Immutable profile that controls GUI feature visibility per course."""

    id: str
    name: str
    description: str
    allowed_components: List[str] = field(default_factory=list)
    allowed_analyses: List[str] = field(default_factory=list)
    show_advanced_panels: bool = False


# ── Built-in profiles ──────────────────────────────────────────────

BUILTIN_PROFILES: Dict[str, CourseProfile] = {}


def _register(profile: CourseProfile) -> CourseProfile:
    BUILTIN_PROFILES[profile.id] = profile
    return profile


_register(
    CourseProfile(
        id="ee120",
        name="EE 120 – Intro to Circuits",
        description="DC-only basics: resistors, sources, and ground.",
        allowed_components=[
            "Resistor",
            "Voltage Source",
            "Current Source",
            "Ground",
        ],
        allowed_analyses=["op"],
        show_advanced_panels=False,
    )
)

_register(
    CourseProfile(
        id="circuits1",
        name="Circuits I",
        description="RLC fundamentals with DC and AC analysis.",
        allowed_components=[
            "Resistor",
            "Capacitor",
            "Inductor",
            "Voltage Source",
            "Current Source",
            "Ground",
        ],
        allowed_analyses=["op", "ac", "tran"],
        show_advanced_panels=False,
    )
)

_register(
    CourseProfile(
        id="circuits2",
        name="Circuits II",
        description="Advanced analysis including op-amps and dependent sources.",
        allowed_components=[
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
        ],
        allowed_analyses=["op", "ac", "tran", "dc"],
        show_advanced_panels=True,
    )
)

_register(
    CourseProfile(
        id="me301",
        name="ME 301 – System Dynamics",
        description="Passive components and transient analysis for mechanical engineers.",
        allowed_components=[
            "Resistor",
            "Capacitor",
            "Inductor",
            "Voltage Source",
            "Current Source",
            "Ground",
        ],
        allowed_analyses=["op", "tran"],
        show_advanced_panels=False,
    )
)

_register(
    CourseProfile(
        id="full",
        name="Full Access",
        description="Unrestricted access to all components and analyses.",
        allowed_components=[
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
            "Transformer",
        ],
        allowed_analyses=["op", "ac", "tran", "dc"],
        show_advanced_panels=True,
    )
)
