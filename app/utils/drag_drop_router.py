"""Route dropped files to the correct import handler based on extension.

Pure-Python module (no Qt) so the routing logic is testable without a display.
"""

# Map file extensions to the FileController method name that handles them.
EXTENSION_ROUTES = {
    ".json": "load_circuit",
    ".asc": "import_asc",
    ".cir": "import_netlist",
    ".spice": "import_netlist",
    ".sp": "import_netlist",
    ".net": "import_netlist",
}


def route_dropped_file(extension):
    """Return the handler name for *extension*, or None if unsupported.

    Args:
        extension: file extension including the dot, e.g. ".json"

    Returns:
        str | None: handler name like "load_circuit", or None
    """
    return EXTENSION_ROUTES.get(extension.lower())
