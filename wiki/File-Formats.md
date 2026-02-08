# File Formats

SDM Spice uses several file formats for circuits, simulation, and data.

## Circuit Files (.json)

SDM Spice saves circuits in JSON format for easy readability and portability.

### File Structure

```json
{
  "version": "1.0",
  "metadata": {
    "created": "2024-01-15T10:30:00Z",
    "modified": "2024-01-15T14:45:00Z",
    "author": "username"
  },
  "components": [
    {
      "id": "R1",
      "type": "Resistor",
      "value": "1k",
      "position": [100, 200],
      "rotation": 0,
      "properties": {}
    },
    {
      "id": "V1",
      "type": "VoltageSource",
      "value": "10",
      "position": [100, 100],
      "rotation": 0,
      "properties": {}
    }
  ],
  "wires": [
    {
      "id": "W1",
      "start_component": "R1",
      "start_terminal": 0,
      "end_component": "V1",
      "end_terminal": 1,
      "path": [[100, 180], [100, 150], [100, 120]]
    }
  ],
  "nodes": [
    {
      "id": "N1",
      "label": "Vout",
      "position": [150, 150]
    }
  ]
}
```

### Component Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (R1, C1, V1, etc.) |
| `type` | string | Component type name |
| `value` | string | Component value with units |
| `position` | [x, y] | Canvas coordinates |
| `rotation` | number | Rotation in degrees (0, 90, 180, 270) |
| `properties` | object | Additional component-specific properties |

### Wire Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `start_component` | string | Starting component ID |
| `start_terminal` | number | Terminal index on start component |
| `end_component` | string | Ending component ID |
| `end_terminal` | number | Terminal index on end component |
| `path` | [[x,y], ...] | Wire routing path points |

### Waveform Source Properties

For waveform sources, the `properties` object contains:

```json
{
  "waveform_type": "SIN",
  "parameters": {
    "offset": 0,
    "amplitude": 5,
    "frequency": 1000,
    "delay": 0,
    "theta": 0,
    "phase": 0
  }
}
```

---

## SPICE Netlist

Generated netlists follow standard SPICE syntax.

### Example Netlist

```spice
* SDM Spice Generated Netlist
* Circuit: voltage_divider.json
* Date: 2024-01-15

* Components
R1 n001 n002 1k
R2 n002 0 2k
V1 n001 0 10

* Analysis
.op

* Control
.control
run
print all
.endc

.end
```

### Netlist Sections

| Section | Purpose |
|---------|---------|
| Header | Comments with metadata |
| Components | Component definitions |
| Subcircuits | Custom component models |
| Analysis | Analysis command (.op, .dc, .ac, .tran) |
| Control | ngspice control commands |

### Component Syntax

| Component | Syntax |
|-----------|--------|
| Resistor | `R<name> <n+> <n-> <value>` |
| Capacitor | `C<name> <n+> <n-> <value>` |
| Inductor | `L<name> <n+> <n-> <value>` |
| Voltage Source | `V<name> <n+> <n-> <value>` |
| Current Source | `I<name> <n+> <n-> <value>` |
| Waveform | `V<name> <n+> <n-> SIN(...)` |

---

## Simulation Output

### DC Operating Point

Text format showing node voltages and branch currents:

```
Node Voltages:
V(n001) = 10.0000
V(n002) = 6.6667

Branch Currents:
I(V1) = -3.3333m
```

### Transient Data

Tab-separated values saved to file:

```
time	V(n001)	V(n002)	I(V1)
0.000000e+00	0.000000e+00	0.000000e+00	0.000000e+00
1.000000e-06	9.987654e+00	6.658765e+00	-3.328888e-03
2.000000e-06	9.999876e+00	6.666543e+00	-3.333210e-03
...
```

### AC Sweep Data

Complex values with magnitude and phase:

```
frequency	V(n002)_mag	V(n002)_phase
1.000000e+00	6.666667e+00	0.000000e+00
1.258925e+00	6.666665e+00	-1.234567e-02
...
```

---

## Session File

`last_session.txt` stores the path to the last opened circuit:

```
C:\Users\username\Documents\circuits\my_circuit.json
```

This enables automatic restoration on application startup.

---

## Export Formats (Future)

Planned export capabilities:

| Format | Purpose |
|--------|---------|
| PNG/SVG | Schematic image export |
| PDF | Documentation/printing |
| CSV | Simulation data for spreadsheets |
| Raw SPICE | Standard netlist format |

---

## Import Formats (Future)

Planned import capabilities:

| Format | Purpose |
|--------|---------|
| SPICE Netlist | Import existing circuits |
| LTspice | Cross-tool compatibility |
| KiCad | Schematic import |

---

## File Locations

### Windows
```
%USERPROFILE%\Documents\SDM Spice\
├── circuits\          # Saved circuits
├── exports\           # Exported files
└── temp\              # Temporary simulation files
```

### macOS/Linux
```
~/Documents/SDM Spice/
├── circuits/
├── exports/
└── temp/
```

---

## Best Practices

1. **Use descriptive filenames**: `rc_lowpass_filter.json` not `circuit1.json`
2. **Organize by project**: Create folders for related circuits
3. **Version your work**: Use Save As for major changes
4. **Back up important circuits**: Copy to cloud storage

---

## See Also

- [[Quick Start Tutorial]] - Saving and loading
- [[Components]] - Component specifications
- [[Analysis Types]] - Simulation options
