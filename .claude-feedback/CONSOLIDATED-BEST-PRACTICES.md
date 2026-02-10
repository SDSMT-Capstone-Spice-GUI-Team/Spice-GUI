# Consolidated Best Practices — Multi-Agent Workflow

**Synthesized from**: 16 feedback files, 6+ agents, 4+ sessions (2026-02-09 to 2026-02-10)
**Date**: 2026-02-10

---

## 1. Pain Points by Severity

### Critical (hit by every agent)

| # | Issue | Impact | Fix Status |
|---|-------|--------|------------|
| 1 | **Black version mismatch** | Every commit fails first attempt; must re-stage and retry | **FIXED** — pinned `black==26.1.0` in requirements-dev.txt |
| 2 | **Context window exhaustion** | Sessions of 3+ issues lose context; summaries lose implementation details | **MITIGATED** — CLAUDE.md soft limit of 3-4 issues, checkpointing added |
| 3 | **main_window.py merge conflicts** | God object (~1700 lines); every feature touches it; 6 conflicts in one PR | **OPEN** — needs refactoring into smaller modules |
| 4 | **Formatting drift in PRs** | 7 of 12 PRs in session 3 had same black formatting issue | **FIXED** — baseline formatting now on main; agents must run `make format` |

### Moderate

| # | Issue | Impact | Fix Status |
|---|-------|--------|------------|
| 5 | Board ID discovery overhead | ~2 min wasted per session on 3 gh calls + JSON parsing | **MITIGATED** — cached in MEMORY.md with re-query fallback |
| 6 | Stale Ready items | Already-fixed issues still show as Ready; agents waste time investigating | **FIXED** — triage step added to work loop |
| 7 | gh CLI broken pipe on Linux | `gh ... \| python3` fails with empty stdin | **FIXED** — use `--jq` instead of piping to python |
| 8 | item-list default limit (30) | Silently drops items beyond first 30; board has 117+ items | **FIXED** — always use `--limit 200` |
| 9 | item-add doesn't set status | New items appear with null status, invisible in column views | **DOCUMENTED** — must follow item-add with item-edit |
| 10 | MEMORY.md gets stale | Multiple agents overwrite each other's session state | **OPEN** — needs per-directory isolation |

### Minor

| # | Issue | Fix |
|---|-------|-----|
| 11 | `replace_all` breaks multi-level indentation | Edit each occurrence individually |
| 12 | Venv path confusion (`../.venv/bin/activate`) | Use `make test` / `make format` consistently |
| 13 | Pre-commit hooks missing on legacy branches | Documented `PRE_COMMIT_ALLOW_NO_CONFIG=1` workaround |
| 14 | MainWindow not instantiable in offscreen tests | Test lower-level components (QGraphicsScene, QPrinter) |
| 15 | File corruption during pre-commit stash/unstash | Monitor for recurrence; re-create files if corrupted |

---

## 2. Confirmed Best Practices

### Development Workflow

1. **Always start from fresh main**: `git checkout main && git pull origin main`
2. **One feature branch per issue**: `issue-<N>-short-description`
3. **Run formatters before committing**: `make format && make lint`
4. **Rebase on origin/main before pushing**: catches merge conflicts early
5. **Re-run tests after rebase**: catches regressions from conflict resolution
6. **Triage before coding**: check issue state (`gh issue view <N> --json state,comments`). If already resolved, skip.
7. **Checkpoint after each issue**: post progress comment, update MEMORY.md
8. **Commit Co-author tag**: `Co-Authored-By: Claude <model> <noreply@anthropic.com>`

### Board Management

1. **Use `--jq` on gh CLI**: avoids temp files and broken-pipe race conditions on Linux
2. **Always `--limit 200`**: board has 117+ items, default 30 silently truncates
3. **item-add requires item-edit**: adding an issue to the board does NOT set its status
4. **Cache board IDs in MEMORY.md**: re-query only if a mutation fails
5. **Compact jq output**: use `{n: .content.number, s: .status}` to minimize token usage
6. **Use `--json` on `gh issue view`**: avoids Projects Classic deprecation errors

### Testing

1. **Use `make test`** from project root — handles venv and path automatically
2. **Use `tmp_path` in tests** — never hardcode Unix paths like `/some/path`
3. **Test count must increase by ≥5** for new features
4. **MainWindow cannot be instantiated in offscreen mode** — test with lower-level Qt components
5. **Pre-existing GUI test errors are expected** — Qt display server issues in headless environments

### Code Quality

1. **MVC architecture**: model (no Qt deps) → controller (business logic) → view (PyQt6)
2. **Observer pattern**: controllers notify views via callbacks, not direct coupling
3. **Command pattern**: all operations that need undo/redo go through commands
4. **Reuse existing patterns**: check for existing helpers before writing new ones (e.g., `parse_value`, `format_si_value`, `_get_circuit_source_rect`)

---

## 3. CLAUDE.md Updates Needed

