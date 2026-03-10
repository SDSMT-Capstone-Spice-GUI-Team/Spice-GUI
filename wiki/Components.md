# Components

SDM Spice includes a library of fundamental electronic components for circuit design.

## Available Components

### Resistor (R)

| Property | Value |
|----------|-------|
| Symbol | R |
| Terminals | 2 |
| Color | Blue |
| Status | Fully Functional |

**Description:** A passive two-terminal component that implements electrical resistance.

**Value Format:**
- `100` - 100 ohms
- `1k` - 1 kilo-ohm (1,000 ohms)
- `4.7k` - 4.7 kilo-ohms
- `1M` - 1 mega-ohm (1,000,000 ohms)

**SPICE Syntax:** `R<name> <node1> <node2> <value>`

---

### Capacitor (C)

| Property | Value |
|----------|-------|
| Symbol | C |
| Terminals | 2 |
| Color | Green |
| Status | Fully Functional |

**Description:** A passive two-terminal component that stores energy in an electric field.

**Value Format:**
- `1u` - 1 microfarad
- `100n` - 100 nanofarads
- `10p` - 10 picofarads
- `1m` - 1 millifarad

**SPICE Syntax:** `C<name> <node1> <node2> <value>`

---

### Inductor (L)

| Property | Value |
|----------|-------|
| Symbol | L |
| Terminals | 2 |
| Color | Orange |
| Status | Fully Functional |

**Description:** A passive two-terminal component that stores energy in a magnetic field.

**Value Format:**
- `1m` - 1 millihenry
- `100u` - 100 microhenries
- `10n` - 10 nanohenries

**SPICE Syntax:** `L<name> <node1> <node2> <value>`

---

### Voltage Source (V)

| Property | Value |
|----------|-------|
| Symbol | V |
| Terminals | 2 |
| Color | Red |
| Status | Fully Functional |

**Description:** An independent DC voltage source that maintains a constant voltage between its terminals.

**Value Format:**
- `5` - 5 volts
- `12` - 12 volts
- `3.3` - 3.3 volts

**SPICE Syntax:** `V<name> <node+> <node-> <value>`

---

### Current Source (I)

| Property | Value |
|----------|-------|
| Symbol | I |
| Terminals | 2 |
| Color | Purple |
| Status | Fully Functional |

**Description:** An independent DC current source that maintains a constant current through its terminals.

**Value Format:**
- `1m` - 1 milliamp
- `10u` - 10 microamps
- `1` - 1 amp

**SPICE Syntax:** `I<name> <node+> <node-> <value>`

---

### Waveform Source (VW)

| Property | Value |
|----------|-------|
| Symbol | VW |
| Terminals | 2 |
| Color | Pink |
| Status | Fully Functional |

**Description:** A time-varying voltage source that can generate different waveforms for transient analysis.

**Waveform Types:**

#### Sinusoidal (SIN)
Parameters: offset, amplitude, frequency, delay, damping, phase

Example: `SIN(0 5 1k 0 0 0)` - 5V amplitude, 1kHz sine wave

#### Pulse (PULSE)
Parameters: V1, V2, delay, rise time, fall time, pulse width, period

Example: `PULSE(0 5 0 1n 1n 0.5m 1m)` - 5V pulse, 1kHz

#### Exponential (EXP)
Parameters: V1, V2, delay1, tau1, delay2, tau2

Example: `EXP(0 5 0 1m 5m 1m)` - Exponential rise and fall

**Configuration:** Double-click the waveform source or use the "Configure Waveform" button in the Properties panel.

---

### Ground (GND)

| Property | Value |
|----------|-------|
| Symbol | GND |
| Terminals | 1 |
| Color | Black |
| Status | Fully Functional |

**Description:** The reference node (0V) for the circuit. Every circuit must have at least one ground connection.

**Important:**
- Ground is required for simulation
- All voltages are measured relative to ground
- SPICE node 0 is always ground

---

### Op-Amp (OA)

| Property | Value |
|----------|-------|
| Symbol | OA |
| Terminals | 5 |
| Color | Yellow |
| Status | Fully Functional |

**Description:** An ideal operational amplifier with very high gain.

**Terminals:**
1. Inverting input (-)
2. Non-inverting input (+)
3. Output
4. Positive supply (V+)
5. Negative supply (V-)

**Model:** Uses an ideal op-amp subcircuit with:
- Gain: 1,000,000 (1e6)
- Output resistance: 0.001 ohms

**Note:** Currently uses an ideal model. Real op-amp models with bandwidth limitations and other non-idealities are planned for future releases.

---

### Dependent Sources

#### VCVS — Voltage-Controlled Voltage Source (E)

| Property | Value |
|----------|-------|
| Symbol | E |
| Terminals | 4 |
| Status | Fully Functional |

**Description:** Output voltage is proportional to a controlling voltage elsewhere in the circuit.

