"""
simulation/svg_shareable.py

Embed and extract Spice-GUI circuit JSON in SVG files for shareable
round-trip export/import.  Circuit data is stored inside an SVG
``<metadata>`` block using a dedicated XML namespace so it does not
interfere with standard SVG rendering.

No Qt dependencies.
"""

import base64
import binascii
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_NS = "https://spice-gui.github.io/schema/circuit"
_TAG_PREFIX = "spice-gui"
_MARKER = f"<!-- {_TAG_PREFIX}-circuit-data: "
_MARKER_END = " -->"


def embed_circuit_data(svg_path, model):
    """Post-process an SVG file to embed circuit JSON data.

    Inserts a ``<metadata>`` block containing the circuit model
    serialised as base64-encoded JSON.  If the SVG already has a
    ``<metadata>`` section it is left intact and the circuit block is
    appended.

    Args:
        svg_path: Path to the SVG file (modified in place).
        model: CircuitModel instance whose ``to_dict()`` output will
            be embedded.
    """
    svg_path = Path(svg_path)
    svg_text = svg_path.read_text(encoding="utf-8")

    circuit_dict = model.to_dict()
    json_bytes = json.dumps(circuit_dict, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(json_bytes).decode("ascii")

    # Build the metadata snippet to inject
    metadata_block = (
        f'<metadata xmlns:{_TAG_PREFIX}="{_NS}"><{_TAG_PREFIX}:circuit>{b64}</{_TAG_PREFIX}:circuit></metadata>'
    )

    # Insert right after the opening <svg ...> tag
    # Use a regex to find the end of the <svg> opening tag
    match = re.search(r"(<svg[^>]*>)", svg_text, re.IGNORECASE | re.DOTALL)
    if match:
        insert_pos = match.end()
        svg_text = svg_text[:insert_pos] + "\n" + metadata_block + "\n" + svg_text[insert_pos:]
    else:
        logger.warning("Could not find <svg> tag in %s; skipping circuit data embedding", svg_path)
        return

    svg_path.write_text(svg_text, encoding="utf-8")


def extract_circuit_data(svg_path):
    """Extract embedded circuit JSON from an SVG file.

    Returns:
        dict: The circuit data dictionary (suitable for
            ``CircuitModel.from_dict()``), or ``None`` if no embedded
            data is found.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the embedded data is corrupt.
    """
    svg_path = Path(svg_path)
    svg_text = svg_path.read_text(encoding="utf-8")

    return extract_circuit_data_from_string(svg_text)


def extract_circuit_data_from_string(svg_text):
    """Extract embedded circuit JSON from SVG text content.

    Returns:
        dict or None: The circuit data dictionary, or ``None`` if no
            embedded data is found.

    Raises:
        ValueError: If the embedded data is corrupt.
    """
    # Look for the <spice-gui:circuit> element containing base64 data
    pattern = re.compile(
        rf"<{_TAG_PREFIX}:circuit[^>]*>(.*?)</{_TAG_PREFIX}:circuit>",
        re.DOTALL,
    )
    match = pattern.search(svg_text)
    if not match:
        return None

    b64_data = match.group(1).strip()
    try:
        json_bytes = base64.b64decode(b64_data)
        return json.loads(json_bytes)
    except (binascii.Error, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Corrupt circuit data in SVG: {exc}") from exc
