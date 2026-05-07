# Architecture and Design Document — SDM Spice

**Last Updated:** 2026-05-06
**Audience:** Developers, technical reviewers

---

## 1. System Overview

SDM Spice is a local-first PyQt6 desktop application for circuit design and SPICE simulation. There are no user accounts, no cloud services, and no server-side logic — all data lives on the user's filesystem. See [ADR 004](../adr/004-local-first-no-user-accounts.md) for the rationale.

```
┌──────────────────────────────────────────────────────────────┐
│              User's Machine (Windows / macOS / Linux)        │
│                                                              │
│   ┌──────────────────────┐     ┌───────────────────────┐    │
│   │   SDM Spice (PyQt6)  │────▶│  ngspice (external)   │    │
│   │   app/               │◀────│  subprocess            │    │
│   └──────────────────────┘     └───────────────────────┘    │
│             │                                                │
│             ▼                                                │
│   ┌──────────────────────┐                                   │
│   │  Filesystem           │                                  │
│   │  circuits/*.json      │                                  │
│   │  exports/             │                                  │
│   └──────────────────────┘                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. MVC Architecture

The codebase follows a strict **Model-View-Controller** pattern with one hard rule: **no PyQt6 imports in models or controllers**. This keeps business logic testable without a display server. See [ADR 001](../adr/001-mvc-testability.md) and [ADR 005](../adr/005-mvc-architecture-zero-qt-dependencies.md).

```
┌─────────────────────────────────────────────────────────┐
│                  GUI Layer (PyQt6)                       │
│  MainWindow, CircuitCanvasView, Dialogs, Panels         │
│  ─ renders model state                                  │
│  ─ sends user actions to controllers                    │
└──────────────────────┬──────────────────────────────────┘
                       │ calls / observes
┌──────────────────────▼──────────────────────────────────┐
│             Controllers (pure Python, no Qt)            │
│  CircuitController, SimulationController,               │
│  FileController, UndoManager                            │
│  ─ modifies models                                      │
│  ─ broadcasts events to registered observer callbacks   │
└──────────────────────┬──────────────────────────────────┘
                       │ reads / writes
┌──────────────────────▼──────────────────────────────────┐
│               Models (pure Python, no Qt)               │
│  CircuitModel, ComponentData, WireData, NodeData        │
│  ─ single source of truth                               │
│  ─ pure data, no behavior beyond serialization          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Observer Pattern

Controllers use a **callback-based** observer system — not Qt signals — so the business logic has no Qt dependency:

```
User interaction → View captures event
  → Controller.method() is called
    → Controller mutates the Model
      → Controller._notify("event_name", data)
        → All registered observer callbacks fire
          → Views re-render from current model state
```

The view registers itself with the controller at startup:

```python
# GUI/circuit_canvas.py
self.controller.add_observer(self._on_circuit_changed)

def _on_circuit_changed(self, event_name: str, data: dict) -> None:
    if event_name == "component_added":
        self._add_component_item(data["component"])
    ...
```

---

## 4. Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| **MVC** | `models/`, `controllers/`, `GUI/` | Separation of concerns; testable business logic |
| **Observer** | `CircuitController._notify()` | Decoupled view updates without Qt signals |
| **Command** | `controllers/commands.py`, `undo_manager.py` | Undo/redo support |
| **Strategy** | `algorithms/path_finding.py` | Swappable IDA* / A* pathfinding algorithms |
| **Singleton** | `services/theme_manager.py` | Global theme access across all widgets |
| **Protocol** | `protocols/` | Type-safe interfaces that decouple layers without inheritance |
| **Mixin** | `GUI/main_window_*.py` | `MainWindow` is composed of 8 focused mixin classes |

---

## 5. Protocol Interfaces

`app/protocols/` defines structural interfaces (using `typing.Protocol`) that decouple the controller and service layers from concrete Qt implementations. This makes the codebase replaceable — a headless frontend, a web frontend, or a test double can satisfy the same protocols without inheriting from Qt.

