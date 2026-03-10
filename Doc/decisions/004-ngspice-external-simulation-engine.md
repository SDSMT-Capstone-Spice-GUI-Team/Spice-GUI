# ADR 004: ngspice as External Simulation Engine

**Date:** 2024-09-15 (Initial implementation)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** Early prototype commits, ef2d7b5

---

## Context

SDM Spice needs to perform circuit simulation to provide students with accurate analysis of their designs. The application must support:
- **DC Operating Point** - Steady-state node voltages and currents
- **DC Sweep** - Parameter sweeps (voltage source variation)
- **AC Sweep** - Frequency domain analysis (Bode plots, impedance)
- **Transient** - Time-domain simulation (waveforms)

### Options for Simulation
1. **External SPICE engine** (ngspice, LTspice, Xyce)
2. **Python SPICE library** (PySpice with direct binding)
3. **Build custom simulator** (circuit solver from scratch)
4. **Commercial SPICE API** (PSpice, HSPICE)

### Requirements
- **Accuracy:** Industry-standard SPICE simulation
- **Free/Open-source:** No licensing costs for students
- **Cross-platform:** Windows, macOS, Linux
- **Well-documented:** Students can learn standard SPICE syntax
- **Active maintenance:** Continued bug fixes and support

---

## Decision

**We will use ngspice as an external process, generating SPICE netlists and parsing ngspice output.**

### Architecture

```
Circuit Model
    ↓
Netlist Generator (Python) → SPICE netlist text
    ↓
ngspice subprocess → Execute simulation
    ↓
Result Parser (Python) → Parse ngspice output
    ↓
Simulation Results → Display in GUI
```

### Integration Method
- **Netlist generation:** Python code builds `.cir` netlist from CircuitModel
- **Execution:** `subprocess.run(['ngspice', '-b', 'netlist.cir'])`
- **Output parsing:** Regex and text processing of ngspice stdout
- **Data format:** CSV/tabular output from ngspice `.print` commands

---

## Consequences

### Positive

✅ **Industry-standard:** Students learn SPICE, transferable to other tools
✅ **Accurate:** Proven simulation engine used in professional EDA
✅ **Free & open-source:** No licensing costs, inspectable source
✅ **Cross-platform:** Available on Windows, macOS, Linux
✅ **Actively maintained:** Regular releases, bug fixes, community support
✅ **Comprehensive:** Supports all SPICE models (BJT, MOSFET, Op-Amp, etc.)
✅ **Decoupled:** We don't maintain simulation engine, focus on GUI
✅ **Debuggable:** Students can inspect generated netlists, run manually

### Negative

❌ **External dependency:** Users must install ngspice separately
❌ **Installation friction:** Not bundled with application
❌ **PATH requirement:** Must be in system PATH or configured
❌ **Subprocess overhead:** Process startup latency (~50-200ms)
❌ **Output parsing fragility:** ngspice output format can change
❌ **Error handling:** Must parse text errors, no structured API
❌ **Platform differences:** PATH detection varies (Windows/Unix)

### Mitigation Strategies

**Installation:**
- Document installation in README for each platform
- Detect ngspice on startup, show friendly error if missing
- Future: Bundle ngspice binary with application (if licensing allows)

**PATH detection:**
```python
def find_ngspice():
    # Try common locations
    paths = [
        'ngspice',  # In PATH
        r'C:\Program Files\ngspice\bin\ngspice.exe',  # Windows default
        '/usr/local/bin/ngspice',  # macOS Homebrew
        '/usr/bin/ngspice'  # Linux package manager
    ]
    for path in paths:
        if shutil.which(path):
            return path
    raise FileNotFoundError("ngspice not found")
```

**Output parsing robustness:**
- Use regex with flexible whitespace matching
- Handle multiple ngspice version output formats
- Add tests with real ngspice output samples
- Graceful degradation if parsing fails

**Error messages:**
- Parse ngspice error output for common issues
- Show user-friendly messages ("Ground node missing" vs raw error)

---

## Alternatives Considered

### Alternative 1: PySpice Library (Python Bindings)
**Approach:** Use PySpice package which wraps ngspice shared library

**Pros:**
- No subprocess overhead
- Structured Python API
- Direct access to simulation data

**Rejected because:**
- PySpice development stalled (last release 2019)
- Requires compiled shared library (platform-specific builds)
- Harder to debug (black-box Python wrapper)
- Students can't inspect intermediate steps
- Adds dependency that's harder to install than ngspice itself

### Alternative 2: Build Custom Simulator
**Approach:** Implement circuit solver in Python (NumPy/SciPy)

**Pros:**
- Full control over simulation
- No external dependencies
- Could optimize for educational use cases

**Rejected because:**
- Enormous development effort (person-years)
- Would never match SPICE accuracy/completeness
- Must implement all device models (BJT, MOSFET, etc.)
- Defeats purpose: students need to learn industry-standard SPICE
- Maintenance burden grows indefinitely

