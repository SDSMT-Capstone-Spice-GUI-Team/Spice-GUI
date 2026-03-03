# Canvas Architecture

## Overview

The canvas is a three-layer Qt MVC system built on the standard `QGraphicsView → QGraphicsScene → QGraphicsItem` stack.

### The Three Layers

```
CircuitCanvasView (QGraphicsView)     ← primary interaction surface
    └── QGraphicsScene
            ├── ComponentGraphicsItem  (one per component)
            ├── WireGraphicsItem       (one per wire)
            │   └── WaypointHandle     (draggable interior waypoints)
            └── AnnotationItem         (free-form text labels)
```

**Model layer** (Qt-free, pure Python): `ComponentData`, `WireData`, `NodeData` in `app/models/`

**Controller** (`CircuitController`) sits between the view and model, owns the undo/redo command stack.

---

## Class Hierarchy

```
QGraphicsView
└── CircuitCanvasView                    app/GUI/circuit_canvas.py (~2266 lines)
    │
    └── QGraphicsScene (aggregated)
            │
            ├── ComponentGraphicsItem (QGraphicsItem)
            │   └── Subclasses: Resistor, Capacitor, Inductor, VoltageSource,
            │       CurrentSource, WaveformVoltageSource, Ground, OpAmp,
            │       VCVS, CCVS, VCCS, CCCS, BJTNPN, BJTPNP,
            │       MOSFETNMOS, MOSFETPMOS, VCSwitch, Diode, LEDComponent,
            │       ZenerDiode, Transformer
            │
            ├── WireGraphicsItem (QGraphicsPathItem)
            │   └── WaypointHandle (QGraphicsEllipseItem)
            │
            └── AnnotationItem (QGraphicsTextItem)
```

### Pathfinding Adapters (in `wire_item.py`)

```
_ComponentAdapter   — wraps ComponentGraphicsItem for pathfinding obstacle queries
_WireAdapter        — wraps WireGraphicsItem for pathfinding obstacle queries
```

### Rendering

```
ComponentRenderer (ABC)                  app/GUI/renderers.py (~585 lines)
├── IEEEResistor, IEEECapacitor, IEEEInductor, …
└── (IEC variants follow the same interface)
```

Each renderer implements `draw(painter, component)` and `get_obstacle_shape(component)`.

### Data Models (Qt-free)

```
ComponentData   component_id, component_type, value, position,
                rotation, flip_h, flip_v, waveform_type/params,
                initial_condition

WireData        start_component_id, start_terminal,
                end_component_id, end_terminal,
                waypoints, algorithm, runtime, iterations,
                routing_failed, locked

NodeData        terminals: set[(comp_id, term_idx)]
                wire_indices: set[int]
                is_ground: bool
                custom_label, auto_label
```

---

## Constants & Configuration

All tunables live in `app/GUI/styles/constants.py` (single source of truth).

| Constant | Value | Purpose |
|---|---|---|
| `GRID_SIZE` | 10 | Snap-to-grid unit (pixels) |
| `GRID_EXTENT` | 500 | Half the scene size (scene spans -500 to 500) |
| `MAJOR_GRID_INTERVAL` | 100 | Pixels between major (labeled) grid lines |
| `TERMINAL_CLICK_RADIUS` | 10 | Click hit-test radius for terminals |
| `TERMINAL_HOVER_RADIUS` | 15 | Hover detection radius for terminals |
| `WIRE_CLICK_WIDTH` | 10 | Clickable area width around wires |
| `DEFAULT_TERMINAL_PADDING` | 15 | Gap between component body edge and terminal |
| `WIRE_UPDATE_DELAY_MS` | 50 | Debounce delay before rerouting wires after drag |
| `ZOOM_FACTOR` | 1.15 | Multiplier per zoom step (15%) |
| `ZOOM_MIN` | 0.1 | Minimum zoom level (10%) |
| `ZOOM_MAX` | 5.0 | Maximum zoom level (500%) |
| `ZOOM_FIT_PADDING` | 50 | Pixels of padding when fitting to circuit |

---

## State Flow

### User Action → Model

```
User drags component
  → ComponentGraphicsItem.itemChange (snap to grid, debounce 50ms timer)
  → canvas.on_component_moved()
  → controller.push(MoveComponentCommand)
  → model updated
  → observer fires "component_moved"
```

### Model → Canvas

```
controller fires "component_moved"
  → canvas._on_model_changed("component_moved", data)
  → canvas._handle_component_moved(data)
  → graphics item position updated
  → wires scheduled for batch rerouting (QTimer(0) deferred to next event loop)
```

**Rule**: The canvas never mutates model state directly. All edits route through the controller.

---

## Observer Events (Controller → Canvas)

Canvas subscribes via `controller.add_observer(self._on_model_changed)`.

