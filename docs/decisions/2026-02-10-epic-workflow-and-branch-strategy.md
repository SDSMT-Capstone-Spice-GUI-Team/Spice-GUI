# ADR: Epic Workflow and Branch Strategy

**Date**: 2026-02-10
**Status**: Proposed
**Participants**: Jeremy (Software Architect), Claude Agent (Opus 4.6)
**Context**: Discussion continued from Session 3 feedback review

---

## Background

### Team Composition

**Stakeholders:**
- **The Boss** — PhD, SDSMT EECS Department Head and Professor. Provides vision, direction, and funding.
- **Middle Manager** — SDSMT EECS Grad Student. Ensures academic requirements are met and progress is tracked.

**Undergrad Team:**
- **Jeremy** (CS) — Software Architect, DevOps management, backend engineer.
- **Jon** (CS) — UI/UX Designer, frontend engineer.
- **Marc** (EE) — Subject Matter Expert, circuit designer. Co-Product Owner. Academic use case testing.
- **Micah** (EE) — Subject Matter Expert, NGspice and netlists. Co-Product Owner. Academic use case testing.

**Claude Agent Roles (concurrent):**
- Issue coding: 2-5 agents simultaneously
- Backlog grooming: 1-2 agents
- DevOps implementations: 1-2 agents
- Wiki review and update: 0-1 agents
- PR management: 1-2 agents
- Feedback to workflow: all agents

**Effective concurrent contributors**: up to 7 simultaneous writers (5 agents + Jeremy + Jon), plus 2 testers (Marc, Micah) working against integration branches.

### Friction Points That Motivated This Discussion

From Session 3 (2026-02-10), which completed 8 issues across 2 context windows:

1. **Context window exhaustion** — Session interrupted mid-issue #56 with a pending commit. Conversation summary lost implementation details. Occurs around every 5 issues.
2. **Merge conflicts from consecutive PRs** — All PRs target `main`. When PRs aren't merged before the next agent starts, rebase conflicts multiply. `main_window.py` is the primary conflict hotspot (~1500 lines, touched by nearly every feature).
3. **No testing gate** — Marc and Micah have no stable branch to test against. Features land on `main` and may be incomplete or untested from a circuit-design perspective.
4. **No epic grouping** — Related issues (e.g., all Monte Carlo work) are tracked individually with no structural relationship.

### Full Automation Tradeoffs Discussed

**Concerns raised by Jeremy:**
- Losing context and gradually becoming less connected to the codebase as agents do more work.
- Product owner context acquisition time increases — understanding new features takes longer when you didn't write them.
- Knowing how to actually test new items when the implementation was fully automated.

**Positives identified:**
- "Failing fast" allows the team to pivot — a shipped feature that's wrong teaches more than a perfect spec that's never built.
- Poor implementations are better than no implementation for highlighting knowledge gaps about user expectations. Agent output functions as rapid prototyping.

**Key reframe**: The agent's role is best understood as a *hypothesis generator*, not a final-product developer. "We think users want Bode plot markers" -> agent builds it in 1.5h -> team tests -> "actually users need to drag the markers" -> write a better issue.

---

## Options Considered

### Option 1: Jeremy's Initial Proposal (7 Long-Lived Branches)

```
Production-Main
Production-Ready
Testing-Epic
Testing-Regression
Testing-Integration
Dev-Main
Dev-Epic
issue-<N>-<name>
```

**Assessment**: Provides maximum gating and visibility. However, 7 long-lived branches require significant merge ceremony, and every promotion step is a potential conflict resolution point. The overhead is justifiable for a large enterprise team but may bottleneck a capstone project where Jeremy is the primary DevOps person.

### Option 2: GitHub Flow + Release Tags (No New Branches)

```
main
├── issue-<N>-<name>
```

Everything PRs to `main`, epics tracked entirely in GitHub Projects. Release via git tags.

**Assessment**: Zero workflow change from current state. Doesn't solve the concurrent-writer collision problem or give Marc/Micah a stable testing target. Dismissed.

### Option 3: Lightweight Epics (Minimal Change)

```
main
├── release/vX.Y
├── epic/<name>     (only when needed)
│   └── issue-<N>-<name>
└── issue-<N>-<name>  (standalone)
```

**Assessment**: Low ceremony but doesn't provide an integration gate between epic work and production. Marc/Micah would need to know which epic branch to pull for testing.

### Option 4: Epic Branches with Integration (Selected)

