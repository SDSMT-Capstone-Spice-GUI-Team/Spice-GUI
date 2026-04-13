"""
simulation/spice_sanitizer.py

Input sanitization for SPICE netlist generation.

Prevents injection of dangerous ngspice directives (.system, .shell, etc.)
and validates file paths against traversal attacks.
"""

import re

# ngspice directives that can execute arbitrary shell commands
_DANGEROUS_DIRECTIVES = re.compile(
    r"^\s*\.\s*(system|shell)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Valid SPICE value: optional sign, digits/decimal, optional SI suffix and unit,
# or a known model/subcircuit name (alphanumeric with underscores).
# Examples: "1k", "4.7u", "10MEG", "+3.3V", "2N3904", "SINE(0 1 1k)"
_SPICE_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_.+\-*/() ,=]+$")

# Disallowed patterns within values — newlines and directive injections
_VALUE_INJECTION_PATTERN = re.compile(
    r"[\n\r]|\.\s*(system|shell|include|lib)\b",
    re.IGNORECASE,
)


def sanitize_spice_value(value: str) -> str:
    """Sanitize a user-supplied SPICE component value.

    Strips leading/trailing whitespace and rejects values containing
    dangerous ngspice directives or newlines that could inject extra
    netlist lines.

    Args:
        value: Raw user-supplied component value string.

    Returns:
        The sanitized value string.

    Raises:
        ValueError: If the value contains dangerous content.
    """
    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if not value:
        raise ValueError("Component value must not be empty")

    if _VALUE_INJECTION_PATTERN.search(value):
        raise ValueError(f"Component value contains dangerous directive: {value!r}")

    if not _SPICE_VALUE_PATTERN.match(value):
        raise ValueError(f"Component value contains invalid characters: {value!r}")

    return value


def sanitize_spice_identifier(name: str) -> str:
    """Sanitize a SPICE identifier (component name, source name, node label).

    Args:
        name: Raw identifier string.

    Returns:
        The sanitized identifier.

    Raises:
        ValueError: If the identifier contains dangerous content.
    """
    if not isinstance(name, str):
        name = str(name)

    name = name.strip()

    if not name:
        raise ValueError("SPICE identifier must not be empty")

    # Identifiers must be alphanumeric with underscores
    if not re.match(r"^[A-Za-z0-9_]+$", name):
        raise ValueError(f"SPICE identifier contains invalid characters: {name!r}")

    return name


def sanitize_netlist_text(text: str) -> str:
    """Remove dangerous directives from a block of netlist text.

    This is a defence-in-depth measure applied to the final netlist
    before writing it to disk, catching any directives that slipped
    through value-level sanitization.

    Args:
        text: Complete or partial netlist text.

    Returns:
        Text with dangerous directives commented out.
    """

    def _comment_out(match):
        return f"* SANITIZED: {match.group(0)}"

    return _DANGEROUS_DIRECTIVES.sub(_comment_out, text)


def validate_wrdata_filepath(filepath: str) -> str:
    """Validate the wrdata output file path.

    Rejects path traversal sequences and absolute paths (the wrdata path
    should be relative to the simulation output directory).

    Args:
        filepath: The wrdata file path to validate.

    Returns:
        The validated filepath.

    Raises:
        ValueError: If the path contains traversal sequences or is absolute.
    """
    if not isinstance(filepath, str):
        filepath = str(filepath)

    filepath = filepath.strip()

    if not filepath:
        raise ValueError("wrdata filepath must not be empty")

    # Reject path traversal
    # Normalize to forward slashes for consistent checking
    normalized = filepath.replace("\\", "/")
    if ".." in normalized.split("/"):
        raise ValueError(f"wrdata filepath contains path traversal: {filepath!r}")

    # Reject newlines that could inject control commands
    if "\n" in filepath or "\r" in filepath:
        raise ValueError(f"wrdata filepath contains newline characters: {filepath!r}")

    return filepath


def validate_output_dir(output_dir: str) -> str:
    """Validate the simulation output directory path.

    Rejects path traversal sequences that could write files outside the
    intended directory.

    Args:
        output_dir: The output directory path to validate.

    Returns:
        The validated directory path.

    Raises:
        ValueError: If the path contains traversal sequences.
    """
    if not isinstance(output_dir, str):
        output_dir = str(output_dir)

    output_dir = output_dir.strip()

    if not output_dir:
        raise ValueError("Output directory must not be empty")

    # Reject path traversal
    normalized = output_dir.replace("\\", "/")
    if ".." in normalized.split("/"):
        raise ValueError(f"Output directory contains path traversal: {output_dir!r}")

    return output_dir
