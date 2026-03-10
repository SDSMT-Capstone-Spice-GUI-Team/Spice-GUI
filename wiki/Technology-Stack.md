# Technology Stack

SDM Spice is built with modern, well-supported technologies.

## Core Technologies

### Python 3.10+

**Role:** Primary programming language

**Why Python:**
- Excellent ecosystem for scientific computing
- Strong GUI framework support (PyQt6)
- Easy to learn and maintain
- Cross-platform compatibility
- Extensive library support

### PyQt6 (6.9.1)

**Role:** GUI framework

**Why PyQt6:**
- Native look and feel on all platforms
- Powerful graphics capabilities (QGraphicsScene)
- Mature, well-documented framework
- Signal/slot architecture for event handling
- Professional-quality widgets

**Key Components Used:**
- `QMainWindow` - Application window
- `QGraphicsScene/View` - Circuit canvas
- `QDockWidget` - Resizable panels
- `QDialog` - Configuration dialogs
- `QFileDialog` - File operations

### ngspice

**Role:** SPICE simulation engine

**Why ngspice:**
- Open-source and free
- Industry-standard SPICE compatibility
- Active development community
- Cross-platform support
- Comprehensive analysis capabilities

**Version:** 36+ recommended, 42+ preferred

### matplotlib (3.10.6)

**Role:** Waveform plotting and visualization

**Why matplotlib:**
- De facto standard for Python plotting
- Publication-quality output
- Interactive features (zoom, pan)
- Extensive customization options
- Tight numpy integration

## Supporting Libraries

### numpy (2.3.3)

**Role:** Numerical computing (via matplotlib/scipy)

**Use Cases:**
- Array operations for simulation data
- Mathematical calculations
- Data manipulation

**Note:** Application code avoids direct NumPy imports for faster startup; NumPy features are accessed through matplotlib and scipy where needed.

### scipy (1.16.2)

**Role:** Scientific computing

**Use Cases:**
- Signal processing
- Optimization (future)
- Advanced math functions

### PySpice (1.5)

**Role:** SPICE utilities

**Use Cases:**
- Netlist parsing reference
- SPICE syntax utilities
- Component model references

## File Formats

### JSON (Circuit Files)

**Purpose:** Save and load circuit designs

**Structure:**
```json
{
  "components": [
    {
      "id": "R1",
      "type": "Resistor",
      "value": "1k",
      "position": [100, 200],
      "rotation": 0
    }
  ],
  "wires": [
    {
      "start_component": "R1",
      "start_terminal": 0,
      "end_component": "V1",
      "end_terminal": 1
    }
  ]
}
```

### SPICE Netlist (Export)

**Purpose:** Simulation input for ngspice

**Example:**
```spice
* SDM Spice Generated Netlist
R1 n001 n002 1k
V1 n001 0 10
.op
.end
```

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                    SDM Spice                     │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │  GUI Layer  │  │ Simulation  │  │  File   │  │
│  │   (PyQt6)   │  │   Layer     │  │  I/O    │  │
│  └──────┬──────┘  └──────┬──────┘  └────┬────┘  │
│         │                │              │       │
│         ▼                ▼              ▼       │
│  ┌─────────────────────────────────────────┐   │
│  │           Core Application              │   │
│  │  • Circuit Model                        │   │
│  │  • Component Registry                   │   │
│  │  • Event Handling                       │   │
│  └─────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│  External Dependencies                          │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐    │
│  │ ngspice │  │matplotlib│  │ numpy/scipy │    │
│  └─────────┘  └──────────┘  └─────────────┘    │
└─────────────────────────────────────────────────┘
```

## Module Structure

```
app/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── GUI/                    # User interface
│   ├── main_window.py              # Main window
│   ├── circuit_canvas.py       # Drawing surface
│   ├── component_item.py       # Component graphics
│   ├── component_palette.py    # Drag source
│   ├── properties_panel.py     # Property editor
│   ├── wire_item.py            # Wire graphics
│   ├── circuit_node.py         # Node abstraction
│   ├── analysis_dialog.py      # Analysis config
│   ├── waveform_dialog.py      # Waveform viewer
│   ├── path_finding.py         # Wire routing
│   ├── format_utils.py         # SI units
│   ├── algorithm_layers.py     # Multi-algorithm layer management
│   ├── layer_control_widget.py # Layer visibility UI
│   └── styles/                 # Theming system
│       ├── __init__.py         # Public API
│       ├── theme_manager.py    # Singleton accessor
│       ├── light_theme.py      # Theme implementation
│       └── constants.py        # Grid/canvas constants
└── simulation/             # SPICE integration
    ├── netlist_generator.py    # Netlist creation
    ├── ngspice_runner.py       # Simulation exec
    └── result_parser.py        # Output parsing
```

## Development Tools

### Recommended IDE
- **VS Code** with Python extension
- **PyCharm** Community or Professional

### Version Control
- **Git** for source control
- **GitHub** for repository hosting

### Package Management
- **pip** for Python packages
- **venv** for virtual environments

## Deployment

### Desktop Application
SDM Spice runs as a desktop application installed locally.

### Distribution Options (Future)
- Python package (pip install)
- Standalone executable (PyInstaller)
- Platform-specific installers

## Performance Considerations

### Startup Optimization

Heavy modules use lazy loading for faster startup:
- `path_finding` - Loaded on first wire creation
- `simulation` - Loaded when simulation is run
- `waveform_dialog` - Loaded when waveform config is opened

Grid drawing is deferred until the window is first shown.

### Memory Usage
- Typical: 100-200 MB
- Large circuits: Up to 500 MB
- Transient analysis with many points: May require more

### CPU Usage
- GUI operations: Low
- Simulation: Delegated to ngspice
- Plotting: Moderate during updates

### Storage
- Application: ~50 MB
- Dependencies: ~400 MB
- Circuit files: < 1 MB typically

## See Also

- [[System Requirements]] - Hardware requirements
- [[Installation Guide]] - Setup instructions
- [[Architecture Overview]] - Detailed design