### Alternative 3: Commercial SPICE (PSpice, HSPICE)
**Approach:** Integrate with commercial SPICE tools

**Rejected because:**
- Licensing costs prohibitive for students
- Closed-source (can't inspect/modify)
- Platform-specific (not cross-platform)
- Against open-source mission of project

### Alternative 4: Xyce (Sandia SPICE)
**Approach:** Use Xyce parallel SPICE simulator

**Pros:**
- Open-source, modern codebase
- Parallel simulation (faster for large circuits)

**Rejected because:**
- Less widely adopted than ngspice (smaller community)
- Installation more complex (fewer binary packages)
- Students less likely to encounter in industry
- Can reconsider in future if ngspice becomes inadequate

### Alternative 5: LTspice
**Approach:** Use LTspice command-line mode

**Pros:**
- Very fast simulation
- Widely used in industry
- Good device models

**Rejected because:**
- Windows-only (not cross-platform)
- Closed-source (can't fix bugs)
- Output format proprietary
- Freeware but not open-source

---

## Implementation Details

### Netlist Generation
```python
# netlist_generator.py
def generate_netlist(circuit: CircuitModel, analysis: AnalysisConfig) -> str:
    lines = ["* Generated by SDM Spice"]

    # Add components
    for comp in circuit.components:
        lines.append(f"{comp.id} {comp.netlist_line()}")

    # Add analysis command
    if analysis.type == 'transient':
        lines.append(f".tran {analysis.tstep} {analysis.tstop}")

    # Add output directives
    lines.append(".control")
    lines.append("run")
    lines.append("print all")
    lines.append(".endc")
    lines.append(".end")

    return "\n".join(lines)
```

### Execution
```python
# ngspice_runner.py
def run_simulation(netlist: str, timeout: int = 30) -> str:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cir', delete=False) as f:
        f.write(netlist)
        netlist_path = f.name

    try:
        result = subprocess.run(
            ['ngspice', '-b', netlist_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout
    finally:
        os.unlink(netlist_path)
```

### Output Parsing
```python
# result_parser.py
def parse_transient_output(output: str) -> Dict[str, np.ndarray]:
    # Find data section
    match = re.search(r'Values:\n(.*?)$', output, re.DOTALL)
    if not match:
        raise ValueError("No simulation data found")

    # Parse tabular data
    data = {}
    for line in match.group(1).split('\n'):
        if match := re.match(r'\s*(\d+)\s+(\S+)\s+=\s+([+-]?\d+\.?\d*e?[+-]?\d*)', line):
            var_name = match.group(2)
            value = float(match.group(3))
            data.setdefault(var_name, []).append(value)

    return {k: np.array(v) for k, v in data.items()}
```

---

## Platform-Specific Considerations

### Windows
- Installer from ngspice.sourceforge.io
- Default install: `C:\Program Files\ngspice\bin\`
- Must manually add to PATH or detect location

### macOS
- `brew install ngspice` (Homebrew)
- Automatically in PATH after install

### Linux (Debian/Ubuntu)
- `sudo apt install ngspice`
- Automatically in PATH after install

### CI/CD
- GitHub Actions: `apt install ngspice` in workflow
- xvfb not needed for headless ngspice execution

---

## Testing Strategy

**Unit tests:**
- Netlist generation for all component types
- Output parsing with sample ngspice output files
- Error handling for malformed output

**Integration tests:**
- End-to-end simulation with real ngspice
- Verify results match expected values (voltage divider, RC circuit)
- Test all analysis types (OP, DC, AC, Transient)

**Manual tests:**
- Cross-platform verification (Windows/Mac/Linux)
- ngspice version compatibility (test 3+ versions)

---

## Future Considerations

### Potential Enhancements
1. **Bundle ngspice:** Package with application (evaluate licensing)
2. **ngspice shared library:** Switch to library API for better performance
3. **Parallel simulation:** Use Xyce for large circuits
4. **Cloud simulation:** Offload heavy simulations to server (Phase 6+)

### Monitoring ngspice Development
- Track ngspice releases for breaking changes
- Test new versions before recommending to users
- Document supported version range in README

---

## Related Decisions

- [ADR 003](003-json-circuit-file-format.md) - Circuit file format (netlist is separate)
- [ADR 002](002-mvc-architecture-zero-qt-dependencies.md) - SimulationController design

---

## References

- ngspice homepage: http://ngspice.sourceforge.io/
- Netlist generator: [netlist_generator.py](../../app/simulation/netlist_generator.py)
- ngspice runner: [ngspice_runner.py](../../app/simulation/ngspice_runner.py)
- Result parser: [result_parser.py](../../app/simulation/result_parser.py)
- Simulation tests: [test_simulation_controller.py](../../app/tests/unit/test_simulation_controller.py)

---

## Review and Revision

This decision should be reviewed if:
- ngspice development stalls or project becomes abandoned
- Performance becomes unacceptable for large circuits
- Platform compatibility issues arise
- Better open-source alternative emerges

**Status:** Working well across all platforms, no plans to change
