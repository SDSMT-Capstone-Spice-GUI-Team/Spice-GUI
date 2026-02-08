# Multi-Algorithm Example Application

## Overview

The `example_multi_algorithm.py` script provides a complete demonstration application showcasing the multi-algorithm wire routing system with a full-featured GUI.

## Features

### 🎨 Full GUI Interface
- **Component Palette**: Drag-and-drop components onto the canvas
- **Circuit Canvas**: Interactive grid-based circuit design area
- **Layer Controls**: Toggle visibility of algorithm layers
- **Performance Metrics**: Real-time comparison of algorithm performance

### 📁 File Operations
- **Save/Load**: Save and load circuits as JSON files
- **Quick Save**: Ctrl+S for quick save to current file
- **Open**: Ctrl+O to load existing circuits
- **New**: Ctrl+N to clear canvas and start fresh

### 🔍 Algorithm Comparison
- **Three Algorithms**: A* (Blue), IDA* (Green), Dijkstra (Orange)
- **Real-time Metrics**: Runtime and iteration counts
- **Visual Comparison**: See all three paths side-by-side
- **Performance Report**: Detailed comparison via View menu or Ctrl+R

## Running the Example

### From the app directory:
```bash
cd app
python example_multi_algorithm.py
```

### From the project root:
```bash
python -m app.example_multi_algorithm
```

## Usage Guide

### Creating a Circuit

1. **Add Components**
   - Drag components from the left palette onto the canvas
   - Available components: Resistors, Capacitors, Inductors, Voltage/Current Sources, Ground

2. **Draw Wires**
   - Click on a component terminal (the connection points)
   - Click on another component's terminal to complete the wire
   - **Three wires are created automatically** - one for each algorithm!

3. **View Performance**
   - Check the right panel for real-time metrics
   - Click "Refresh Metrics" to update statistics
   - Use View → Performance Report for detailed comparison

### Layer Controls

Located at the top of the canvas:
- **■ A* (Blue)**: Toggle A* algorithm visibility
- **■ IDA* (Green)**: Toggle IDA* algorithm visibility
- **■ Dijkstra (Orange)**: Toggle Dijkstra algorithm visibility
- **Show Metrics**: View performance comparison in console

### File Operations

**Menu Bar:**
- File → New (Ctrl+N): Clear canvas
- File → Open (Ctrl+O): Load a saved circuit
- File → Save (Ctrl+S): Quick save
- File → Save As (Ctrl+Shift+S): Save with new filename
- View → Performance Report (Ctrl+R): Show detailed metrics

**Note on Loading Circuits:**
When you load a saved circuit, the components appear but the wires need to be redrawn for multi-algorithm comparison. The save format stores the circuit topology but not the algorithm-specific routing data.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New circuit (clear canvas) |
| Ctrl+O | Open circuit file |
| Ctrl+S | Save circuit |
| Ctrl+Shift+S | Save As |
| Ctrl+R | Performance report |
| R | Rotate selected components |
| Delete | Remove selected items |
| Right-click | Context menu |

## Testing Scenarios

### 1. Simple Path Test
**Goal:** Verify all algorithms work correctly on simple paths

**Steps:**
1. Place 2 resistors far apart with clear path
2. Draw wire between them
3. Observe three colored wires appear
4. Check metrics - should all be similar

**Expected Results:**
- All three paths should be nearly identical
- Runtimes < 5ms for all algorithms
- Low iteration counts (< 50)

### 2. Complex Routing Test
**Goal:** Compare algorithm performance with obstacles

**Steps:**
1. Place 10+ components creating a dense grid
2. Route wires between distant components
3. Add components that block direct paths
4. Compare metrics in the side panel

**Expected Results:**
- A* typically fastest (fewer iterations due to heuristic)
- Dijkstra explores more nodes but finds optimal path
- IDA* slower but memory-efficient
- Paths may differ due to bend penalties

### 3. Grid Complexity Comparison
**Goal:** Test performance across different scenarios

**Sparse Grid:**
- Few components, lots of space
- All algorithms fast and similar

**Dense Grid:**
- Many components, tight spaces
- A* advantage becomes clear
- Higher iteration counts overall

**Obstacle-Heavy:**
- Components blocking direct paths
- Bend penalties affect routing choices
- Good test of edge weight system

## Understanding the Metrics

### Performance Panel (Right Side)

**Per Algorithm:**
- **Wire Count**: Number of wires routed by this algorithm
- **Avg Runtime**: Average time to route each wire (milliseconds)
- **Avg Iterations**: Average iterations needed per wire

**Comparison:**
- **Fastest Avg Runtime**: Which algorithm was fastest overall
- **Fewest Avg Iterations**: Which algorithm needed least exploration

### Console Output

