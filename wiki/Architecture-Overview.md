# Architecture Overview

Technical architecture and design patterns used in SDM Spice.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SDM Spice Application                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Presentation Layer (app/GUI/)             │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │ │
│  │  │  MainWindow  │ │  Component   │ │  Properties Panel  │ │ │
│  │  │  + 8 mixins  │ │   Palette    │ │  Results Panel     │ │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────┘ │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │ │
│  │  │ CircuitCanvas│ │  Waveform /  │ │  Grading Panel     │ │ │
│  │  │    View      │ │  Plot Dialog │ │  Analysis Dialog   │ │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │ protocols/                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Controller Layer (app/controllers/)       │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │ │
│  │  │  Circuit     │ │    File      │ │   Simulation       │ │ │
│  │  │  Controller  │ │  Controller  │ │   Controller       │ │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────┘ │ │
│  │  ┌──────────────┐ ┌──────────────┐                         │ │
│  │  │   Template   │ │    Undo      │                         │ │
│  │  │  Controller  │ │   Manager    │                         │ │
│  │  └──────────────┘ └──────────────┘                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Model Layer (app/models/)                 │ │
│  │  CircuitModel · ComponentData · WireData · NodeData         │ │
│  │  AnnotationData · TemplateData · SubcircuitLibrary          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
│  ┌──────────────────────────┐ │ ┌─────────────────────────────┐ │
│  │  Simulation (app/sim/)   │ │ │  Grading (app/grading/)     │ │
│  │  NetlistGenerator        │ │ │  CircuitGrader · Rubric     │ │
│  │  NgspiceRunner           │ │ │  BatchGrader · Analytics    │ │
│  │  ResultParser + exports  │ │ │  FeedbackExporter           │ │
│  └──────────────────────────┘ │ └─────────────────────────────┘ │
│                               │                                  │
│  ┌──────────────────────────┐   ┌─────────────────────────────┐ │
│  │  Services (app/services/)│   │  Scripting (app/scripting/) │ │
│  │  ThemeManager            │   │  Circuit (headless API)     │ │
│  │  ReportDataBuilder       │   │  Jupyter integration        │ │
│  │  PaletteProfiles         │   └─────────────────────────────┘ │
│  └──────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Dependencies                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   ngspice   │  │  matplotlib  │  │     PyQt6 / Qt6      │   │
│  └─────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Design Patterns

### MVC — The Core Invariant

The architecture enforces a strict rule: **controllers and models never import Qt**. This makes the business logic independently testable without a display server.

```
Models (app/models/)          No Qt, no GUI imports
Controllers (app/controllers/) No Qt, no GUI imports
Protocols (app/protocols/)     No Qt, typed contracts only
GUI (app/GUI/)                 Qt-dependent; observes controllers
```

### Observer Pattern (Callback-Based)

The model-to-view notification path uses a plain callback observer registered on `CircuitController`, not PyQt signals. PyQt signals exist only *within* the GUI layer (canvas-to-mainwindow communication).

```python
# Controller side — no Qt
class CircuitController:
    def add_observer(self, callback: Callable[[str, Any], None]) -> None:
        self._observers.append(callback)

    def _notify(self, event: str, data: Any) -> None:
        for cb in self._observers:
            cb(event, data)

    def add_component(self, component_type, position) -> ComponentData:
        # mutate model, then notify
        self._notify("component_added", {"id": comp.component_id, ...})

# Canvas side — Qt-aware observer
class CircuitCanvasView(QGraphicsView):
    def __init__(self, controller):
        self.controller = controller
        self.controller.add_observer(self._on_model_changed)

    def _on_model_changed(self, event: str, data: Any) -> None:
        if event == "component_added":
            self._handle_component_added(data)
        elif event == "wire_added":
            self._handle_wire_added(data)
        # ...
```

The full set of event names and their payload types is documented in `app/protocols/events.py`.