| Protocol | Defines |
|----------|---------|
| `ApplicationShellProtocol` | Main window interface (dialogs, status bar, menus) |
| `CanvasProtocol` | Canvas observer registration and redraw |
| `ComponentPaletteProtocol` | Palette profile switching, icon regeneration |
| `PropertiesPanelProtocol` | Display selected component properties |
| `ResultsDisplayProtocol` | Show simulation results |
| `DialogsProtocol` | Unified dialog provider |
| `ObserverEvent` | Constants for event names |

---

## 6. Directory Structure

```
Spice-GUI/
│
├── app/                            ← Main application package
│   ├── main.py                     ← Entry point
│   ├── cli.py                      ← CLI for batch/headless operations
│   │
│   ├── models/                     ← Data layer (pure Python, no Qt)
│   │   ├── circuit.py              ←   CircuitModel — single source of truth
│   │   ├── component.py            ←   ComponentData + SPICE_SYMBOLS registry
│   │   ├── wire.py                 ←   WireData
│   │   ├── node.py                 ←   NodeData + NodeLabelGenerator
│   │   ├── annotation.py           ←   Canvas annotations
│   │   ├── clipboard.py            ←   Copy/paste data
│   │   ├── assignment.py           ←   Assignment/grading model
│   │   ├── template.py             ←   Circuit templates
│   │   ├── grading_session.py      ←   Grading state
│   │   ├── subcircuit_library.py   ←   Subcircuit definitions
│   │   └── circuit_schema_validator.py
│   │
│   ├── controllers/                ← Business logic (pure Python, no Qt)
│   │   ├── circuit_controller.py   ←   Component/wire CRUD + observer
│   │   ├── simulation_controller.py←   Simulation pipeline
│   │   ├── file_controller.py      ←   File I/O + session persistence
│   │   ├── commands.py             ←   Command pattern (undo/redo)
│   │   ├── undo_manager.py         ←   Undo/redo stack
│   │   ├── keybindings.py          ←   Keyboard shortcut registry
│   │   ├── theme_controller.py     ←   Theme switching logic
│   │   ├── settings_service.py     ←   QSettings bridge
│   │   ├── template_controller.py  ←   Template operations
│   │   ├── template_manager.py     ←   Template file management
│   │   ├── assignment_controller.py←   Assignment management
│   │   └── recent_exports.py       ←   Recent file tracking
│   │
│   ├── GUI/                        ← PyQt6 views
│   │   ├── main_window.py          ←   MainWindow + 8 mixin files
│   │   ├── circuit_canvas.py       ←   CircuitCanvasView (QGraphicsView)
│   │   ├── component_item.py       ←   ComponentGraphicsItem (QGraphicsItem)
│   │   ├── wire_item.py            ←   Wire rendering
│   │   ├── component_palette.py    ←   Draggable component source
│   │   ├── properties_panel.py     ←   Component property editor
│   │   ├── results_panel.py        ←   Simulation results display
│   │   ├── styles/                 ←   Theming system
│   │   │   ├── theme.py            ←     Abstract theme interface
│   │   │   ├── dark_theme.py / light_theme.py
│   │   │   ├── dark_theme.qss / light_theme.qss
│   │   │   ├── custom_theme.py     ←     User-defined theme
│   │   │   ├── font_loader.py      ←     Bundled font loading
│   │   │   └── constants.py        ←     Grid size (10px), canvas size
│   │   └── ... (20+ dialog files)
│   │
│   ├── simulation/                 ← SPICE pipeline (pure Python, no Qt)
│   │   ├── netlist_generator.py    ←   CircuitModel → SPICE netlist
│   │   ├── ngspice_runner.py       ←   Run ngspice subprocess
│   │   ├── ngspice_config.py       ←   Binary location resolution
│   │   ├── result_parser.py        ←   Parse ngspice output
│   │   ├── circuit_semantic_validator.py ← Pre-simulation checks
│   │   ├── csv_exporter.py / excel_exporter.py
│   │   ├── markdown_exporter.py    ←   Markdown circuit reports
│   │   ├── asc_exporter.py / asc_parser.py ← LTSpice format
│   │   ├── circuitikz_exporter.py / circuitikz_parser.py ← LaTeX
│   │   ├── netlist_parser.py       ←   Import SPICE netlists
│   │   ├── svg_shareable.py        ←   Embed/extract circuit data in SVG
│   │   ├── bom_exporter.py         ←   Bill of materials
│   │   ├── bundle_exporter.py      ←   ZIP with all artifacts
│   │   ├── fft_analysis.py         ←   FFT computation
│   │   ├── monte_carlo.py          ←   Monte Carlo simulation
│   │   ├── power_calculator.py / power_metrics.py
│   │   ├── freq_markers.py         ←   Bode plot markers
│   │   ├── convergence.py          ←   Convergence checking
│   │   └── measurement_builder.py  ←   Custom SPICE .meas directives
│   │
│   ├── grading/                    ← Educational auto-grading (no Qt)
│   │   ├── grader.py               ←   Main grading engine
│   │   ├── rubric.py               ←   Rubric data structure
│   │   ├── rubric_generator.py     ←   Auto-generate from reference circuit
│   │   ├── rubric_validator.py     ←   Validate rubric structure
│   │   ├── circuit_comparer.py     ←   Match components/wires between circuits
│   │   ├── component_mapper.py     ←   Map student → reference components
│   │   ├── batch_grader.py         ←   Grade multiple submissions
│   │   ├── feedback_exporter.py    ←   Student-facing feedback
│   │   ├── grade_exporter.py       ←   Grade data export
│   │   ├── check_analytics.py      ←   Complexity and quality metrics
│   │   ├── histogram.py            ←   Grade distribution histograms
│   │   └── session_persistence.py  ←   Persist grading session state
│   │
│   ├── algorithms/                 ← Graph algorithms (no Qt)
│   │   ├── path_finding.py         ←   IDA* wire routing (~850 lines)
│   │   └── graph_ops.py            ←   Node graph operations
│   │
│   ├── scripting/                  ← Headless API (no Qt)
│   │   ├── circuit.py              ←   Programmatic circuit creation
│   │   └── jupyter.py              ←   Jupyter notebook integration
│   │
│   ├── services/                   ← Cross-cutting services
│   │   ├── theme_manager.py        ←   Theme singleton
│   │   ├── theme_store.py          ←   Persisted theme preferences
│   │   ├── palette_profiles.py     ←   Course-specific palette filtering
│   │   └── report_generator.py     ←   Report creation
│   │
│   ├── protocols/                  ← Type contracts (no Qt)
│   │   └── application.py, canvas.py, dialogs.py, events.py, palette.py, properties.py, results.py
│   │
│   ├── utils/                      ← Shared utilities (no Qt)
│   │   ├── format_utils.py         ←   SI unit parsing (1k → 1000)
│   │   ├── connectivity.py         ←   Wire connectivity helpers
│   │   ├── atomic_write.py         ←   Crash-safe file writes
│   │   ├── drag_drop_router.py     ←   Drag-and-drop MIME routing
│   │   └── constants.py            ←   Global constants
│   │
│   ├── tests/                      ← Test suite
│   │   ├── unit/                   ←   186 unit test files
│   │   └── integration/            ←   3 integration test files
│   │
│   ├── templates/                  ← 7 built-in circuit templates (JSON)
│   └── examples/                   ← Example circuit files
│
├── data/                           ← Example circuits (JSON)
├── Doc/                            ← All documentation
├── wiki/                           ← User-facing documentation
├── scripts/                        ← Build/dev scripts
├── Makefile
├── pyproject.toml                  ← Pytest configuration
├── ruff.toml                       ← Linter configuration
└── .pre-commit-config.yaml
```

