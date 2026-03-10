# Project Scope

This document defines what SDM Spice will and will not include.

## Project Vision

SDM Spice aims to make circuit simulation approachable for every student, efficient for every instructor, and powerful enough for every researcher.

## In Scope

### Phase 1: Student MVP (Current)

**Circuit Design**
- Desktop circuit schematic editor
- Drag-and-drop component placement
- Grid-aligned layout
- Interactive wire routing with pathfinding
- Component rotation and manipulation
- Visual component library

**Components**
- Passive components (R, L, C)
- DC voltage and current sources
- Waveform sources (SIN, PULSE, EXP)
- Ground reference
- Ideal op-amp

**Simulation**
- DC Operating Point analysis
- DC Sweep analysis
- AC Sweep analysis
- Transient analysis
- Integration with ngspice

**Visualization**
- Node voltage display on canvas
- Waveform viewer with matplotlib
- Interactive plots
- Data tables

**File Management**
- Save/Load circuits (JSON format)
- Session persistence
- Netlist generation

**Platform Support**
- Windows 10/11
- macOS 10.14+
- Linux (Ubuntu 20.04+)

### Phase 2: User Accounts (Future)
- User registration and login
- Cloud storage for circuits
- Project organization
- Settings persistence across devices

### Phase 3-4: Instructor Features (Future)
- Course creation and management
- Assignment creation and distribution
- Student submission collection
- Grading tools
- Analytics and insights

### Phase 5: TA Role (Future)
- Student support interface
- Limited grading capabilities
- Help queue system

### Phase 6: Researcher Features (Future)
- Advanced simulation controls
- Custom SPICE model import
- Scripting API (Python)
- Batch simulations
- Parameter sweeps

### Phase 7: Administration (Future)
- User management
- System configuration
- LMS integration (Canvas, Blackboard, Moodle)
- SSO support

## Out of Scope

The following items are explicitly **not** part of SDM Spice:

### Hardware Design
- PCB layout design
- Gerber file generation
- Bill of Materials (BOM) management
- Manufacturing outputs
- Physical design rule checking

### Advanced Simulation
- Electromagnetic simulation
- Thermal analysis
- Mixed-signal (analog + digital) simulation
- Hardware-in-the-loop testing
- Real-time simulation

### Other CAD Features
- 3D visualization
- Mechanical CAD integration
- Enclosure design
- Cable/harness design

### Enterprise Features
- Multi-tenant deployment
- High-availability clustering
- Audit logging for compliance
- Enterprise SSO (LDAP/Active Directory) - basic SSO planned

## Boundaries

### What SDM Spice IS
- An educational tool for learning circuit simulation
- A visual schematic capture application
- A frontend for ngspice simulation
- A platform for circuit analysis assignments

### What SDM Spice IS NOT
- A replacement for professional EDA tools (Cadence, Altium, KiCad)
- A PCB design tool
- A hardware testing platform
- A real-time simulation system

## Success Criteria

### Phase 1 (Student MVP)
- Student can complete a basic lab assignment (voltage divider, RC circuit)
- Simulation produces accurate results matching hand calculations
- Interface is intuitive for beginners (validated through usability testing)
- Runs reliably on campus lab machines

### Overall Project
- 80% of pilot students use the tool for assignments
- 4/5 average rating on usability surveys
- Simulation results match professional tools within acceptable tolerance
- Less than 5% data loss incidents

## Scope Change Process

Any changes to this scope document require:

1. Discussion with the project team
2. Impact assessment
3. Stakeholder approval
4. Documentation update

Feature requests can be submitted via [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues).

## See Also

- [[Roadmap]] - Timeline for feature delivery
- [[User Personas]] - Target users
- [[Architecture Overview]] - Technical design
