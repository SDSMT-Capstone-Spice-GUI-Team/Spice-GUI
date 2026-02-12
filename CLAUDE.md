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
| Bug fix | >=1 regression test that reproduces the bug | Only if visual/interaction |
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
| `develop` | `main` | `main` (via release) | Authoring agents + Jeremy | Require CI pass |
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

**All IDs must be discovered dynamically — do NOT hardcode them.** Use `/board-state` skill for quick access.

### Discover IDs at Session Start
```bash
# Get project node ID:
gh project view 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json
# Get field IDs and status option IDs:
gh project field-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json
# Get all board items (issue-to-item ID mapping) — always use --limit 200:
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200
```

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

## Agent Roles

Claude Code is authorized to work **fully autonomously** on Ready items.

Role-specific workflows and instructions are defined in `.claude/agents/`:
- `authoring.md` — picks Ready issues, implements code, writes tests, creates PRs, merges after CI passes
- `grooming.md` — labels issues with epic tags, updates epics, maintains board hygiene
- `orchestrator.md` — monitors workflow health, tracks epic progress, updates process docs

Common task templates are in `.claude/skills/`:
- `/board-state` — fetch current board state (Ready queue, In Progress, PRs)
- `/work-issue <N>` — implement a specific issue end-to-end
- `/merge-prs` — review and merge open PRs
- `/reset-local-settings` — clean up accumulated permission cruft

### Multi-Agent Coordination
- **GitHub board is the shared state** — board status is the coordination mechanism
- **Issue locking**: Moving to In Progress = acquiring the lock. If already In Progress, skip it.
- **Never hold two issues simultaneously** — complete one before starting the next
- **Agents communicate via GitHub** — issue comments, PR reviews, board status changes

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

## Platform Notes
- **Windows**: Avoid piping `gh` output directly to `python` (fails with "pipe is being closed"). Write to a temp file first, then read it.
- **Board field updates**: `updateProjectV2Field` with `singleSelectOptions` regenerates all option IDs. Always re-query IDs after modifying field options.
