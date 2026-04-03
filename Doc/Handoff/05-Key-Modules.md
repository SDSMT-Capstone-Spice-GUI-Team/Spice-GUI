# Key Modules

## Models (`app/models/`)

The data layer. Pure Python — no Qt imports allowed.

### CircuitModel (`circuit.py`)
The **single source of truth** for circuit state.

```python
CircuitModel
├── components: dict[str, ComponentData]   # keyed by ID ("R1", "V1", etc.)
├── wires: list[WireData]
├── nodes: list[NodeData]
├── terminal_to_node: dict                 # terminal → node lookup
├── analysis_type: str                     # "DC Operating Point", etc.
├── analysis_params: dict
├── annotations: list[AnnotationData]
├── to_dict() → dict                      # serialize to JSON
└── from_dict(d) → CircuitModel            # deserialize from JSON
```

### ComponentData (`component.py`)
Defines a circuit element with its type, value, position, and orientation.
Also contains `SPICE_SYMBOLS` — a mapping of component types to their SPICE letter prefixes and terminal definitions.

### WireData (`wire.py`)
A connection between two component terminals, including routed waypoints.

### NodeData (`node.py`)
An electrical node — a set of terminals that are electrically connected. `NodeLabelGenerator` assigns unique node labels.

---

## Controllers (`app/controllers/`)

Business logic. Pure Python — no Qt.

### CircuitController (`circuit_controller.py`)
The main controller. Manages CRUD operations on the circuit and broadcasts changes via the observer pattern.

```python
CircuitController
├── model: CircuitModel
├── undo_manager: UndoManager
├── add_component(type, pos) → ComponentData
├── remove_component(id)
├── add_wire(start, end) → WireData
├── remove_wire(index)
├── add_observer(callback)
└── _notify(event_name, data)
```

### SimulationController (`simulation_controller.py`)
Orchestrates the full simulation pipeline: validate → generate netlist → run ngspice → parse results.

### FileController (`file_controller.py`)
Handles save/load, recent files, autosave, and session recovery.

### UndoManager + Commands (`undo_manager.py`, `commands.py`)
Command pattern implementation. Every mutating action creates a `Command` object that can be undone/redone.

---

## GUI (`app/GUI/`)

The view layer. PyQt6 widgets, dialogs, and rendering.

### CircuitCanvasView (`circuit_canvas.py`)
A `QGraphicsView` + `QGraphicsScene` that renders the circuit. Handles:
- Drag-and-drop from the palette
- Component selection, movement, rotation
- Wire drawing between terminals
- Zoom, pan (middle mouse), grid rendering

### ComponentGraphicsItem (`component_item.py`)
A `QGraphicsItem` that draws a single component using custom paint logic. Handles hit testing, selection highlighting, and terminal indicators.

### ComponentPalette (`component_palette.py`)
A sidebar listing all available components, grouped by category. Supports drag-and-drop onto the canvas.

### PropertiesPanel (`properties_panel.py`)
Shows editable properties (value, model, label) for the currently selected component.

### ResultsPanel (`results_panel.py`)
Displays simulation output: data tables, node voltages, branch currents.

### Styles System (`GUI/styles/`)
- `theme.py` — abstract theme interface
- `dark_theme.py` / `light_theme.py` — concrete themes with color maps
- `dark_theme.qss` / `light_theme.qss` — Qt stylesheets
- `constants.py` — grid size (10px), canvas dimensions

---

## Simulation (`app/simulation/`)

The SPICE pipeline. Pure Python — no Qt.

### NetlistGenerator (`netlist_generator.py`)
Converts a `CircuitModel` into a SPICE-format netlist string.

### NgspiceRunner (`ngspice_runner.py`)
Executes `ngspice` as a subprocess, manages temp files, captures stdout/stderr.

### ResultParser (`result_parser.py`)
Parses ngspice text output into structured `SimulationResult` objects.

### Exporters
- `csv_exporter.py`, `excel_exporter.py` — data export
- `asc_exporter.py` / `asc_parser.py` — LTSpice format
- `circuitikz_exporter.py` — LaTeX diagrams
- `bom_exporter.py` — bill of materials
- `bundle_exporter.py` — ZIP with all artifacts

---

## Grading (`app/grading/`)

Educational auto-grading system. Pure Python — no Qt.

- `grader.py` — compares a student circuit against a rubric
- `rubric.py` — defines grading criteria
- `circuit_comparer.py` — matches components/wires between circuits
- `batch_grader.py` — grades multiple submissions at once
- `feedback_exporter.py` — generates student-facing feedback

---

## Algorithms (`app/algorithms/`)

- `path_finding.py` — **IDA\*** algorithm for routing wires around components on the grid. This is the largest single file in the project (~28 KB).
- `graph_ops.py` — maintains the node graph when wires/components change.

---

## Scripting (`app/scripting/`)

Headless API for programmatic circuit manipulation:

- `circuit.py` — create circuits, add components, run simulations without a GUI
- `jupyter.py` — Jupyter notebook integration with inline rendering