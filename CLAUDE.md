# Spice-GUI

## Project
- **Stack**: Python 3.11+, PyQt6, ngspice
- **Repo**: SDSMT-Capstone-Spice-GUI-Team/Spice-GUI
- **Org**: SDSMT-Capstone-Spice-GUI-Team
- **Board**: GitHub Projects #2 on the org

## Setup
Prerequisites: Python 3.11+, `gh` CLI (authenticated), git.
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r app/requirements.txt -r app/requirements-dev.txt
make install-hooks  # Install pre-commit hooks (black, isort, ruff)
```
Or run `scripts/setup.sh` (Linux/Mac) or `scripts/setup.ps1` (Windows).

## Testing & Linting

**Formatters**: black + isort (canonical). Do NOT use `ruff format` — it conflicts with black.

```bash
python -m pytest              # run all tests (works from repo root)
python -m pytest -v           # verbose
python -m pytest app/tests/unit/test_foo.py  # single file
make format                   # auto-format: black + isort + ruff --fix
make lint                     # full lint: ruff + black --check + isort --check
make format-check             # verify formatting without modifying files
```

### Testing Conventions
- Use `tmp_path` (pytest fixture) for all file path tests — never hardcode paths like `/some/path` (Windows uses backslash separators)
- Use `qtbot` fixture for Qt widget tests
- Run tests from repo root: `python -m pytest` or `make test`
- **MainWindow cannot be instantiated in offscreen test mode** — it hangs. Test with lower-level components (QGraphicsScene, QPrinter, keybinding registries) instead
- Pre-existing GUI test errors (~46) in headless environments are expected (Qt display server issues)

### Test Layer Priority

The MVC architecture exists specifically to enable testing without the GUI (see `docs/adr/001-mvc-testability.md`). When writing tests, work down this list and stop at the first level that covers the behavior:

1. **Model/controller test** — if the logic lives below the GUI, test it there (serialization, undo, node consistency, file operations)
2. **Netlist snapshot test** — if it affects simulation output (component lines, analysis directives, model deduplication)
3. **qtbot widget test** — if it's dialog, menu, or panel behavior (analysis dialogs, keybindings editor, palette search)
4. **Structural assertion** — if it's about rendering (terminal positions, bounding boxes, z-order via `zValue()`)
5. **Human testing item** — only if none of the above can verify it (drag feel, visual aesthetics, print dialogs, cross-session UX)

### Test Expectations by Change Type

| Change Type | Automated Tests | Human Testing Item? |
|-------------|----------------|-------------------|
| Bug fix | ≥1 regression test that reproduces the bug | Only if visual/interaction |
| New feature | Tests covering core behavior at appropriate layer | Yes, for UI-visible behavior |
| Refactor | Existing tests must pass, no new tests required | No |
| UI-only | Structural assertions where applicable | Yes, always |

Tests should cover the *behavior*, not just the *count*. A single test that exercises the real code path is worth more than five tests that assert obvious properties.

## Project Structure
```
app/
├── models/          # Data classes, no Qt (CircuitModel, ComponentData, WireData, NodeData)
├── controllers/     # Business logic (CircuitController, SimulationController, FileController)
├── GUI/             # PyQt6 views (MainWindow, CircuitCanvas, dialogs, graphics items)
├── simulation/      # ngspice pipeline (netlist gen, runner, parser, validator, CSV export)
└── tests/           # pytest suite (unit/ and integration/)
```

## Model API Quick Reference

Constructor signatures for test fixtures (all are `@dataclass`):

```python
ComponentData(component_id, component_type, value, position, rotation=0, flip_h=False, flip_v=False, waveform_type=None, waveform_params=None)
WireData(start_component_id, start_terminal, end_component_id, end_terminal, waypoints=[], algorithm="idastar")
NodeData(terminals=set(), wire_indices=set(), is_ground=False, custom_label=None, auto_label="")
CircuitModel(components={}, wires=[], nodes=[], terminal_to_node={}, component_counter={}, analysis_type="DC Operating Point", analysis_params={})
```

**Common mistakes**: `value` not `properties`, `start_terminal` not `start_terminal_index`, `component_id` not `id`.

## Git Conventions

### Branch Structure (see `docs/adr/003-branching-strategy.md`)

```
main                              <- always human-verified, student-safe
├── develop                       <- integration branch, CI must pass
│   ├── epic/<name>               <- grouped multi-issue feature work
│   │   └── issue-<N>-<description>
│   └── issue-<N>-<description>   <- standalone fixes/features
└── release/vX.Y                  <- cut from develop for releases
```

| Branch | Base | PR Target | Who Merges | Protection |
|--------|------|-----------|------------|------------|
| `main` | — | — | Jeremy | Require PR, no direct push |
| `develop` | `main` | `main` (via release) | PR mgmt agents + Jeremy | Require CI pass |
| `epic/<name>` | `develop` | `develop` | Jeremy reviews | Require CI pass |
| `issue-<N>-*` | epic or develop | epic or develop | Coding agents | — |

### Branch Naming
- Epic branches: `epic/<name>` (e.g., `epic/stability`, `epic/ui-customization`)
- Issue branches: `issue-<N>-short-description` (e.g. `issue-75-csv-export`)
- Release branches: `release/v<major>.<minor>` (e.g., `release/v1.0`)

### Commit Messages
- Lowercase imperative (e.g. "add CSV export", "fix wire rendering")
- Co-author tag on all commits:
  ```
  Co-Authored-By: Claude <model> <noreply@anthropic.com>
  ```

## GitHub Board (Project #2)

**All IDs must be discovered dynamically — do NOT hardcode them.**

### Discover IDs at Session Start
```bash
# Get project node ID:
gh project view 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json
# Get field IDs and status option IDs:
gh project field-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json
# Get all board items (issue-to-item ID mapping) — always use --limit 200:
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200
```
Parse the JSON to find: project ID, Status field ID, Hours field ID, and the option IDs for each status (Backlog, Ready, In progress, Blocked, In review, Done).

**Important**: The default `--limit` is 30, which silently truncates results. The board has 100+ items — always use `--limit 200`.

**Caching**: IDs may be cached in MEMORY.md for speed. If a board mutation fails, re-query all IDs before retrying.

### Board Commands
```bash
# Move item to a status:
gh project item-edit --project-id <PROJECT_ID> --id <ITEM_ID> \
  --field-id <STATUS_FIELD_ID> --single-select-option-id <STATUS_OPTION_ID>