### Factory Pattern

Component creation uses a registry dictionary that maps type strings to graphics item classes:

```python
# app/GUI/component_item.py
COMPONENT_CLASSES = {
    "Resistor": Resistor,
    "Capacitor": Capacitor,
    "VoltageSource": VoltageSource,
    "WaveformVoltageSource": WaveformVoltageSource,
    "ACVoltageSource": ACVoltageSource,
    "Ground": Ground,
    "OpAmp": OpAmp,
    "Transformer": Transformer,
    "CurrentProbe": CurrentProbe,
    # ... all component types
}

def create_component(component_type: str, component_id: str) -> ComponentGraphicsItem:
    component_class = COMPONENT_CLASSES.get(component_type, GenericComponent)
    return component_class(component_id)
```

### Strategy Pattern (Wire Routing)

The pathfinder is a single concrete strategy (`IDAStarPathfinder`) inheriting from an abstract base. It is lazy-imported from `algorithms/path_finding.py` on first wire creation:

```python
# app/GUI/wire_item.py
def update_position(self):
    # Lazy import — only loaded when wires are routed
    from algorithms.path_finding import IDAStarPathfinder, get_component_obstacles
    pathfinder = IDAStarPathfinder()
    path, runtime, iterations = pathfinder.find_path(start, end, obstacles)
```

### Protocol Layer

`app/protocols/` defines typed `Protocol` interfaces that decouple controllers from specific GUI implementations. Controllers accept these interfaces rather than concrete Qt classes:

| Protocol | Implemented by |
|----------|---------------|
| `CircuitCanvasProtocol` | `CircuitCanvasView` |
| `ApplicationShellProtocol` | `MainWindow` |
| `DialogProvider` | `QtDialogProvider` |
| `ComponentPaletteProtocol` | `ComponentPalette` |
| `PropertiesPanelProtocol` | `PropertiesPanel` |
| `ResultsDisplayProtocol` | `ResultsPanel` |

## Module Breakdown

### GUI Layer (`app/GUI/`)

| Module | Responsibility |
|--------|----------------|
| `main_window.py` | Main window base class; wires together controllers and panels |
| `main_window_menus.py` | Menu bar construction |
| `main_window_file_ops.py` | File menu handlers (new, open, save, import, export) |
| `main_window_simulation.py` | Simulation menu handlers |
| `main_window_analysis.py` | Analysis settings handlers |
| `main_window_view.py` | View menu handlers (grid, probe mode, zoom) |
| `main_window_print.py` | Print and print-preview handlers |
| `main_window_settings.py` | Preferences, auto-save, settings restore |
| `circuit_canvas.py` | `CircuitCanvasView` — main drawing surface |
| `component_item.py` | `ComponentGraphicsItem` base + all component subclasses + `COMPONENT_CLASSES` registry |
| `wire_item.py` | Wire rendering, waypoint handles, routing |
| `annotation_item.py` | Text annotations on the canvas |
| `canvas_probe_overlay.py` | Interactive voltage/current probing |
| `component_palette.py` | Drag source for placing components |
| `properties_panel.py` | Component property editing |
| `results_panel.py` | Simulation results display |
| `netlist_preview.py` | Live SPICE netlist preview widget |
| `circuit_statistics_panel.py` | Component/wire count display |
| `grading_panel.py` | Instructor grading panel |
| `renderers.py` | IEEE/IEC component drawing (one renderer class per component type) |
| `dialog_provider.py` | `QtDialogProvider` implementing `DialogProvider` protocol |
| `analysis_dialog.py` | Analysis type and parameter selection |
| `waveform_dialog.py` | Waveform result viewer |
| `waveform_config_dialog.py` | Waveform source configuration |
| `parameter_sweep_dialog.py` | Parameter sweep configuration |
| `parameter_sweep_plot_dialog.py` | Parameter sweep results plots |
| `monte_carlo_dialog.py` | Monte Carlo configuration |
| `monte_carlo_results_dialog.py` | Monte Carlo results with overlaid traces |
| `results_plot_dialog.py` | DC/AC/Transient/Noise result plots with cursors |
| `report_dialog.py` | PDF report section selection |
| `report_renderer.py` | `PDFReportRenderer` — multi-page PDF via QPainter |
| `template_dialog.py` | Template selection and loading |
| `template_metadata_dialog.py` | Template metadata entry |
| `template_preview_dialog.py` | Template preview before loading |
| `rubric_editor_dialog.py` | Rubric creation and editing |
| `batch_grading_dialog.py` | Batch grading run dialog |
| `preferences_dialog.py` | App-wide preferences |
| `theme_editor_dialog.py` | Custom theme color editor |
| `keybindings_dialog.py` | Keyboard shortcut editor |
| `subcircuit_dialog.py` | Subcircuit library management |
| `plot_utils.py` | Shared matplotlib utilities |
| `canvas_context_menu.py` | Right-click context menu builder |
| `validation_helpers.py` | Dialog field validation styling |

