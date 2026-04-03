# Feature List

## Circuit Design

- Drag-and-drop component placement from categorized palette
- Grid-aligned layout (10px snap)
- Component rotation (90° increments) and flipping
- IDA* pathfinding for automatic wire routing
- Multi-select and group operations
- Undo/redo (command pattern)
- Cut, copy, paste
- 7 built-in circuit templates
- Subcircuit support
- Context menus on canvas

## Supported Components

| Category | Components |
|----------|-----------|
| **Passive** | Resistor, Capacitor, Inductor |
| **Sources** | Voltage Source, Current Source, Waveform Source, Ground |
| **Semiconductors** | Diode, LED, Zener Diode, BJT (NPN/PNP), MOSFET (NMOS/PMOS) |
| **Controlled Sources** | VCVS, CCVS, VCCS, CCCS |
| **Other** | Op-Amp, VC Switch, Transformer |

## Simulation

- 9 analysis types (DC OP, DC Sweep, AC Sweep, Transient, Noise, Sensitivity, Transfer Function, Pole-Zero, Temperature)
- Parameter sweeps with batch execution
- Monte Carlo statistical analysis
- FFT analysis
- Power metrics (average, RMS, peak)
- Convergence checking
- Custom measurement directives

## Visualization

- Interactive waveform viewer (matplotlib)
- Frequency domain markers
- Node voltage overlay on canvas
- Data tables with scrollable results

## Import / Export

| Format | Import | Export |
|--------|--------|--------|
| JSON (native) | Yes | Yes |
| SPICE netlist | Yes | Yes |
| LTSpice (.asc) | Yes | Yes |
| LaTeX (CircuitikZ) | Yes | Yes |
| CSV | — | Yes |
| Excel (.xlsx) | — | Yes |
| Markdown report | — | Yes |
| ZIP bundle | — | Yes |
| Bill of Materials | — | Yes |

## Educational Features

- Rubric-based auto-grading
- Batch grading of multiple submissions
- Auto-generated rubrics from reference circuits
- Circuit comparison engine
- Student feedback export
- Grade distribution histograms
- Grading session persistence

## UI / UX

- Dark and light themes with QSS stylesheets
- Custom theme editor
- Configurable keyboard shortcuts
- Properties panel for selected components
- Results panel with tabs
- Print and PDF export with preview
- Status bar messages
- Tooltips and help system
- Recent files tracking
- Autosave with session recovery

## Scripting / Headless

- Python scripting API for programmatic circuit creation
- Jupyter notebook integration with inline rendering
- CLI for batch operations (`cli.py`)