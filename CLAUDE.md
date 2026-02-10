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
- Test count should increase by ≥5 for new features
- Run tests from repo root: `python -m pytest` or `make test`

## Project Structure
```
app/
├── models/          # Data classes, no Qt (CircuitModel, ComponentData, WireData, NodeData)
├── controllers/     # Business logic (CircuitController, SimulationController, FileController)
├── GUI/             # PyQt6 views (MainWindow, CircuitCanvas, dialogs, graphics items)
├── simulation/      # ngspice pipeline (netlist gen, runner, parser, validator, CSV export)
└── tests/           # pytest suite (unit/ and integration/)
```

## Git Conventions
- Branch naming: `issue-<N>-short-description` (e.g. `issue-75-csv-export`)
- Commit messages: lowercase imperative (e.g. "add CSV export", "fix wire rendering")
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
# Get all board items (issue-to-item ID mapping):
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 100
```
Parse the JSON to find: project ID, Status field ID, Hours field ID, and the option IDs for each status (Backlog, Ready, In progress, Blocked, In review, Done).

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

# Add issue to board:
gh project item-add 2 --owner SDSMT-Capstone-Spice-GUI-Team --url <ISSUE_URL>

# View issue details (use --json to avoid Projects Classic deprecation errors):
gh issue view <N> --repo SDSMT-Capstone-Spice-GUI-Team/Spice-GUI --json title,body,labels,comments
```

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

1. **Start from Fresh Main**
   ```bash
   git checkout main && git pull origin main
   ```
   - Ensures feature branches are based on the latest code
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
1. Discover board IDs (see above)
2. Query board for next **Ready** item (prefer higher priority, lower issue number)
3. **Triage**: Check issue comments and state (`gh issue view <N> --json state,comments`). If already resolved or closed, move to In Review/Done and skip to next Ready item.
4. Move issue to **In Progress**
5. Create branch `issue-<N>-short-description` from `main`
6. Write a brief plan, assess complexity
7. Implement the change
8. **Format, test, and lint**
   ```bash
   # Auto-format first (black + isort + ruff --fix)
   make format

   # Then run tests and lint checks
   make test
   make lint
   ```

   **Requirements**:
   - ✅ Code is formatted (`make format` produces no diff)
   - ✅ All new tests pass
   - ✅ All existing tests still pass (no regressions)
   - ✅ Full lint passes: ruff + black --check + isort --check (`make lint`)
   - ✅ Formatting verified: `make format-check` (optional — `make lint` also checks)
   - ✅ Test count increased by ≥5 for new features

   **Troubleshooting**:
   - `ModuleNotFoundError`: Venv not activated or deps not installed
   - `pytest: command not found`: Run `pip install -r app/requirements-dev.txt`
   - Formatting drift: Run `make format` then `make lint` to verify
   - Pre-commit hook missing: Run `make install-hooks`

9. Commit changes
10. Fetch and rebase on latest `origin/main` — resolves merge conflicts from PRs merged mid-session
11. Re-run tests and linting after rebase to catch conflicts (e.g. duplicate imports from merged PRs)
12. Push branch to remote
13. Create PR targeting `main` (or push directly for small fixes)
14. Close the GitHub issue (reference the commit/PR)
15. Move issue to **In Review** on the board
16. Log hours: comment `⏱️ Xh - description` on issue, update Hours field
17. Pick next Ready item → repeat from step 2

**Post-issue checklist** (verify before picking next item):
- [ ] PR created and linked to issue
- [ ] Issue closed (`gh issue close <N>`)
- [ ] Board status updated to In Review
- [ ] Hours logged (comment + field)
- [ ] MEMORY.md updated with issue/PR number

### Hours Estimates
- Small fix/tweak: **0.5h**
- Medium feature/refactor: **1–2h**
- Large feature/multi-file: **3h+**

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
| Hard to test (UI, ngspice) | Implement, commit, flag manual testing needed in issue comment |
| Vague requirements | Make judgment call, note assumptions in commit/issue comment |
| Conflicting issues | Move to Blocked with explanation, pick next Ready item |
| Stale Ready item (already fixed/closed) | Verify via issue comments/state, move to In Review/Done, pick next Ready item |
| Context window full / subagent "prompt too long" | Stop work loop, notify user to start fresh session |

### Agent Feedback (required on every issue/PR)

After completing work on an issue, post a structured feedback comment on the issue:

```markdown
### Agent Feedback
- **Issue clarity**: X/5 — [what was clear/unclear]
- **Blockers**: [what slowed you down, or "None"]
- **Confidence**: [High/Medium/Low] — [what you're confident about, what needs human review]
- **Assumptions made**: [any judgment calls, or "None"]
- **Review focus**: [specific areas the reviewer should check]
```

After reviewing a PR, post feedback on the PR:

```markdown
### Review Feedback
- **Issue scope**: [too broad / too narrow / just right]
- **Code quality**: [follows patterns / introduces new conventions / concerns]
- **Test coverage**: [adequate / gaps in X]
- **Suggestion for issue writing**: [what would have made this easier]
```

This feedback improves future issue quality and agent effectiveness over time.

## Session Management

### Checkpointing (for long autonomous sessions)

For sessions working on >3 issues or >4 hours of work:

**After each issue completion**:
1. Post checkpoint comment on the completed issue:
   ```markdown
   ### 🏁 Checkpoint - Issue #{N} Complete

   **Completed**: Issue #{N} - {title}
   **PR**: #{PR_number}
   **Status**: Tests passing, moved to In Review
   **Next**: Issue #{next_number} - {next_title}
   **Session time**: ~{hours}h elapsed, estimated {remaining}h remaining
   ```

2. Update session progress in MEMORY.md:
   ```markdown
   ## Current Session (YYYY-MM-DD)
   - [x] Issue #X - {title} (PR #{PR}, {hours}h)
   - [ ] Issue #Y - {title} (In Progress)
   - [ ] Issue #Z - {title} (Next)

   Total: {completed}/{planned} issues, {hours_spent}/{hours_estimated}h
   ```

**Benefits**:
- Easy recovery if context window reached
- Clear progress tracking for user
- Helps prioritize if session must stop early

**Recovery**: If session interrupted, read MEMORY.md → latest checkpoint comment → resume from "Next" issue.

## Platform Notes
- **Windows**: Avoid piping `gh` output directly to `python` (fails with "pipe is being closed"). Write to a temp file first, then read it.
- **Board field updates**: `updateProjectV2Field` with `singleSelectOptions` regenerates all option IDs. Always re-query IDs after modifying field options.

### Legacy Branch Handling

> **Note**: This section applies to branches created before PR #138 (2026-02-09). New branches from main already include `.pre-commit-config.yaml`.

**Problem**: Feature branches created before Issue #106 (pre-commit hooks) lack `.pre-commit-config.yaml`.

**Symptoms**:
- `git commit` fails with "No .pre-commit-config.yaml file was found"
- Hook suggests `PRE_COMMIT_ALLOW_NO_CONFIG=1` or `--allow-missing-config`

**Solution A - Bypass hooks** (quick fix):
```bash
PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "message"
```

**Solution B - Add config** (proper fix):
```bash
# Copy pre-commit config from main
git show main:.pre-commit-config.yaml > .pre-commit-config.yaml
git add .pre-commit-config.yaml
git commit -m "Add pre-commit config"
```

**Prevention**: Pre-flight checklist (above) ensures you're on a current feature branch.