---

## 7. Key Classes

### CircuitModel (`models/circuit.py`)
Single source of truth for all circuit data. Serializes to/from JSON.

```python
CircuitModel
├── components: dict[str, ComponentData]   # keyed by ID ("R1", "V1", etc.)
├── wires: list[WireData]
├── nodes: list[NodeData]
├── terminal_to_node: dict
├── analysis_type: str
├── analysis_params: dict
├── annotations: list[AnnotationData]
├── to_dict() → dict
└── from_dict(d) → CircuitModel
```

### CircuitController (`controllers/circuit_controller.py`)
Primary controller. All mutations go through here; the undo/redo stack and observer callbacks are managed here.

```python
CircuitController
├── model: CircuitModel
├── undo_manager: UndoManager
├── add_component(type, pos) → ComponentData
├── remove_component(id)
├── add_wire(start, end) → WireData
├── remove_wire(index)
├── cut(), copy(), paste()
├── route_wire(), toggle_wire_lock()
├── add_annotation(), remove_annotation()
├── lock_component(), unlock_component()
├── add_observer(callback)
└── _notify(event_name, data)
```

### SimulationController (`controllers/simulation_controller.py`)
Orchestrates the full simulation pipeline: validate → generate netlist → run ngspice → parse results. Also handles parameter sweeps and Monte Carlo.

