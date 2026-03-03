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

### Data Models (Qt-free)

```
ComponentData   component_id, component_type, value, position,
                rotation, flip_h, flip_v, waveform_type/params,
                initial_condition

WireData        start_component_id, start_terminal,
                end_component_id, end_terminal,
                waypoints, algorithm, routing_failed, locked

NodeData        terminals: set[(comp_id, term_idx)]
                wire_indices: set[int]
                is_ground: bool
                custom_label, auto_label
```

---

## State Flow

### User Action → Model

```
User drags component
  → ComponentGraphicsItem.mouseReleaseEvent
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
  → wires scheduled for batch rerouting
```

**Rule**: The canvas never mutates model state directly. All edits route through the controller.

---

## Observer Events (Controller → Canvas)

Canvas subscribes via `controller.add_observer(self._on_model_changed)`.

| Event | Handler | Effect |
|---|---|---|
| `component_added` | `_handle_component_added` | Create graphics item, add to scene |
| `component_removed` | `_handle_component_removed` | Remove from scene and dict |
| `component_moved` | `_handle_component_moved` | Update position, schedule reroute |
| `component_rotated` | `_handle_component_rotated` | Recalc terminals, reroute wires |
| `component_flipped` | `_handle_component_flipped` | Recalc terminals |
| `component_value_changed` | `_handle_component_value_changed` | Update label, clear stale OP results |
| `wire_added` | `_handle_wire_added` | Create item, route, add to scene |
| `wire_removed` | `_handle_wire_removed` | Remove from scene and list |
| `wire_routed` | `_handle_wire_routed` | Update waypoints, rebuild path |
| `wire_lock_changed` | `_handle_wire_lock_changed` | Update visual style (dotted vs solid) |
| `wire_reroute_requested` | `_handle_wire_reroute_requested` | Trigger pathfinding |
| `circuit_cleared` | `_handle_circuit_cleared` | Clear all items, reset counters |
| `nodes_rebuilt` | `_handle_nodes_rebuilt` | Sync node list from controller |
| `model_loaded` | `_handle_model_loaded` | Rebuild canvas from scratch |
| `annotation_added/removed/updated` | `_handle_annotation_*` | Sync annotation items |

---

## Signals the Canvas Emits

```python
componentAdded = pyqtSignal(str)              # component_id
wireAdded = pyqtSignal(str, str)              # start_comp_id, end_comp_id
selectionChanged = pyqtSignal(object)         # selected component or None
componentRightClicked = pyqtSignal(object, object)  # component, global position
canvasClicked = pyqtSignal()
zoomChanged = pyqtSignal(float)               # 1.0 = 100%
probeRequested = pyqtSignal(str, str)         # signal_name, "node"|"component"
statusMessage = pyqtSignal(str, int)          # message, timeout_ms
```

---

## Key Responsibilities by Concern

| Concern | Methods |
|---|---|
| Observer routing | `_on_model_changed` → `_handle_*` handlers |
| Wire drawing mode | `mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent` |
| Drag-drop from palette | `dragEnterEvent`, `dragMoveEvent`, `dropEvent` |
| Editing operations | `delete_selected`, `rotate_selected`, `flip_selected`, `paste_components` |
| Zoom / pan | `zoom_fit`, `zoom_in/out`, `zoom_reset` |
| Simulation display | `set_node_voltages`, `set_op_results`, probe mode |
| Serialization | `to_dict`, `from_dict`, `export_image` |
| Rendering overlays | `drawForeground` — node labels, voltages, debug markers |
| Grid | `draw_grid`, `refresh_theme` |
| Selection | `select_all`, `clear_selection`, `get_selected_component_ids` |

---

## Z-Order (Rendering Layers)

| Z-value | Items |
|---|---|
| 0 | Grid lines, ComponentGraphicsItem |
| 1 | WireGraphicsItem (above components) |
| 90 | AnnotationItem |
| 200 | WaypointHandle (topmost for dragging) |
| overlay | `drawForeground`: node labels, voltages, probe results, debug markers |

---

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `app/GUI/circuit_canvas.py` | ~2266 | Main view: events, editing, serialization, overlays |
| `app/GUI/component_item.py` | ~873 | Component rendering, drag/drop, terminal detection |
| `app/GUI/wire_item.py` | ~525 | Wire routing, waypoint management, rendering |
| `app/GUI/annotation_item.py` | ~73 | Free-form text labels |
| `app/models/component.py` | — | `ComponentData`, `COMPONENT_TYPES`, `SPICE_SYMBOLS` |
| `app/models/wire.py` | — | `WireData` |
| `app/models/node.py` | — | `NodeData`, node label generator |

---

## Design Patterns

- **Observer Pattern** — canvas subscribes to controller events for model→view sync
- **Command Pattern** — all edits push commands onto the undo/redo stack
- **Factory Pattern** — `COMPONENT_CLASSES` registry for polymorphic item creation
- **Adapter Pattern** — Qt `QPointF` ↔ pure-Python tuples for pathfinding module
- **Deferred Rendering** — grid drawn on first `showEvent()`, debug overlays in `drawForeground()`

---

## Restricted View Considerations

When implementing a restricted (e.g. read-only or viewer) variant of the canvas, key decisions:

1. **Interaction** — override or suppress wire drawing mode and drag handlers
2. **Signals** — block `componentRightClicked` to suppress context menus
3. **Controller access** — pass a read-only proxy or reject write commands at the controller layer
4. **Probe mode** — likely still useful; keep `probeRequested` signal active
5. **Simulation display** — `set_node_voltages`, `set_op_results` almost certainly still needed
6. **Approach** — subclass `CircuitCanvasView` and override interaction handlers to no-ops, or add a `read_only: bool` mode flag checked at each interaction entry point
