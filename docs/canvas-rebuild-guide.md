# Canvas Rebuild Guide — Code-Along Plan

**Goal:** Rebuild the 5 canvas files from scratch to reduce bloat and produce
clean, well-documented code. Each phase is independently testable.

**Current state:** ~4,300 lines across 5 files.
**Target:** ~3,500 lines (−800, ~19% reduction) with better docs.

---

## Bloat Reduction Targets

| Area | Current | Savings | How |
|---|---|---|---|
| Renderer terminal-lead checks | 23 × `if scene()` blocks | ~70 lines | Base class draws leads; renderers draw body only |
| Renderer drawing helpers | Diamond, arrow, markers duplicated | ~40 lines | Shared `_draw_diamond()`, `_draw_polarity_marks()` |
| Obstacle shape boilerplate | 20 hand-typed tuples | ~30 lines | Default `_rect_obstacle(w, h)` helper |
| Component subclass boilerplate | 18 classes × 6 lines | ~60 lines | `_make_subclass()` factory for trivial subclasses |
| Ground custom `paint()` | Duplicates base class | ~35 lines | Base class handles label via `_format_label()` hook |
| Transformer custom draw/obstacle | Bypasses renderer system | ~25 lines | Add `IEEETransformer` renderer |
| `COMPONENT_CLASSES` registry | 35 lines of mappings | ~15 lines | Auto-build from subclasses' `type_name` |
| Path-building duplication (wire) | 3 identical path loops | ~12 lines | Single `_build_path()` helper |
| `mousePressEvent` (canvas) | 157-line method | ~30 lines | Extract `_handle_wire_click()`, `_handle_rubberband()` |
| Context menu (canvas) | 145-line method | ~20 lines | Extract `_ctx_component()`, `_ctx_wire()`, `_ctx_empty()` |
| `sys.path.insert` hacks | 2 files | ~4 lines | Remove (app/ is already on path) |
| **Total** | | **~340 lines** | |

---

## Files and Dependencies

```
renderers.py          ← no internal GUI deps (uses only PyQt6.QtGui, models)
annotation_item.py    ← no internal GUI deps (uses only styles.theme_manager)
component_item.py     ← imports renderers.py, styles
wire_item.py          ← imports styles, models.wire
circuit_canvas.py     ← imports all above + controller + models
```