Every wire creation prints:
```
=== Wire Added: R1 → R2 ===
=== Algorithm Performance Comparison ===

A*: 1 wires, Avg Runtime: 1.23ms, Avg Iterations: 45
IDA*: 1 wires, Avg Runtime: 2.15ms, Avg Iterations: 67
Dijkstra: 1 wires, Avg Runtime: 1.89ms, Avg Iterations: 78

=== Comparison ===
Fastest Avg Runtime: A* (1.23ms)
Fewest Avg Iterations: A* (45)
```

## Tips and Tricks

### Viewing Individual Algorithms
1. Uncheck two algorithms in layer controls
2. Only one colored wire remains visible
3. Re-enable to see comparison

### Comparing Path Choices
1. Draw a wire with obstacles nearby
2. Toggle layers on/off individually
3. Observe how each algorithm handles the routing
4. Look for differences in bend counts

### Performance Testing
1. Create identical circuits
2. Route same connections multiple times
3. Check if performance is consistent
4. Try different component densities

### Saving Test Circuits
1. Create representative test cases
2. Save them (e.g., "simple_test.json", "complex_test.json")
3. Load and redraw wires to reproduce tests
4. Build a test suite of circuits

## Troubleshooting

### Wires Not Appearing
- Check if layer visibility is enabled (checkboxes at top)
- Verify multi-algorithm mode is on (should be by default)
- Check console for error messages

### Slow Performance
- Reduce number of active algorithms (canvas.set_active_algorithms)
- Simplify circuit layout
- Check for excessive iterations in console output

### All Wires Same Color
- Multi-algorithm mode might be disabled
- Check that all three algorithms are in active list
- Restart application if needed

### Can't Connect Components
- Ensure clicking on terminal circles (not component body)
- Terminals must be available (not already connected for 2-terminal components)
- Ground components can have multiple connections

## Architecture

The example demonstrates integration of:
- **CircuitCanvas**: Core canvas with multi-algorithm support
- **ComponentPalette**: Drag-and-drop component creation
- **LayerControlWidget**: Full-featured layer management
- **CompactLayerControlWidget**: Horizontal layer toggles
- **AlgorithmLayerManager**: Coordinates algorithm layers

## Code Structure

```python
class MultiAlgorithmDemo(QMainWindow):
    def __init__(self):
        # Setup GUI with three main areas:
        # 1. Left: Component palette + instructions
        # 2. Center: Canvas with layer controls
        # 3. Right: Performance metrics panel

    def _create_menu_bar(self):
        # File, View, Help menus with shortcuts

    def _on_wire_added(self, start, end):
        # Update metrics when wire is created
        # Print performance report to console
```

## Extending the Example

### Add Custom Algorithms
```python
# In canvas initialization
canvas.set_active_algorithms(['astar', 'idastar', 'dijkstra', 'custom'])

# Define custom algorithm in path_finding.py
def _find_path_custom(self, start, end, obstacles, bounds, ...):
    # Your algorithm implementation
    pass
```

### Customize Colors
```python
# In algorithm_layers.py, modify _create_default_layers()
self.layers['astar'] = AlgorithmLayer(
    name="A*",
    algorithm_type='astar',
    color=QColor(255, 0, 0),  # Red instead of blue
    z_value=10,
    visible=True
)
```

### Add More Metrics
```python
# In AlgorithmLayer class
self.path_length = 0
self.bend_count = 0

# Track additional statistics
def add_path_data(self, waypoints):
    self.path_length += len(waypoints)
    self.bend_count += count_bends(waypoints)
```

## Known Limitations

1. **Loaded circuits**: Wires must be redrawn for multi-algorithm comparison
2. **Memory usage**: IDA* uses less memory but not tracked in metrics
3. **Net awareness**: Same-net bundling not yet fully implemented
4. **Undo/Redo**: Not implemented in this example

## Future Enhancements

- [ ] Undo/Redo functionality
- [ ] Export performance data to CSV
- [ ] Animated path exploration visualization
- [ ] Heatmap of explored nodes
- [ ] Batch testing multiple circuits
- [ ] Memory usage tracking
- [ ] Path quality scoring (beyond iterations)

## Related Files

- **Main Implementation**: `GUI/path_finding.py` - Algorithm implementations
- **Layer System**: `GUI/algorithm_layers.py` - Layer management
- **Canvas**: `GUI/circuit_canvas.py` - Multi-algorithm routing
- **Widgets**: `GUI/layer_control_widget.py` - UI controls
- **Documentation**: `MULTI_ALGORITHM_README.md` - System overview

## Support

For issues or questions:
1. Check console output for error messages
2. Verify all three algorithms are implemented
3. Test with simple circuits first
4. Review the main README for architecture details