### Styles Layer (`app/GUI/styles/`)

| Module | Responsibility |
|--------|----------------|
| `__init__.py` | Public API — exports `theme_manager` singleton and constants |
| `theme.py` | `ThemeProtocol` interface and `BaseTheme` base class |
| `light_theme.py` | `LightTheme` — light color palette |
| `dark_theme.py` | `DarkTheme` — dark color palette |
| `custom_theme.py` | `CustomTheme` — user-defined color overrides |
| `constants.py` | `GRID_SIZE`, `CANVAS_SIZE`, z-order constants |
| `font_loader.py` | Registers bundled fonts (JetBrains Mono, OpenDyslexic) with Qt |
| `theme_store.py` | Re-exports from `app/services/theme_store.py` |

### Controllers Layer (`app/controllers/`)

| Module | Responsibility |
|--------|----------------|
| `circuit_controller.py` | All circuit mutations — add/remove/move/rotate/flip components and wires, observer notifications, undo/redo, clipboard |
| `file_controller.py` | Save, load, recent files, auto-save |
| `simulation_controller.py` | Validate → generate → run → parse pipeline; parameter sweep, Monte Carlo |
| `template_controller.py` | Template save/load, instructor assignment bundles |
| `template_manager.py` | Template file discovery and metadata |
| `undo_manager.py` | `UndoManager` + `Command` ABC |
| `commands.py` | Concrete command classes (one per reversible operation) |
| `settings_service.py` | `SettingsService` singleton — persistent key/value store |
| `keybindings.py` | `KeybindingsRegistry` — load, save, look up shortcuts |
| `theme_controller.py` | Bridges `ThemeManager` singleton to settings persistence |
| `assignment_controller.py` | Save/load `.spice-assignment` bundles |
| `recent_exports.py` | Track last 5 export paths via settings |

### Model Layer (`app/models/`)

| Module | Responsibility |
|--------|----------------|
| `circuit.py` | `CircuitModel` — the single source of truth for circuit state |
| `component.py` | `ComponentData` — position, value, rotation, terminal geometry |
| `wire.py` | `WireData` — connectivity, waypoints, routing metadata |
| `node.py` | `NodeData` + `NodeLabelGenerator` — electrical node abstraction |
| `annotation.py` | `AnnotationData` — text labels on the canvas |
| `clipboard.py` | `ClipboardData` — copy/paste buffer |
| `template.py` | `TemplateData` + `TemplateMetadata` — assignment templates |
| `assignment.py` | `AssignmentBundle` — template + rubric as a single file |
| `subcircuit_library.py` | `SubcircuitLibrary` + `SubcircuitDefinition` |
| `builtin_subcircuits.py` | Built-in voltage regulator definitions (7805, LM317, LM7812) |
| `grading_session.py` | `GradingSessionData` — serializable grading session |
| `circuit_schema_validator.py` | JSON schema validation before deserializing circuit files |
| `waveform_defaults.py` | Default waveform parameters and SPICE value formatting |

