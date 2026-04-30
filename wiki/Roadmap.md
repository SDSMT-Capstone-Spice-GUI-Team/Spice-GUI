# Roadmap

SDM Spice follows a phased development approach, prioritizing the student experience first.

> **Note:** This roadmap reflects the **actual implementation plan** based on stakeholder feedback and project constraints. See [Project Evolution](../Doc/project-evolution.md) for how this evolved from initial discovery.

---

## Development Phases

### Phase 1: Student MVP (Current) ✅

**Goal:** Create a functional circuit design tool for individual student use.

**Status:** ✅ **COMPLETE** (Capstone Phase 1)

**Features Implemented:**
- [x] Circuit schematic editor with drag-and-drop
- [x] Grid-aligned layout (10px snap) - [ADR 011](../docs/adr/011-grid-aligned-layout-10px.md)
- [x] 20+ component library (R, L, C, V, I, Diode, LED, Zener, BJT NPN/PNP, MOSFET NMOS/PMOS, dependent sources, VC switch, Ground, Op-Amp)
- [x] Intelligent wire routing with A*/IDA*/Dijkstra pathfinding
- [x] Simulation engine integration (ngspice) - [ADR 007](../docs/adr/007-ngspice-external-simulation-engine.md)
- [x] All analysis types (DC OP, DC Sweep, AC, Transient, Temperature Sweep)
- [x] Parameter sweep across component values
- [x] FFT/harmonic analysis with THD calculation
- [x] Waveform viewer with measurement cursors and result overlay
- [x] Frequency response markers on Bode plots (AC Sweep)
- [x] DC operating point annotations on schematic
- [x] Interactive voltage/current probes
- [x] Power dissipation per component
- [x] File save/load (JSON format) - [ADR 006](../docs/adr/006-json-circuit-file-format.md)
- [x] SPICE netlist import (.cir/.spice)
- [x] Session persistence (auto-restore last circuit)
- [x] Auto-save with crash recovery
- [x] Export capabilities (CSV, PNG, SVG, PDF, netlist)
- [x] Component rotation, flip, and properties editing
- [x] In-place component value editing
- [x] Copy/paste/cut operations
- [x] Multi-select with marquee selection
- [x] Undo/redo system
- [x] Circuit annotations and net labels
- [x] Zoom controls
- [x] Dark mode and theme switching
- [x] Configurable keyboard shortcuts
- [x] Recent files menu
- [x] Comprehensive test suite - [ADR 009](../docs/adr/009-pytest-github-actions-testing.md)

**Architecture:**
- Desktop application (PyQt6) - [ADR 008](../docs/adr/008-pyqt6-desktop-framework.md)
- Local file storage only (no accounts) - [ADR 004](../docs/adr/004-local-first-no-user-accounts.md)
- MVC architecture with zero-Qt dependencies in core logic - [ADR 005](../docs/adr/005-mvc-architecture-zero-qt-dependencies.md) (testing rationale: [ADR 001](../docs/adr/001-mvc-testability.md))
- Ruff + black + isort + bandit for code quality - [ADR 010](../docs/adr/010-ruff-linting-code-quality.md)
- GitHub Actions CI/CD - [ADR 009](../docs/adr/009-pytest-github-actions-testing.md)
- develop + main branching with epic branches - [ADR 003](../docs/adr/003-branching-strategy.md)
- Tiered testing (CI gate + human-testing gate) - [ADR 002](../docs/adr/002-tiered-testing.md)

**Success Criteria:** ✅ Met
- Students can complete basic lab assignments
- Simulation produces accurate results
- Interface is intuitive for beginners
- Runs reliably on Windows, macOS, Linux

---

### Phase 2: Enhanced Export/Sharing and LMS Integration

**Goal:** Enable assignment distribution and submission without building custom account system.

**Status:** 📋 Planned

**Planned Features:**
- Enhanced export features (circuit reports, better image export)
- LMS integration via API (Canvas, Blackboard)
  - Export assignment as template JSON
  - Submit completed circuit via LMS file upload
- Shared circuit library (read-only examples, no accounts needed)
- Batch operations via CLI (for instructors)
- Improved documentation and tutorials

**Technical Approach:**
- **No user accounts** - Leverage existing LMS infrastructure
- **File-based distribution** - Templates shared as JSON files
- **Integration not duplication** - Use existing tools for what they do well

**Rationale:** See [ADR 004](../docs/adr/004-local-first-no-user-accounts.md)

---

### Phase 3: Instructor Tools (Templates, Assignments)

**Goal:** Support instructor workflows without custom assignment system.

**Planned Features:**
- Assignment template creation wizard
- Verification scripts for auto-grading
  - Define circuit requirements (component count, values)
  - Simulation result checking (voltage at node X = Y ± tolerance)
- Template circuit library
- Bulk circuit validation tools
- Export to LMS-compatible format

**Technical Approach:**
- Local tools (desktop app features)
- Command-line utilities for batch operations
- Export scripts for LMS integration
- No cloud storage required

---

### Phase 4: Advanced Instructor Features (Analytics)

**Goal:** Provide analytics and insights without centralized system.

**Planned Features:**
- Circuit analysis tools (complexity metrics)
- Batch testing of student circuits (via CLI)
- Common error detection
- Export data for external analytics tools
- Rubric templates

**Technical Approach:**
- Standalone analysis scripts
- Export to CSV/Excel for instructors to analyze
- Integration with existing analytics tools

