# End-User Guide — SDM Spice

**Last Updated:** 2026-05-06
**Audience:** Students, instructors, and researchers using SDM Spice

---

## 1. What Is SDM Spice?

SDM Spice is a free, open-source circuit design and simulation application for Windows, macOS, and Linux. It lets you:

- Draw electronic circuits using a drag-and-drop interface
- Run SPICE simulations and see results instantly
- Export circuits as images, netlists, reports, and more
- Use built-in templates to get started quickly

---

## 2. Installation

### Windows (Recommended)

1. Go to the [Releases page](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/releases)
2. Download **`SpiceGUI-vX.Y.Z-win64-setup.exe`**
3. Run the installer — click **"More info" → "Run anyway"** if Windows SmartScreen warns you (normal for unsigned software)
4. Launch from the Start Menu

ngspice is bundled — no separate installation needed.

### macOS / Linux (From Source)

```bash
# Install ngspice first
brew install ngspice          # macOS
sudo apt install ngspice      # Ubuntu/Debian
sudo pacman -S ngspice        # Arch

# Clone and run
git clone https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI.git
cd Spice-GUI
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
python app/main.py
```

**System Requirements:**
- Python 3.10+
- 4 GB RAM recommended
- 500 MB disk space
- OpenGL 2.0+ (for canvas rendering)

---