### Simulation Layer (`app/simulation/`)

| Module | Responsibility |
|--------|----------------|
| `netlist_generator.py` | `CircuitModel` → SPICE netlist text |
| `ngspice_runner.py` | Subprocess management, output file cleanup, ngspice detection |
| `ngspice_config.py` | Platform-specific ngspice binary resolution |
| `result_parser.py` | Raw ngspice output → structured `SimulationResult` |
| `circuit_semantic_validator.py` | Pre-simulation checks (ground, connected terminals, source requirements) |
| `preset_manager.py` | Save/load named analysis presets |
| `convergence.py` | `ErrorCategory` enum + `ErrorDiagnosis` — classify ngspice errors |
| `spice_sanitizer.py` | Sanitize component values and identifiers against injection |
| `fft_analysis.py` | FFT with windowing on transient results |
| `freq_markers.py` | Bode plot markers (-3 dB, bandwidth, gain/phase margin) |
| `monte_carlo.py` | Random tolerance application and multi-run Monte Carlo |
| `power_calculator.py` | DC operating-point power dissipation per component |
| `power_metrics.py` | RMS and average/peak power from transient data |
| `measurement_builder.py` | Build ngspice `.meas` directives from structured params |
| `selftest.py` | Post-install smoke tests (`CheckResult`, `SelftestResult`) |
| `asc_exporter.py` | Export to LTspice `.asc` schematic format |
| `asc_parser.py` | Import LTspice `.asc` files |
| `circuitikz_exporter.py` | Export to CircuiTikZ LaTeX |
| `circuitikz_parser.py` | Import CircuiTikZ LaTeX |
| `netlist_parser.py` | Import raw SPICE netlists (`.cir`, `.spice`) |
| `bom_exporter.py` | Bill-of-materials export (CSV, Excel) |
| `bundle_exporter.py` | Lab submission ZIP bundle (circuit + netlist + PNG + results) |
| `csv_exporter.py` | CSV export for all analysis types |
| `excel_exporter.py` | Excel `.xlsx` export with styled worksheets |
| `markdown_exporter.py` | Markdown pipe-table export for all analysis types |
| `svg_shareable.py` | Embed/extract circuit JSON in SVG for round-trip sharing |

### Grading Layer (`app/grading/`)

| Module | Responsibility |
|--------|----------------|
| `rubric.py` | `Rubric` + `RubricCheck` dataclasses |
| `grader.py` | `CircuitGrader` — runs checks against a student circuit |
| `circuit_comparer.py` | `CircuitComparer` — component existence, value, topology checks |
| `batch_grader.py` | `BatchGrader` — grade a directory of student files |
| `rubric_generator.py` | Auto-generate a rubric skeleton from a reference circuit |
| `rubric_validator.py` | Validate rubric structure and required parameters |
| `component_mapper.py` | Extract component IDs embedded in rubric check identifiers |
| `check_analytics.py` | `CheckAnalytics` — pass rates and statistics across batch results |
| `feedback_exporter.py` | Per-student HTML feedback reports |
| `grade_exporter.py` | Batch results as a gradebook CSV |
| `histogram.py` | Score distribution histogram (matplotlib) |
| `session_persistence.py` | Save/load `.spice-grades` grading session files |

### Services Layer (`app/services/`)

| Module | Responsibility |
|--------|----------------|
| `theme_manager.py` | `ThemeManager` singleton — theme, symbol style, wire thickness, font, observer notifications |
| `theme_store.py` | Persist custom themes as JSON in `~/.spice-gui/themes/` |
| `report_generator.py` | `ReportConfig`, `ReportData`, `ReportDataBuilder` — assemble report content (Qt-free) |
| `palette_profiles.py` | Named component palette layouts (full vs. course-restricted subsets) |

