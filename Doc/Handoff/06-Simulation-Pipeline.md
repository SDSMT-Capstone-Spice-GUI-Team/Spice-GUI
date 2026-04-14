# Simulation Pipeline

## End-to-End Flow

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│ CircuitModel │────▶│ NetlistGenerator │────▶│ SPICE Netlist │
│ (in memory)  │     │                  │     │ (text string) │
└──────────────┘     └──────────────────┘     └──────┬────────┘
                                                     │
                     ┌──────────────────┐            │
                     │  NgspiceRunner   │◀───────────┘
                     │  (subprocess)    │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐     ┌──────────────────┐
                     │  ngspice output  │────▶│  ResultParser    │
                     │  (stdout/files)  │     │                  │
                     └──────────────────┘     └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │ SimulationResult │
                                              │ (structured data)│
                                              └──────────────────┘
```

## Step-by-Step

### 1. Validation
`CircuitSemanticValidator` checks the circuit before simulation:
- At least one voltage/current source exists
- Ground node is present
- No floating nodes or disconnected components
- Analysis type is configured

### 2. Netlist Generation
`NetlistGenerator.generate()` walks the `CircuitModel` and produces SPICE syntax:

```spice
* Circuit: Voltage Divider
V1 nodeA 0 5V
R1 nodeA nodeB 1k
R2 nodeB 0 2k
.op
.end
```

### 3. Execution
`NgspiceRunner` writes the netlist to a temp file, runs `ngspice -b <file>`, and captures output.

### 4. Result Parsing
`ResultParser` extracts node voltages, branch currents, and measurement values from the text output into a `SimulationResult` dict.

## Supported Analysis Types

| Analysis | SPICE Directive | What It Computes |
|----------|----------------|-----------------|
| DC Operating Point | `.op` | Steady-state voltages and currents |
| DC Sweep | `.dc` | Sweep a source value, plot response |
| AC Sweep | `.ac` | Frequency response (magnitude + phase) |
| Transient | `.tran` | Time-domain waveforms |
| Temperature Sweep | `.temp` | Response over temperature range |
| Noise | `.noise` | Noise spectral density |
| Sensitivity | `.sens` | Output sensitivity to component values |
| Transfer Function | `.tf` | Gain, input/output impedance |
| Pole-Zero | `.pz` | Stability analysis |

## Advanced Features

- **Parameter Sweep** — batch runs varying a component value
- **Monte Carlo** — statistical analysis with component tolerances
- **FFT Analysis** — frequency domain from transient data
- **Power Metrics** — average, RMS, peak power calculation
- **Convergence Analysis** — checks if simulation converged properly
- **Measurement Directives** — custom `.meas` expressions for automated measurements