# Update hours:
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "<PROJECT_ID>", itemId: "<ITEM_ID>",
    fieldId: "<HOURS_FIELD_ID>", value: { number: <N> }
  }) { projectV2Item { id } }
}'

# Add issue to board (NOTE: does NOT set status — item gets null status):
gh project item-add 2 --owner SDSMT-Capstone-Spice-GUI-Team --url <ISSUE_URL>
# MUST follow with item-edit to set status, otherwise item is invisible in column views

# View issue details (use --json to avoid Projects Classic deprecation errors):
gh issue view <N> --repo SDSMT-Capstone-Spice-GUI-Team/Spice-GUI --json title,body,labels,comments
```

### Board Query Patterns (--jq)

Use `--jq` instead of piping to python — avoids broken-pipe race conditions on Linux.

```bash
# Get Ready items (compact output for token efficiency):
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 \
  --jq '.items[] | select(.status == "Ready") | {n: .content.number, id: .id, t: .content.title}'

# Get item IDs for specific issue numbers:
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 \
  --jq '.items[] | select(.content.number == 42) | {id: .id, s: .status}'

# Find items with no status (newly added, need column assignment):
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 \
  --jq '.items[] | select(.status == null) | {n: .content.number, id: .id}'

# Compact board overview:
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 \
  --jq '.items[] | {n: .content.number, s: .status}'
