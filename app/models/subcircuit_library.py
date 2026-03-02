"""
SubcircuitLibrary - Manages external .subckt definitions for use as components.

Provides parsing, storage, persistence, and dynamic registration of subcircuit
definitions so they appear in the component palette and generate correct netlists.

No Qt dependencies -- pure Python model.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Default persistence directory
_DEFAULT_LIBRARY_DIR = Path.home() / ".spice-gui" / "library"


@dataclass
class SubcircuitDefinition:
    """A parsed .subckt definition that can be placed as a component."""

    name: str  # Subcircuit name (e.g. "7805")
    terminals: list[str]  # Ordered terminal/pin names from .subckt header
    spice_definition: str  # Full SPICE text (.subckt ... .ends)
    description: str = ""  # Human-readable description
    builtin: bool = False  # True for built-in subcircuits (not user-deletable)

    @property
    def terminal_count(self) -> int:
        return len(self.terminals)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SubcircuitDefinition":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def parse_subckt(text: str) -> list[SubcircuitDefinition]:
    """Parse one or more .subckt definitions from raw SPICE text.

    Args:
        text: Raw text that may contain one or more .subckt/.ends blocks,
              optionally with comments and other SPICE directives mixed in.

    Returns:
        List of SubcircuitDefinition objects parsed from the text.

    Raises:
        ValueError: If no valid .subckt definitions are found.
    """
    definitions: list[SubcircuitDefinition] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Match .subckt header (case-insensitive)
        match = re.match(r"\.subckt\s+(\S+)\s+(.*)", line, re.IGNORECASE)
        if match:
            name = match.group(1)
            # Terminal names are everything after the subcircuit name,
            # excluding optional params (key=value pairs)
            raw_terminals = match.group(2).split()
            terminals = [t for t in raw_terminals if "=" not in t]

            # Collect lines until .ends
            block_lines = [lines[i]]
            i += 1
            while i < len(lines):
                block_lines.append(lines[i])
                if lines[i].strip().lower().startswith(".ends"):
                    break
                i += 1

            # Extract description from comment lines inside the block
            desc_parts = []
            for bl in block_lines[1:]:
                stripped = bl.strip()
                if stripped.startswith("*"):
                    desc_parts.append(stripped[1:].strip())
                elif not stripped.lower().startswith(".ends"):
                    break

            definitions.append(
                SubcircuitDefinition(
                    name=name,
                    terminals=terminals,
                    spice_definition="\n".join(block_lines),
                    description=" ".join(desc_parts) if desc_parts else "",
                )
            )
        i += 1

    if not definitions:
        raise ValueError("No valid .subckt definitions found in the provided text")

    return definitions


class SubcircuitLibrary:
    """Manages a collection of subcircuit definitions with persistence.

    Definitions are stored as individual JSON files in the library directory
    (default: ``~/.spice-gui/library/``).  The library is loaded on
    construction and can be modified at runtime.
    """

    def __init__(self, library_dir: str | Path | None = None):
        self._library_dir = Path(library_dir) if library_dir else _DEFAULT_LIBRARY_DIR
        self._definitions: dict[str, SubcircuitDefinition] = {}
        self._load()

    # -- Public API ----------------------------------------------------------

    @property
    def definitions(self) -> dict[str, SubcircuitDefinition]:
        """Return a copy of the name -> definition mapping."""
        return dict(self._definitions)

    def get(self, name: str) -> SubcircuitDefinition | None:
        return self._definitions.get(name)

    def names(self) -> list[str]:
        return sorted(self._definitions.keys())

    def add(self, definition: SubcircuitDefinition, *, persist: bool = True) -> None:
        """Add or replace a subcircuit definition."""
        self._definitions[definition.name] = definition
        if persist:
            self._save_one(definition)

    def remove(self, name: str) -> bool:
        """Remove a subcircuit by name. Returns True if removed."""
        defn = self._definitions.pop(name, None)
        if defn is None:
            return False
        if defn.builtin:
            # Re-insert -- built-ins cannot be removed
            self._definitions[name] = defn
            return False
        path = self._path_for(name)
        if path.exists():
            path.unlink()
        return True

    def import_file(self, filepath: str | Path) -> list[SubcircuitDefinition]:
        """Parse a .subckt file and add all definitions to the library.

        Returns the list of newly imported definitions.
        """
        text = Path(filepath).read_text(encoding="utf-8", errors="replace")
        defs = parse_subckt(text)
        for d in defs:
            self.add(d)
        return defs

    def import_text(self, text: str) -> list[SubcircuitDefinition]:
        """Parse raw SPICE text and add all definitions to the library."""
        defs = parse_subckt(text)
        for d in defs:
            self.add(d)
        return defs

    # -- Registration into the component system ------------------------------

    def register_all(self) -> None:
        """Register all library subcircuits into the component system dicts."""
        for defn in self._definitions.values():
            register_subcircuit_component(defn)

    # -- Persistence ---------------------------------------------------------

    def _path_for(self, name: str) -> Path:
        # Sanitise name for filesystem
        safe = re.sub(r"[^\w\-.]", "_", name)
        return self._library_dir / f"{safe}.json"

    def _save_one(self, defn: SubcircuitDefinition) -> None:
        self._library_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(defn.name)
        path.write_text(json.dumps(defn.to_dict(), indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._library_dir.is_dir():
            return
        for path in sorted(self._library_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                defn = SubcircuitDefinition.from_dict(data)
                self._definitions[defn.name] = defn
            except Exception:
                logger.warning("Failed to load subcircuit from %s", path, exc_info=True)


# ---------------------------------------------------------------------------
# Dynamic component-system registration
# ---------------------------------------------------------------------------


def _generate_terminal_geometry(terminal_count: int):
    """Generate terminal positions for a subcircuit with *terminal_count* pins.

    Uses the same 3-terminal layout as Op-Amp for 3 terminals (IN on left-top,
    OUT on right, GND on left-bottom).  For other counts, distributes
    terminals evenly on left/right sides.
    """
    if terminal_count == 1:
        return (15, 15, [(-30, 0)])
    if terminal_count == 2:
        return (15, 15, None)  # standard horizontal layout
    if terminal_count == 3:
        # Same as Op-Amp: left-top, left-bottom, right-center
        return (20, 10, [(-30, -10), (-30, 10), (30, 0)])
    # Even split: ceil(n/2) on left, floor(n/2) on right
    left_count = (terminal_count + 1) // 2
    right_count = terminal_count - left_count
    spacing = 20
    terminals = []
    # Left side
    total_left = (left_count - 1) * spacing
    for i in range(left_count):
        y = -total_left / 2 + i * spacing
        terminals.append((-30, y))
    # Right side
    total_right = (right_count - 1) * spacing
    for i in range(right_count):
        y = -total_right / 2 + i * spacing
        terminals.append((30, y))
    return (20, 10, terminals)


def register_subcircuit_component(defn: SubcircuitDefinition) -> None:
    """Register a SubcircuitDefinition into the component system dictionaries.

    This makes the subcircuit available as a placeable component: it appears
    in COMPONENT_TYPES, can be created via CircuitController.add_component(),
    and generates correct netlist lines.
    """
    from models.component import (
        COMPONENT_CATEGORIES,
        COMPONENT_COLORS,
        COMPONENT_TYPES,
        DEFAULT_VALUES,
        SPICE_SYMBOLS,
        TERMINAL_COUNTS,
        TERMINAL_GEOMETRY,
    )

    name = defn.name

    # Skip if already registered
    if name in SPICE_SYMBOLS:
        return

    # Add to COMPONENT_TYPES
    if name not in COMPONENT_TYPES:
        COMPONENT_TYPES.append(name)

    # SPICE symbol is always "X" for subcircuit instances
    SPICE_SYMBOLS[name] = "X"

    # Terminal count
    TERMINAL_COUNTS[name] = defn.terminal_count

    # Default value: subcircuit name (used as the .subckt model reference)
    DEFAULT_VALUES[name] = name

    # Color -- use a consistent colour for all subcircuits
    COMPONENT_COLORS[name] = "#FF6F00"

    # Terminal geometry
    TERMINAL_GEOMETRY[name] = _generate_terminal_geometry(defn.terminal_count)

    # Add to "Subcircuits" category
    if "Subcircuits" not in COMPONENT_CATEGORIES:
        COMPONENT_CATEGORIES["Subcircuits"] = []
    if name not in COMPONENT_CATEGORIES["Subcircuits"]:
        COMPONENT_CATEGORIES["Subcircuits"].append(name)

    # Update COMPONENTS dict in styles/constants
    try:
        from GUI.styles.constants import _COLOR_KEYS, COMPONENTS

        _COLOR_KEYS[name] = "component_subcircuit"
        COMPONENTS[name] = {
            "symbol": "X",
            "terminals": defn.terminal_count,
            "color_key": "component_subcircuit",
        }
    except Exception:
        pass  # OK if GUI not available (headless tests)

    # Register graphics class and renderer
    _register_graphics(name, defn)


def _register_graphics(name: str, defn: SubcircuitDefinition) -> None:
    """Register a ComponentGraphicsItem subclass and renderer for *name*."""
    try:
        from GUI.component_item import COMPONENT_CLASSES, ComponentGraphicsItem

        # Create a dynamic subclass for this subcircuit type
        if name not in COMPONENT_CLASSES:
            cls = type(
                f"Subcircuit_{name}",
                (ComponentGraphicsItem,),
                {
                    "type_name": name,
                    "__init__": lambda self, component_id, model=None, _tn=name: ComponentGraphicsItem.__init__(
                        self, component_id, _tn, model=model
                    ),
                },
            )
            COMPONENT_CLASSES[name] = cls
    except Exception:
        pass  # GUI not importable in headless/model-only tests

    try:
        from GUI.renderers import _make_iec_delegate, register

        _register_subcircuit_renderer(name, defn, register, _make_iec_delegate)
    except Exception:
        pass


def _register_subcircuit_renderer(name, defn, register_fn, make_iec_delegate_fn):
    """Register IEEE + IEC renderers for a subcircuit component."""
    from GUI.renderers import ComponentRenderer, _bounding_rect_obstacle

    class SubcircuitRenderer(ComponentRenderer):
        """Generic box renderer for subcircuit components."""

        def __init__(self, defn):
            self._defn = defn

        def draw(self, painter, component):
            # Draw a rectangular box
            painter.drawRect(-18, -15, 36, 30)

            # Draw terminal connection lines
            if component.scene() is not None:
                tc = self._defn.terminal_count
                if tc == 2:
                    painter.drawLine(-30, 0, -18, 0)
                    painter.drawLine(18, 0, 30, 0)
                elif tc == 3:
                    painter.drawLine(-30, -10, -18, -10)
                    painter.drawLine(-30, 10, -18, 10)
                    painter.drawLine(18, 0, 30, 0)
                else:
                    # Draw leads for custom terminal positions
                    geom = self._defn and _generate_terminal_geometry(tc)
                    if geom and geom[2]:
                        for tx, ty in geom[2]:
                            if tx < 0:
                                painter.drawLine(int(tx), int(ty), -18, int(ty))
                            else:
                                painter.drawLine(18, int(ty), int(tx), int(ty))

            # Draw subcircuit name inside the box
            from PyQt6.QtCore import QRectF

            painter.drawText(QRectF(-16, -12, 32, 24), 0x0084, self._defn.name)

        def get_obstacle_shape(self, component):
            return _bounding_rect_obstacle(component)

    renderer = SubcircuitRenderer(defn)
    try:
        register_fn(name, "ieee", renderer)
        register_fn(name, "iec", make_iec_delegate_fn(renderer))
    except Exception:
        pass
