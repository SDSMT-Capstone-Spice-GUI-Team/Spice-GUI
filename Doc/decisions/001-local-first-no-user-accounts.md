# ADR 001: Local-First Architecture Without User Accounts

**Date:** 2026-02-08
**Status:** Accepted
**Deciders:** Development Team

---

## Context

SDM Spice is an educational circuit design and simulation tool being developed for South Dakota School of Mines and Technology as a Capstone project.

### Discovery Phase vs. Implementation Reality

**Initial Discovery (Academic Assignment):**
During our discovery phase, we explored a comprehensive multi-user system with:
- 5 user roles (Student, Instructor, TA, Researcher, Administrator)
- Cloud-based storage with cross-device sync
- Assignment creation, submission, and grading workflows
- Role-based permissions and SSO integration
- 20-month phased implementation timeline

*See [DiscoveryDocs/](../../DiscoveryDocs/) for full initial exploration.*

**Stakeholder Discussions Revealed:**
After presenting discovery findings to faculty advisors, student users, IT stakeholders, and project sponsors, we identified critical constraints:

- **Timeline:** Capstone project duration (~8 months) insufficient for 20-month plan
- **Complexity:** Authentication, backend API, database infrastructure too ambitious for scope
- **Infrastructure:** No hosting budget, maintenance burden post-graduation
- **Privacy/Compliance:** FERPA concerns with cloud-stored student data
- **Existing Solutions:** LMS (Canvas, Blackboard) already handles assignment distribution well
- **Core Value:** Circuit simulation quality matters more than custom account system
- **Team Capacity:** Focus on what makes this tool unique (circuit design), not rebuilding auth

**The Pivot:**
We needed to decide whether to:
1. Build the multi-user cloud system (original discovery vision)
2. Pivot to local-first architecture (stakeholder-informed approach)

### Use Cases Considered

**Educational workflow:**
- Students need to design circuits for coursework
- Instructors may want to distribute templates/assignments
- Students need to submit work for grading
- Users may work from multiple locations (lab computers, home, etc.)

**Technical considerations:**
- Current implementation: PyQt6 desktop application
- File storage: Local JSON files with session persistence
- No existing server infrastructure
- Team capacity and maintenance constraints

---

## Decision

**We will maintain a local-first architecture without user accounts.**

Circuit files will continue to be stored locally as JSON. The application will remain a standalone desktop tool with no authentication, cloud storage, or backend server requirements.

---

## Consequences

### Positive

✅ **Simplicity**: No backend infrastructure to build, secure, or maintain
✅ **Privacy**: Student data stays on their devices (FERPA-compliant by default)
✅ **Speed**: No network latency, works offline
✅ **Lower barrier**: No signup friction, works immediately
✅ **Focus**: Team can prioritize core circuit simulation features
✅ **Reliability**: No server downtime or dependency on network connectivity
✅ **Cost**: No hosting, bandwidth, or database costs

### Negative

❌ **No automatic backup**: Users responsible for backing up their own files
❌ **Manual sharing**: Circuit files must be shared via external tools (email, LMS, file shares)
❌ **Device-specific**: Work doesn't automatically sync across devices
❌ **Assignment workflow**: Requires integration with existing systems (Canvas, Blackboard, etc.)

### Mitigation Strategies

To address the limitations while maintaining local-first design:

1. **File sharing**: Document workflows using existing tools
   - LMS integration for assignment submission (Canvas API, file upload)
   - Email/Slack for quick sharing
   - Git repositories for version control and collaboration
   - Network drives or cloud storage (Dropbox, Google Drive) for backup

2. **Export features**: Enhanced export capabilities
   - PDF reports for submission
   - PNG/SVG circuit images
   - Netlist export for compatibility
   - Simulation data as CSV

3. **Instructor workflows**: Templates and examples
   - Distribute starter circuits as JSON files
   - Provide reference designs in repository
   - Course packs as downloadable ZIP files

4. **Future opt-in features** (if needed):
   - Lightweight cloud sync (like VS Code Settings Sync)
   - Assignment submission API (no full account system)
   - LMS integration via LTI standard

---

## Alternatives Considered

### Alternative 1: Full Account System with Cloud Storage

**Approach:**
- Backend API (Flask/FastAPI)
- PostgreSQL database
- User authentication (OAuth or custom)
- Cloud file storage
- Web dashboard for instructors

**Rejected because:**
- High development and maintenance cost
- Security and compliance burden (FERPA, password management)
- Infrastructure costs (hosting, databases)
- Adds complexity and dependencies
- Distracts from core simulation features
- Creates login friction for students

### Alternative 2: Hybrid - Local Files + Optional Cloud Sync

**Approach:**
- Keep local-first design
- Add optional cloud backup/sync
- Similar to VS Code Settings Sync

**Deferred because:**
- Still requires backend infrastructure (though simpler)
- Added complexity without clear immediate need
- Can be added later if demand emerges

### Alternative 3: Git-Based Collaboration

**Approach:**
- Treat circuits like code
- Students work in Git repositories
- Instructors clone/fork for review

**Not chosen as default because:**
- Git learning curve for non-CS students
- Overkill for simple circuit assignments
- Could still be used by advanced users voluntarily

---

## Implications for Future Phases

### Phase 2 - Cloud Storage (Revised)
Instead of accounts:
- Document best practices for file backup
- Add robust export/import features
- Consider read-only circuit library (no accounts needed)

### Phase 3 - Instructor Tools (Revised)
Instead of built-in grading:
- LMS integration via API or file upload
- Export features for gradebook compatibility
- Template distribution via file sharing

### Phase 4-7 - Advanced Features
If user accounts become truly necessary:
- Reassess based on user feedback and pain points
- Consider lightweight solutions first (OAuth only, no custom auth)
- Evaluate university SSO integration
- Build incrementally rather than full system upfront

---

## References

### Discovery to Decision Evolution
- **Initial exploration:** [DiscoveryDocs/](../../DiscoveryDocs/) - Academic assignment discovery phase
- **Multi-user vision:** [User Roles and Permissions](../../DiscoveryDocs/User%20Roles%20and%20Permissions.md) - Original 5-role system design
- **Original timeline:** [Proposed Timeline](../../DiscoveryDocs/Proposed%20Timeline%20User%20Roles%20Implementation.md) - 20-month rollout plan
- **Evolution explained:** [DiscoveryDocs/README](../../DiscoveryDocs/README.md) - How stakeholder feedback shaped final decision

### Current Implementation
- Phase 1 focuses on student-facing circuit design (current)
- Current architecture: [file_controller.py](../../app/controllers/file_controller.py)
- Session persistence already implemented for last-opened file
- README roadmap: [README.md](../../README.md#roadmap)

---

## Review and Revision

This decision should be reviewed if:
- User feedback indicates significant pain around file sharing/backup
- University requires centralized storage for compliance
- LMS integration proves insufficient for instructor workflows
- Team capacity increases significantly and can support backend infrastructure

**Next review:** End of Phase 1 (before planning Phase 2 features)