### Already Implemented (by previous sessions)
- [x] Pre-flight checklist with 5 steps
- [x] Legacy branch handling (PRE_COMMIT_ALLOW_NO_CONFIG workaround)
- [x] Session checkpointing section
- [x] `gh issue view --json` guidance
- [x] Triage step for stale Ready items
- [x] Edge case table (stale items, blocked, vague requirements)
- [x] `make format && make lint` in work loop

### Still Needed
- [ ] Add `--limit 200` to all `item-list` commands in Board Commands section
- [ ] Replace python-pipe patterns with `--jq` equivalents
- [ ] Add note: "item-add does not set status — must follow with item-edit"
- [ ] Add Board Query Patterns subsection with copy-paste recipes
- [ ] Add note: MainWindow cannot be tested in offscreen mode
- [ ] Add note: use `tmp_path` in tests, never hardcode paths
- [ ] Document `main_window.py` as merge conflict hotspot (future refactoring target)

---

## 4. Multi-Agent Coordination (Critical Section Patterns)

### Mapping Multiprocessing Concepts to Agent Workflow

| CS Concept | Agent Equivalent | Implementation |
|------------|-----------------|----------------|
| **Process** | One Claude Code instance in one repo directory | Each directory is an independent worker |
| **Thread-local storage** | `MEMORY.md` per directory | Ephemeral session state, never shared |
| **Shared memory (read-only)** | `CLAUDE.md` in git | The "program" all agents follow |
| **Shared mutable state** | GitHub board + `origin/main` | The "heap" agents coordinate around |
| **Mutex / Lock** | Board status field | "In Progress" = lock acquired |
| **Critical section** | Working on an issue; merging a PR | One agent at a time per issue |
| **Message passing** | Issue comments, PR reviews, feedback files | Async communication between agents |
| **Semaphore** | Ready queue count | Natural work distribution |

### Rule 1: Mutual Exclusion on Issues

```
ACQUIRE: Move issue to "In Progress" on board
  → If already "In Progress", SKIP (non-blocking trylock)
  → Only one agent works on an issue at a time

RELEASE: Move issue to "In Review" and push PR
  → Always release before acquiring next issue
  → Never hold two issues simultaneously
```

**Why**: Two agents working on the same issue creates merge conflicts, wasted work, and confusion. The board status is the coordination mechanism — it's the lock.

### Rule 2: Atomic Board Operations

Board queries and mutations are NOT atomic. Between "query Ready items" and "move to In Progress", another agent could claim the same issue.

**Mitigation — Work partitioning by directory**:
```
Directory A: works on odd-numbered issues (or P0 issues)
Directory B: works on even-numbered issues (or P1 issues)
Directory C: PR monitor / reviewer only (never claims issues)
```

Or use **Epic partitioning** (preferred once Epics exist):
```
Directory A: works on "Stability & Polish" epic
Directory B: works on "Advanced Simulation" epic
Directory C: PR monitor — merges all green PRs
```

### Rule 3: Feature Branches as Thread-Local State

Each agent works on its own feature branch. Branches never overlap. The only shared state is `origin/main`, and it's updated exclusively through PR merges (the "critical section").

```
Agent A: issue-124-spice-import (local branch)
Agent B: issue-127-wire-labels (local branch)
Agent C: (monitors PRs, merges to origin/main)

No two agents touch the same branch.
```

### Rule 4: PR Merge as the Critical Section