**SPICE Syntax:** `E<name> <n+> <n-> <nc+> <nc-> <gain>`

---

#### CCVS — Current-Controlled Voltage Source (H)

| Property | Value |
|----------|-------|
| Symbol | H |
| Terminals | 4 |
| Status | Fully Functional |

**Description:** Output voltage is proportional to a controlling current elsewhere in the circuit.

**SPICE Syntax:** `H<name> <n+> <n-> <vcontrol> <gain>`

---

#### VCCS — Voltage-Controlled Current Source (G)

| Property | Value |
|----------|-------|
| Symbol | G |
| Terminals | 4 |
| Status | Fully Functional |

**Description:** Output current is proportional to a controlling voltage elsewhere in the circuit.

**SPICE Syntax:** `G<name> <n+> <n-> <nc+> <nc-> <gain>`

---

#### CCCS — Current-Controlled Current Source (F)

| Property | Value |
|----------|-------|
| Symbol | F |
| Terminals | 4 |
| Status | Fully Functional |

**Description:** Output current is proportional to a controlling current elsewhere in the circuit.

**SPICE Syntax:** `F<name> <n+> <n-> <vcontrol> <gain>`

---

### Semiconductors

#### Diode (D)

| Property | Value |
|----------|-------|
| Symbol | D |
| Terminals | 2 |
| Status | Fully Functional |

**Description:** A PN junction diode that allows current to flow in one direction.

**SPICE Syntax:** `D<name> <anode> <cathode> <model>`

---

#### LED — Light-Emitting Diode (D)

| Property | Value |
|----------|-------|
| Symbol | D |
| Terminals | 2 |
| Status | Fully Functional |

**Description:** A diode that emits light when forward-biased.

**SPICE Syntax:** `D<name> <anode> <cathode> <model>`

---

#### Zener Diode (D)

| Property | Value |
|----------|-------|
| Symbol | D |
| Terminals | 2 |
| Status | Fully Functional |

**Description:** A diode designed to operate in reverse breakdown, used for voltage regulation.

**SPICE Syntax:** `D<name> <anode> <cathode> <model>`

---

#### BJT NPN (Q)

| Property | Value |
|----------|-------|
| Symbol | Q |
| Terminals | 3 |
| Status | Fully Functional |

**Description:** NPN bipolar junction transistor. Current flows from collector to emitter when base current is applied.

**Terminals:** Base, Collector, Emitter

**SPICE Syntax:** `Q<name> <collector> <base> <emitter> <model>`

---

#### BJT PNP (Q)

| Property | Value |
|----------|-------|
| Symbol | Q |
| Terminals | 3 |
| Status | Fully Functional |

**Description:** PNP bipolar junction transistor. Current flows from emitter to collector when base current is sunk.

**Terminals:** Base, Collector, Emitter

**SPICE Syntax:** `Q<name> <collector> <base> <emitter> <model>`

---

#### MOSFET NMOS (M)

| Property | Value |
|----------|-------|
| Symbol | M |
| Terminals | 3 |
| Status | Fully Functional |

**Description:** N-channel metal-oxide-semiconductor field-effect transistor.

**Terminals:** Gate, Drain, Source

**SPICE Syntax:** `M<name> <drain> <gate> <source> <body> <model>`

---

#### MOSFET PMOS (M)

| Property | Value |
|----------|-------|
| Symbol | M |
| Terminals | 3 |
| Status | Fully Functional |

**Description:** P-channel metal-oxide-semiconductor field-effect transistor.

**Terminals:** Gate, Drain, Source

**SPICE Syntax:** `M<name> <drain> <gate> <source> <body> <model>`

---

### Switches

#### Voltage-Controlled Switch (S)

| Property | Value |
|----------|-------|
| Symbol | S |
| Terminals | 4 |
| Status | Fully Functional |

**Description:** A switch that opens or closes based on a controlling voltage.

**SPICE Syntax:** `S<name> <n+> <n-> <nc+> <nc-> <model>`

---

## Component Value Notation

SDM Spice supports standard engineering notation:

| Suffix | Multiplier | Name |
|--------|------------|------|
| T | 10^12 | Tera |
| G | 10^9 | Giga |
| MEG | 10^6 | Mega |
| k | 10^3 | Kilo |
| m | 10^-3 | Milli |
| u | 10^-6 | Micro |
| n | 10^-9 | Nano |
| p | 10^-12 | Pico |
| f | 10^-15 | Femto |

**Examples:**
- `4.7k` = 4,700 ohms
- `100n` = 100 nanofarads = 0.0000001 farads
- `2.2u` = 2.2 microfarads

---

## Planned Components

The following components are planned for future releases:

- **Transformer** - Coupled inductors

See the [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) for component requests and status.

---

## See Also

- [[Quick Start Tutorial]] - Using components in a circuit
- [[Analysis Types]] - Running simulations
- [[File Formats]] - How circuits are saved
