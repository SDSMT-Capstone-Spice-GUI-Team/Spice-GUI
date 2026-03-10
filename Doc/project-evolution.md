# SDM Spice: Project Evolution from Discovery to Implementation

**Document Purpose:** Explain how SDM Spice evolved from initial discovery to actual implementation
**Audience:** Team members, stakeholders, academic reviewers, future contributors
**Last Updated:** 2026-02-08

---

## Executive Summary

SDM Spice began with an ambitious vision for a multi-user, cloud-based circuit simulation platform. Through stakeholder engagement and constraint analysis, we pivoted to a **local-first desktop application** that delivers core value faster while maintaining potential for future expansion.

**Key Takeaway:** We made an informed decision to simplify architecture based on real-world constraints, not a failure to achieve the original vision.

---

## Timeline

### Fall 2024: Discovery Phase (Academic Assignment)

**Activities:**
- Requirements gathering and user research
- Competitive analysis of existing tools
- User persona development
- Multi-user role system design
- 20-month implementation roadmap

**Deliverables:**
- [DiscoveryDocs/](../DiscoveryDocs/) - Comprehensive exploration
- User role definitions (5 roles: Student, Instructor, TA, Researcher, Admin)
- Permission matrix and security requirements
- Phased implementation plan

**Vision:** Enterprise-grade multi-user SaaS with authentication, cloud storage, LMS integration, and role-based permissions.

---

### Fall 2024 - Winter 2025: Stakeholder Engagement

**Who We Talked To:**
- **Faculty Advisors:** Provided reality check on scope and timeline
- **Student Users:** Validated core needs (simulation quality > fancy features)
- **IT Stakeholders:** Explained hosting limitations and maintenance concerns
- **Project Sponsors:** Clarified success criteria and constraints

**What We Learned:**

| Discovery Assumption | Stakeholder Reality |
|---------------------|-------------------|
| 20 months to build | 8-month Capstone timeline |
| Cloud hosting available | No hosting budget, no post-grad maintenance |
| Custom assignment system needed | LMS already does this well |
| Students want cross-device sync | Students want reliable simulation first |
| SSO integration straightforward | Complex, requires university IT approval |
| Team has backend expertise | Team stronger in Python/desktop dev |

---

### Winter 2025: The Pivot Decision

**Decision Point:** Build multi-user cloud system vs. local-first desktop app

**Factors Considered:**
1. **Timeline:** Capstone deadline vs. 20-month plan
2. **Scope:** What's achievable with available resources?
3. **Value:** What delivers most value to users soonest?
4. **Risk:** What can we maintain post-graduation?
5. **Constraints:** Budget, infrastructure, team skills

**Outcome:** [ADR 001 - Local-First Architecture Without User Accounts](decisions/001-local-first-no-user-accounts.md)

---

## What Changed

### Architecture

| Aspect | Discovery Vision | Implemented Reality | Rationale |
|--------|-----------------|-------------------|-----------|
| **Deployment** | Cloud-hosted SaaS | Desktop application | No hosting costs, works offline |
| **User Accounts** | SSO + custom auth | None - local only | Simpler, FERPA-compliant by default |
| **File Storage** | Cloud database | Local JSON files | Privacy, speed, no infrastructure |
| **Multi-User** | 5 roles with permissions | Single-user desktop | Focus on core simulation quality |
| **Assignment System** | Custom creation/submission | Export + LMS integration | Leverage existing tools |

### Timeline

| Phase | Discovery Plan | Actual Implementation |
|-------|---------------|---------------------|
| **Phase 1** | Student MVP (Months 1-4) | ✅ Core circuit design tool |
| **Phase 2** | User accounts + cloud (Months 5-7) | ❌ **PIVOTED:** Export/sharing + LMS integration |
| **Phase 3** | Instructor tools (Months 8-10) | Deferred - Templates & examples instead |
| **Phase 4** | Advanced grading (Months 11-13) | Deferred |
| **Phase 5** | TA role (Months 14-15) | Not applicable (no multi-user) |
| **Phase 6** | Researcher features (Months 16-18) | Deferred to future phases |
| **Phase 7** | Admin tools (Months 19-20) | Not applicable (no accounts) |

---

## What Stayed the Same

### Core Values Preserved

✅ **Student-first design** - Beginner-friendly interface, clear error messages
✅ **Accurate simulation** - Industry-standard ngspice integration
✅ **Educational focus** - Designed for learning, not professional EDA
✅ **Open source** - Free for students, inspectable code
✅ **Cross-platform** - Windows, macOS, Linux support

### Features Implemented

✅ Circuit schematic editor with drag-and-drop
✅ Component library (R, L, C, voltage/current sources, transistors, etc.)
✅ Wire routing with intelligent pathfinding
✅ All SPICE analysis types (DC OP, DC Sweep, AC, Transient)
✅ Waveform visualization
✅ File save/load (JSON format)
✅ Export capabilities (netlist, CSV, PNG/SVG)
✅ Session persistence

---

## Why This Was the Right Decision

### ✅ Delivered on Time
**Discovery:** 20-month timeline
**Reality:** Working application in 8 months (Capstone duration)

### ✅ Focused on Core Value
**Discovery:** Broad feature set across 5 user roles
**Reality:** Excellent student circuit design experience

### ✅ Maintainable Long-Term
**Discovery:** Required ongoing backend maintenance, hosting costs
**Reality:** Desktop app continues working without infrastructure

