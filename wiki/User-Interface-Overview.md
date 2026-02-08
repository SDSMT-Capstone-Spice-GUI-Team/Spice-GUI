# User Interface Overview

A guide to the SDM Spice user interface layout and components.

## Main Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  File   Edit   Simulation   Analysis   Help            [Menu]   │
├─────────────┬───────────────────────────────────┬───────────────┤
│             │                                   │               │
│  Component  │        Circuit Canvas             │  Properties   │
│   Palette   │                                   │    Panel      │
│             │    ┌───────────────────────┐      │               │
│  [Resistor] │    │                       │      │  Component:   │
│  [Capacitor]│    │    Your Circuit       │      │  R1           │
│  [Inductor] │    │    Appears Here       │      │               │
│  [V Source] │    │                       │      │  Type:        │
│  [I Source] │    │                       │      │  Resistor     │
│  [Waveform] │    └───────────────────────┘      │               │
│  [Ground]   │                                   │  Value:       │
│  [Op-Amp]   ├───────────────────────────────────┤  [1k     ]    │
│             │                                   │               │
│             │     Results / Waveform Panel      │  [Apply]      │
│             │                                   │               │
└─────────────┴───────────────────────────────────┴───────────────┘
```

## Component Palette (Left Panel)

The Component Palette contains all available circuit elements.

### How to Use
1. **Click and drag** a component from the palette
2. **Drop** it onto the circuit canvas
3. The component appears at the drop location

### Available Components
- **Resistor** (R) - Blue
- **Capacitor** (C) - Green
- **Inductor** (L) - Orange
- **Voltage Source** (V) - Red
- **Current Source** (I) - Purple
- **Waveform Source** (VW) - Pink
- **Ground** (GND) - Black
- **Op-Amp** (OA) - Yellow

## Circuit Canvas (Center)

The main workspace where you design your circuit.

### Features
- **Grid alignment**: Components snap to a 10-pixel grid
- **Wire routing**: Automatic pathfinding for connections
- **Visual feedback**: Node voltages displayed after DC analysis

### Interactions

| Action | How To |
|--------|--------|
| Add component | Drag from palette |
| Move component | Click and drag on canvas |
| Rotate component | Select + press R |
| Delete component | Select + press Del |
| Create wire | Click terminal → Click another terminal |
| Select | Click on component |
| Edit properties | Select → Use Properties Panel |

### Visual Elements

| Element | Appearance |
|---------|------------|
| Grid | Light gray lines |
| Components | Colored symbols |
| Terminals | Red circles |
| Wires | Black lines |
| Node voltages | Text labels (after simulation) |
| Selection | Highlight/outline |

## Properties Panel (Right Panel)

Edit properties of selected components.

### Fields

| Field | Description | Editable |
|-------|-------------|----------|
| Component ID | Unique identifier (R1, V1, etc.) | No |
| Type | Component type (Resistor, etc.) | No |
| Value | Component value (1k, 10u, etc.) | Yes |

### Buttons

| Button | Action |
|--------|--------|
| **Apply** | Save changes to component |
| **Configure Waveform** | Open waveform settings (for waveform sources) |

### Value Notation

Use engineering notation for values:
- `1k` = 1,000 (kilo)
- `4.7k` = 4,700
- `1M` = 1,000,000 (mega)
- `100n` = 0.0000001 (nano)
- `10u` = 0.00001 (micro)

## Results Panel (Bottom)

Displays simulation output and waveforms.

### After Simulation
- **DC Operating Point**: Node voltages and branch currents
- **DC Sweep**: Plot of voltage vs swept parameter
- **AC Sweep**: Magnitude and phase plots
- **Transient**: Time-domain waveforms

### Waveform Viewer Features
- Interactive zoom and pan
- Toggle individual traces on/off
- Data table with numerical values
- Export options

## Menu Bar

### File Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| New | Ctrl+N | Create empty circuit |
| Open | Ctrl+O | Open circuit file |
| Save | Ctrl+S | Save current circuit |
| Save As | Ctrl+Shift+S | Save with new name |
| Exit | Ctrl+Q | Close application |

### Edit Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Delete | Del | Delete selected |
| Rotate CW | R | Rotate clockwise |
| Rotate CCW | Shift+R | Rotate counter-clockwise |
| Clear Canvas | - | Remove all components |

### Simulation Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Generate Netlist | Ctrl+G | Create SPICE netlist |
| Run Simulation | F5 | Execute analysis |

### Analysis Menu
| Item | Description |
|------|-------------|
| DC Operating Point | Steady-state analysis |
| DC Sweep | Voltage sweep analysis |
| AC Sweep | Frequency response |
| Transient | Time-domain analysis |

Analysis types are mutually exclusive (radio buttons).

## Status Bar

The status bar at the bottom shows:
- Current file name
- Last action performed
- Brief status messages

## Window Management

### Resizing Panels
- Drag the dividers between panels to resize
- Panels have minimum sizes to ensure usability

### Fullscreen
- Press F11 or use window controls for fullscreen mode

## Tips for Efficient Use

1. **Keyboard shortcuts** speed up common tasks
2. **Double-click** components to quickly edit values
3. **Use the grid** for neat, organized layouts
4. **Save frequently** with Ctrl+S
5. **Start simple** - build circuits incrementally

## Accessibility

- Keyboard navigation supported
- High contrast colors for components
- Resizable panels and text
- Color-blind friendly waveform colors

## See Also

- [[Quick Start Tutorial]] - Hands-on introduction
- [[Keyboard Shortcuts]] - All shortcuts
- [[Components]] - Component details