```

## Epics

Epics group related issues into goal-oriented swimlanes (see `docs/decisions/2026-02-10-epic-workflow-and-branch-strategy.md`). They serve three purposes:
1. **Milestone** — track progress toward a larger goal
2. **Swimlane** — partition work across agents to reduce merge conflicts
3. **Context** — give agents the bigger picture when working on individual issues

### Active Epics

| Epic | Label | Branch | Priority | Description |
|------|-------|--------|----------|-------------|
| #209 | `epic:stability` | `epic/stability` | P0 | Bug fixes, test coverage, architectural improvements |
| #210 | `epic:simulation` | `epic/simulation` | P1 | New analysis types, accuracy, error handling |
| #211 | `epic:export` | `epic/export` | P1 | Export formats, sharing, templates |
| #287 | `epic:ui-customization` | `epic/ui-customization` | P1 | Symbol styles, themes, color modes, preferences |
| #212 | `epic:instructor` | `epic/instructor` | P2 | Instructor tools, grading, templates |
| #213 | `epic:scripting` | `epic/scripting` | P2 | Python API, batch operations, plugins |

### Epic Workflow
- Issues carry an `epic:*` label linking them to their parent epic
- When assigned to an epic, filter Ready queue by that label
- Read the epic issue before starting work for goal context
- Epic branches are created from `develop` by the first agent that picks up a labeled issue
- Completing all issues in an epic is a precondition for promoting that epic's work to `main`

## Human Testing

Human testing board: [Project #3](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)
Testing guide: `docs/human-testing-guide.md`
Quality model: `docs/adr/002-tiered-testing.md`

### Filing Human Testing Items
When a PR includes UI-visible behavior not covered by automated tests, add a checkbox item to the appropriate testing issue:

| Feature Area | Issue |
|-------------|-------|
| Smoke Test | #269 |
| Components | #270 |
| Selection & Clipboard | #271 |
| Wires | #272 |
| Undo/Redo | #273 |
| Annotations | #279 |
| File Operations | #274 |
| Simulation | #275 |
| Plot Features | #276 |
| User Interface | #277 |

Format: `- [ ] Brief description (PR #NNN)`

### Bugs from Human Testing
- Bugs found during human testing get the `bug` label
- They enter Project #2 board at Backlog until triaged
- Reference the testing issue they came from (e.g., "Found during #270")

## Environment Setup

### Virtual Environment

**Activation**:
```bash
# From project root
source .venv/bin/activate

# From app/ directory
source ../.venv/bin/activate

# Verify activation
which python  # Should show: /path/to/project/.venv/bin/python
```

**Common Issues**:

| Issue | Symptom | Solution |
|-------|---------|----------|
| Wrong Python | `which python` shows system Python | Run `source .venv/bin/activate` |
| Missing dependencies | `ModuleNotFoundError` on import | `pip install -r app/requirements.txt -r app/requirements-dev.txt` |
| pytest not found | `pytest: command not found` | `pip install pytest` or use Makefile |
| GUI tests skipped | Missing qtbot errors (pre-2026-02-09) | `pip install pytest-qt>=4.4.0` |

**Installation**:
```bash
# Create venv (if doesn't exist)
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install all dependencies
pip install -r app/requirements.txt -r app/requirements-dev.txt

# Install pre-commit hooks
make install-hooks

# Or use Makefile for deps
make install-dev
```

## Autonomous Workflow

Claude Code is authorized to work **fully autonomously** on Ready items.

### Pre-flight Checklist

Before starting implementation on any issue, verify:

1. **Start from Fresh Develop**
   ```bash
   git checkout develop && git pull origin develop
   ```
   - Feature branches are based on `develop`, not `main`
   - Run this at session start and before creating each new feature branch

2. **Virtual Environment**
   ```bash
   which python  # Should show .venv/bin/python
   ```
   - ✅ Venv activated: Proceed
   - ❌ Venv not activated: Run `source .venv/bin/activate` (from project root)

3. **Test Infrastructure**
   ```bash
   make test  # Or: cd app && python -m pytest tests/ --collect-only
   ```
   - ✅ Tests can be collected: Proceed
   - ❌ Import errors/missing deps: Fix environment first

4. **Pre-commit Hooks**
   ```bash
   ls .git/hooks/pre-commit  # Should exist
   ```
   - ✅ Hook file exists: Proceed
   - ❌ Missing: Run `make install-hooks` (or `pre-commit install`)

5. **Clean Working Tree**
   ```bash
   git status
   ```
   - ✅ No uncommitted changes: Proceed
   - ❌ Uncommitted changes: Stash or commit first

**If any check fails**: Fix the issue before creating new files or writing code.

**Shortcut**: After creating your feature branch, run `make preflight` to verify all checks at once.

### Work Loop
1. Discover board IDs (see above — use `--jq` patterns from Board Query Patterns section)
2. Query board for next **Ready** item. If assigned to an epic, filter by that epic's label. Otherwise prefer P0 > P1 > P2, then lower issue number. If an item is already **In Progress**, skip it (another agent may own it).
3. **Triage**: Check issue comments and state (`gh issue view <N> --json state,comments`). If already resolved or closed, move to In Review/Done and skip to next Ready item.
4. **Read epic context**: If the issue has an `epic:*` label, read the epic issue for context on the larger goal before starting work.
5. Move issue to **In Progress**
6. **Resolve base branch and create issue branch**:
   a. Read issue labels: `gh issue view <N> --json labels --jq '.labels[].name'`
   b. Check for `epic:<name>` label
   c. If epic label found: BASE = `epic/<name>`. If branch doesn't exist on remote, create it from `develop`.
   d. If no epic label: BASE = `develop`
   e. Create issue branch from BASE:
      ```bash
      git checkout <BASE> && git pull origin <BASE>
      git checkout -b issue-<N>-short-description
      ```
7. Write a brief plan, assess complexity
8. Implement the change
9. **Format, test, and lint**
   ```bash
   # Auto-format first (black + isort + ruff --fix)
   make format

   # Then run tests and lint checks
   make test
   make lint
   ```

   **Requirements**:
   - ✅ Code is formatted (`make format` produces no diff)
   - ✅ All new tests pass at the appropriate layer (see Test Layer Priority)
   - ✅ All existing tests still pass (no regressions)
   - ✅ Full lint passes: ruff + black --check + isort --check (`make lint`)

   **Troubleshooting**:
   - `ModuleNotFoundError`: Venv not activated or deps not installed
   - `pytest: command not found`: Run `pip install -r app/requirements-dev.txt`
   - Formatting drift: Run `make format` then `make lint` to verify
   - Pre-commit hook missing: Run `make install-hooks`

10. **File human testing items** if the change includes UI-visible behavior not covered by automated tests. Add a checkbox to the appropriate human testing issue (see Human Testing section). Format: `- [ ] Brief description (PR #NNN)`
11. Commit changes
12. Fetch and rebase on latest base branch (epic or `origin/develop`) — resolves merge conflicts from PRs merged mid-session
13. Re-run tests and linting after rebase to catch conflicts (e.g. duplicate imports from merged PRs)
14. Push branch to remote
15. Create PR targeting the **base branch** (epic or `develop`). NEVER target `main` directly.
16. Close the GitHub issue (reference the commit/PR)
17. Move issue to **In Review** on the board
18. Log hours: comment `⏱️ Xh - description` on issue, update Hours field
19. Pick next Ready item → repeat from step 2

**Post-issue checklist** (verify before picking next item):
- [ ] PR created and linked to issue (targeting epic or `develop`, never `main`)
- [ ] Issue closed (`gh issue close <N>`)
- [ ] Board status updated to In Review
- [ ] Hours logged (comment + field)
- [ ] Human testing items filed (if UI-visible behavior not covered by automated tests)
- [ ] MEMORY.md updated with issue/PR number

### Hours Estimates
Small: **0.5h** | Medium: **1–2h** | Large: **3h+**

### Stop Conditions
- **Blocked**: Move issue to Blocked with explanatory comment. Pick next Ready item.
- **Ready queue empty**: **Stop and notify user.** Do NOT pull from Backlog.

### Session Limits
- **Soft limit**: ~3–4 issues per session. Context accumulates (file reads, tool results, conversation history) and subagents inherit the full parent context, risking "prompt too long" errors.
- **Mitigations for long sessions**:
  - Use `limit`/`head_limit` on Read/Grep to keep tool results compact
  - Pass specific file paths and facts to subagents rather than relying on inherited context
  - Prefer `haiku` model for simple subagent tasks (search, small checks)
  - If a subagent fails with "prompt too long", stop the work loop and notify the user

### Edge Cases
| Scenario | Action |
|----------|--------|
| Hard to test (UI, ngspice) | Implement, commit, add human testing item to appropriate issue (#269-#279) |
| Vague requirements | Make judgment call, note assumptions in commit/issue comment |
| Conflicting issues | Move to Blocked with explanation, pick next Ready item |
| Stale Ready item (already fixed/closed) | Verify via issue comments/state, move to In Review/Done, pick next Ready item |
| Context window full / subagent "prompt too long" | Stop work loop, notify user to start fresh session |

### Agent Feedback (required on every issue/PR)

Post structured feedback as a comment on each completed issue and reviewed PR:

**Issue feedback fields**: Issue clarity (X/5), Blockers, Confidence (High/Med/Low), Assumptions made, Review focus areas.

**PR review fields**: Issue scope, Code quality, Test coverage, Suggestion for issue writing.

## Session Management

### Checkpointing (for long autonomous sessions)

For sessions working on >3 issues or >4 hours of work:
1. After each issue, post a checkpoint comment: completed issue/PR, next issue, elapsed time
2. Update MEMORY.md with session progress: `[x] Issue #X (PR #Y, Zh)` / `[ ] Issue #N (Next)`

**Recovery**: If session interrupted, read MEMORY.md → latest checkpoint comment → resume from "Next" issue.

## Multi-Agent Coordination

Multiple Claude Code instances may run concurrently across different directories and machines.

### Coordination Model
- **Each directory is an independent process** with its own git checkout, venv, and MEMORY.md
- **GitHub board is the shared state** — board status is the coordination mechanism
- **CLAUDE.md is shared read-only** — the "program" all agents follow (changes require a PR)
- **MEMORY.md is thread-local** — ephemeral session state, never shared between directories
- **Agents communicate via GitHub** — issue comments, PR reviews, board status changes

### Issue Locking (Mutual Exclusion)
- Moving an issue to **In Progress** = acquiring the lock
- If an issue is already **In Progress**, **skip it** (another agent owns it)
- Moving to **In Review** = releasing the lock
- **Never hold two issues simultaneously** — complete one before starting the next

### Work Partitioning
Agents are assigned to **Epics** to avoid merge conflicts and provide focus:
- Each epic has a label (`epic:stability`, `epic:simulation`, etc.) and an `epic/<name>` branch
- Agents filter Ready items by their assigned epic label
- Before starting an issue, read the epic issue for context on the larger goal
- If no epic is assigned, fall back to priority ordering (P0 > P1 > P2)
- PR monitor agents never claim issues — they only merge and fix PRs

### PR Merge Ordering
Only merge one PR at a time to prevent cascading rebase conflicts:
- PR monitor merges one PR → waits for CI → merges next
- Or enable GitHub merge queue for automatic ordering
- `main_window.py` is the #1 merge conflict hotspot (~1700 lines) — prefer changes to other files when possible

### Agent Roles
| Role | Responsibilities |
|------|-----------------|
| **Authoring** | Pick Ready issues, implement, create PRs |
| **PR Monitor** | Merge green PRs, fix formatting, resolve conflicts |
| **Review** (human) | Approve PRs, manage board priorities, steer Epics |

## Platform Notes
- **Windows**: Avoid piping `gh` output directly to `python` (fails with "pipe is being closed"). Write to a temp file first, then read it.
- **Board field updates**: `updateProjectV2Field` with `singleSelectOptions` regenerates all option IDs. Always re-query IDs after modifying field options.