### Scripting Layer (`app/scripting/`)

| Module | Responsibility |
|--------|----------------|
| `circuit.py` | `Circuit` — high-level headless API wrapping model/controller/simulation |
| `jupyter.py` | SVG rendering and matplotlib plotting for Jupyter notebooks |

### Utilities (`app/utils/`, `app/algorithms/`)

| Module | Responsibility |
|--------|----------------|
| `utils/format_utils.py` | SI unit parsing and formatting |
| `utils/connectivity.py` | Detect floating (unconnected) terminals |
| `utils/atomic_write.py` | Crash-safe file writes (write-then-replace) |
| `utils/drag_drop_router.py` | Map dropped file extensions to import handlers |
| `utils/constants.py` | App-wide constants (e.g., `SIMULATION_TIMEOUT`) |
| `algorithms/path_finding.py` | `IDAStarPathfinder` — wire routing (Qt-free) |
| `algorithms/graph_ops.py` | Node graph operations (ground handling, wire merges) |

## Data Flow

### Circuit Creation

```
User drops component     Component Palette
        │                       │
        │  mime drag event      │
        └──────────────────────>│
                                │  drop event
                                ▼
                        CircuitCanvasView
                                │  circuit_ctrl.add_component(type, pos)
                                ▼
                        CircuitController  ──────>  CircuitModel
                                │  _notify("component_added", data)
                                ▼
                        CircuitCanvasView._on_model_changed()
                                │  creates ComponentGraphicsItem
                                ▼
                        Scene renders component
```

### Save / Load

Save and load go through `FileController`, not the canvas directly. The canvas is kept in sync via observer notifications after a load.

```python
# Saving — FileController.save_circuit()
data = self.circuit_ctrl.to_dict()
from utils.atomic_write import atomic_write_text
atomic_write_text(filepath, json.dumps(data, indent=2))

# Loading — FileController.load_circuit()
data = json.loads(filepath.read_text())
validate_circuit_data(data)          # schema check
self.circuit_ctrl.load_circuit(data) # mutates model → observer notifies canvas
```

### Simulation Pipeline

```
User triggers simulation
        │
        ▼
SimulationController.run_simulation()
        │
        ├─ circuit_semantic_validator.validate_circuit(model)
        │    returns (ok, errors, warnings)
        │
        ├─ NetlistGenerator(components, wires, nodes, ...).generate()
        │    returns SPICE text
        │
        ├─ NgspiceRunner.run_simulation(netlist, timeout)
        │    returns (success, stdout, stderr)
        │
        └─ ResultParser.parse(raw_output, analysis_type)
             returns structured SimulationResult
```

## Key Classes

### `MainWindow`

Main application window, assembled from 8 behaviour mixins:

```python
class MainWindow(
    MenuBarMixin,
    FileOperationsMixin,
    SimulationMixin,
    AnalysisSettingsMixin,
    ViewOperationsMixin,
    PrintExportMixin,
    HelpMixin,
    SettingsMixin,
    QMainWindow,
):
    def __init__(self):
        self.model = CircuitModel()
        self._circuit_ctrl = CircuitController(self.model)
        self._file_ctrl = FileController(self.model, self._circuit_ctrl)
        self._simulation_ctrl = SimulationController(self.model, self._circuit_ctrl)
        self.canvas = CircuitCanvasView(self._circuit_ctrl)
```

### `CircuitCanvasView`

The main drawing surface. A `QGraphicsView` (not a `QGraphicsScene`) that observes `CircuitController`:

```python
class CircuitCanvasView(QGraphicsView):
    def __init__(self, controller: CircuitController):
        self.controller = controller
        self.components: dict[str, ComponentGraphicsItem] = {}
        self.wires: list[WireGraphicsItem] = []
        self.controller.add_observer(self._on_model_changed)
```

### `CircuitController`