**Unchanged files** (import but don't modify):
- `app/models/component.py`, `wire.py`, `node.py`, `annotation.py`
- `app/controllers/circuit_controller.py`, `commands.py`
- `app/algorithms/path_finding.py`
- `app/GUI/styles/constants.py`, `app/protocols/canvas.py`, `events.py`

---

## Phase 1 — Canvas Shell (~250 lines)

**File:** `circuit_canvas.py`

**What you build:** An empty `QGraphicsView` that the `MainWindow` can instantiate.
App launches, shows a grid, no crashes. No components, no wires.

### Checklist

- [ ] Class `CircuitCanvasView(QGraphicsView)` with all 8 `pyqtSignal` declarations
- [ ] `__init__(self, controller=None)`:
  - Store controller
  - Create `QGraphicsScene`, set scene rect from `GRID_EXTENT`
  - Configure antialiasing + `MinimalViewportUpdate`
  - Init empty data structures: `components = {}`, `wires = []`, `nodes = []`,
    `terminal_to_node = {}`, `annotations = []`, `component_counter`
  - Init display toggles: `show_component_labels/values`, `show_node_labels`,
    `show_node_voltages`, `show_op_annotations`
  - Init simulation dicts: `node_voltages = {}`, `branch_currents = {}`
  - Init probe state: `probe_mode = False`, `probe_results = []`
  - Init debug viz: `show_obstacle_boundaries = False`
  - Grid deferred flag: `_grid_drawn = False`, `_grid_items = []`
  - Batch reroute infra: `_pending_reroute_components = set()`, `_batch_reroute_timer = None`
  - Wire drawing state: `wire_start_comp/term = None`, `temp_wire_line = None`,
    `_wire_waypoints = []`, `_wire_waypoint_markers = []`
  - Rubber band state: `_rubber_band = None`, `_rubber_band_origin`
  - Clipboard: `_clipboard = ClipboardData()`
  - Enable drops, mouse tracking, context menu
  - Connect `scene.selectionChanged → on_selection_changed`
  - Register as observer: `controller.add_observer(self._on_model_changed)`
- [ ] `showEvent` — draw grid on first show
- [ ] `draw_grid()` — minor/major lines + axis labels (pens from `theme_manager`)
- [ ] `_on_model_changed(event, data)` — dict-based dispatcher with **no-op stubs** for
  all 17 event types listed in `protocols.events`; stale-OP clearing on
  circuit-modifying events
- [ ] `handle_observer_event` — alias for `_on_model_changed`
  (satisfies `CircuitCanvasProtocol`)
- [ ] Zoom — fully working (~60 lines):
  `zoom_in`, `zoom_out`, `zoom_fit`, `zoom_reset`, `set_default_zoom`,
  `get_zoom_level`, `_apply_zoom`
- [ ] Display-toggle setters (set bool + `scene.update()`):
  `set_show_component_labels`, `set_show_component_values`, `set_show_node_labels`
- [ ] Simulation result stubs (store dict, set flag, `scene.update()`):
  `set_node_voltages`, `clear_node_voltages`, `set_op_results`, `clear_op_results`,
  `display_node_voltages`, `hide_node_voltages`
- [ ] `refresh_theme()` — set background brush, redraw grid, update wire pens
- [ ] Protocol stubs: `clear_selection`, `select_components`,
  `get_selected_component_ids`, `on_selection_changed`, `export_image`
- [ ] `CircuitCanvas = CircuitCanvasView` alias at module bottom

### Verify

```
python -m app.main  # App launches, grid visible, zoom buttons work
pytest app/tests/ -x -q --timeout=10  # No import errors from the rest of the app
```

### Document

Write a module docstring explaining the canvas's role (observer, signals, data
ownership). Inline doc the `_on_model_changed` dispatch table.

---

## Phase 2 — Renderers & Static Components (~500 + 400 = 900 lines)

**Files:** `renderers.py` (full), `component_item.py` (base + subclasses)

### renderers.py — Bloat-reduced design

**Key change:** Renderers draw the *body only*. Terminal leads are drawn by the
base class in `ComponentGraphicsItem.paint()`. This eliminates 23 duplicated
`if component.scene() is not None:` blocks.

```python
class ComponentRenderer(ABC):
    @abstractmethod
    def draw_body(self, painter) -> None: ...

    @abstractmethod
    def get_obstacle_shape(self) -> list[tuple[float, float]]: ...
```

#### Shared helpers (module-level functions)

```python
def _draw_diamond(painter):
    """Draw the standard controlled-source diamond shape."""
    painter.drawLine(-15, 0, 0, -15)
    painter.drawLine(0, -15, 15, 0)
    painter.drawLine(15, 0, 0, 15)
    painter.drawLine(0, 15, -15, 0)

def _draw_polarity_marks(painter):
    """Draw +/- polarity markers for controlled sources."""
    ...

def _draw_control_arrow(painter):
    """Draw the small control-side arrow for CCVS/CCCS."""
    ...

def _rect_obstacle(half_w, half_h):
    """Return a rectangular obstacle polygon from half-width/height."""
    return [(-half_w, -half_h), (half_w, -half_h),
            (half_w, half_h), (-half_w, half_h)]
```

#### Checklist

- [ ] `ComponentRenderer` ABC with `draw_body(painter)` and `get_obstacle_shape()`
- [ ] `_registry`, `register()`, `get_renderer()` — same as before
- [ ] Shared helpers: `_draw_diamond`, `_draw_polarity_marks`, `_draw_control_arrow`,
  `_rect_obstacle`