```
main                              <- always demo-ready
├── develop                       <- integration point, CI gate
│   ├── epic/<name>               <- grouped feature work
│   │   └── issue-<N>-<name>
│   └── issue-<N>-<name>          <- standalone work
└── release/vX.Y                  <- cut from develop for releases
    └── hotfix/vX.Y.Z             <- critical fixes on released versions
```

**Assessment**: 2 long-lived branches (`main`, `develop`) + ephemeral epic/issue/release branches. Provides conflict isolation via epics, a stable integration point for testing (`develop`), and a demo-ready `main` for stakeholders. Manageable overhead for the team size.

---

## Decision: Option 4 — Epic Branches with Integration

### Branch Topology

```
main                              <- always demo-ready for boss
│
├── develop                       <- integration branch, CI gate
│   │
│   ├── epic/monte-carlo          <- agent coding lanes
│   │   ├── issue-144-mc-dialog
│   │   └── issue-145-mc-results
│   │
│   ├── epic/ui-overhaul          <- Jon's lane
│   │   └── issue-150-new-palette
│   │
│   ├── epic/circuit-validation   <- Marc/Micah-informed work
│   │   └── issue-160-subcircuits
│   │
│   └── issue-140-probes          <- standalone fixes
│
└── release/v1.3                  <- cut when milestone complete
    └── hotfix/v1.3.1             <- critical fix on released version
```

### Branch Purposes

| Branch | Lifetime | Purpose | Who Merges To It |
|--------|----------|---------|------------------|
| `main` | Permanent | Production-ready, tagged for releases. Boss can demo at any time. | Jeremy (from `develop` or `release/*`) |
| `develop` | Permanent | Integration point. All work flows through here. CI must pass. | PR management agents + Jeremy |
| `epic/<name>` | Weeks | Groups related issues. Conflict containment for concurrent agents. | Coding agents (issue PRs) |
| `issue-<N>-<name>` | Days | Individual feature/fix implementation. | N/A (PRs to epic or develop) |
| `release/vX.Y` | Days-weeks | Stabilization before release. Only bug fixes, no new features. | Jeremy |
| `hotfix/vX.Y.Z` | Hours-days | Critical fix on a released version. | Jeremy |

### Branch Resolution Algorithm (How Agents Pick Base Branch)

Agents determine their base branch using this deterministic algorithm:

```
1. Check issue body for explicit override
   -> Contains "Base-Branch: <branch>"?
   -> Use that branch

2. Check issue labels for epic assignment
   -> Has label matching "epic:<name>"?
   -> Base = epic/<name>
   -> If epic branch doesn't exist, create it from develop

3. Default
   -> Base = develop
```

**Implementation:**
```bash
# Step 1: Read the issue
LABELS=$(gh issue view $N --repo $REPO --json labels --jq '.labels[].name')

# Step 2: Check for epic label
EPIC=$(echo "$LABELS" | grep '^epic:' | sed 's/epic://')

# Step 3: Resolve base branch
if [ -n "$EPIC" ]; then
    BASE="epic/$EPIC"
    # Create epic branch if it doesn't exist
    if ! git ls-remote --heads origin "$BASE" | grep -q "$BASE"; then
        git checkout develop
        git pull origin develop
        git checkout -b "$BASE"
        git push -u origin "$BASE"
    fi
else
    BASE="develop"
fi

# Step 4: Create issue branch
git checkout "$BASE"
git pull origin "$BASE"
git checkout -b "issue-${N}-${SLUG}"
```

### Role Interactions

**Jeremy (Architect / DevOps):**
- Manages branch protection rules on `main` and `develop`
- Reviews/approves epic -> develop merges
- Cuts release branches when milestones are hit
- Maintains CLAUDE.md workflow rules

**Jon (UI/UX Frontend):**
- Works on `epic/ui-*` branches — these are reserved lanes
- Agents don't touch `epic/ui-*` unless an issue is explicitly labeled `epic:ui-*`
- PRs to his epic branch or directly to `develop` for small UI fixes

**Marc & Micah (EE / Testing / Co-Product Owners):**
- Pull and test from `epic/*` branches (feature-specific testing)
- Pull and test from `develop` (integration testing)
- Pull and test from `release/*` (pre-release regression testing)
- File issues from testing -> backlog -> grooming agents prioritize
- Simple testing script: `./scripts/test-epic.sh monte-carlo`

**Coding Agents (2-5 concurrent):**
1. Check issue labels for epic assignment
2. If epic label exists and `epic/*` branch exists: branch from epic, PR to epic
3. If no epic: branch from `develop`, PR to `develop`
4. NEVER PR directly to `main`
5. One issue per agent, no file overlap