| Event | Handler | Effect |
|---|---|---|
| `component_added` | `_handle_component_added` | Create graphics item, add to scene |
| `component_removed` | `_handle_component_removed` | Remove from scene and dict |
| `component_moved` | `_handle_component_moved` | Update position, schedule batch reroute |
| `component_rotated` | `_handle_component_rotated` | Recalc terminals, reroute wires |
| `component_flipped` | `_handle_component_flipped` | Recalc terminals, reroute wires |
| `component_value_changed` | `_handle_component_value_changed` | Update label, clear stale OP results |
| `wire_added` | `_handle_wire_added` | Create item, route, add to scene |
| `wire_removed` | `_handle_wire_removed` | Remove from scene and list |
| `wire_routed` | `_handle_wire_routed` | Update waypoints, rebuild path |
| `wire_lock_changed` | `_handle_wire_lock_changed` | Update visual style (dotted vs solid) |
| `wire_reroute_requested` | `_handle_wire_reroute_requested` | Trigger pathfinding |
| `circuit_cleared` | `_handle_circuit_cleared` | Clear all items, reset counters |
| `nodes_rebuilt` | `_handle_nodes_rebuilt` | Sync node list from controller |
| `model_loaded` | `_handle_model_loaded` | Rebuild canvas from scratch |
| `annotation_added` | `_handle_annotation_added` | Create annotation item, add to scene |
| `annotation_removed` | `_handle_annotation_removed` | Remove annotation from scene |
| `annotation_updated` | `_handle_annotation_updated` | Update annotation text/style |

---

## Signals the Canvas Emits

```python
componentAdded = pyqtSignal(str)              # component_id
wireAdded = pyqtSignal(str, str)              # start_comp_id, end_comp_id
selectionChanged = pyqtSignal(object)         # selected component, list, or None
componentRightClicked = pyqtSignal(object, object)  # component, global position
canvasClicked = pyqtSignal()
zoomChanged = pyqtSignal(float)               # 1.0 = 100%
probeRequested = pyqtSignal(str, str)         # signal_name, "node"|"component"
statusMessage = pyqtSignal(str, int)          # message, timeout_ms (relay for scene items)
```

---

## Key Responsibilities by Concern

| Concern | Methods |
|---|---|
| Observer routing | `_on_model_changed` → `_handle_*` dispatch table |
| Wire drawing mode | `mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent` (state machine) |
| Drag-drop from palette | `dragEnterEvent`, `dragMoveEvent`, `dropEvent` |
| Editing operations | `delete_selected`, `rotate_selected`, `flip_selected`, `paste_components` |
| Zoom / pan | `zoom_fit`, `zoom_in/out`, `zoom_reset`, `_apply_zoom` |
| Simulation display | `set_node_voltages`, `set_op_results`, probe mode |
| Serialization | `to_dict`, `from_dict`, `export_image` |
| Rendering overlays | `drawForeground` — node labels, OP voltages, branch currents, probe results |
| Grid | `draw_grid` (deferred to first `showEvent`), `refresh_theme` |
| Selection | `select_all`, `clear_selection`, `get_selected_component_ids`, rubber-band selection |
| Context menus | Right-click component/wire/empty space/terminal |
| Clipboard | `copy_selected_components`, `cut_selected_components`, `paste_components` |

---

## Z-Order (Rendering Layers)

| Z-value | Items |
|---|---|
| -1 | Grid labels (axis labels along edges) |
| 0 | Grid lines, `ComponentGraphicsItem` |
| 1 | `WireGraphicsItem` (above components) |
| 50 | Obstacle boundary visualization (debug) |
| 90 | `AnnotationItem` |
| 100 | Temp wire preview line, terminal markers (debug) |
| 101 | Waypoint markers (wire-in-progress) |
| 200 | `WaypointHandle` (topmost interactive element) |
| 1000 | Legend overlays (debug obstacle visualization) |
| overlay | `drawForeground`: node labels, OP voltages, branch currents, probe results |

---

## Wire Routing System

### Pathfinding

Wires are routed using `IDAStarPathfinder` (imported lazily for fast startup). The pathfinder receives obstacle polygons built from component shapes and existing wire paths via the `_ComponentAdapter` and `_WireAdapter` helpers.

### Debounced Batch Rerouting

During group drag, multiple components may move simultaneously. To avoid redundant pathfinding:

1. `_handle_component_moved` collects components into `_pending_reroute_components`
2. A `QTimer(0)` schedules `_do_batch_reroute` on the next event loop tick
3. Batch reroute collects all unique wires connected to pending components
4. Each wire's `update_position()` runs once, then the pending set is cleared

### Locked Wires

- User drags a `WaypointHandle` → on release, `model.locked = True`
- Locked wires skip auto-rerouting on component moves
- Visual style: dotted line
- Context menu: Unlock to re-enable auto-routing

### Failed Routing

- If pathfinding exceeds max iterations → fallback to straight line
- `model.routing_failed = True`, wire displayed in red dashed style
- Status message emitted via `statusMessage` signal

### Wire Drawing State Machine

1. Click terminal → set `wire_start_comp`/`wire_start_term`, show temp preview line (z=100), cursor → CrossCursor
2. Move mouse → temp line follows cursor (or last waypoint)
3. Click empty space → waypoint added to `_wire_waypoints`, visual marker at z=101
4. Click terminal → wire created via controller, temp line/markers cleaned up, cursor reset
5. ESC → cancel and clean up