- [ ] IEEE renderers (21 total — **include Transformer**):
  Resistor, Capacitor, Inductor, VoltageSource, CurrentSource,
  WaveformVoltageSource, Ground, OpAmp, VCVS, CCVS, VCCS, CCCS,
  BJTNPN, BJTPNP, MOSFETNMOS, MOSFETPMOS, VCSwitch, Diode, LED,
  ZenerDiode, **Transformer**
- [ ] IEC renderers: unique for Resistor, Capacitor, Inductor; delegates for rest
- [ ] All registered for both `"ieee"` and `"iec"` styles

### component_item.py — Bloat-reduced design

**Key changes:**
1. Base `paint()` draws terminal leads itself (the leads that renderers used to draw)
2. `_format_label()` hook so Ground can customize without overriding all of `paint()`
3. Trivial subclasses generated with `_make_subclass()`
4. `COMPONENT_CLASSES` auto-built from subclass `type_name`
5. Transformer uses the renderer (no custom `draw_component_body` / `get_obstacle_shape`)

```python
# Instead of 18 identical classes:
def _make_subclass(name, type_name, bounding=None):
    """Generate a trivial ComponentGraphicsItem subclass."""
    attrs = {"type_name": type_name}
    if bounding:
        attrs["boundingRect"] = lambda self, b=bounding: b
    cls = type(name, (ComponentGraphicsItem,), attrs)
    cls.__doc__ = f"{type_name} component"
    cls.__init__ = lambda self, cid, model=None: ComponentGraphicsItem.__init__(
        self, cid, type_name, model=model
    )
    return cls

Resistor = _make_subclass("Resistor", "Resistor")
Capacitor = _make_subclass("Capacitor", "Capacitor")
# ... etc.
```

#### Checklist

- [ ] `ComponentGraphicsItem(QGraphicsItem)` base:
  - Constructor: `(component_id, component_type, model=None)`
  - Flags: `ItemIsMovable`, `ItemIsSelectable`, `ItemSendsGeometryChanges`
  - `update_terminals()` — reads base positions from model, applies flip → rotate
  - `boundingRect()` → `QRectF(-40, -30, 80, 60)`
  - `paint()` — **draws terminal leads here**, then body via renderer, then labels
  - `_format_label()` → `f"{id} ({value})"` (override in Ground for `"GND (0V)"`)
  - `draw_component_body(painter)` → dispatches to `get_renderer()`
  - `get_terminal_pos(index)`, `get_obstacle_shape()`
  - `sync_from_data(component_data)`
  - `set_locked(locked)`
- [ ] Interaction (Phase 3 will wire these up, but define the methods now):
  - `mousePressEvent`, `mouseReleaseEvent`, `_commit_drag_to_undo()`
  - `itemChange` — grid snap + group drag + debounced controller update
  - `_schedule_controller_update()`, `_notify_controller_position()`
  - `hoverEnterEvent`, `hoverLeaveEvent`, `hoverMoveEvent`
  - `mouseDoubleClickEvent` — value-edit dialog
- [ ] Subclasses — use `_make_subclass()` for trivial ones, hand-write only:
  - `WaveformVoltageSource` (has extra `waveform_type`/`waveform_params` properties)
  - `Ground` (overrides `_format_label()`)
  - Manual `boundingRect` overrides for: OpAmp, VCVS, CCVS, VCCS, CCCS,
    BJTNPN, BJTPNP, VCSwitch, Transformer
- [ ] `COMPONENT_CLASSES` — auto-built from all subclasses
- [ ] `create_component(type, id)` factory
- [ ] `from_dict(data)` static method

### Canvas additions (circuit_canvas.py)

- [ ] `_handle_component_added(data)` — create item, add to scene, store in dict
- [ ] `_handle_component_removed(id)` — remove from scene and dict
- [ ] `_handle_model_loaded(data)` — clear, redraw grid, restore everything
- [ ] `_handle_circuit_cleared(data)` — clear scene, empty all dicts

