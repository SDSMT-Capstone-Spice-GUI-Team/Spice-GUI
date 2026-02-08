# Autonomous Development Workflow

This document defines the workflow for Claude Code to autonomously work through issues on the project board.

---

## AI-Assisted Development Methodology

### Overview

SDM Spice is developed using **AI-assisted development** with Claude (Anthropic's AI assistant) as a core development tool. This approach combines human direction and decision-making with AI-powered implementation, testing, and documentation.

### What AI Assists With

**Architecture & Design:**
- Architecture Decision Records (ADRs) documentation
- Design pattern recommendations and implementation
- Code structure and organization
- Refactoring strategies (e.g., MVC migration)

**Implementation:**
- Code generation for new features
- Boilerplate reduction (controllers, models, tests)
- Algorithm implementation (pathfinding, parsing)
- PyQt6 GUI code and signal/slot wiring

**Testing:**
- Unit test generation with comprehensive coverage
- Integration test scenarios
- Test fixture creation
- Edge case identification

**Documentation:**
- README and technical documentation
- Code comments and docstrings
- API documentation
- Architecture diagrams and explanations

**Code Quality:**
- Linting and style consistency
- Type hint additions
- Error handling improvements
- Performance optimization suggestions

### What Humans Direct

**Strategic Decisions:**
- Product requirements and priorities
- Architecture choices (local-first, MVC, PyQt6)
- Technology selection (ngspice, JSON format)
- User experience design

**Quality Assurance:**
- Code review and validation
- Manual testing of UI/UX
- Design decision approval
- Acceptance criteria verification

**Domain Expertise:**
- Electrical engineering requirements
- Educational use cases
- SPICE simulation knowledge
- Academic workflow needs

### Benefits Observed

✅ **Velocity:** Features implemented 3-5x faster than traditional development
✅ **Test Coverage:** 108+ unit tests generated alongside implementation
✅ **Documentation:** Comprehensive docs as natural byproduct of AI workflow
✅ **Consistency:** Enforced patterns (MVC, zero-Qt dependencies, naming conventions)
✅ **Learning:** Team learns from AI-generated examples and explanations
✅ **Refactoring:** Large-scale refactors (monolith → MVC) completed systematically

### Best Practices

**When AI is Most Valuable:**
- Implementing well-defined requirements
- Writing comprehensive test suites
- Generating boilerplate code (models, controllers)
- Documenting architecture decisions
- Refactoring for code quality

**When Human Judgment is Critical:**
- Defining product direction and priorities
- Making architecture trade-offs
- Evaluating UX/UI design
- Reviewing security implications
- Final acceptance of implementations

**Validation Process:**
1. AI generates implementation with tests
2. Automated test suite runs (CI/CD)
3. Human reviews code and tests
4. Manual testing for UI/UX flows
5. Approval before merge

### Co-Authoring Attribution

All commits include co-author attribution when AI-assisted:
```
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

This provides transparency about which commits involved AI assistance.

### Tools Used

- **Claude Code CLI:** Primary development assistant
- **Claude 4.5 Sonnet:** Model for code generation and architecture
- **Git integration:** Automatic commit attribution
- **pytest:** Test execution and validation

### Guidelines for Future Contributors

**Working with AI assistance:**
1. Clearly specify requirements and acceptance criteria
2. Review all AI-generated code before accepting
3. Run full test suite to validate implementations
4. Ask AI to explain complex implementations
5. Iterate on solutions if first attempt doesn't meet needs

**When to use AI assistance:**
- ✅ Implementing features from clear specifications
- ✅ Writing tests for existing code
- ✅ Refactoring for better structure
- ✅ Generating documentation
- ❌ Making product decisions without context
- ❌ Blindly accepting code without review
- ❌ Replacing domain expertise

### Transparency & Ethics

This project is transparent about AI assistance:
- README acknowledges AI usage
- Git history shows co-authored commits
- This document explains the methodology
- Code is reviewed and validated by humans
- Final responsibility rests with human developers

### Related Documents

- [Architecture Decision Records](decisions/) - Documents major design choices
- Git commit history - Shows co-authored commits with attribution

---

## The Work Loop

```
1. Query the project board for the next "Ready" item
2. Move the issue to "In Progress"
3. Write a brief internal plan and assess complexity
4. Implement the change
5. Run tests: python -m pytest tests/ -v (from app/)
6. Commit with a descriptive message
7. Push to remote
8. Close the GitHub issue (reference the commit)
9. Move the issue to "In Review" on the board
10. Log estimated hours on the issue
11. Pick the next Ready item and repeat from step 1
```

### Stop Conditions

- **Blocked** on an issue (dependency, ambiguity, conflict)
- **Ready queue is empty** (notify the user)

---

## Edge Case Handling

| Scenario | Action |
|----------|--------|
| **Hard to test** (UI-heavy, needs manual verification, depends on ngspice) | Implement, commit, and push. Flag in the issue comment that manual testing is needed. |
| **Vague requirements** (unclear scope, multiple interpretations) | Make a reasonable judgment call. Note assumptions in the commit message and issue comment. |
| **Conflicting issues** (overlapping scope, contradictory requirements) | Move to **Blocked** with a comment explaining the conflict. Pick the next Ready item. |
| **Blocked for any reason** | Move to **Blocked** with an explanatory comment. Pick the next Ready item. |
| **Ready queue empty** | **Stop and notify the user.** Do not pull from Backlog autonomously. |

---

## Planning

- Always write a brief plan before implementing
- **Low complexity** issues: proceed immediately without waiting for approval
- **High complexity** issues: still proceed, using judgment calls for ambiguous decisions
- The plan is a record of decisions and assumptions, not a gate

---

## Hours Logging

- Estimate time based on issue complexity:
  - Small fix / tweak: ~0.5h
  - Medium feature or refactor: ~1-2h
  - Large feature or multi-file change: ~3h+
- Add a comment on the issue: `⏱️ Xh - description of work done`
- Update the "Hours" number field on the project board

---

## Git Rules

- Auto-commit with descriptive messages after implementation
- Auto-push to remote after each commit
- Work on the current active branch

---

## Board Status Flow

```
Backlog → Ready → In Progress → In Review → Done
                       ↓
                    Blocked
```

### Status Definitions

| Status | Meaning |
|--------|---------|
| **Backlog** | Validated request, not yet prioritized for work |
| **Ready** | Fully understood, prioritized, ready for autonomous work |
| **In Progress** | Actively being worked on |
| **Blocked** | Waiting on a dependency, conflict, or user decision |
| **In Review** | Code complete, pushed, awaiting validation |
| **Done** | Review passed |

---

## User's Role

- **Curate the Ready queue**: Move issues from Backlog to Ready when they should be worked on
- **Review completed work**: Items in "In Review" need validation before moving to Done
- **Unblock issues**: Resolve blockers and move items back to Ready
- **Provide direction**: If the Ready queue is empty, populate it with the next priorities
