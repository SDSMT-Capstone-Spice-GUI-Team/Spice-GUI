# Discovery Documentation

**Created:** Fall 2024
**Purpose:** Academic assignment - Initial exploration and requirements gathering
**Status:** Historical record - Superseded by stakeholder-informed decisions

---

## Overview

This directory contains discovery documentation created during the initial exploration phase of the SDM Spice project. These documents represent **exploratory planning** and requirements gathering completed as part of our Capstone course curriculum.

### What's Here

| Document | Purpose | Status |
|----------|---------|--------|
| [User Personas](User%20Personas.md) | Guide for creating user personas | ✅ Still relevant methodology |
| [User Roles and Permissions](User%20Roles%20and%20Permissions.md) | Initial multi-user role system design | 📋 Exploratory - See ADR 001 |
| [Proposed Timeline User Roles Implementation](Proposed%20Timeline%20User%20Roles%20Implementation.md) | 20-month roadmap for multi-user system | 📋 Exploratory - See updated roadmap |
| [Backlog Item Template](Backlog%20Item%20Template.md) | Template for feature requests | ✅ Still in use |
| [Feature Request Template](Feature%20Request%20Template.md) | Template for feature documentation | ✅ Still in use |
| [Discovery Conversation with Claud](Discovery%20Conversation%20with%20Claud.md) | Initial AI-assisted exploration | 📋 Historical record |

---

## What Changed After Stakeholder Discussions

### Initial Discovery Vision (This Directory)

**Architecture:** Multi-user SaaS application with cloud storage
**User Management:** 5 distinct roles (Student, Instructor, TA, Researcher, Administrator)
**Infrastructure:** Backend API, database, authentication system, SSO integration
**Timeline:** 20-month phased rollout
**Deployment:** Cloud-hosted with LMS integration

**Key Features Envisioned:**
- User accounts and authentication
- Cloud-based circuit storage and sync
- Assignment creation and submission workflow
- Automated grading and analytics
- Role-based permissions and access control
- Collaborative workspaces for researchers

---

### Stakeholder-Informed Decisions (Actual Implementation)

After discussions with:
- Faculty advisors
- Student users (target audience)
- IT stakeholders
- Project sponsors

**We learned:**
- Complexity of building/maintaining authentication system
- Cost and infrastructure requirements for cloud hosting
- FERPA compliance concerns for student data
- Time constraints of Capstone project timeline
- Value of getting core simulation features right first
- Existing solutions for assignment submission (LMS integration simpler than custom)

**This led to a pivot documented in:**
- **[ADR 001: Local-First Architecture Without User Accounts](../Doc/decisions/001-local-first-no-user-accounts.md)**
- **[Updated Roadmap in README](../README.md#roadmap)**

---

## Evolution of Key Decisions

### User Accounts & Roles
**Discovery Phase:** Designed 5-role system with SSO, permissions, cloud storage
**Stakeholder Feedback:** Too complex for Phase 1, infrastructure burden too high
**Final Decision:** Local-first desktop app, no accounts (ADR 001)
**Rationale:** Focus on core circuit design, leverage existing tools (LMS) for distribution

### Assignment Workflow
**Discovery Phase:** Custom assignment creation, submission, and grading system
**Stakeholder Feedback:** LMS already handles this well (Canvas, Blackboard)
**Final Decision:** Export features + LMS integration instead of custom system
**Rationale:** Don't rebuild what already exists, interoperate instead

### Cloud Storage & Sync
**Discovery Phase:** Cloud-based file storage, cross-device sync, version history
**Stakeholder Feedback:** Adds cost, maintenance, privacy concerns
**Final Decision:** Local JSON files, manual backup via file sharing tools
**Rationale:** Simpler, private, works offline, no hosting costs

### Researcher Features
**Discovery Phase:** Advanced simulation controls, scripting API, collaboration tools
**Stakeholder Feedback:** Still valuable, but not Phase 1 priority
**Final Decision:** Deferred to Phase 6+, focus on student experience first
**Rationale:** Student use case is 80% of users, get that right first

---

## Why We Keep These Documents

### Academic Requirement
These documents were deliverables for our Capstone course and demonstrate:
- Thorough requirements exploration
- Understanding of user needs across personas
- Consideration of long-term product vision
- Professional discovery process

### Learning Record
They show the evolution of our thinking:
- What we initially envisioned (ambitious multi-user system)
- How we adapted based on constraints (realistic Phase 1)
- Trade-offs we made consciously (not by accident)

### Future Reference
If the project continues beyond Capstone:
- Phase 2+ may revisit some of these features
- Understanding original vision helps future teams
- Design patterns explored here may become relevant

### Transparency
Shows we:
- Did comprehensive discovery work
- Made informed decisions, not arbitrary ones
- Adapted based on stakeholder feedback
- Documented our reasoning (ADRs)

---

## How to Use These Documents

### For Current Development
- ✅ **User Personas methodology** - Still relevant for understanding users
- ✅ **Templates** - Use for issues and feature requests
- ❌ **Role system design** - Reference only, not implementing
- ❌ **20-month timeline** - Superseded by updated roadmap

### For Future Phases
If the project grows beyond Phase 1:
- Review these documents for feature ideas
- Consider whether cloud features now make sense
- Evaluate role-based permissions if multi-user becomes needed
- Reference permission matrix for security design

### For Academic Review
- Shows comprehensive discovery process
- Demonstrates understanding of enterprise software patterns
- Evidence of stakeholder engagement and iteration
- Professional documentation standards

---

## Related Documentation

- **[Architecture Decision Records](../Doc/decisions/)** - Why we made specific technical choices
- **[README Roadmap](../README.md#roadmap)** - Current project phases and priorities
- **[Development Methodology](../Doc/autonomous-workflow.md)** - How we build the software
- **[ADR 001](../Doc/decisions/001-local-first-no-user-accounts.md)** - Key decision to go local-first

---

## Lessons Learned

### What Worked Well
✅ Comprehensive user role analysis helped understand needs
✅ Permission matrix thinking influenced security design
✅ Timeline planning taught us about project scope management
✅ Discovery process revealed complexity early

### What We Adjusted
🔄 Simplified architecture to match Capstone timeline
🔄 Leveraged existing tools (LMS) instead of building custom
🔄 Prioritized core simulation quality over multi-user features
🔄 Chose desktop-first over web-based for faster development

### Key Insights
💡 **Scope management is critical** - Better to excel at core features than build everything poorly
💡 **Stakeholder input invaluable** - Discovery docs alone don't capture real constraints
💡 **Integration > Building** - Use existing systems (LMS, file sharing) when possible
💡 **Privacy by design** - Local-first architecture is FERPA-compliant by default
💡 **Iterate based on feedback** - Initial vision evolves with real-world input

---

## Contact & Questions

For questions about the evolution from discovery to implementation, see:
- Architecture Decision Records in `Doc/decisions/`
- Git commit history showing implementation choices
- Capstone project documentation