### Verify

```
python -m app.main              # Load a saved .json circuit → components appear
pytest app/tests/unit/test_symbol_style.py -v
pytest app/tests/unit/test_grading_overlays.py -v
```

### Document

- Module docstring for `renderers.py` explaining the Strategy pattern and the
  terminal-lead split (base class draws leads, renderers draw bodies)
- Module docstring for `component_item.py` explaining data delegation to
  `ComponentData` and the `_make_subclass` factory

---

## Phase 3 — Component Interaction (~150 lines added to canvas)

**Files:** `component_item.py` (interaction methods), `circuit_canvas.py`

### component_item.py — already defined in Phase 2, but now test:

- [ ] Drag: `mousePressEvent` records `_drag_start_positions`
- [ ] Drop: `mouseReleaseEvent` → `_commit_drag_to_undo()` → `MoveComponentCommand`
- [ ] Grid snap: `itemChange(ItemPositionChange)` — snap + group peers
- [ ] Hover cursors: open hand / closed hand / arrow near terminals
- [ ] Double-click: value-edit dialog (skip for Ground, Op-Amp, Waveform Source)
- [ ] `set_locked(locked)` — disable movable/selectable flags

### circuit_canvas.py additions

- [ ] Drag-drop from palette: `dragEnterEvent`, `dragMoveEvent`, `dropEvent`
- [ ] `add_component_at_center(type)` — viewport center, grid snap
- [ ] `on_selection_changed()` — emit `selectionChanged` with single/multi/none
- [ ] `select_components(ids)`, `get_selected_component_ids()`
- [ ] `delete_selected()`, `delete_component()`, `rotate_component()`,
  `rotate_selected()`, `flip_component()`, `flip_selected()`
- [ ] Observer handlers: `_handle_component_moved/rotated/flipped/value_changed`
- [ ] Rubber-band selection: `mousePressEvent` on empty → `QRubberBand`;
  `mouseMoveEvent` resizes; `mouseReleaseEvent` selects enclosed items
- [ ] `keyPressEvent` — Escape deselects / cancels wire

**Bloat tip:** Extract `mousePressEvent` into private helpers:
```python
def mousePressEvent(self, event):
    if self.probe_mode: return self._handle_probe_click(event)
    if event.button() == LeftButton:
        if self._try_wire_click(event): return
        if self._try_rubberband(event): return
    super().mousePressEvent(event)
```

### Verify

```
# Manual: Drag from palette, grid snap, select, move, double-click edit,
#         delete, rotate/flip, rubber-band, undo/redo
pytest app/tests/unit/test_drag_undo.py -v
pytest app/tests/unit/test_grid_snap_group_drag.py -v
pytest app/tests/unit/test_multi_select.py -v
pytest app/tests/unit/test_component_flip.py -v
```

---

## Phase 4 — Observer Completeness (~60 lines added)

**File:** `circuit_canvas.py`

### Checklist

- [ ] `_handle_component_moved` — full impl with flag toggling
  (disable `ItemSendsGeometryChanges` → set pos → re-enable)
  + schedule batch reroute
- [ ] Batch reroute: `_schedule_batch_reroute()`, `_do_batch_reroute()`
  — `QTimer(0)` deferred; collect unique wires, call `update_position()` once each
- [ ] `_sync_nodes_from_model()` — pull `(nodes, terminal_to_node)` from controller
- [ ] `_handle_nodes_rebuilt(data)` — calls sync + `scene.update()`
- [ ] `reroute_connected_wires(component)` — iterate wires, skip locked,
  dedup co-selected endpoints
- [ ] `_reroute_wires_near_components(components)` — reroute after wire deletion
- [ ] Stale-OP clearing on circuit-modifying events (already in dispatcher)

### Verify