### FileController (`controllers/file_controller.py`)
Handles save/load, autosave, session recovery, and recent files. Uses `atomic_write_text` from `utils/atomic_write.py` for crash-safe writes.

### UndoManager + Commands (`controllers/undo_manager.py`, `commands.py`)
Command pattern. Every mutating action creates a `Command` object (e.g., `AddComponentCommand`, `RemoveWireCommand`, `CutCommand`, `LockComponentCommand`) that can be undone/redone.

### CircuitCanvasView (`GUI/circuit_canvas.py`)
A `QGraphicsView` + `QGraphicsScene` composite that renders the circuit, handles drag-and-drop from the palette, wire drawing, zoom, and grid rendering.

### MainWindow (`GUI/main_window.py`)
Assembled from 8 mixins to keep it maintainable:

| Mixin | File | Responsibility |
|-------|------|----------------|
| `MenuBarMixin` | `main_window_menus.py` | All menu construction |
| `FileOperationsMixin` | `main_window_file_ops.py` | Open, save, import, export |
| `SimulationMixin` | `main_window_simulation.py` | Run/stop simulation, results |
| `AnalysisSettingsMixin` | `main_window_analysis.py` | Analysis type configuration |
| `ViewOperationsMixin` | `main_window_view.py` | Zoom, theme, annotations |
| `PrintExportMixin` | `main_window_print.py` | Print preview, export |
| `HelpMixin` | `main_window_help.py` | About, documentation links |
| `SettingsMixin` | `main_window_settings.py` | Preferences, keybindings |

### ThemeManager (`services/theme_manager.py`)
Singleton. Owns the active theme object, current symbol style (IEEE/IEC), and font selection. All widgets that need color or font values call through `ThemeManager` — no hardcoded colors anywhere in the codebase.

---

## 8. Simulation Pipeline

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│ CircuitModel │────▶│ NetlistGenerator │────▶│ SPICE Netlist │
│ (in memory)  │     │                  │     │ (text string) │
└──────────────┘     └──────────────────┘     └──────┬────────┘
                                                     │
                     ┌──────────────────┐            │
                     │  NgspiceRunner   │◀───────────┘
                     │  (subprocess)    │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐     ┌──────────────────┐
                     │  ngspice output  │────▶│  ResultParser    │
                     │  (stdout/files)  │     │                  │
                     └──────────────────┘     └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │ SimulationResult │
                                              │ (structured data)│
                                              └──────────────────┘
