# Analysis Types

SDM Spice supports multiple types of circuit analysis through ngspice integration, plus advanced features like parameter sweeps, FFT/harmonic analysis, and temperature sweeps.

## DC Operating Point (.op)

### Description
Calculates the steady-state (DC) voltages and currents in the circuit with all capacitors treated as open circuits and all inductors treated as short circuits.

### When to Use
- Finding quiescent (bias) points in amplifier circuits
- Verifying DC voltage levels
- Initial circuit verification

### Parameters
None required.

### How to Run
1. Go to **Analysis > DC Operating Point (.op)**
2. Press **F5** or **Simulation > Run Simulation**

### Output
- Node voltages displayed on the canvas
- All node voltages and branch currents in the results panel

### Example Output
```
Node Voltages:
V(n001) = 10.0000
V(n002) = 6.6667
V(n003) = 0.0000
```

---

## DC Sweep

### Description
Sweeps a DC source through a range of values and records how circuit voltages and currents change. Useful for characterizing circuit behavior over a range of input conditions.

### When to Use
- Plotting transfer characteristics (Vout vs Vin)
- Finding operating ranges
- Characterizing nonlinear circuits

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Source | The voltage source to sweep | V1 |
| Start | Starting voltage value | 0 |
| Stop | Ending voltage value | 10 |
| Step | Voltage increment | 0.1 |

### How to Run
1. Go to **Analysis > DC Sweep**
2. Configure parameters in the dialog
3. Press **F5** or **Simulation > Run Simulation**

### Output
- Plot of node voltages vs swept source voltage
- Data table with all sweep points

### SPICE Command Generated
```spice
.dc V1 0 10 0.1
```

---

## AC Sweep

### Description
Performs frequency-domain analysis by applying a small-signal AC excitation and sweeping through a range of frequencies. Shows how the circuit responds to different frequencies (frequency response).

### When to Use
- Analyzing filters (low-pass, high-pass, band-pass)
- Finding resonant frequencies
- Measuring gain and phase vs frequency
- Bode plot generation

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Start Frequency | Starting frequency (Hz) | 1 |
| Stop Frequency | Ending frequency (Hz) | 1000000 |
| Points per Decade | Number of frequency points per decade | 100 |
| Sweep Type | Decade (dec), Octave (oct), or Linear (lin) | dec |

### How to Run
1. Go to **Analysis > AC Sweep**
2. Configure parameters in the dialog
3. Ensure your voltage source has an AC magnitude set
4. Press **F5** or **Simulation > Run Simulation**

### Output
- Magnitude plot (dB vs frequency)
- Phase plot (degrees vs frequency)
- Data table with complex values

### SPICE Command Generated
```spice
.ac dec 100 1 1000000
```

### Note
For AC analysis, voltage sources need an AC magnitude specified. The waveform source or a voltage source with AC parameters should be used.

---

## Transient Analysis

### Description
Simulates the circuit behavior over time. Shows how voltages and currents change from an initial state, including the effects of capacitors charging, inductors responding, and time-varying sources.

### When to Use
- Analyzing switching circuits
- Viewing waveforms from oscillators
- Studying rise/fall times
- Simulating pulse responses
- Any time-domain behavior analysis

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Duration | Total simulation time | 10m (10 milliseconds) |
| Time Step | Maximum time step | 1u (1 microsecond) |
| Start Time | When to start recording (optional) | 0 |

### How to Run
1. Go to **Analysis > Transient**
2. Configure parameters in the dialog
3. Add a time-varying source (Waveform Source) to your circuit
4. Press **F5** or **Simulation > Run Simulation**

### Output
- Waveform plot (voltage/current vs time)
- Interactive plot with zoom and pan
- Data table with time-series values
- Toggle visibility of individual waveforms

### SPICE Command Generated
```spice
.tran 1u 10m
```

### Tips
- Use a small enough time step to capture fast transitions
- For 1kHz signals, a time step of 1us or smaller is recommended
- Longer simulations generate more data points

---

## Temperature Sweep

### Description
Runs a simulation across a range of temperatures to observe how circuit behavior changes with temperature. Useful for understanding thermal sensitivity and ensuring designs work across operating conditions.

### When to Use
- Evaluating circuit stability over temperature
- Characterizing semiconductor behavior vs temperature
- Verifying designs meet specifications across an operating range

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Start Temperature | Starting temperature (°C) | -40 |
| Stop Temperature | Ending temperature (°C) | 125 |
| Step | Temperature increment (°C) | 5 |

### How to Run
1. Go to **Analysis > Temperature Sweep**
2. Configure temperature range in the dialog
3. Press **F5** or **Simulation > Run Simulation**