## 3. Interface Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  File  Edit  Simulation  Analysis  View  Help           [Menu]  │
├─────────────┬───────────────────────────────┬───────────────────┤
│             │                               │                   │
│  Component  │        Circuit Canvas         │   Properties      │
│   Palette   │                               │     Panel         │
│             │    ┌───────────────────────┐  │                   │
│  [Resistor] │    │                       │  │  Component: R1    │
│  [Capacitor]│    │    Your Circuit       │  │  Type: Resistor   │
│  [Inductor] │    │    Appears Here       │  │                   │
│  [V Source] │    │                       │  │  Value: [1k     ] │
│  [Ground]   │    └───────────────────────┘  │  [Apply]          │
│  ...        ├───────────────────────────────┤                   │
│             │    Results / Waveform Panel   │  Power: 10mW      │
└─────────────┴───────────────────────────────┴───────────────────┘
```

### Component Palette (Left)
All available circuit elements, grouped by category. Drag any component onto the canvas to place it.

### Circuit Canvas (Center)
The main workspace. Components snap to a 10-pixel grid. Wires route automatically around obstacles.

### Properties Panel (Right)
Shows editable properties for the selected component. Double-click a component's value label on the canvas to edit in-place.

### Results Panel (Bottom)
Displays simulation output — text results for DC analysis, interactive waveform plots for sweep and transient analysis.

---

## 4. Quick Start: Your First Circuit

This tutorial builds a voltage divider and runs a simulation.

### Step 1 — Place Components

1. Drag a **Voltage Source** from the palette onto the canvas
2. Drag two **Resistors** and place them vertically in series
3. Drag a **Ground** symbol and place it at the bottom

### Step 2 — Connect with Wires

Click on a red terminal dot, then click on another terminal dot. The wire routes automatically.

Connect:
- Voltage Source (+) → top of R1
- Bottom of R1 → top of R2
- Bottom of R2 → Voltage Source (−)
- Ground → Voltage Source (−)

### Step 3 — Set Values

Click each component to select it, then edit its **Value** in the Properties Panel:
- Voltage Source: `10` (10 volts)
- R1: `1k` (1 kilo-ohm)
- R2: `2k` (2 kilo-ohms)

Click **Apply** after each change.

### Step 4 — Run a Simulation

1. **Analysis → DC Operating Point (.op)**
2. Press **F5** (or **Simulation → Run Simulation**)

Node voltages appear on the canvas. The junction between R1 and R2 should show **≈ 6.67 V** (= 10 × 2k / (1k + 2k)).

### Step 5 — Save

**Ctrl+S** — saves as a JSON file you can reopen anytime.

---

## 5. Components

### Passive Components

| Component | Symbol | SPICE Letter | Notes |
|-----------|--------|-------------|-------|
| Resistor | R | R | Values: `100`, `1k`, `4.7k`, `1M` |
| Capacitor | C | C | Values: `100n`, `1u`, `10p` |
| Inductor | L | L | Values: `1m`, `100u` |
| Transformer | K | K | Coupled inductors, configurable turns ratio |

### Sources

| Component | Symbol | Notes |
|-----------|--------|-------|
| Voltage Source | V | DC voltage |
| Current Source | I | DC current |
| Waveform Source | VW | SIN, PULSE, EXP — configure with "Configure Waveform" button |
| AC Voltage Source | VAC | For AC sweep analysis |
| AC Current Source | IAC | For AC sweep analysis |
| Ground | GND | Required in every circuit |

### Semiconductors

| Component | Symbol | Terminals | Models Available |
|-----------|--------|-----------|-----------------|
| Diode | D | 2 | Standard silicon |
| LED | D | 2 | Light-emitting diode |
| Zener Diode | D | 2 | Reverse-breakdown |
| BJT NPN | Q | 3 (B/C/E) | — |
| BJT PNP | Q | 3 (B/C/E) | — |
| MOSFET NMOS | M | 3 (G/D/S) | — |
| MOSFET PMOS | M | 3 (G/D/S) | — |

### Controlled Sources

| Component | Symbol | Controlled By |
|-----------|--------|---------------|
| VCVS | E | Voltage → Voltage |
| CCVS | H | Current → Voltage |
| VCCS | G | Voltage → Current |
| CCCS | F | Current → Current |

### Other

| Component | Symbol | Notes |
|-----------|--------|-------|
| Op-Amp | OA | Models: Ideal, LM741, TL081, LM358 |
| Voltage-Controlled Switch | S | Opens/closes based on control voltage |
| Current Probe | CP | Measures branch current; insert in series |

### Value Notation

| Suffix | Multiplier | Example |
|--------|------------|---------|
| k | 10³ | `4.7k` = 4,700 Ω |
| M or MEG | 10⁶ | `1M` = 1,000,000 Ω |
| m | 10⁻³ | `10m` = 0.01 H |
| u | 10⁻⁶ | `1u` = 0.000001 F |
| n | 10⁻⁹ | `100n` = 100 nF |
| p | 10⁻¹² | `10p` = 10 pF |

---

## 6. Canvas Operations

| Action | How |
|--------|-----|
| Add component | Drag from palette |
| Move component | Click + drag on canvas |
| Rotate clockwise | Select + press **R** |
| Rotate counter-clockwise | Select + press **Shift+R** |
| Flip horizontal | Select + press **F** |
| Flip vertical | Select + press **Shift+F** |
| Delete | Select + press **Del** |
| Edit value in-place | Double-click the component's value label |
| Draw wire | Click one terminal, then another |
| Multi-select | Click + drag on empty canvas (marquee) |
| Copy / Cut / Paste | **Ctrl+C** / **Ctrl+X** / **Ctrl+V** |
| Undo / Redo | **Ctrl+Z** / **Ctrl+Shift+Z** |
| Zoom in/out | **Ctrl+=** / **Ctrl+-** |
| Fit circuit | **Ctrl+0** |
| Pan | Middle mouse button + drag |

---

## 7. Analysis Types

### DC Operating Point

Calculates steady-state voltages and currents. Every circuit should start here.

**How to run:** Analysis → DC Operating Point (.op) → F5

**Output:** Node voltages and branch currents, both in the Results panel and annotated directly on the canvas.

---

### DC Sweep

Sweeps a DC source through a range of values and plots how circuit voltages/currents change.

**How to run:** Analysis → DC Sweep → configure source, start, stop, step → F5

**Use for:** Transfer characteristics, finding operating ranges, nonlinear circuit characterization.

---

### AC Sweep

Frequency-domain analysis. Sweeps across a frequency range and shows gain + phase (Bode plots).

**How to run:** Analysis → AC Sweep → configure frequency range → F5

**Use for:** Filter design, bandwidth measurement, gain/phase margin.

**Note:** Voltage sources need an AC magnitude set. Use the AC Voltage Source (VAC) component or set the AC parameter on a regular voltage source.

---

### Transient Analysis

Time-domain simulation showing how voltages and currents evolve over time.

**How to run:** Analysis → Transient → configure duration and time step → F5

**Use for:** Waveform analysis, oscillators, switching circuits, pulse response.

**Tip:** Add a Waveform Source (VW) configured as SIN or PULSE to drive a time-varying signal.

---

### Temperature Sweep

Runs simulation across a range of temperatures.

**How to run:** Analysis → Temperature Sweep → configure temperature range → F5

---

### Parameter Sweep

Sweeps a component value across a range, running the selected base analysis at each step.

**How to run:** Simulation → Parameter Sweep → select component, value range, base analysis → Run Sweep

**Output:** Overlaid traces for each parameter value, color-coded with a legend.

---

### Monte Carlo Analysis

Runs multiple simulations with randomized component values within specified tolerances.

**How to run:** Analysis → Monte Carlo → set tolerances and iteration count → Run

**Output:** Overlaid traces + statistical summary (mean, std dev, min/max).

---

### FFT / Harmonic Analysis

Computes the frequency spectrum of transient simulation data.

**How to run:** Run a Transient analysis first, then click **Show Spectrum** in the Waveform Viewer.

**Output:** Frequency spectrum, fundamental + harmonic markers, THD%.

---

### Noise Analysis

Noise spectral density at a specified output node vs frequency.

**How to run:** Analysis → Noise Analysis → select output node and frequency range → Run

---

### Sensitivity Analysis

Ranks components by their impact on a circuit output.

**How to run:** Analysis → Sensitivity → select output variable → Run

---

### Transfer Function

Computes DC gain, input resistance, and output resistance.

**How to run:** Analysis → Transfer Function → select output variable and input source → F5

---

### Pole-Zero Analysis

Finds poles and zeros of the transfer function.

**How to run:** Analysis → Pole-Zero → select nodes → F5

---

## 8. Waveform Viewer

The Results panel shows an interactive waveform viewer for sweep and transient analyses.

| Feature | How to Use |
|---------|-----------|
| Zoom / Pan | Mouse wheel and click-drag |
| Toggle traces | Click trace label in legend |
| Measurement cursors | Two vertical cursors (A & B) — drag to snap to data points; ΔX and ΔY shown |
| Overlay results | Run multiple simulations; previous results stay on the plot |
| Show FFT spectrum | Click **Show Spectrum** (after Transient) |
| Export data | Click **Export CSV** |
| Frequency markers | Shown automatically on AC Sweep plots (-3dB, bandwidth, unity-gain, gain/phase margin) |

---

## 9. File Operations

| Action | Shortcut | Notes |
|--------|----------|-------|
| New circuit | Ctrl+N | |
| Open | Ctrl+O | Loads `.json` circuit files |
| Save | Ctrl+S | |
| Save As | Ctrl+Shift+S | |
| Open recent | File → Open Recent | |
| Load template | File → Templates | 7 built-in circuits |

### Import Formats

| Format | How |
|--------|-----|
| SPICE netlist (.cir, .spice) | File → Import → SPICE Netlist |
| LTSpice (.asc) | File → Import → LTSpice |
| CircuiTikZ (LaTeX) | File → Import → CircuiTikZ |
| SVG with embedded circuit | File → Import from SVG… |

### Export Formats

| Format | How |
|--------|-----|
| PNG / SVG / PDF (schematic image) | File → Export Image (Ctrl+E) |
| SVG with embedded circuit data | File → Export Image → SVG |
| SPICE netlist | Ctrl+G (generates + shows in Results) |
| LTSpice (.asc) | File → Export → LTSpice |
| CircuiTikZ (LaTeX) | File → Export → CircuiTikZ |
| CSV (simulation data) | From the Waveform Viewer |
| Excel (.xlsx) | File → Export → Excel |
| Markdown report | File → Export → Markdown Report |
| PDF report | File → Export → PDF Report |
| Bill of Materials | File → Export → Bill of Materials |
| ZIP bundle | File → Export → ZIP Bundle |

---

## 10. Templates

SDM Spice ships 7 built-in circuit templates accessible via **File → Templates**:

- Voltage Divider
- RC Low-Pass Filter
- RC High-Pass Filter
- Inverting Amplifier
- Non-Inverting Amplifier
- Half-Wave Rectifier
- More…

Templates load a pre-wired circuit ready to simulate.

---

## 11. Themes and Appearance

- **Switch theme:** View → Theme → Light / Dark
- **Symbol style:** View → Symbol Style → IEEE (American) / IEC (European) — palette icons update in real-time
- **Font:** Edit → Preferences → Font — choose between default, OpenDyslexic (accessibility), or JetBrains Mono
- **Custom theme:** Edit → Preferences → Theme Editor

Preferences persist across sessions.

---

## 12. Keyboard Shortcuts

### Quick Reference

| Action | Shortcut |
|--------|----------|
| New circuit | Ctrl+N |
| Open | Ctrl+O |
| Save | Ctrl+S |
| Export image | Ctrl+E |
| Exit | Ctrl+Q |
| Undo | Ctrl+Z |
| Redo | Ctrl+Shift+Z |
| Copy | Ctrl+C |
| Cut | Ctrl+X |
| Paste | Ctrl+V |
| Select All | Ctrl+A |
| Delete | Del |
| Rotate CW | R |
| Rotate CCW | Shift+R |
| Flip horizontal | F |
| Flip vertical | Shift+F |
| Generate netlist | Ctrl+G |
| Run simulation | F5 |
| Zoom in | Ctrl+= |
| Zoom out | Ctrl+- |
| Fit circuit | Ctrl+0 |
| Reset zoom | Ctrl+1 |

All shortcuts are configurable via **Edit → Keybindings…**

---

## 13. Auto-Save and Recovery

SDM Spice automatically saves your circuit every 60 seconds to a temporary file. If the application crashes, you will be asked to recover your work on next startup. The autosave file is cleared on a clean exit.

**Manual save:** Always press **Ctrl+S** before closing — autosave is a safety net, not a substitute.

---

## 14. Troubleshooting

### "No ground node" Error
Every circuit must have at least one **Ground (GND)** component connected.

### "Floating node" Error
All nodes must connect to at least two components. Check for unconnected wire endpoints.

### "ngspice not found" Error
ngspice is not installed or not on your PATH.
- Windows: Check **Edit → Preferences** and verify the ngspice path.
- Linux/macOS: Run `ngspice --version` in a terminal. If not found, install it.

### "Singular matrix" Error
Circuit topology issue:
- Voltage sources in parallel
- Current sources in series with no other path
- Node with no DC path to ground

### Simulation Takes Too Long
- Reduce transient duration or increase time step
- Simplify the circuit for initial testing
- Check for convergence issues in complex nonlinear circuits

### Display Issues on Linux

```bash
sudo apt install libxcb-xinerama0
```

---

## 15. Instructor Features

### Assignment Templates

Create a circuit, then **File → Save as Template** to distribute it to students. Students open it via **File → Templates**.

### Grading

1. Define a rubric (expected components, connections, simulation results)
2. Collect student `.json` circuit files
3. Use **Grade → Batch Grade** to auto-grade multiple submissions
4. Export feedback and grade distributions

### Palette Profiles

Restrict which components appear in the palette for a specific assignment:
**Edit → Preferences → Palette Profile** — select a built-in profile (`circuits_1`, `circuits_2`) or load a custom one.

---

## 16. Scripting (Researchers and Advanced Users)

SDM Spice exposes a headless Python API for programmatic circuit creation:

```python
from scripting.circuit import Circuit

c = Circuit()
c.add_component("Resistor", value="1k", position=(100, 100))
c.add_component("VoltageSource", value="5", position=(100, 200))
c.connect("V1", 0, "R1", 0)
result = c.run_dc_op()
print(result.node_voltages)
```

Jupyter notebook integration with inline rendering is available via `scripting/jupyter.py`.

The CLI (`python -m app.cli --help`) supports batch simulation from the command line.