---

## Component Interaction

### Drag & Movement

- Components snap to `GRID_SIZE` during drag via `itemChange()`
- Group dragging supported via `_group_moving` flag
- Position changes are debounced (50ms timer) to avoid excessive wire rerouting
- Drag-start positions recorded for undo (`_drag_start_positions`)

### Terminal System

- Each component defines base terminal positions via `ComponentData.get_base_terminal_positions()`
- Terminals are transformed: flip (negate x/y) → rotate (apply angle) → scene position
- Terminal padding (`DEFAULT_TERMINAL_PADDING = 15`) anchors terminals to the component body edge
- Terminal geometry is per-component-type (e.g., Op-Amp has 3 terminals at custom positions)

### Component State

```python
_locked: bool                    # Non-editable (disables selection/movement)
_hovered: bool                   # Hover visual feedback
_grading_state: str              # "passed", "failed", or None
_grading_feedback: str           # Tooltip for grading
is_being_dragged: bool           # Drag tracking
_drag_start_positions: dict      # For undo
_pending_position: QPointF       # Debounced position
```

---

## Rendering & Themes

### Renderer Strategy

Renderers follow the Strategy pattern. A registry maps `(component_type, symbol_style)` to a `ComponentRenderer` subclass. Each renderer implements:
- `draw(painter, component)` — draw the component symbol
- `get_obstacle_shape(component)` — return polygon for pathfinding avoidance

Symbol styles: IEEE (default), IEC (same interface).

### Theme Integration

The `theme_manager` singleton provides all style values:

```python
theme_manager.color(key) → QColor
theme_manager.pen(key) → QPen
theme_manager.brush(key) → QBrush
theme_manager.font(key) → QFont
theme_manager.get_component_color(component_type) → QColor
theme_manager.symbol_style → "IEEE" | "IEC"
```

Key style keys: `grid_minor`, `grid_major`, `wire_default`, `wire_selected`, `wire_preview`, `terminal`, `terminal_fill`, `component_selected`, `node_label_*`, `op_voltage`, `probe_*`.

### Foreground Overlays (`drawForeground`)

Drawn after all scene items, in order:
1. Node labels (if `show_node_labels`)
2. OP voltage annotations (if `show_op_annotations` + `node_voltages`)
3. Branch current annotations
4. Probe results (topmost)

### Display Toggles

```python
show_component_labels: bool     # Component IDs (R1, V1)
show_component_values: bool     # Values (1k, 5V)
show_node_labels: bool          # Node names (nodeA, nodeB)
show_obstacle_boundaries: bool  # Debug visualization
show_op_annotations: bool       # Voltage display
show_node_voltages: bool        # OP results
probe_mode: bool                # Probe tool active
```

---

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `app/GUI/circuit_canvas.py` | ~2266 | Main view: events, editing, serialization, overlays |
| `app/GUI/component_item.py` | ~872 | Component rendering, drag, terminal detection |
| `app/GUI/wire_item.py` | ~524 | Wire routing, waypoint handles, pathfinding adapters |
| `app/GUI/annotation_item.py` | ~72 | Free-form text labels |
| `app/GUI/renderers.py` | ~585 | Component symbol renderers (IEEE/IEC), obstacle shapes |
| `app/GUI/styles/constants.py` | ~79 | Grid, zoom, terminal, and layout constants |
| `app/models/component.py` | — | `ComponentData`, `COMPONENT_TYPES`, `SPICE_SYMBOLS`, `TERMINAL_COUNTS` |
| `app/models/wire.py` | ~96 | `WireData` |
| `app/models/node.py` | — | `NodeData`, node label generator |

---

## Design Patterns

- **Observer Pattern** — canvas subscribes to controller events for model→view sync
- **Command Pattern** — all edits push commands onto the undo/redo stack
- **Factory Pattern** — `COMPONENT_CLASSES` registry for polymorphic item creation
- **Strategy Pattern** — `ComponentRenderer` subclasses for IEEE/IEC symbol styles
- **Adapter Pattern** — `_ComponentAdapter`/`_WireAdapter` wrap Qt objects for pathfinding; `QPointF` ↔ tuples
- **Singleton** — `theme_manager` instance for global styling
- **Deferred Rendering** — grid drawn on first `showEvent()`, debug overlays in `drawForeground()`
- **Debouncing** — batched wire rerouting during group drags via `QTimer(0)`

---

## Performance Considerations

1. **Viewport Update Mode** — `MinimalViewportUpdate` avoids full scene redraws
2. **Targeted Updates** — `scene.update(old_rect)` + `scene.update(new_rect)` on item change
3. **Deferred Grid** — drawn on first `showEvent()`, not in `__init__()`
4. **Debounced Rerouting** — batch multiple wire updates into a single pass
5. **Lazy Imports** — pathfinding module loaded only when first wire is created
6. **Timer Reuse** — single `_position_update_timer` per component (no QTimer churn)
7. **Wireframe Preview** — straight-line drag preview instead of full pathfinding during drag