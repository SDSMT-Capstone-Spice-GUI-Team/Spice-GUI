# Keyboard Shortcuts

SDM Spice provides keyboard shortcuts for common operations to improve workflow efficiency.

## File Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+N | New Circuit | Create a new empty circuit |
| Ctrl+O | Open | Open an existing circuit file |
| Ctrl+S | Save | Save the current circuit |
| Ctrl+Shift+S | Save As | Save circuit with a new filename |
| Ctrl+Q | Exit | Close the application |

## Edit Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Del | Delete | Delete selected component(s) or wire(s) |
| R | Rotate CW | Rotate selected component 90° clockwise |
| Shift+R | Rotate CCW | Rotate selected component 90° counter-clockwise |

## Simulation Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+G | Generate Netlist | Create SPICE netlist from circuit |
| F5 | Run Simulation | Execute the current analysis |

## View Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| (Planned) Ctrl++ | Zoom In | Increase canvas magnification |
| (Planned) Ctrl+- | Zoom Out | Decrease canvas magnification |
| (Planned) Ctrl+0 | Reset Zoom | Return to default zoom level |

## Component Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Double-click | Edit Properties | Open properties for the clicked component |
| Click+Drag | Move | Move a component on the canvas |

## Selection

| Shortcut | Action | Description |
|----------|--------|-------------|
| Click | Select | Select a single component |
| (Planned) Ctrl+A | Select All | Select all components on canvas |
| Escape | Deselect | Clear current selection |

## Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│           SDM Spice Keyboard Shortcuts          │
├─────────────────────────────────────────────────┤
│  FILE                 │  SIMULATION             │
│  Ctrl+N   New         │  Ctrl+G   Gen Netlist   │
│  Ctrl+O   Open        │  F5       Run Sim       │
│  Ctrl+S   Save        │                         │
│  Ctrl+Q   Exit        │                         │
├─────────────────────────────────────────────────┤
│  EDIT                 │  COMPONENT              │
│  Del      Delete      │  R        Rotate CW     │
│                       │  Shift+R  Rotate CCW    │
│                       │  Dbl-clk  Edit Props    │
└─────────────────────────────────────────────────┘
```

## Menu Access

All keyboard shortcuts are also shown in their respective menus:

- **File Menu**: New, Open, Save, Save As, Exit
- **Edit Menu**: Delete, Rotate, Clear Canvas
- **Simulation Menu**: Generate Netlist, Run Simulation
- **Analysis Menu**: Select analysis type

## Customization

Keyboard shortcuts are currently not customizable. Custom shortcut configuration is planned for a future release.

## Platform Notes

### Windows
- All shortcuts work as documented
- Use `Ctrl` key for modifier shortcuts

### macOS
- Use `Cmd` instead of `Ctrl` for most shortcuts
- `Cmd+Q` to quit

### Linux
- All shortcuts work as documented
- Use `Ctrl` key for modifier shortcuts

## See Also

- [[User Interface Overview]] - Understanding the UI layout
- [[Quick Start Tutorial]] - Getting started with SDM Spice
