# Architecture Overview

Technical architecture and design patterns used in SDM Spice.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SDM Spice Application                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Presentation Layer                  │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐│   │
│  │  │   Main      │ │  Component  │ │    Properties   ││   │
│  │  │   Window    │ │   Palette   │ │      Panel      ││   │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘│   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐│   │
│  │  │   Circuit   │ │   Waveform  │ │    Analysis     ││   │
│  │  │   Canvas    │ │    Viewer   │ │     Dialog      ││   │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Business Logic Layer                │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐│   │
│  │  │   Circuit   │ │    Wire     │ │   Component     ││   │
│  │  │    Model    │ │   Routing   │ │    Factory      ││   │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Simulation Layer                    │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐│   │
│  │  │   Netlist   │ │   ngspice   │ │    Result       ││   │
│  │  │  Generator  │ │   Runner    │ │    Parser       ││   │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    Data Layer                         │   │
│  │  ┌─────────────┐ ┌─────────────┐                     │   │
│  │  │    File     │ │   Session   │                     │   │
│  │  │    I/O      │ │   Manager   │                     │   │
│  │  └─────────────┘ └─────────────┘                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Dependencies                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │   ngspice   │ │  matplotlib │ │      PyQt6 / Qt6        ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Design Patterns

### Factory Pattern

Used for component creation:

```python
# Component factory registry
COMPONENT_CLASSES = {
    "Resistor": ResistorItem,
    "Capacitor": CapacitorItem,
    "VoltageSource": VoltageSourceItem,
    # ...
}

def create_component(component_type: str, **kwargs) -> ComponentItem:
    """Factory method for creating components."""
    if component_type not in COMPONENT_CLASSES:
        raise ValueError(f"Unknown component type: {component_type}")
    return COMPONENT_CLASSES[component_type](**kwargs)
```

### Observer Pattern (Signals & Slots)

PyQt6 signals for event handling:

```python
class CircuitCanvas(QGraphicsScene):
    # Define signals
    componentAdded = pyqtSignal(object)
    componentRemoved = pyqtSignal(str)
    wireCreated = pyqtSignal(object)

    def add_component(self, component):
        # ... add component logic ...
        self.componentAdded.emit(component)
```

### Strategy Pattern

Multiple pathfinding algorithms:

```python
class PathFinder:
    def __init__(self, algorithm="ida_star"):
        self.algorithms = {
            "ida_star": self._ida_star,
            "a_star": self._a_star,
            "dijkstra": self._dijkstra,
        }
        self.current_algorithm = self.algorithms[algorithm]

    def find_path(self, start, end, obstacles):
        return self.current_algorithm(start, end, obstacles)
```

### Model-View Pattern

Separation of data and presentation:

```
Circuit Model (Data)          Canvas View (Presentation)
├── Components dict    ──────>  ComponentItem graphics
├── Wires list         ──────>  WireItem graphics
└── Nodes list         ──────>  NodeItem graphics
```

## Module Breakdown

### GUI Layer (`app/GUI/`)

| Module | Responsibility |
|--------|----------------|
| `circuit_design_gui.py` | Main window, menus, layout orchestration |
| `circuit_canvas.py` | Graphics scene, component/wire management |
| `component_item.py` | Component visualization and interaction |
| `component_palette.py` | Drag source for components |
| `properties_panel.py` | Component property editing |
| `wire_item.py` | Wire rendering and path display |
| `circuit_node.py` | Electrical node abstraction |
| `analysis_dialog.py` | Simulation configuration dialogs |
| `waveform_dialog.py` | Result visualization |
| `path_finding.py` | Wire routing algorithms |
| `format_utils.py` | SI unit parsing and formatting |

### Simulation Layer (`app/simulation/`)

| Module | Responsibility |
|--------|----------------|
| `netlist_generator.py` | Convert circuit to SPICE netlist |
| `ngspice_runner.py` | Execute ngspice and manage process |
| `result_parser.py` | Parse simulation output |

## Data Flow

### Circuit Creation Flow

```
User Action        Component Palette      Circuit Canvas       Circuit Model
    │                    │                     │                    │
    │  Drag component    │                     │                    │
    ├───────────────────>│                     │                    │
    │                    │  Drop event         │                    │
    │                    ├────────────────────>│                    │
    │                    │                     │  Create component  │
    │                    │                     ├───────────────────>│
    │                    │                     │                    │
    │                    │                     │  Add to scene      │
    │                    │                     │<───────────────────┤
    │                    │                     │                    │
    │  Visual feedback   │                     │                    │
    │<─────────────────────────────────────────┤                    │
```

### Simulation Flow