Only one PR should merge at a time. Otherwise, cascading rebase conflicts accumulate (observed: 6 conflicts in PR #175 after 5 PRs merged to main while pending).

**Options**:
1. **Sequential merge** (simplest): PR monitor agent merges one PR, waits for CI, merges next
2. **GitHub merge queue** (best): Enable merge queue in repo settings — GitHub handles ordering
3. **Auto-merge** (good): `gh pr merge --auto --squash` — merges when CI passes

### Rule 5: Message Passing via Issue Comments

Agents communicate asynchronously through issue comments:
- **Checkpoint comments**: "Completed X, next working on Y"
- **Agent feedback comments**: Structured feedback on issue clarity, blockers, assumptions
- **Hour logging**: `⏱️ Xh — description`

Agents do NOT communicate through shared files (MEMORY.md, CLAUDE.md edits) during sessions — those are read at startup and written at shutdown.

### Rule 6: Deadlock Prevention

Deadlock requires: mutual exclusion + hold-and-wait + no preemption + circular wait.

**Prevention**:
- **No hold-and-wait**: Agents complete one issue fully before starting the next
- **Ordered acquisition**: Issues are worked in priority order (P0 > P1 > P2, then by issue number) — no circular dependencies
- **Timeout**: Soft limit of 3-4 issues per session prevents indefinite resource holding
- **Blocked escape hatch**: If blocked, release issue (move to Blocked), pick next Ready item

### Rule 7: MEMORY.md as Thread-Local Storage

Each directory's `MEMORY.md` is ephemeral and local to that agent. It should contain:
- Cached board IDs (for speed, re-query if mutations fail)
- Current session state (which issues are in progress, what's been completed)
- Known gotchas from recent experience

**MEMORY.md should NOT contain**:
- Shared process rules (those go in CLAUDE.md)
- Board field definitions (those are queryable)
- Information another agent needs to function

### Rule 8: CLAUDE.md as Shared Read-Only Program

`CLAUDE.md` is the shared "program" all agents execute. Changes to it should be:
- Infrequent (once per session at most)
- Made via PR (reviewed by human)
- Never made during an active coding session (agents read it at startup)

Think of it like updating a shared library — you don't modify it while processes are running.

---

## 5. Directory Architecture for Multi-Machine Scaling

```
Machine 1 (Linux Desktop)
├── ~/sr_design/Spice-GUI/          → Agent A (authoring)
├── ~/sr_design/claude-a/Spice-GUI/ → Agent B (authoring)
└── ~/sr_design/claude-b/Spice-GUI/ → Agent C (PR monitor)

Machine 2 (Windows Laptop)
├── C:\repos\Spice-GUI\             → Agent D (authoring)
└── C:\repos\Spice-GUI-monitor\     → Agent E (PR monitor)
```

**Each directory is a fully independent process**:
- Its own git checkout, own `.venv`, own `MEMORY.md`
- Communicates only through GitHub (board, issues, PRs)
- No local file sharing between directories

**Scaling rules**:
- Adding a machine = adding a new worker process
- Each machine needs `gh auth login` and a fresh `git clone`
- Assign work partitions (by Epic or priority) to avoid conflicts
- One PR monitor per cluster of 3-4 authoring agents

---

## 6. Agent Roles

### Authoring Agent
- Picks Ready issues from the board
- Implements features, writes tests
- Creates PRs
- Runs `make format && make lint && make test`
- Moves issues In Progress → In Review

### PR Monitor Agent
- Watches for open PRs (`gh pr list`)
- Fixes formatting issues (`make format`)
- Resolves merge conflicts (rebase)
- Merges green PRs
- Moves issues In Review → Done
- Creates emergency fix PRs (CI-breaking tests, etc.)

### Review Agent (human)
- Reviews PR code quality
- Approves architectural decisions
- Manages board priorities (moves items between Backlog/Ready)
- Decides on Epic structure and priority changes
- Merges CLAUDE.md updates

---

## 7. Aggregate Metrics (All Sessions)

| Metric | Value |
|--------|-------|
| Total issues completed | ~25 |
| Total PRs created/merged | ~30 |
| Total tests added | ~300+ |
| Test count (start → current) | 494 → 907 |
| Average issues/hour | 1.0-2.7 (varies by complexity) |
| First-attempt commit success | 0% (black mismatch, now fixed) |
| Second-attempt commit success | 100% |
| Test regression rate | 0% |
| Merge conflict rate | ~15% of PRs |
| Main conflict hotspot | main_window.py (100% of conflicts) |

---

## 8. Files in This Directory

After consolidation, these files can be **archived or deleted** — their insights are captured above:

| File | Status | Content Summary |
|------|--------|-----------------|
| `CONSOLIDATED-BEST-PRACTICES.md` | **CURRENT** | This file — the single source of truth |
| `2026-02-10-roadmap-epics-proposal.md` | **ACTIVE** | Epics proposal, awaiting decision |
| `session-template.md` | **KEEP** | Template for future session summaries |
| `README.md` | **KEEP** | Directory overview (update to point here) |
| `2026-02-09-session-feedback.json` | Archive | Session 1 (Sonnet, issues #29, #50) |
| `2026-02-09-autonomous-workflow-session.json` | Archive | Session 1 (Opus, issues #113, #27, triages) |
| `2026-02-09-session-2-feedback.json` | Archive | Session 2 (Opus, issue #145 dark mode) |
| `2026-02-09-pr-maintenance-session.json` | Archive | PR maintenance (Opus, PRs #151-166) |
| `2026-02-10-session-3-feedback.json` | Archive | Session 3 authoring (Opus, issues #148, #146, etc.) |
| `2026-02-10-session-3-pr-monitor-feedback.json` | Archive | Session 3 PR monitor (Opus, 12 PRs processed) |
| `2026-02-10-session-4-feedback.json` | Archive | Session 4 (Opus, issues #124, #127, #147) |
| `2026-02-10-gh-cli-patterns.json` | Archive | gh CLI investigation and patterns |
| `workflow-feedback-2026-02-09.md` | Archive | Detailed workflow feedback (Sonnet) |
| `session-summary-2026-02-09-session-2.md` | Archive | Session 2 summary |
| `session-summary-2026-02-10-session-3.md` | Archive | Session 3 summary |
| `session-summary-2026-02-10-session-4.md` | Archive | Session 4 summary |
| `commands-reference-2026-02-09.md` | Archive | Command reference (superseded by CLAUDE.md) |
| `session-data-2026-02-09.json` | Archive | Structured session data |
| `Agent-Feedback-Prior-To-New-Workflow.md` | Archive | Pre-restart agent notes |
