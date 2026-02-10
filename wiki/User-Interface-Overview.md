# User Interface Overview

A guide to the SDM Spice user interface layout and components.

## Main Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  File   Edit   Simulation   Analysis   View   Help      [Menu]  │
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
│  [Diode]    │                                   │               │
│  [BJT NPN]  │     Results / Waveform Panel      │  [Apply]      │
│  [MOSFET]   │                                   │               │
│  ...        │                                   │  Power: 10mW  │
└─────────────┴───────────────────────────────────┴───────────────┘
```

## Component Palette (Left Panel)

The Component Palette contains all available circuit elements, organized by category.

### How to Use
1. **Click and drag** a component from the palette onto the circuit canvas
2. The component appears at the drop location, snapped to the grid

### Available Components

**Passive Components:**
- Resistor (R)
- Capacitor (C)
- Inductor (L)

**Sources:**
- Voltage Source (V)
- Current Source (I)
- Waveform Source (VW)

**Dependent Sources:**
- VCVS (E) — Voltage-controlled voltage source
- CCVS (H) — Current-controlled voltage source
- VCCS (G) — Voltage-controlled current source
- CCCS (F) — Current-controlled current source

**Semiconductors:**
- Diode (D)
- LED (D)
- Zener Diode (D)
- BJT NPN (Q)
- BJT PNP (Q)
- MOSFET NMOS (M)
- MOSFET PMOS (M)

**Other:**
- Ground (GND) — Required for every circuit
- Op-Amp (OA)
- Voltage-Controlled Switch (S)

## Circuit Canvas (Center)

The main workspace where you design your circuit.

### Features
- **Grid alignment**: Components snap to a 10-pixel grid
- **Wire routing**: Automatic pathfinding for connections
- **Visual feedback**: Node voltages and branch currents displayed after DC analysis
- **DC OP annotations**: Simulation results shown directly on the schematic (toggle via View menu)
- **Marquee selection**: Click and drag on empty canvas to rubber-band select multiple components
- **Zoom controls**: Zoom in/out/fit/reset via toolbar or keyboard shortcuts

### Interactions

| Action | How To |
|--------|--------|
| Add component | Drag from palette |
| Move component | Click and drag on canvas |
| Rotate component | Select + press R (or Shift+R for CCW) |
| Flip component | Select + press F (or Shift+F for vertical) |
| Delete component | Select + press Del |
| Create wire | Click terminal, then click another terminal |
| Select | Click on component |
| Multi-select | Click + drag on empty canvas (marquee) |
| Edit properties | Select, then use Properties Panel |
| Copy/Cut/Paste | Ctrl+C / Ctrl+X / Ctrl+V |
| Undo/Redo | Ctrl+Z / Ctrl+Shift+Z |

### Visual Elements

| Element | Appearance |
|---------|------------|
| Grid | Light gray lines (dark theme: subtle dark lines) |
| Components | Colored symbols (theme-aware) |
| Terminals | Red circles |
| Wires | Black lines (dark theme: light lines) |
| Node voltages | Text labels (after simulation) |
| Selection | Highlight/outline |
| Annotations | DC OP results overlaid on schematic |

## Properties Panel (Right Panel)

Edit properties of selected components.

### Fields

| Field | Description | Editable |
|-------|-------------|----------|
| Component ID | Unique identifier (R1, V1, etc.) | No |
| Type | Component type (Resistor, etc.) | No |
| Value | Component value (1k, 10u, etc.) | Yes |
| Power | Power dissipation (after simulation) | No |

### Buttons

| Button | Action |
|--------|--------|
| **Apply** | Save changes to component |
| **Configure Waveform** | Open waveform settings (for waveform sources) |

### In-Place Editing
You can also double-click a component's value label directly on the canvas to edit its value in place.

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
- **DC Operating Point**: Node voltages and branch currents (also annotated on canvas)
- **DC Sweep**: Plot of voltage vs swept parameter
- **AC Sweep**: Magnitude and phase (Bode) plots with frequency response markers
- **Transient**: Time-domain waveforms with optional FFT spectrum view

### Waveform Viewer Features
- Interactive zoom and pan
- Toggle individual traces on/off
- **Measurement cursors**: Two draggable vertical cursors (A & B) showing X/Y values and deltas
- **Result overlay**: Compare multiple simulation runs on the same plot
- CSV export of simulation data
- Data table with numerical values

## Menu Bar

### File Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| New | Ctrl+N | Create empty circuit |
| Open | Ctrl+O | Open circuit file |
| Open Recent | - | List of recently opened files |
| Save | Ctrl+S | Save current circuit |
| Save As | Ctrl+Shift+S | Save with new name |
| Export Image | Ctrl+E | Export as PNG/SVG/PDF |
| Exit | Ctrl+Q | Close application |

### Edit Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Undo | Ctrl+Z | Undo last action |
| Redo | Ctrl+Shift+Z | Redo last undone action |
| Copy | Ctrl+C | Copy selected |
| Cut | Ctrl+X | Cut selected |
| Paste | Ctrl+V | Paste clipboard |
| Delete | Del | Delete selected |
| Rotate CW | R | Rotate clockwise |
| Rotate CCW | Shift+R | Rotate counter-clockwise |
| Flip Horizontal | F | Mirror horizontally |
| Flip Vertical | Shift+F | Mirror vertically |
| Select All | Ctrl+A | Select all components |
| Clear Canvas | - | Remove all components |
| Keybindings... | - | Customize keyboard shortcuts |

### Simulation Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Generate Netlist | Ctrl+G | Create SPICE netlist |
| Run Simulation | F5 | Execute analysis |
| Parameter Sweep | - | Sweep a component value |

### Analysis Menu
| Item | Description |
|------|-------------|
| DC Operating Point | Steady-state analysis |
| DC Sweep | Voltage sweep analysis |
| AC Sweep | Frequency response |
| Transient | Time-domain analysis |
| Temperature Sweep | Thermal sensitivity analysis |

### View Menu
| Item | Description |
|------|-------------|
| Zoom In/Out/Fit/Reset | Canvas zoom controls |
| Show Annotations | Toggle DC OP annotations on canvas |
| Theme > Light | Switch to light theme |
| Theme > Dark | Switch to dark theme |

## Dark Mode

SDM Spice supports light and dark themes:

- Switch via **View > Theme > Light/Dark**
- Theme preference is saved and persists across sessions
- All UI elements update: canvas, components, wires, plots, panels
- Waveform plots also respect the selected theme

## Auto-Save and Recovery

- Circuits are automatically saved to a temporary file every 60 seconds
- If the application crashes, on next startup you will be prompted to recover unsaved changes
- Auto-save interval is configurable
- The temporary file is cleared on clean exit

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

1. **Keyboard shortcuts** speed up common tasks — customize them via Edit > Keybindings
2. **Double-click** components to quickly edit values in place
3. **Use the grid** for neat, organized layouts
4. **Auto-save** protects your work, but still save manually with Ctrl+S
5. **Start simple** — build circuits incrementally
6. **Overlay results** to compare different simulations
7. **Use measurement cursors** to precisely read waveform values

## Accessibility

- Full keyboard/tab navigation with visible focus indicators
- High contrast colors for components
- Dark mode for reduced eye strain
- Resizable panels and text
- Color-blind friendly waveform colors
- Configurable keybindings

## See Also

- [[Quick Start Tutorial]] - Hands-on introduction
- [[Keyboard Shortcuts]] - All shortcuts
- [[Components]] - Component details
