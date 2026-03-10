# ADR 008: Grid-Aligned Layout with 10px Snap

**Date:** 2024-09-15 (Initial prototype)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** Early prototype development

---

## Context

Circuit schematics need a layout system for placing and connecting components. The layout system fundamentally affects:
- Visual appearance and professionalism
- Wire routing complexity
- User experience (placement precision)
- File format (coordinate storage)
- Alignment and aesthetics

### Requirements

**User Experience:**
- Easy to align components visually
- Wires should route cleanly
- Minimize manual micro-adjustments
- Familiar to users of other EDA tools

**Technical:**
- Simplify wire pathfinding (discrete grid)
- Deterministic component placement
- Clean serialization (integer coordinates)
- Consistent cross-platform rendering

**Visual Quality:**
- Professional-looking schematics
- Components align naturally
- Wires connect at right angles
- Print-ready output

---

## Decision

**We will use a 10-pixel grid with snap-to-grid component placement.**

### Grid Specifications

**Grid Size:** 10 pixels (px)
**Snap Behavior:** All component positions snap to nearest grid point
**Wire Routing:** Wires route along grid lines (orthogonal paths)
**Visual Grid:** Display dots at grid intersections for user reference
**Coordinate System:** Grid-aligned coordinates (multiples of 10)

### Implementation

**Component Placement:**
- Component center positions stored as (x, y) in multiples of 10
- When user drags component, position snaps to nearest 10px grid point
- Mouse cursor shows preview of snap position

**Wire Routing:**
- Wires connect component terminals (also at grid points)
- Pathfinding algorithm (A*) searches grid-aligned paths only
- Waypoints stored as (x, y) coordinates on 10px grid

**Grid Rendering:**
- Major grid: 10px spacing, visible as light gray dots
- Minor grid: None (simpler visual)
- Grid can be toggled on/off in view menu

---

## Consequences

### Positive

✅ **Clean Alignment:**
- Components naturally align with each other
- Schematics look professional and organized
- No components at (103, 247) — always (100, 250)

✅ **Simplified Wire Routing:**
- Pathfinding only searches discrete grid points
- Reduces search space by ~100x
- Guarantees orthogonal (right-angle) wire paths
- Easier to implement Manhattan distance heuristic

✅ **Better Serialization:**
- Coordinates are always integers (multiples of 10)
- No floating-point precision issues
- Smaller JSON files (ints vs floats)
- Clean diffs in version control

✅ **Familiar UX:**
- Industry standard (LTspice, Multisim, KiCad all use grids)
- Users expect grid alignment in EDA tools
- Reduces frustration from misalignment

✅ **Predictable Behavior:**
- Components can't be "almost aligned" — they are or aren't
- Deterministic placement (no sub-pixel variations)
- Consistent rendering across platforms/zoom levels

### Negative

❌ **Limited Precision:**
- Can't place component at exact arbitrary position
- Minimum spacing is 10px (might be too coarse for dense circuits)
- Some users may want finer control