---

### Phase 5: TA Role Support

**Goal:** Enable TAs to help students effectively.

**Planned Features:**
- Annotation and feedback tools
- Circuit review mode (read-only view with comments)
- Help documentation for TAs
- Quick-reference guides

**Note:** Without multi-user accounts, TA "role" is more about tooling than permissions.

---

### Phase 6: Researcher Features (Scripting API)

**Goal:** Unlock advanced features for research users.

**Planned Features:**
- Python scripting API for automation
- Batch simulation capabilities
- Parameter sweep utilities
- Custom SPICE model import
- Advanced data export formats
- Performance profiling tools
- Integration with Jupyter notebooks

**Technical Approach:**
- Expose model/controller as Python API
- CLI tools for scripting
- No GUI changes needed (use programmatic interface)

---

### Phase 7: Advanced Features and Polish

**Goal:** Refine and optimize for production use.

**Planned Features:**
- Performance optimization
- Advanced component models
- Improved error messages
- Accessibility improvements
- Mobile/tablet view support (read-only)
- Internationalization (if needed)

---

## Timeline Summary

| Phase | Duration | Focus | Status |
|-------|----------|-------|--------|
| **1** | Months 1-8 | Student MVP | ✅ Complete |
| **2** | TBD | Enhanced export & LMS integration | 📋 Planned |
| **3** | TBD | Instructor tools | 📋 Planned |
| **4** | TBD | Advanced instructor features | 📋 Planned |
| **5** | TBD | TA support | 📋 Planned |
| **6** | TBD | Researcher features | 📋 Planned |
| **7** | TBD | Advanced features & polish | 📋 Planned |

**Note:** Timeline depends on post-Capstone project continuation and available resources.

---

## What Changed From Initial Discovery?

**Initial Discovery Vision (Exploratory):**
- Multi-user SaaS with 5 roles (Student, Instructor, TA, Researcher, Admin)
- Cloud storage with cross-device sync
- Custom authentication and user management
- Role-based permissions and SSO
- 20-month implementation timeline

**Actual Implementation (Stakeholder-Informed):**
- Local-first desktop application
- No user accounts or cloud storage
- Leverage existing tools (LMS, file sharing)
- Focus on core circuit simulation quality
- Realistic timeline for Capstone project

**Why the Change:**
- Capstone timeline constraints (8 months vs 20 months)
- Team capacity and post-graduation maintenance
- Infrastructure costs and complexity
- FERPA compliance simpler with local files
- Stakeholder feedback prioritizing simulation quality

**Full Story:** See [Project Evolution](../Doc/project-evolution.md) and [ADR 004](../docs/adr/004-local-first-no-user-accounts.md)

---

## Current Status (as of Feb 2026)

### Recently Completed
- ✅ Dark mode and theme switching
- ✅ Parameter sweep across component values
- ✅ Measurement cursors in waveform viewer
- ✅ Configurable keyboard shortcuts
- ✅ Auto-save and crash recovery
- ✅ Overlay multiple simulation results
- ✅ FFT/harmonic analysis for transient results
- ✅ Temperature sweep analysis
- ✅ Fourier/FFT analysis
- ✅ SPICE netlist import (.cir/.spice)
- ✅ DC operating point annotations on schematic
- ✅ Interactive voltage/current probes
- ✅ Frequency response markers on Bode plots
- ✅ Power dissipation per component
- ✅ Drag-and-drop from component palette
- ✅ In-place component value editing
- ✅ Circuit annotations and net labels
- ✅ Copy/paste/cut for components
- ✅ Image/PDF export (PNG/SVG/PDF)
- ✅ CSV export for simulation data
- ✅ Diodes, LEDs, Zener diodes, BJTs, MOSFETs
- ✅ Voltage-controlled switch
- ✅ Dependent sources (VCVS, CCVS, VCCS, CCCS)
- ✅ Multi-select with marquee selection
- ✅ Component flip (horizontal/vertical)
- ✅ Undo/redo system
- ✅ Zoom controls
- ✅ Recent files menu

### In Progress
- Wire labels and net names
- Monte Carlo analysis for component tolerance simulation
- Documentation and examples

### Next Up
- Print preview and print schematic
- Additional polish and bug fixes

---

## Feature Requests

**How to Request Features:**

1. Check [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) for existing requests
2. Review [DiscoveryDocs](../Doc/DiscoveryDocs/) to see if it was already explored
3. Create new issue with `enhancement` label
4. Explain use case and how it aligns with local-first architecture

**Note:** Features requiring user accounts or cloud storage are unlikely to be prioritized. See [ADR 004](../docs/adr/004-local-first-no-user-accounts.md) for rationale.

---

## See Also

- **[Architecture Decision Records](../docs/adr/)** - Technical decisions with rationale
- **[Architecture Guides](../docs/architecture/)** - Canvas internals, GUI protocols, implementation details
- **[Project Evolution](../Doc/project-evolution.md)** - How we got from discovery to implementation
- **[Development Methodology](../Doc/autonomous-workflow.md)** - How we build this software
- **[Discovery Documentation](../DiscoveryDocs/)** - Initial exploration (academic assignment)
- **[Project Scope](Project-Scope.md)** - What's in and out of scope
- **[Contributing](Contributing.md)** - How to contribute

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 (Phase 1) | Feb 2026 | Initial Student MVP - Core circuit design and simulation |

---

*Last Updated: 2026-02-10*
