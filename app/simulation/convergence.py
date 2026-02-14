"""
simulation/convergence.py

Classifies ngspice simulation errors and provides retry strategies
with relaxed tolerances for convergence failures.
"""

import re
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """Categories of ngspice simulation failures."""

    DC_CONVERGENCE = "dc_convergence"
    TIMESTEP_TOO_SMALL = "timestep_too_small"
    SINGULAR_MATRIX = "singular_matrix"
    SOURCE_STEPPING_FAILED = "source_stepping_failed"
    UNKNOWN = "unknown"


# Patterns matched against combined stdout+stderr (case-insensitive)
_ERROR_PATTERNS: list[tuple[re.Pattern, ErrorCategory]] = [
    (re.compile(r"singular matrix", re.IGNORECASE), ErrorCategory.SINGULAR_MATRIX),
    (
        re.compile(r"no convergence in dc operating point", re.IGNORECASE),
        ErrorCategory.DC_CONVERGENCE,
    ),
    (
        re.compile(r"doAnalyses:.*timestep too small", re.IGNORECASE),
        ErrorCategory.TIMESTEP_TOO_SMALL,
    ),
    (
        re.compile(r"source stepping failed", re.IGNORECASE),
        ErrorCategory.SOURCE_STEPPING_FAILED,
    ),
    (
        re.compile(r"no convergence", re.IGNORECASE),
        ErrorCategory.DC_CONVERGENCE,
    ),
]


@dataclass
class ErrorDiagnosis:
    """Structured diagnosis of a simulation failure."""

    category: ErrorCategory
    message: str
    causes: list[str]
    suggestions: list[str]


_DIAGNOSES: dict[ErrorCategory, ErrorDiagnosis] = {
    ErrorCategory.DC_CONVERGENCE: ErrorDiagnosis(
        category=ErrorCategory.DC_CONVERGENCE,
        message=(
            "The simulator could not find a stable DC operating point for your circuit."
        ),
        causes=[
            "A node is not connected to ground (floating node)",
            "Component values are unrealistic (e.g. 0 ohm resistor, extremely large gain)",
            "Positive feedback loop without a stable bias point",
        ],
        suggestions=[
            "Check that every node has a DC path to ground",
            "Add a large resistor (e.g. 1G) from floating nodes to ground",
            "Verify component values are within realistic ranges",
        ],
    ),
    ErrorCategory.TIMESTEP_TOO_SMALL: ErrorDiagnosis(
        category=ErrorCategory.TIMESTEP_TOO_SMALL,
        message=(
            "The transient simulation could not advance in time — the required timestep became too small."
        ),
        causes=[
            "Very fast switching edges combined with large time constants",
            "Numerical oscillation in a feedback loop",
            "Unrealistic component values causing stiff equations",
        ],
        suggestions=[
            "Increase the simulation time step in the analysis settings",
            "Reduce the simulation duration or avoid very fast signal edges",
            "Check for unrealistic component values (very small capacitors with very large resistors)",
        ],
    ),
    ErrorCategory.SINGULAR_MATRIX: ErrorDiagnosis(
        category=ErrorCategory.SINGULAR_MATRIX,
        message="The circuit equations could not be solved — the matrix is singular.",
        causes=[
            "Two voltage sources are connected in parallel",
            "A loop of voltage sources and/or inductors with no resistance",
            "A node is completely disconnected from the rest of the circuit",
        ],
        suggestions=[
            "Ensure no two voltage sources are directly in parallel",
            "Add a small series resistor (e.g. 1m ohm) to inductor or voltage-source loops",
            "Check for disconnected nodes or components",
        ],
    ),
    ErrorCategory.SOURCE_STEPPING_FAILED: ErrorDiagnosis(
        category=ErrorCategory.SOURCE_STEPPING_FAILED,
        message=(
            "The simulator tried ramping sources gradually but still could not converge."
        ),
        causes=[
            "Circuit has a very sensitive operating point",
            "Non-linear devices (diodes, transistors) with difficult bias conditions",
        ],
        suggestions=[
            "Simplify the circuit and add components back one at a time",
            "Check transistor bias conditions — ensure they are in the expected region",
            "Try different initial conditions or component values",
        ],
    ),
    ErrorCategory.UNKNOWN: ErrorDiagnosis(
        category=ErrorCategory.UNKNOWN,
        message="The simulation failed for an unexpected reason.",
        causes=[],
        suggestions=[
            "Check the netlist for syntax errors",
            "Verify all components are connected properly",
            "Try a simpler circuit to isolate the problem",
        ],
    ),
}

# Convergence-related categories that benefit from relaxed tolerances
_RETRIABLE_CATEGORIES = {
    ErrorCategory.DC_CONVERGENCE,
    ErrorCategory.TIMESTEP_TOO_SMALL,
    ErrorCategory.SOURCE_STEPPING_FAILED,
}

# Relaxed SPICE options for retry attempts
RELAXED_OPTIONS = {
    "reltol": "0.01",
    "abstol": "1e-10",
    "vntol": "1e-4",
    "itl1": "500",
    "itl4": "200",
}


def classify_error(stderr: str, stdout: str = "") -> ErrorCategory:
    """Classify an ngspice error from its stderr/stdout output.

    Checks stderr first, then stdout, returning the first matching category.
    """
    for text in (stderr, stdout):
        if not text:
            continue
        for pattern, category in _ERROR_PATTERNS:
            if pattern.search(text):
                return category
    return ErrorCategory.UNKNOWN


def diagnose_error(stderr: str, stdout: str = "") -> ErrorDiagnosis:
    """Classify and return a full diagnosis for a simulation failure."""
    category = classify_error(stderr, stdout)
    return _DIAGNOSES[category]


def is_retriable(category: ErrorCategory) -> bool:
    """Return True if this error category may benefit from relaxed tolerances."""
    return category in _RETRIABLE_CATEGORIES


def format_options_lines(options: dict[str, str] | None = None) -> list[str]:
    """Format a dict of SPICE options as netlist lines.

    Returns a list like [".options reltol=0.01 abstol=1e-10 ..."].
    If *options* is None, uses the default RELAXED_OPTIONS.
    If *options* is an empty dict, returns [].
    """
    if options is None:
        options = RELAXED_OPTIONS
    if not options:
        return []
    pairs = " ".join(f"{k}={v}" for k, v in options.items())
    return [f".options {pairs}"]


def format_user_message(diagnosis: ErrorDiagnosis, relaxed: bool = False) -> str:
    """Build a student-friendly error message string.

    If *relaxed* is True, prepend a note that relaxed tolerances were used.
    """
    parts = [diagnosis.message]

    if diagnosis.causes:
        parts.append("\nCommon causes:")
        for cause in diagnosis.causes:
            parts.append(f"  - {cause}")

    if diagnosis.suggestions:
        parts.append("\nSuggestions:")
        for suggestion in diagnosis.suggestions:
            parts.append(f"  - {suggestion}")

    if relaxed:
        parts.insert(
            0,
            "Simulation converged with relaxed tolerances (results may be less accurate).\n",
        )

    return "\n".join(parts)