### ✅ Privacy-First
**Discovery:** Cloud storage with FERPA compliance complexity
**Reality:** Local files = inherently private

### ✅ Lower Barrier to Entry
**Discovery:** Account signup, email verification, password management
**Reality:** Download, install, start designing

### ✅ Works Offline
**Discovery:** Requires internet for cloud sync
**Reality:** Full functionality without network

---

## What We Learned About Software Development

### 1. Discovery ≠ Requirements
Discovery explores possibilities. Requirements are constrained by reality.

### 2. Stakeholder Input is Critical
Documents alone don't capture real constraints (budget, timeline, politics, existing systems).

### 3. Start with Core Value
Better to excel at one thing than do many things poorly.

### 4. Integrate, Don't Rebuild
LMS already handles assignment distribution. File sharing tools already handle backup. Don't reinvent wheels.

### 5. Iterate Based on Usage
Ship Phase 1, learn what users actually need, then build Phase 2.

### 6. Document the Journey
ADRs capture "why" decisions were made. Future teams benefit from understanding the evolution.

---

## Future Possibilities

### If Project Continues Beyond Capstone

The local-first architecture doesn't preclude future enhancements:

**Phase 2 - Enhanced Sharing (Months 9-12)**
- LMS integration API for direct assignment submission
- Cloud export option (optional, not required)
- Shared circuit library (read-only, no accounts needed)

**Phase 3 - Instructor Tools (Months 13-18)**
- Template distribution via file sharing
- Verification scripts for auto-grading
- Batch operations via command-line interface

**Phase 6 - Researcher Features (Months 19-24)**
- Scripting API (Python)
- Batch simulation capabilities
- Advanced SPICE model import

**Later - If Multi-User Becomes Essential**
- Could add optional cloud sync (like VS Code Settings Sync)
- Could add lightweight sharing (no full account system)
- Local-first + optional cloud hybrid

**Key:** MVC architecture ([ADR 002](decisions/002-mvc-architecture-zero-qt-dependencies.md)) makes this evolution possible. Core logic has zero GUI dependencies, enabling future web interface if needed.

---

## For Academic Reviewers

### Why Discovery Docs Differ from Implementation

This demonstrates:
- ✅ Thorough requirements exploration
- ✅ Understanding of enterprise software patterns
- ✅ Stakeholder engagement and iteration
- ✅ Constraint-driven decision making
- ✅ Scope management and prioritization
- ✅ Transparent documentation of evolution

**We didn't fail to execute discovery plan. We succeeded in adapting to reality.**

### Deliverables Showing This Process

1. **[DiscoveryDocs/](../DiscoveryDocs/)** - Initial exploration (assignment deliverable)
2. **[Architecture Decision Records](decisions/)** - Stakeholder-informed decisions
3. **[README Roadmap](../README.md#roadmap)** - Updated project phases
4. **Working Software** - Functional Phase 1 implementation
5. **This Document** - Explanation of evolution

---

## Key Documents

### Discovery Phase
- [DiscoveryDocs/README](../DiscoveryDocs/README.md) - Overview of discovery documents
- [User Roles and Permissions](../DiscoveryDocs/User%20Roles%20and%20Permissions.md) - Original multi-user design
- [Proposed Timeline](../DiscoveryDocs/Proposed%20Timeline%20User%20Roles%20Implementation.md) - 20-month plan

### Decision Phase
- [ADR 001: Local-First Architecture](decisions/001-local-first-no-user-accounts.md) - The pivot decision
- [ADR 002: MVC Architecture](decisions/002-mvc-architecture-zero-qt-dependencies.md) - Enables future flexibility
- [All ADRs](decisions/) - Full architectural decision history

### Implementation
- [README](../README.md) - Current project status and roadmap
- [Development Methodology](autonomous-workflow.md) - How we build
- [Git Commit History](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/commits/) - Implementation timeline

---

## Questions & Answers

### Q: Did you abandon the discovery findings?
**A:** No. Discovery helped us understand user needs. We just found a simpler way to meet those needs.

### Q: Will you ever build the multi-user system?
**A:** Maybe, if the project continues post-Capstone and user feedback indicates it's needed. The architecture allows for this evolution.

### Q: Why keep the discovery docs if they're not the plan?
**A:** They're academic deliverables and show our discovery process. They also contain user insights still relevant today.

### Q: How do instructors distribute assignments without the custom system?
**A:** Export circuit templates as JSON files, distribute via LMS or file sharing, students import and work locally.

### Q: What about cloud backup for students?
**A:** Students can use Google Drive, Dropbox, Git, or any file backup tool. We don't need to build this.

### Q: Is this a failure to deliver on the original vision?
**A:** No. It's **adapting to constraints** discovered through stakeholder engagement. This is good project management.

---

## Conclusion

SDM Spice demonstrates a mature software development process:

1. ✅ **Explore broadly** (Discovery phase)
2. ✅ **Validate with stakeholders** (Reality check)
3. ✅ **Decide based on constraints** (ADRs)
4. ✅ **Deliver core value** (Working software)
5. ✅ **Document the journey** (Transparency)

The final product is simpler than the initial vision, but **delivers more value to users in less time with fewer resources**. That's a success, not a compromise.

---

**Last Updated:** 2026-02-08
**Maintained By:** SDM Spice Development Team
**Questions:** See [Contributing Guide](../README.md#contributing)
