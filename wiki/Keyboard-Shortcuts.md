# Keyboard Shortcuts

SDM Spice provides keyboard shortcuts for common operations to improve workflow efficiency. All shortcuts are fully configurable through the Keybindings dialog.

## File Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+N | New Circuit | Create a new empty circuit |
| Ctrl+O | Open | Open an existing circuit file |
| Ctrl+S | Save | Save the current circuit |
| Ctrl+Shift+S | Save As | Save circuit with a new filename |
| Ctrl+E | Export Image | Export circuit as PNG/SVG |
| Ctrl+Q | Exit | Close the application |

## Edit Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+Z | Undo | Undo the last action |
| Ctrl+Shift+Z | Redo | Redo the last undone action |
| Ctrl+C | Copy | Copy selected components |
| Ctrl+X | Cut | Cut selected components |
| Ctrl+V | Paste | Paste copied components |
| Del | Delete | Delete selected component(s) or wire(s) |
| R | Rotate CW | Rotate selected component 90° clockwise |
| Shift+R | Rotate CCW | Rotate selected component 90° counter-clockwise |
| F | Flip Horizontal | Mirror component horizontally |
| Shift+F | Flip Vertical | Mirror component vertically |
| Ctrl+A | Select All | Select all components on canvas |

## Simulation Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+G | Generate Netlist | Create SPICE netlist from circuit |
| F5 | Run Simulation | Execute the current analysis |

## View Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+= | Zoom In | Increase canvas magnification |
| Ctrl+- | Zoom Out | Decrease canvas magnification |
| Ctrl+0 | Fit to Circuit | Zoom to fit entire circuit |
| Ctrl+1 | Reset Zoom | Return to default zoom level |

## Component Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| Double-click | Edit Properties | Open properties for the clicked component |
| Click+Drag | Move | Move a component on the canvas |

## Selection

| Shortcut | Action | Description |
|----------|--------|-------------|
| Click | Select | Select a single component |
| Click+Drag (canvas) | Marquee Select | Rubber-band selection of multiple components |
| Ctrl+A | Select All | Select all components on canvas |
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
│  Ctrl+E   Export Img  │  VIEW                   │
│  Ctrl+Q   Exit        │  Ctrl+=   Zoom In       │
├───────────────────────┤  Ctrl+-   Zoom Out      │
│  EDIT                 │  Ctrl+0   Fit Circuit   │
│  Ctrl+Z   Undo        │  Ctrl+1   Reset Zoom   │
│  Ctrl+Shift+Z  Redo   │                         │
│  Ctrl+C   Copy        │  COMPONENT              │
│  Ctrl+X   Cut         │  R        Rotate CW     │
│  Ctrl+V   Paste       │  Shift+R  Rotate CCW    │
│  Ctrl+A   Select All  │  F        Flip H        │
│  Del      Delete      │  Shift+F  Flip V        │
│                       │  Dbl-clk  Edit Props    │
└─────────────────────────────────────────────────┘
```

## Menu Access

All keyboard shortcuts are also shown in their respective menus:

- **File Menu**: New, Open, Save, Save As, Export Image, Exit
- **Edit Menu**: Undo, Redo, Copy, Cut, Paste, Delete, Rotate, Flip, Select All, Clear Canvas
- **Simulation Menu**: Generate Netlist, Run Simulation
- **Analysis Menu**: Select analysis type
- **View Menu**: Zoom controls, Theme switching

## Customization

Keyboard shortcuts are fully configurable:

1. Go to **Edit > Keybindings...** to open the Keybindings dialog
2. Click on any shortcut to change it
3. Press the new key combination you want to assign
4. Conflicts with existing bindings are detected and highlighted
5. Click **Reset to Defaults** to restore all default shortcuts

Custom keybindings are saved to `~/.spice-gui/keybindings.json` and persist across sessions.

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
