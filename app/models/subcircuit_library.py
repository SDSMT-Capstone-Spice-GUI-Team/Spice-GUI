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


# Default persistence directory — evaluated lazily to avoid module-level I/O.
def _default_library_dir() -> Path:
    """Return the default subcircuit library directory (deferred until needed)."""
    return Path.home() / ".spice-gui" / "library"


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
        self._library_dir = Path(library_dir) if library_dir else _default_library_dir()
        self._definitions: dict[str, SubcircuitDefinition] = {}
        self._load()
        self._load_builtins()

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

    def _load_builtins(self) -> None:
        """Load built-in subcircuit definitions (e.g. voltage regulators)."""
        try:
            from models.builtin_subcircuits import BUILTIN_SUBCIRCUITS

            for defn in BUILTIN_SUBCIRCUITS:
                if defn.name not in self._definitions:
                    self._definitions[defn.name] = defn
        except ImportError:
            pass


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

    # Also register in the theme system so theme_manager.get_component_color()
    # returns the correct color for dynamically registered subcircuits.
    try:
        from GUI.styles.constants import _COLOR_KEYS, COMPONENTS

        color_key = f"component_subcircuit_{name.lower().replace(' ', '_')}"
        _COLOR_KEYS[name] = color_key
        COMPONENTS[name] = {
            "symbol": "X",
            "terminals": defn.terminal_count,
            "color_key": color_key,
        }
        # Inject the color into the current theme's color dict
        from GUI.styles import theme_manager

        theme = theme_manager.current_theme
        if hasattr(theme, "_colors"):
            theme._colors.setdefault(color_key, "#FF6F00")
    except Exception:
        pass  # GUI styles unavailable (headless / test environment)

    # Terminal geometry
    TERMINAL_GEOMETRY[name] = _generate_terminal_geometry(defn.terminal_count)

    # Add to "Subcircuits" category
    if "Subcircuits" not in COMPONENT_CATEGORIES:
        COMPONENT_CATEGORIES["Subcircuits"] = []
    if name not in COMPONENT_CATEGORIES["Subcircuits"]:
        COMPONENT_CATEGORIES["Subcircuits"].append(name)