**PR Management Agents (1-2):**
- Monitor open PRs, verify CI checks
- Merge `issue -> epic` when CI passes and agent feedback is posted
- Flag `epic -> develop` merges for Jeremy's review
- Auto-merge standalone `issue -> develop` if CI passes and tests increase

**Backlog Grooming Agents (1-2):**
- Assign `epic:<name>` labels to new issues
- Break large issues into sub-tasks
- Ensure issues have clear acceptance criteria
- Flag issues needing Marc/Micah input (circuit-domain issues)

### Why Epics Solve the Conflict Problem

Without epics (current state):
```
Agent 1 (issue-144) --PR--> main <--PR-- Agent 2 (issue-145)
Agent 3 (issue-146) --PR--> main <--PR-- Agent 4 (issue-140)
Jon     (issue-150) --PR--> main

= 5 PRs all targeting main, all potentially touching main_window.py
= merge conflict hell
```

With epics:
```
Agent 1 (issue-144) --PR--> epic/monte-carlo <--PR-- Agent 2 (issue-145)
Agent 3 (issue-146) --PR--> epic/monte-carlo
Agent 4 (issue-140) --PR--> develop           (standalone, isolated)
Jon     (issue-150) --PR--> epic/ui-overhaul  (isolated from agents)

= conflicts contained within each epic
= epic -> develop merge is ONE merge point, handled by Jeremy
```

---

## Concerns and Mitigations

| Concern | Mitigation |
|---------|------------|
| Epic branches drift from `develop` | PR management agents periodically rebase epics on `develop`. Set 2-week max epic lifetime. |
| Two agents grab same-file issues in one epic | Backlog grooming agents flag file-overlap risk. PR management agents serialize merges within an epic. |
| Marc/Micah find git complexity overwhelming | Provide `./scripts/test-epic.sh <name>` script that checks out the branch and runs the app. |
| Agent creates epic branch, another tries simultaneously | `git ls-remote` check before creation. Race condition window is seconds — acceptable risk. |
| Jeremy loses codebase context with more automation | Review every PR (2-min skim for design awareness, not correctness). Periodic architecture review sessions every 10-15 issues. |
| Testing gaps for UI/UX features | Batch manual testing every 5-8 features. Use `QT_QPA_PLATFORM=offscreen` for automated widget tests. |

---

## Implementation Plan

### Phase 1: Foundation (Immediate)
- [ ] Create `develop` branch from current `main`
- [ ] Set branch protection rules on `main` (require PR, no direct push)
- [ ] Set branch protection on `develop` (require CI pass)
- [ ] Create `epic:*` label convention in GitHub repo
- [ ] Update CLAUDE.md with new workflow rules

### Phase 2: Tooling
- [ ] Create `scripts/test-epic.sh` for Marc/Micah
- [ ] Update preflight checklist for `develop`-based workflow
- [ ] Add branch resolution logic to agent workflow documentation

### Phase 3: Process
- [ ] Create first epic (e.g., `epic:monte-carlo`) and label existing issues
- [ ] Add "Epic" field to GitHub Project board
- [ ] Brief team on new branch structure

### Phase 4: Refinement
- [ ] Monitor for 1-2 weeks
- [ ] Collect agent feedback on workflow friction
- [ ] Adjust epic lifetime limits and merge policies based on experience

---

## Context: Session 3 Performance Data

For reference, these metrics from the session that prompted this discussion:

- **Issues completed**: 8 across 2 context windows (~3h)
- **Tests added**: 110+ (net +37 in second context window)
- **Agent commit success rate**: 0% first attempt (black version mismatch), 100% second attempt
- **Rebase conflict rate**: 14% (1 of 7 PRs)
- **Test regression rate**: 0%

The black version mismatch (pre-commit hook uses 25.1.0, pip installs 26.1.0) should be fixed independently — it's the #1 friction point regardless of branch strategy.

---

## Related Decisions

- **Splitting `main_window.py`**: Orthogonal to branch strategy but reduces the merge conflict surface area that motivated this discussion. Recommended as a parallel effort.
- **Auto-merge for agent PRs**: Compatible with this strategy. Agent sets `gh pr merge --auto --squash` after creating PRs within epics. Epic -> develop merges remain manual.
- **Context window management**: Hard stop at 5 issues per context window. Checkpoint after each issue. Branch strategy doesn't change this limit but reduces the blast radius of mid-session interruptions.