```
# Programmatic controller operations reflected visually
# Load → save → load roundtrip preserves components
# Undo/redo works for all component ops
pytest app/tests/unit/test_batch_reroute.py -v
pytest app/tests/unit/test_wire_reroute_dedup.py -v
pytest app/tests/unit/test_canvas_sync.py -v
```

---

## Phase 5 — Wires (Largest Phase, ~520 lines)

**Files:** `wire_item.py` (full), `circuit_canvas.py` (wire mode)

### wire_item.py — Bloat-reduced design

**Key change:** Extract `_build_path_from_waypoints()` used in 3 places.
Normalize waypoints to `QPointF` once in `update_position()` / `_restore_waypoints()`.

#### Checklist

- [ ] `WaypointHandle(QGraphicsEllipseItem)`:
  - Draggable, grid-snapped on `itemChange`
  - `mouseReleaseEvent` → locks wire via `_finish_waypoint_drag()`
- [ ] `WireGraphicsItem(QGraphicsPathItem)`:
  - Constructor: `(start_comp, start_term, end_comp, end_term, canvas, algorithm, layer_color, model)`
  - Creates or accepts `WireData` model
  - `update_position()` — lazy-import pathfinder, build obstacles,
    run IDA*, build path, persist result
  - `show_drag_preview()` — straight line between terminals
  - `_restore_waypoints()` — rebuild path from model waypoints
  - `_build_path_from_waypoints()` — **single helper** used by
    `update_position`, `_restore_waypoints`, `_rebuild_path_from_waypoints`
  - `paint()` — pen styles: selected / hovered / locked / failed, junction dots
  - `shape()` — `QPainterPathStroker` with `WIRE_CLICK_WIDTH`
  - Waypoint handle lifecycle: `_show_handles`, `_hide_handles`,
    `_move_waypoint`, `_finish_waypoint_drag`
  - `_ComponentAdapter`, `_WireAdapter` — Qt-to-tuple adapters for pathfinder
- [ ] `WireItem = WireGraphicsItem` alias

### circuit_canvas.py wire additions

- [ ] Wire drawing state machine in `_try_wire_click()`:
  - Start: terminal proximity → `wire_start_comp/term`, temp line, CrossCursor
  - Waypoint: click empty space → append to `_wire_waypoints`, add marker
  - Complete: click second terminal → `controller.add_wire()`, emit signal, cleanup
- [ ] `mouseMoveEvent` — update temp line from last waypoint/start terminal
- [ ] `cancel_wire_drawing()` — clean up temp line, waypoints, markers, cursor
- [ ] `_add_waypoint_marker(pos)`, `_remove_waypoint_markers()`
- [ ] `is_terminal_available(component, terminal_index)` — duplicate wire check
- [ ] Observer handlers: `_handle_wire_added/removed/routed/lock_changed/reroute_requested`
- [ ] Scene-item callbacks: `on_wire_routing_complete()`, `on_routing_failed()`,
  `on_wire_waypoints_changed()`
- [ ] `delete_wire()`, `toggle_wire_lock()`, `reroute_wire()`, `reroute_selected_wires()`
- [ ] `_do_batch_reroute()` — now functional (was no-op in Phase 4)

### component_item.py minor update

- [ ] `itemChange(ItemPositionHasChanged)`: call `wire.show_drag_preview()`
  for connected wires (skip during `_group_moving`)

### Verify

```
# Click terminal A → click terminal B → wire routes
# Drag component → wires preview then reroute
# Select wire → waypoint handles appear
# Manual waypoint drag locks wire
pytest app/tests/unit/test_wire_z_order.py -v
pytest app/tests/unit/test_waypoint_editing.py -v
pytest app/tests/unit/test_wire_deletion.py -v
pytest app/tests/unit/test_click_waypoints.py -v
pytest app/tests/unit/test_wire_preview_cleanup.py -v
```

---

## Phase 6 — Wire Context Menu & Net Names (~80 lines added)

**File:** `circuit_canvas.py`

### Checklist

