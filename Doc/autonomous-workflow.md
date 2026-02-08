# Autonomous Development Workflow

This document defines the workflow for Claude Code to autonomously work through issues on the project board.

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
