# GUI Protocol Guide

How to build a new GUI for Spice-GUI using the protocol interfaces.

## Architecture

```
models/          Pure Python dataclasses — the source of truth
controllers/     Pure Python logic — no Qt imports
protocols/       typing.Protocol contracts between controllers and views
GUI/             PyQt6 implementation (existing, reference)
your_gui/        Your new implementation
```

The controllers own the model and expose all mutations as methods.
Views register as observers to stay in sync.
Views never write to the model directly.

## Bootstrap

```python
from models.circuit import CircuitModel
from controllers.circuit_controller import CircuitController
from controllers.file_controller import FileController
from controllers.simulation_controller import SimulationController

# 1. Create model
model = CircuitModel()

# 2. Create controllers
circuit_ctrl = CircuitController(model)
file_ctrl = FileController(model, circuit_ctrl)
sim_ctrl = SimulationController(model, circuit_ctrl)

# 3. Create your views (implementing the protocols)
canvas = MyCanvas()
properties = MyPropertiesPanel()
palette = MyPalette()
results = MyResultsDisplay()
dialogs = MyDialogProvider()

# 4. Wire the observer
circuit_ctrl.add_observer(canvas.handle_observer_event)

# 5. Wire callbacks
palette.set_component_selected_callback(
    lambda comp_type: circuit_ctrl.add_component(comp_type, (0, 0))
)
properties.set_property_change_callback(on_property_changed)

def on_property_changed(component_id, prop_name, new_value):
    if prop_name == "value":
        circuit_ctrl.update_component_value(component_id, new_value)
    elif prop_name == "waveform":
        wtype, params = new_value
        circuit_ctrl.update_component_waveform(component_id, wtype, params)
    elif prop_name == "initial_condition":
        circuit_ctrl.update_component_initial_condition(component_id, new_value)
```

## Observer Events

When the model changes, every registered observer receives `(event, data)`.
See `protocols/events.py` for the full list.

### Handling events in your canvas

```python
def handle_observer_event(self, event: str, data):
    handlers = {
        "component_added":    self._on_component_added,
        "component_removed":  self._on_component_removed,
        "component_moved":    self._on_component_moved,
        "component_rotated":  self._on_component_rotated,
        "component_flipped":  self._on_component_flipped,
        "component_value_changed": self._on_component_value_changed,
        "wire_added":         self._on_wire_added,
        "wire_removed":       self._on_wire_removed,
        "wire_routed":        self._on_wire_routed,
        "circuit_cleared":    self._on_circuit_cleared,
        "nodes_rebuilt":      self._on_nodes_rebuilt,
        "model_loaded":       self._on_model_loaded,
        "annotation_added":   self._on_annotation_added,
        "annotation_removed": self._on_annotation_removed,
        "annotation_updated": self._on_annotation_updated,
    }
    handler = handlers.get(event)
    if handler:
        handler(data)
```

### Event payload reference

| Event | Data type | When |
|-------|-----------|------|
| `component_added` | `ComponentData` | New component created |
| `component_removed` | `str` (component_id) | Component deleted |
| `component_moved` | `ComponentData` | Position changed |
| `component_rotated` | `ComponentData` | Rotation changed |
| `component_flipped` | `ComponentData` | Flip state changed |
| `component_value_changed` | `ComponentData` | Value, waveform, or IC changed |
| `wire_added` | `WireData` | New wire connection |
| `wire_removed` | `int` (wire_index) | Wire deleted |
| `wire_routed` | `tuple[int, WireData]` | Wire waypoints updated |
| `wire_lock_changed` | `tuple[int, bool]` | Wire lock toggled |
| `circuit_cleared` | `None` | Full reset |
| `nodes_rebuilt` | `None` | Node graph recalculated |
| `model_loaded` | `None` | Circuit loaded from file |
| `model_saved` | `None` | Circuit saved |
| `simulation_started` | `None` | Sim pipeline begins |
| `simulation_completed` | `SimulationResult` | Sim pipeline ends |
| `annotation_added` | `AnnotationData` | Annotation created |
| `annotation_removed` | `int` | Annotation deleted |
| `annotation_updated` | `AnnotationData` | Annotation text changed |
| `net_name_changed` | `NodeData` | Custom node label set |
| `locked_components_changed` | `list[str]` | Lock set changed |
| `recommended_components_changed` | `list[str]` | Recommended list updated |

## Controller Methods by User Action

### Adding a component

```python
component_data = circuit_ctrl.add_component("Resistor", (100.0, 200.0))
# Observer receives: ("component_added", component_data)
```

Available types: see `models.component.COMPONENT_TYPES` and `COMPONENT_CATEGORIES`.

### Moving a component

```python
circuit_ctrl.move_component("R1", (150.0, 250.0))
# Observer receives: ("component_moved", component_data)
```

### Rotating / flipping

```python
circuit_ctrl.rotate_component("R1", clockwise=True)
circuit_ctrl.flip_component("R1", horizontal=True)
```

### Changing a value

```python
circuit_ctrl.update_component_value("R1", "4.7k")
circuit_ctrl.update_component_waveform("V1", "SINE", {"amplitude": "5", "frequency": "1k"})
circuit_ctrl.update_component_initial_condition("C1", "0V")
```

### Adding a wire

```python
wire = circuit_ctrl.add_wire("R1", 0, "R2", 1, waypoints=[(100, 200), (150, 200)])
# Observer receives: ("wire_added", wire)
```

Terminal indices are 0-based. Use `ComponentData.get_terminal_positions()` for positions.

### Removing components / wires

```python
circuit_ctrl.remove_component("R1")  # Also removes connected wires
circuit_ctrl.remove_wire(0)          # By index into wires list
```

### Undo / redo