- [ ] Context menu for wires: Delete, Lock/Unlock, Reroute, Set Net Name
- [ ] Context menu for components: Delete, Rotate CW/CCW, Flip H/V
- [ ] Context menu for empty area: Delete Selected, Copy/Cut (if selected),
  Paste (if clipboard), Add Annotation
- [ ] `label_node(node)` — `QInputDialog` for custom net name via controller
- [ ] `find_node_at_position(scene_pos)` — terminal proximity → node lookup

**Bloat tip:** Split `show_context_menu()` into 3 private methods:
```python
def show_context_menu(self, position):
    item = self.itemAt(position)
    menu = QMenu()
    if isinstance(item, ComponentGraphicsItem):
        self._build_component_menu(menu, item)
    elif isinstance(item, WireItem):
        self._build_wire_menu(menu, item)
    else:
        self._build_empty_menu(menu, position)
    # Always add paste + annotation
    ...
```

### Verify

```
# Right-click wire → contextual actions
# Lock → dotted style
# Reroute recalculates
# Set net name → label appears in drawForeground
pytest app/tests/unit/test_node.py -v
```

---

## Phase 7 — Overlays, OP Annotations, Probes (~150 lines added)

**File:** `circuit_canvas.py`

### Checklist

- [ ] `drawForeground(painter, rect)` — draw in order:
  1. Node labels (if `show_node_labels`)
  2. OP voltage annotations (if `show_op_annotations` + `node_voltages`)
  3. Branch current annotations (if `branch_currents`)
  4. Probe results (always on top if any)
- [ ] `_draw_label_box(painter, pos, text, y_above, pen)` — text + background rect
- [ ] `_get_node_position(node)` — average terminal positions
- [ ] Probe mode: `set_probe_mode()`, `_probe_at_position()`,
  `_probe_node()`, `_probe_component()`, `clear_probes()`
- [ ] Full `set_node_voltages()`, `set_op_results()`, `clear_op_results()`

### Verify

```
# Run DC OP simulation → voltages appear on nodes
# Probe mode → click node → voltage tooltip
# Probe mode → click component → V, I, P summary
# Toggle node labels on/off
pytest app/tests/unit/test_op_annotations.py -v
pytest app/tests/unit/test_probe_tool.py -v
```

---

## Phase 8 — Annotations (~75 lines)

**Files:** `annotation_item.py` (full), `circuit_canvas.py`

### annotation_item.py

- [ ] `AnnotationItem(QGraphicsTextItem)`:
  - Constructor: `(text, x, y, font_size, bold, color)`
  - Flags: movable, selectable, sends geometry changes
  - `z = 90`
  - `mouseDoubleClickEvent` → edit via canvas (for undo support)
  - `to_dict()`, `from_dict(data)` serialization

### circuit_canvas.py additions

- [ ] `add_annotation(scene_pos)` — `QInputDialog` → `AddAnnotationCommand`
- [ ] `_delete_annotation(ann)` → `DeleteAnnotationCommand`
- [ ] `_edit_annotation(ann)` → `EditAnnotationCommand`
- [ ] Observer handlers: `_handle_annotation_added/removed/updated`
- [ ] Update `delete_selected()` to include annotations

### Verify

```
pytest app/tests/unit/test_annotations.py -v
pytest app/tests/unit/test_annotation_undo.py -v
pytest app/tests/unit/test_annotation_default_color.py -v
```

---

## Phase 9 — Clipboard & Serialization (~80 lines added)

**File:** `circuit_canvas.py`

### Checklist

- [ ] `copy_selected_components(ids)` — delegates to `controller.copy_components()`
- [ ] `cut_selected_components(ids)` — copy then delete
- [ ] `paste_components()` — paste from controller clipboard, select new items
- [ ] `to_dict()` — delegates to controller
- [ ] `from_dict(data)` — validate, clear, rebuild
- [ ] `_validate_circuit_data(data)` — check `components`/`wires` structure,
  verify component IDs, verify wire endpoints