```
User              Main Window          Netlist Gen         ngspice Runner       Parser
  │                   │                    │                    │                  │
  │  Run Simulation   │                    │                    │                  │
  ├──────────────────>│                    │                    │                  │
  │                   │  Generate netlist  │                    │                  │
  │                   ├───────────────────>│                    │                  │
  │                   │                    │  SPICE text        │                  │
  │                   │<───────────────────┤                    │                  │
  │                   │                    │                    │                  │
  │                   │  Execute simulation│                    │                  │
  │                   ├────────────────────────────────────────>│                  │
  │                   │                    │                    │  raw output      │
  │                   │<────────────────────────────────────────┤                  │
  │                   │                    │                    │                  │
  │                   │  Parse results     │                    │                  │
  │                   ├─────────────────────────────────────────────────────────>│
  │                   │                    │                    │  structured data │
  │                   │<─────────────────────────────────────────────────────────┤
  │                   │                    │                    │                  │
  │  Display results  │                    │                    │                  │
  │<──────────────────┤                    │                    │                  │
```

## Key Classes

### CircuitDesignGUI

Main application window:

```python
class CircuitDesignGUI(QMainWindow):
    def __init__(self):
        self.canvas = CircuitCanvas()
        self.palette = ComponentPalette()
        self.properties = PropertiesPanel()
        self.results = ResultsPanel()

    def run_simulation(self):
        netlist = NetlistGenerator.generate(self.canvas)
        results = NgspiceRunner.run(netlist)
        parsed = ResultParser.parse(results)
        self.results.display(parsed)
```

### CircuitCanvas

Drawing surface and component manager:

```python
class CircuitCanvas(QGraphicsScene):
    def __init__(self):
        self.components = {}  # id -> ComponentItem
        self.wires = []       # List of WireItem
        self.grid_size = 10

    def add_component(self, component_type, position):
        component = create_component(component_type)
        component.setPos(self.snap_to_grid(position))
        self.addItem(component)
        self.components[component.id] = component
```

### ComponentItem

Base class for all components:

```python
class ComponentItem(QGraphicsItem):
    def __init__(self, component_id, value=""):
        self.component_id = component_id
        self.value = value
        self.terminals = []  # Terminal positions
        self.rotation_angle = 0

    def paint(self, painter, option, widget=None):
        # Subclasses implement specific drawing
        pass

    def get_spice_line(self, nodes):
        # Subclasses return SPICE netlist line
        pass
```

## Wire Routing

The IDA* pathfinding algorithm routes wires around obstacles:

```python
def ida_star_path(start, end, obstacles, grid_size):
    """
    Iterative Deepening A* for wire routing.

    Args:
        start: Starting point (x, y)
        end: Target point (x, y)
        obstacles: List of obstacle shapes
        grid_size: Grid alignment size

    Returns:
        List of points forming the wire path
    """
    def heuristic(point):
        return manhattan_distance(point, end)

    def neighbors(point):
        # Return valid adjacent grid points
        pass

    # IDA* implementation
    # Returns optimal path avoiding obstacles
```

## File I/O

### Saving Circuits

```python
def save_circuit(canvas, filepath):
    data = {
        "version": "1.0",
        "components": [
            c.to_dict() for c in canvas.components.values()
        ],
        "wires": [
            w.to_dict() for w in canvas.wires
        ]
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
```

### Loading Circuits

```python
def load_circuit(canvas, filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    canvas.clear()

    for comp_data in data["components"]:
        component = create_component(
            comp_data["type"],
            **comp_data
        )
        canvas.add_component(component)

    for wire_data in data["wires"]:
        wire = WireItem.from_dict(wire_data)
        canvas.add_wire(wire)
```

## Error Handling Strategy

```python
class SimulationError(Exception):
    """Base exception for simulation errors."""
    pass

class NetlistError(SimulationError):
    """Error generating netlist."""
    pass

class NgspiceError(SimulationError):
    """Error running ngspice."""
    pass

def run_simulation(circuit):
    try:
        netlist = generate_netlist(circuit)
    except NetlistError as e:
        show_error("Netlist Error", str(e))
        return

    try:
        result = run_ngspice(netlist)
    except NgspiceError as e:
        show_error("Simulation Error", str(e))
        return

    return parse_results(result)
```

## Future Architecture Considerations

### Phase 2+: Cloud Backend

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   SDM Spice     │────>│   API Gateway   │────>│   Cloud DB      │
│   Desktop App   │<────│   (REST/GraphQL)│<────│   (PostgreSQL)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  File Storage   │
                        │  (S3/GCS)       │
                        └─────────────────┘
```

### Phase 6: Scripting API

```python
# Future scripting interface
import sdmspice as sdm

circuit = sdm.Circuit()
circuit.add(sdm.Resistor("R1", "1k", node1="n1", node2="n2"))
circuit.add(sdm.VoltageSource("V1", "10", node_pos="n1", node_neg="0"))

results = circuit.run_dc_op()
print(results.voltage("n2"))
```

## See Also

- [[Technology Stack]] - Dependencies and tools
- [[Contributing]] - Development setup
- [[File Formats]] - Data structures
