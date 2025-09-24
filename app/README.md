Spice GUI - Minimal Diagram Prototype

This is a minimal PyQt6-based prototype for drawing simple electronic circuit diagrams.

Features
- Palette: double-click to place Resistor, Capacitor, or Ground
- Move components by dragging
- Draw wires: right-click and drag on the canvas
- Save/load diagram as JSON

Run (Windows PowerShell)

Activate your virtualenv (if using the included `Spice_GUI_env`):

```powershell
& .\Spice_GUI_env\Scripts\Activate.ps1
python app\main.py
```

Notes
- This is a starting point. Next steps: better component graphics, connection snapping, netlist export, undo/redo, selection tools.