### Verify

```
# Select components + wires → copy → paste (offset)
# Cut works
# Save → load roundtrip
pytest app/tests/unit/test_copy_paste.py -v
pytest app/tests/unit/test_circuit_file_validation.py -v
```

---

## Phase 10 — Export, Debug, Polish (~200 lines added)

**File:** `circuit_canvas.py`

### Checklist

- [ ] `export_image(filepath, include_grid)` → route to `_export_png()` or `_export_svg()`
- [ ] `_export_png(filepath, rect)` — 2x resolution render
- [ ] `_export_svg(filepath, rect)` — `QSvgGenerator`
- [ ] `toggle_obstacle_boundaries()`, `draw_obstacle_boundaries()`,
  `clear_obstacle_boundaries()`
- [ ] `wheelEvent` — Ctrl+scroll zoom centered on cursor
- [ ] `focusOutEvent` — cancel wire drawing
- [ ] `clear_circuit()` — full clear + counter reset
- [ ] Data accessors: `get_model_components()`, `get_model_wires()`,
  `get_model_nodes_and_terminal_map()`
- [ ] `select_all()` — select all components + wires
- [ ] Final audit: every method in `CircuitCanvasProtocol` is implemented,
  `__init__.py` exports are satisfied

### Verify

```
pytest app/tests/unit/test_svg_export.py -v
pytest app/tests/ -x -q --timeout=30    # Full test suite
python -m app.main                       # Manual smoke test: all menu actions
```

---

## Line Budget

| File | Current | Target | Savings |
|---|---|---|---|
| `renderers.py` | 586 | ~480 | −106 (terminal leads, helpers, `_rect_obstacle`) |
| `component_item.py` | 873 | ~680 | −193 (factory, Ground paint, Transformer, registry) |
| `wire_item.py` | 525 | ~490 | −35 (path helper, normalize waypoints) |
| `annotation_item.py` | 73 | ~73 | 0 (already lean) |
| `circuit_canvas.py` | 2,266 | ~1,800 | −466 (split methods, remove fallbacks) |
| **Total** | **4,323** | **~3,523** | **−800** |

---

## Documentation Checklist (Per File)

Each rebuilt file must have:

1. **Module docstring** — purpose, design pattern used, dependencies
2. **Class docstrings** — one sentence per class describing its role
3. **Method docstrings** on public methods — args, returns, side effects
4. **Inline comments** only where the *why* isn't obvious (not the *what*)
5. **No `# Phase N` comments** — the code should be self-explanatory

### Example module docstring:
```python
"""Strategy-pattern renderers for circuit component symbols.

Each component type has an IEEE and an IEC renderer registered in a
(component_type, style) registry.  ComponentGraphicsItem.paint() draws
terminal leads, then delegates the component body to the renderer via
get_renderer().

Renderers implement two methods:
    draw_body(painter)           — draw the component symbol (no leads)
    get_obstacle_shape()         — return polygon for pathfinding avoidance

Design decision: terminal leads are drawn by the base class, not the
renderer.  This eliminates 23 duplicated ``if scene() is not None``
checks across renderers (see canvas-architecture.md for rationale).
"""
```

---

## Test Strategy

**After each phase:**
1. `python -m app.main` — no crash, visual check
2. Run the phase-specific tests listed in each "Verify" section
3. Run `pytest app/tests/ -x -q --timeout=30` — no regressions

**Tests that will exercise your rebuild most heavily:**
- `test_phase4_mvc_integration.py` — full MVC flow
- `test_canvas_sync.py` — observer pattern
- `test_batch_reroute.py` — wire rerouting
- `test_annotations.py` — annotation CRUD + undo
- `test_copy_paste.py` — clipboard operations

**Untested areas** (consider adding tests as you go):
- `drawForeground` rendering
- Context menu action dispatch
- Mouse event state machine transitions
- `export_image` output correctness
- `draw_obstacle_boundaries` visualization
