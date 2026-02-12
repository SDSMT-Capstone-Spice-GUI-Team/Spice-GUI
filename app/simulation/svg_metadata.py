"""
simulation/svg_metadata.py

Inject and extract circuit JSON metadata in SVG files.
No Qt dependencies — uses defusedxml for safe XML parsing.
"""

import json
import xml.etree.ElementTree as ET

import defusedxml.ElementTree as SafeET

SVG_NS = "http://www.w3.org/2000/svg"
METADATA_NS = "http://spice-gui.github.io/circuit"
METADATA_TAG = f"{{{METADATA_NS}}}circuit-data"


def inject_metadata(svg_path, circuit_data):
    """Inject circuit JSON into an SVG file's <metadata> element.

    Args:
        svg_path: path to the SVG file (modified in place)
        circuit_data: dict from CircuitModel.to_dict()
    """
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("spice", METADATA_NS)
    tree = SafeET.parse(svg_path)
    root = tree.getroot()

    # Find or create <metadata> element
    metadata = root.find(f"{{{SVG_NS}}}metadata")
    if metadata is None:
        metadata = ET.SubElement(root, f"{{{SVG_NS}}}metadata")
        # Insert as first child for clean ordering
        root.remove(metadata)
        root.insert(0, metadata)

    # Remove existing circuit data if present
    existing = metadata.find(METADATA_TAG)
    if existing is not None:
        metadata.remove(existing)

    # Add circuit data element
    circuit_elem = ET.SubElement(metadata, METADATA_TAG)
    circuit_elem.text = json.dumps(circuit_data)

    tree.write(svg_path, xml_declaration=True, encoding="utf-8")


def extract_metadata(svg_path):
    """Extract circuit JSON from an SVG file's <metadata> element.

    Args:
        svg_path: path to the SVG file

    Returns:
        dict: circuit data, or None if no embedded data found

    Raises:
        json.JSONDecodeError: if metadata exists but is not valid JSON
    """
    tree = SafeET.parse(svg_path)
    root = tree.getroot()

    metadata = root.find(f"{{{SVG_NS}}}metadata")
    if metadata is None:
        return None

    circuit_elem = metadata.find(METADATA_TAG)
    if circuit_elem is None or not circuit_elem.text:
        return None

    return json.loads(circuit_elem.text)


def has_metadata(svg_path):
    """Check if an SVG file contains embedded circuit data.

    Args:
        svg_path: path to the SVG file

    Returns:
        bool: True if circuit metadata is present
    """
    try:
        tree = SafeET.parse(svg_path)
        root = tree.getroot()
        metadata = root.find(f"{{{SVG_NS}}}metadata")
        if metadata is None:
            return False
        return metadata.find(METADATA_TAG) is not None
    except ET.ParseError:
        return False