### Output
- Plot of circuit parameters vs temperature
- Results overlaid for comparison across temperature points

---

## Parameter Sweep

### Description
Sweeps a component parameter (e.g., resistance, capacitance) across a range of values, running the selected analysis at each step. Results are overlaid on a single plot for easy comparison.

### When to Use
- Exploring how a component value affects circuit behavior
- Sensitivity analysis
- Finding optimal component values
- Comparing design trade-offs

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Component | The component to sweep | R1 |
| Start Value | Starting parameter value | 1k |
| Stop Value | Ending parameter value | 10k |
| Steps | Number of sweep steps | 10 |

### How to Run
1. Go to **Simulation > Parameter Sweep**
2. Select the component and value range
3. Choose the underlying analysis type (DC OP, DC Sweep, AC, Transient)
4. Click **Run Sweep**

### Output
- Overlaid traces for each parameter value, color-coded and labeled
- Legend showing the parameter value for each trace
- Toggle individual traces on/off

---

## FFT / Harmonic Analysis

### Description
Performs Fast Fourier Transform on transient simulation results to show the frequency spectrum. Identifies fundamental frequency, harmonics, and computes Total Harmonic Distortion (THD%).

### When to Use
- Analyzing distortion in amplifier circuits
- Identifying harmonic content of waveforms
- Measuring THD for audio or signal circuits
- Verifying oscillator frequency purity

### How to Run
1. Run a **Transient** analysis first
2. In the Waveform Viewer, click **Show Spectrum**
3. Select a windowing function (Hann, Hamming, etc.)
4. View frequency spectrum with harmonic markers

### Output
- Frequency spectrum plot (magnitude vs frequency)
- Fundamental frequency and harmonic markers
- THD% calculation
- Selectable windowing functions for spectral accuracy

---

## Analysis Comparison

| Analysis | Domain | Typical Use | Output |
|----------|--------|-------------|--------|
| DC Operating Point | DC | Bias point verification | Single set of values |
| DC Sweep | DC | Transfer characteristics | Voltage/current vs source |
| AC Sweep | Frequency | Filter response | Magnitude/phase vs frequency |
| Transient | Time | Waveform analysis | Voltage/current vs time |
| Temperature Sweep | Temperature | Thermal sensitivity | Parameters vs temperature |
| Parameter Sweep | Varies | Component sensitivity | Overlaid traces per value |
| FFT Analysis | Frequency | Harmonic distortion | Spectrum from transient data |

---

## Running Simulations

### Via Menu
1. Select analysis type from **Analysis** menu
2. Configure parameters (if applicable)
3. Click **Simulation > Run Simulation**

### Via Keyboard
1. Select analysis type from **Analysis** menu
2. Press **F5**

### Via Netlist
1. Press **Ctrl+G** to generate netlist
2. The netlist appears in the results panel
3. Press **F5** to run simulation

---

## Simulation Results

### Canvas Display
- DC Operating Point shows node voltages and branch currents directly on the canvas as annotations
- Annotations can be toggled on/off via **View > Show Annotations**
- Annotations use distinct styling to avoid overlap with circuit elements

### Results Panel
- Text output from ngspice
- Numerical values for all nodes and branches
- Power dissipation per component (P = V × I)

### Waveform Viewer
- For DC Sweep, AC Sweep, and Transient analyses
- Interactive matplotlib plots
- Zoom, pan, and export capabilities
- Toggle individual traces on/off
- Data table with scrollable results
- **Measurement cursors**: Two vertical cursors (A & B) that snap to data points and display X/Y values with delta measurements (ΔX, ΔY)
- **Result overlay**: Run multiple simulations and overlay results for comparison, with color-coded traces and toggleable legend
- **CSV export**: Export simulation data to CSV for external analysis
- **Frequency response markers** (AC Sweep): Auto-detected -3dB cutoff, bandwidth, unity-gain frequency, gain/phase margins shown on Bode plots

---

## Troubleshooting

### "No ground node" Error
Every circuit needs at least one ground (GND) component connected.

### "Floating node" Error
All nodes must be connected to at least two components. Check for unconnected terminals.

### "Singular matrix" Error
Usually indicates a problem with the circuit topology:
- Voltage sources in parallel
- Current sources in series
- No DC path to ground for a node

### Simulation Takes Too Long
- Reduce transient duration
- Increase time step (but not too much)
- Simplify the circuit for initial testing

---

## See Also

- [[Components]] - Available circuit elements
- [[Quick Start Tutorial]] - Step-by-step guide
- [[Keyboard Shortcuts]] - Faster workflow