```

### Pipeline Steps

1. **Validation** — `CircuitSemanticValidator` checks for ground, reachable nodes, required sources.
2. **Netlist generation** — `NetlistGenerator.generate()` walks `CircuitModel` and emits SPICE syntax.
3. **Execution** — `NgspiceRunner` writes a temp file, runs `ngspice -b <file>` as a subprocess, captures stdout.
4. **Parsing** — `ResultParser` extracts node voltages, branch currents, and measurements into a `SimulationResult`.

### Supported Analysis Types

| Analysis | SPICE Directive | What It Computes |
|----------|----------------|-----------------|
| DC Operating Point | `.op` | Steady-state voltages and currents |
| DC Sweep | `.dc` | Sweep a source, plot response |
| AC Sweep | `.ac` | Frequency response (magnitude + phase) |
| Transient | `.tran` | Time-domain waveforms |
| Temperature Sweep | `.temp` | Response over temperature range |
| Noise | `.noise` | Noise spectral density |
| Sensitivity | `.sens` | Sensitivity to component values |
| Transfer Function | `.tf` | DC gain, input/output impedance |
| Pole-Zero | `.pz` | Stability poles and zeros |

Advanced: **Parameter Sweep**, **Monte Carlo**, **FFT Analysis**, **Power Metrics**, **Convergence Check**, **Custom Measurements**.

---

## 9. File Format

Circuits are stored as JSON. The schema is versioned (`schema_version v1`) and validated by `CircuitSchemaValidator`. See [ADR 006](../adr/006-json-circuit-file-format.md).

```json
{
  "schema_version": "v1",
  "components": [
    { "id": "R1", "type": "Resistor", "value": "1k", "position": [100, 200], "rotation": 0 }
  ],
  "wires": [
    { "id": "W1", "start_component": "R1", "start_terminal": 0, "end_component": "V1", "end_terminal": 1, "path": [[100, 180], [100, 120]] }
  ],
  "nodes": [],
  "analysis_type": "DC Operating Point",
  "analysis_params": {}
}
```

---

## 10. Wire Routing

`app/algorithms/path_finding.py` (~850 lines) implements an **IDA\*** (Iterative Deepening A*) pathfinder with a grid-aligned 10px snap. It routes wires around placed components without penetrating their bounding boxes. See [ADR 011](../adr/011-grid-aligned-layout-10px.md).

---

## 11. Theming System

- `GUI/styles/theme.py` — abstract interface
- `GUI/styles/dark_theme.py` / `light_theme.py` — color maps
- `GUI/styles/dark_theme.qss` / `light_theme.qss` — Qt stylesheets
- `services/theme_manager.py` — singleton access point; exposes `color_hex(key)`, `font()`, `symbol_style`
- `services/theme_store.py` — persists theme preferences across sessions
- `GUI/styles/font_loader.py` — loads bundled OpenDyslexic and JetBrains Mono fonts at startup

**Symbol styles:** IEEE (American) and IEC (European). Switching redraws all component icons in the palette in real-time.

---

## 12. Scripting API

`app/scripting/circuit.py` exposes a headless `Circuit` class for programmatic use:

```python
from scripting.circuit import Circuit

c = Circuit()
c.add_component("Resistor", value="1k", position=(100, 100))
c.add_component("VoltageSource", value="5", position=(100, 200))
c.connect("V1", 0, "R1", 0)
result = c.run_dc_op()
print(result.node_voltages)
```

`app/scripting/jupyter.py` adds inline rendering for Jupyter notebooks.

---

## 13. Architecture Decision Records

All significant architectural decisions are recorded in `Doc/adr/`. Key ADRs:

| ADR | Decision |
|-----|----------|
| [001](../adr/001-mvc-testability.md) | MVC for testability — models and controllers must be Qt-free |
| [002](../adr/002-tiered-testing.md) | Tiered testing: unit → snapshot → widget → structural → human |
| [003](../adr/003-branching-strategy.md) | develop + main + issue-NNN-* branch naming |
| [004](../adr/004-local-first-no-user-accounts.md) | Local-first, no user accounts |
| [005](../adr/005-mvc-architecture-zero-qt-dependencies.md) | Zero Qt in core logic |
| [006](../adr/006-json-circuit-file-format.md) | JSON circuit file format (schema_version v1) |
| [007](../adr/007-ngspice-external-simulation-engine.md) | ngspice as external engine |
| [008](../adr/008-pyqt6-desktop-framework.md) | PyQt6 as the GUI framework |
| [009](../adr/009-pytest-github-actions-testing.md) | pytest + GitHub Actions CI |
| [010](../adr/010-ruff-linting-code-quality.md) | Ruff + black + isort + bandit |
| [011](../adr/011-grid-aligned-layout-10px.md) | 10px grid snap |

---

## 14. Invariants to Preserve

These are the rules that the entire test suite and tooling depend on. Breaking them requires an ADR update and significant rework.

1. **No Qt in models or controllers.** Check with `grep -r "PyQt6\|PySide" app/models/ app/controllers/`.
2. **No hardcoded colors.** All colors go through `ThemeManager`.
3. **Every mutation goes through a Command** so undo/redo works.
4. **Components snap to the 10px grid.** Grid size is in `GUI/styles/constants.py`.
5. **File writes use `atomic_write_text`.** Never write directly to the target path.