❌ **Grid Dependence:**
- Wire routing tied to grid (can't do diagonal wires)
- Components must be designed around grid size
- Changing grid size later would break layouts

❌ **Space Usage:**
- 10px minimum spacing → circuits take more space
- Dense circuits might feel "spread out"
- Larger canvas required for complex schematics

### Mitigation Strategies

**If 10px too coarse:**
- Future: Add zoom levels (grid appears finer when zoomed in)
- Future: Allow 5px sub-grid for dense sections (breaking change)
- Current: 10px sufficient for educational circuits

**Diagonal wire requests:**
- Not supported — industry standard is orthogonal
- Diagonal wires complicate routing and look unprofessional
- Users don't expect diagonal in SPICE schematic tools

**Large circuit canvas:**
- Scrollable canvas handles large circuits
- Zoom out to see overview
- Most student circuits fit in 1000×1000px (100×100 grid)

---

## Implementation Details

### Grid Coordinate System

**Origin:** Top-left corner (0, 0)
**X-axis:** Left to right, in pixels
**Y-axis:** Top to bottom, in pixels
**Grid points:** (0,0), (10,0), (20,0), ..., (10,10), (10,20), ...

### Snapping Function

```python
def snap_to_grid(pos: QPointF, grid_size: int = 10) -> QPointF:
    """Snap position to nearest grid point."""
    x = round(pos.x() / grid_size) * grid_size
    y = round(pos.y() / grid_size) * grid_size
    return QPointF(x, y)
```

### Component Positioning

**Component class:**
```python
@dataclass
class Component:
    id: str
    comp_type: str
    value: str
    pos: dict  # {"x": 100, "y": 200} — always multiples of 10
    rotation: int  # 0, 90, 180, 270
```

**On drag:**
```python
def itemChange(self, change, value):
    if change == QGraphicsItem.ItemPositionChange:
        # Snap to grid during drag
        return snap_to_grid(value)
    return super().itemChange(change, value)
```

### Wire Pathfinding Grid

**Grid representation:**
- Infinite grid (no bounds)
- Obstacles: Component bounding boxes
- Start/end: Component terminals (at grid points)

**A* search:**
- Neighbors: 4 directions (up, down, left, right) at 10px steps
- Heuristic: Manhattan distance
- Cost: Distance + bend penalties

**Example path:**
```
Start: (100, 100)
Path: [(100,100), (100,110), (110,110), (120,110), (120,120)]
End: (120, 120)
```

### Grid Rendering

**QGraphicsScene:**
```python
def drawBackground(self, painter, rect):
    """Draw grid dots."""
    grid_size = 10
    left = int(rect.left()) - (int(rect.left()) % grid_size)
    top = int(rect.top()) - (int(rect.top()) % grid_size)

    for x in range(left, int(rect.right()), grid_size):
        for y in range(top, int(rect.bottom()), grid_size):
            painter.drawPoint(x, y)
```

---

## Grid Size Rationale: Why 10px?

### Alternatives Considered

| Grid Size | Pros | Cons | Decision |
|-----------|------|------|----------|
| **5px** | Finer precision, denser layouts | Smaller click targets, more crowded | Too fine |
| **10px** ✅ | Good balance, standard component sizes | Could be tighter | **CHOSEN** |
| **20px** | Very clean, lots of space | Too coarse, wastes canvas | Too large |
| **Free-form (no grid)** | Ultimate precision | Messy alignment, complex routing | Too chaotic |

### Why 10px is Optimal

**Component Sizing:**
- Standard resistor: 40×20px (4×2 grid squares)
- Terminal spacing: 20px (2 grid squares)
- Text labels: ~50px wide (fits in 5 grid squares)

**Click Targets:**
- Terminals: 8px diameter circles on 10px grid
- Easy to click, not too small
- Good balance for mouse and touchpad

**Industry Comparison:**
- LTspice: ~8px effective grid (at 100% zoom)
- Multisim: ~10px grid
- KiCad: Configurable, default ~12px

**Conclusion:** 10px is industry-standard sweet spot.

---

## Alternatives Considered

### Alternative 1: Free-Form Placement (No Grid)

**Approach:** Allow components at any (x, y) coordinate

**Pros:**
- Maximum flexibility
- Users have complete control
- Can create very dense layouts

**Rejected because:**
- Components misalign easily (looks unprofessional)
- Wire routing much more complex (infinite search space)
- Frustrating to align manually
- Against EDA tool conventions

### Alternative 2: 5px Grid (Finer)

**Approach:** Smaller grid for more precision

**Pros:**
- More precise placement
- Denser circuits possible

**Rejected because:**
- Click targets become too small
- Grid noise (too many grid dots)
- 10px sufficient for student circuits
- Can revisit if users request finer control

### Alternative 3: 20px Grid (Coarser)

**Approach:** Larger grid for simplicity

**Pros:**
- Very clean appearance
- Easy to align
- Simpler pathfinding

**Rejected because:**
- Wastes canvas space
- Components feel too spread out
- Terminal spacing awkward (40px is too far)

### Alternative 4: Dual Grid (10px major, 5px minor)

**Approach:** Components snap to 10px, wires can use 5px

**Rejected because:**
- Complexity in implementation
- Confusing for users (two different snap behaviors)
- Doesn't provide clear benefit
- Can add later if needed (not worth initial complexity)

### Alternative 5: Adaptive Grid (Zoom-Dependent)

**Approach:** Grid size changes with zoom level

**Rejected because:**
- Confusing (placement differs at different zooms)
- File format complexity (what's the "true" coordinate?)
- Implementation complexity
- Fixed grid simpler and sufficient

---

## Grid Visibility

### Design Decision: Optional Grid Display

**Default:** Grid ON (visible gray dots)
**User Control:** View → Toggle Grid

**Rationale:**
- Beginners benefit from visible grid (alignment cues)
- Advanced users can hide for cleaner view
- Grid doesn't print/export (only visual aid)

### Grid Visual Style

**Appearance:**
- Light gray dots (RGB: 200, 200, 200)
- 2px diameter circles
- At every grid intersection (10px spacing)

**Major Grid Lines:** None (simpler than major/minor system)

---

## Impact on Other Systems

### Wire Pathfinding (ADR 006 - Future)

**Grid alignment simplifies pathfinding:**
- Search space reduced to grid points only
- Manhattan distance heuristic exact
- Guaranteed orthogonal paths
- Bend penalties work cleanly

### File Format (ADR 003)

**JSON representation:**
```json
{
  "components": [
    {
      "id": "R1",
      "type": "resistor",
      "value": "1k",
      "pos": {"x": 100, "y": 200},  // Always multiples of 10
      "rotation": 0
    }
  ],
  "wires": [
    {
      "start_comp": "R1",
      "end_comp": "V1",
      "waypoints": [[120, 200], [120, 300], [150, 300]]  // Grid-aligned
    }
  ]
}
```

**Benefits:**
- Clean integer coordinates
- Easy to validate (x % 10 == 0)
- Git diffs readable

### Component Design

**All components designed on 10px grid:**
- Resistor: 40×20px (4×2 grid)
- Capacitor: 20×40px (2×4 grid)
- Voltage source: 40×40px circle (4×4 grid)
- Terminals: Positioned at grid points

**Ensures:** Components align perfectly when placed.

---

## Future Considerations

### If Grid Size Needs to Change

**Migration path:**
1. Add grid_size field to file format
2. Convert old files (multiply all coords by scale factor)
3. Support multiple grid sizes in UI
4. Let users choose grid size per project

**Breaking change:** Requires version bump in file format.

### Sub-Grid Snapping

**Future feature:** Hold Shift to snap to 5px sub-grid

**Use case:** Dense circuits that need finer control
**Implementation:** Easy to add (modify snap function)
**Risk:** Complicates UX (two snap modes)

---

## Related Decisions

- **Wire Pathfinding** (Future ADR) - Grid enables efficient A* search
- [ADR 003: JSON File Format](003-json-circuit-file-format.md) - Grid coordinates in file
- [ADR 005: PyQt6 Framework](005-pyqt6-desktop-framework.md) - QGraphicsScene grid rendering

---

## References

- Grid snapping: [circuit_canvas.py](../../app/GUI/circuit_canvas.py)
- Component positioning: [component_item.py](../../app/GUI/component_item.py)
- Pathfinding grid: [path_finding.py](../../app/GUI/path_finding.py)

---

## Review and Revision

This decision should be reviewed if:
- Users request finer/coarser grid
- Dense circuits become common (consider 5px)
- Diagonal wires requested (unlikely)
- Export quality issues related to grid

**Status:** Working well, industry-standard approach