For undoable operations, wrap in a Command:

```python
from controllers.commands import AddComponentCommand

cmd = AddComponentCommand(circuit_ctrl, "Resistor", (100, 200))
circuit_ctrl.execute_command(cmd)

circuit_ctrl.undo()  # Removes the component
circuit_ctrl.redo()  # Re-adds it
```

### Copy / paste / cut

```python
circuit_ctrl.copy_components(["R1", "R2"])
new_comps, new_wires = circuit_ctrl.paste_components(offset=(40, 40))
circuit_ctrl.cut_components(["R1", "R2"])
```

### File operations

```python
file_ctrl.new_circuit()
file_ctrl.save_circuit("/path/to/file.json")
file_ctrl.load_circuit("/path/to/file.json")

# Recent files
recent = file_ctrl.get_recent_files()

# Auto-save recovery
if file_ctrl.has_auto_save():
    file_ctrl.load_auto_save()
```

### Simulation

```python
sim_ctrl.set_analysis("Transient", {"stop_time": "10m", "step": "1u"})

result = sim_ctrl.validate_circuit()
if not result.success:
    dialogs.show_error("Validation Failed", "\n".join(result.errors))
    return

result = sim_ctrl.run_simulation()
if result.success:
    results_display.display_simulation_result(result)
else:
    dialogs.show_error("Simulation Failed", result.error)
```

### Querying state (read-only)

Use controller query methods instead of accessing `model` directly:

```python
# Good — goes through controller
components = circuit_ctrl.get_components()
count = circuit_ctrl.get_component_count()
comp = circuit_ctrl.get_component("R1")
wires = circuit_ctrl.get_wires()
analysis = sim_ctrl.get_analysis_type()
params = sim_ctrl.get_analysis_params()

# Bad — bypasses controller
components = model.components      # Don't do this
analysis = model.analysis_type     # Don't do this
```

## Model Data Structures

All models are pure Python dataclasses. Import from `models/`.

### ComponentData (`models/component.py`)

```python
@dataclass
class ComponentData:
    component_id: str           # "R1", "V2", etc.
    component_type: str         # "Resistor", "Voltage Source", etc.
    value: str                  # "1k", "5V", etc.
    position: tuple[float, float]
    rotation: int = 0           # 0, 90, 180, 270
    flip_h: bool = False
    flip_v: bool = False
    waveform_type: Optional[str] = None
    waveform_params: Optional[dict] = None
    initial_condition: Optional[str] = None
```

Key methods:
- `get_terminal_count() -> int`
- `get_terminal_positions() -> list[tuple[float, float]]` (world coords, after transform)
- `get_spice_symbol() -> str`

### WireData (`models/wire.py`)

```python
@dataclass
class WireData:
    start_component_id: str
    start_terminal: int
    end_component_id: str
    end_terminal: int
    waypoints: list[tuple[float, float]] = []
    locked: bool = False
```

### NodeData (`models/node.py`)

```python
@dataclass
class NodeData:
    terminals: set[tuple[str, int]]  # (component_id, terminal_index)
    wire_indices: set[int]
    is_ground: bool = False
    custom_label: Optional[str] = None
    auto_label: str = ""
```

Key method: `get_label() -> str` (custom label if set, else auto label).

### AnnotationData (`models/annotation.py`)

```python
@dataclass
class AnnotationData:
    text: str = "Annotation"
    x: float = 0.0
    y: float = 0.0
    font_size: int = 10
    bold: bool = False
    color: str = ""  # hex
```

### SimulationResult (`controllers/simulation_controller.py`)

```python
@dataclass
class SimulationResult:
    success: bool
    analysis_type: str = ""
    data: Any = None
    errors: list[str] = []
    warnings: list[str] = []
    error: str = ""
    netlist: str = ""
    raw_output: str = ""
    measurements: Optional[dict] = None
```

## Protocols Checklist

Implement these protocols to get a working GUI:

| Protocol | File | Purpose | Priority |
|----------|------|---------|----------|
| `CircuitCanvasProtocol` | `protocols/canvas.py` | Drawing surface | Must have |
| `PropertiesPanelProtocol` | `protocols/properties.py` | Property editor | Must have |
| `ComponentPaletteProtocol` | `protocols/palette.py` | Component selector | Must have |
| `ResultsDisplayProtocol` | `protocols/results.py` | Simulation output | Must have |
| `DialogProvider` | `protocols/dialogs.py` | Modal interactions | Must have |
| `ApplicationShellProtocol` | `protocols/application.py` | Top-level window | Must have |
| `ProgressHandle` | `protocols/dialogs.py` | Progress bars | Nice to have |

## Theme

The existing `ThemeProtocol` in `GUI/styles/theme.py` returns Qt types (`QColor`, `QPen`, etc.).
Since both GUIs use PyQt6, you can use it directly.
For non-Qt rendering paths, use `theme.color_hex(key)` which returns hex strings.

## Wire Routing

The pathfinding algorithms in `algorithms/` are pure Python and framework-agnostic.
You can reuse them for wire routing — only the rendering needs reimplementation.

```python
from algorithms.wire_routing import route_wire

waypoints = route_wire(start_pos, end_pos, obstacles, algorithm="idastar")
```

## Reference Implementation

The existing PyQt6 GUI in `GUI/` satisfies these protocols.
Key files to study:

- `GUI/circuit_canvas.py` — `CircuitCanvasProtocol` reference (observer dispatch at lines 140-176)
- `GUI/properties_panel.py` — `PropertiesPanelProtocol` reference
- `GUI/component_palette.py` — `ComponentPaletteProtocol` reference
- `GUI/main_window.py` — `ApplicationShellProtocol` reference (bootstrap at lines 73-127)