Central orchestrator for all circuit mutations. Qt-free.

```python
class CircuitController:
    def __init__(self, model: CircuitModel, max_undo_depth: int = 100):
        self.model = model
        self.undo_manager = UndoManager(max_undo_depth)
        self._observers: list[Callable] = []
        self._clipboard = ClipboardData([], [])

    def add_component(self, component_type: str, position: tuple) -> ComponentData:
        cmd = AddComponentCommand(self.model, component_type, position)
        self.undo_manager.execute(cmd)
        self._notify("component_added", {"id": cmd.component_id, ...})
        return self.model.components[cmd.component_id]
```

### `ComponentGraphicsItem`

Base class for all visual components. Subclasses exist for each component type. Drawing is delegated to the renderer registry:

```python
class ComponentGraphicsItem(QGraphicsItem):
    def paint(self, painter, option, widget=None):
        renderer = _renderer_registry.get((self.component_type, symbol_style))
        if renderer:
            renderer.draw(painter, self)
```

## Theme Management

`ThemeManager` is a singleton in `app/services/theme_manager.py`. Access it through the `app/GUI/styles/` package:

```python
from .styles import theme_manager

color = theme_manager.color('component_body')
pen   = theme_manager.pen('wire_default')
brush = theme_manager.brush('terminal_fill')
font  = theme_manager.font('panel_title')
qss   = theme_manager.stylesheet('muted_label')
```

`ThemeManager` supports observer callbacks for theme-change events, allowing panels to refresh their appearance without polling:

```python
theme_manager.on_theme_changed(self._apply_theme)
```

### Theme Structure

```
app/services/
├── theme_manager.py      # ThemeManager singleton (canonical location)
└── theme_store.py        # Persist custom themes to ~/.spice-gui/themes/

app/GUI/styles/
├── __init__.py           # Exports theme_manager + constants
├── theme.py              # ThemeProtocol interface + BaseTheme
├── light_theme.py        # LightTheme
├── dark_theme.py         # DarkTheme
├── custom_theme.py       # CustomTheme (user-defined overrides)
├── constants.py          # GRID_SIZE, CANVAS_SIZE, z-order values
└── font_loader.py        # Registers JetBrains Mono and OpenDyslexic with Qt
```

## Wire Routing

The IDA* algorithm routes wires around component obstacles on a 10 px grid. It lives in `app/algorithms/path_finding.py` and has no Qt dependency:

```python
# app/algorithms/path_finding.py
class IDAStarPathfinder(WeightedPathfinder):
    def find_path(
        self,
        start: tuple,
        end: tuple,
        obstacles: list,
        existing_wires: list,
        grid_size: int = 10,
    ) -> tuple[list[tuple], float, int]:
        """
        Returns (waypoints, runtime_ms, iterations).
        Penalties applied for bends, component-body crossings,
        and wire-over-wire crossings.
        """
```

Node graph operations (merging nodes when wires connect, splitting when wires are deleted) live in `app/algorithms/graph_ops.py`.

## Scripting API

SDM Spice exposes a headless Python API for use in scripts and Jupyter notebooks. No GUI is required.

```python
from scripting.circuit import Circuit

# Load an existing circuit file
c = Circuit.load("my_circuit.json")

# Or build one programmatically
c = Circuit()
r1 = c.add_component("Resistor", x=100, y=100)
v1 = c.add_component("VoltageSource", x=200, y=100)
c.update_value(r1, "1k")
c.update_value(v1, "5")
c.add_wire(v1, 0, r1, 0)

c.set_analysis("op")
result = c.simulate()
print(result.data)

# In Jupyter, display as SVG inline
c  # calls c._repr_svg_()
```

## See Also

- [[Class Diagram]] - Full UML class diagram
- [[Technology Stack]] - Dependencies and versions
- [[Contributing]] - Development setup and conventions
- [[File Formats]] - Circuit file JSON structure