# Roadmap

SDM Spice follows a phased development approach, prioritizing the student experience first before expanding to serve instructors and researchers.

## Development Phases

### Phase 1: Student MVP (Months 1-4) - CURRENT

**Goal:** Create a functional circuit design tool for individual student use.

**Status:** In Progress

**Features:**
- [x] Circuit schematic editor
- [x] Drag-and-drop component placement
- [x] Basic component library (R, L, C, V, I, GND)
- [x] Wire routing with pathfinding
- [x] Simulation engine integration (ngspice)
- [x] DC Operating Point analysis
- [x] DC Sweep analysis
- [x] AC Sweep analysis
- [x] Transient analysis
- [x] Waveform viewer
- [x] File save/load
- [x] Session persistence
- [ ] Comprehensive error messages
- [ ] Tutorials and getting started guide
- [ ] Example circuit library

**Success Criteria:**
- Student can complete basic lab assignments
- Simulation produces accurate results
- Interface is intuitive for beginners

---

### Phase 2: User Accounts & Cloud (Months 5-7)

**Goal:** Add authentication and cloud storage for student work.

**Planned Features:**
- User registration and login
- Email verification
- Password reset
- Cloud save/sync
- Project organization
- Version history
- Settings persistence

**Technical Requirements:**
- Backend API
- Database for user accounts
- Cloud file storage
- Session management

---

### Phase 3: Instructor Role - Basic (Months 8-10)

**Goal:** Enable instructors to create and distribute assignments.

**Planned Features:**
- Instructor role and permissions
- Course creation and management
- Student roster management
- Assignment creation with templates
- Assignment distribution
- Basic submission collection

---

### Phase 4: Instructor Role - Advanced (Months 11-13)

**Goal:** Add grading, analytics, and automated verification.

**Planned Features:**
- Manual grading interface
- Rubric support
- Automated circuit verification
- Class-wide analytics
- Grade export (CSV for LMS)
- Batch operations

---

### Phase 5: TA Role (Months 14-15)

**Goal:** Enable teaching assistants to support students.

**Planned Features:**
- TA role and permissions
- Student support interface
- Submission viewing
- Feedback tools
- Help queue system

---

### Phase 6: Researcher Role (Months 16-18)

**Goal:** Unlock advanced features for research users.

**Planned Features:**
- Advanced/Standard mode toggle
- Custom SPICE model import
- Subcircuit creation
- Scripting API (Python)
- Batch simulations
- Parameter sweeps
- Monte Carlo analysis
- Advanced data export

---

### Phase 7: Administration & Polish (Months 19-20)

**Goal:** Add system administration and finalize for deployment.

**Planned Features:**
- Administrator role
- User management interface
- System configuration
- LMS integration (Canvas, Blackboard, Moodle)
- SSO support
- Performance optimization
- Security hardening
- Accessibility compliance

---

## Timeline Summary

| Phase | Months | Focus | Key Deliverable |
|-------|--------|-------|-----------------|
| **1** | 1-4 | Student MVP | Functional circuit tool |
| **2** | 5-7 | User Accounts | Cloud-based workspace |
| **3** | 8-10 | Instructor Basic | Assignment distribution |
| **4** | 11-13 | Instructor Advanced | Grading & analytics |
| **5** | 14-15 | TA Role | Student support |
| **6** | 16-18 | Researcher Role | Advanced features |
| **7** | 19-20 | Admin & Polish | Full deployment |

**Total Duration:** ~20 months

---

## Current Sprint Focus

### Active Work
- Fixing properties panel display issue
- Resolving waveform source crashes
- DC current source netlist bug

### Next Up
- Additional components (Diode, BJT)
- Improved error handling
- User documentation

### Backlog
See [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) for full backlog.

---

## Feature Requests

To request a new feature:

1. Check existing [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) for duplicates
2. Create a new issue with the `enhancement` label
3. Provide detailed description of the feature
4. Explain the use case and benefit

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | TBD | Initial Student MVP release |

---

## See Also

- [[Project Scope]] - What's in and out of scope
- [[User Personas]] - Target users
- [[Contributing]] - How to contribute
