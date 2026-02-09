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
pip install -r app/requirements.txt
pip install pytest ruff
```
Or run `scripts/setup.sh` (Linux/Mac) or `scripts/setup.ps1` (Windows).

## Testing & Linting
```bash
python -m pytest              # run all tests (works from repo root)
python -m pytest -v           # verbose
python -m pytest app/tests/unit/test_foo.py  # single file
ruff check app/               # lint
```

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
```

## Autonomous Workflow

Claude Code is authorized to work **fully autonomously** on Ready items.

### Work Loop
1. Discover board IDs (see above)
2. Query board for next **Ready** item (prefer higher priority, lower issue number)
3. Move issue to **In Progress**
4. Create branch `issue-<N>-short-description` from `main`
5. Write a brief plan, assess complexity
6. Implement the change
7. Run `python -m pytest` — all tests must pass
8. Run `ruff check app/` — fix any lint errors
9. Commit with descriptive message, push branch to remote
10. Create PR targeting `main` (or push directly for small fixes)
11. Close the GitHub issue (reference the commit/PR)
12. Move issue to **In Review** on the board
13. Log hours: comment `⏱️ Xh - description` on issue, update Hours field
14. Pick next Ready item → repeat from step 2

### Hours Estimates
- Small fix/tweak: **0.5h**
- Medium feature/refactor: **1–2h**
- Large feature/multi-file: **3h+**

### Stop Conditions
- **Blocked**: Move issue to Blocked with explanatory comment. Pick next Ready item.
- **Ready queue empty**: **Stop and notify user.** Do NOT pull from Backlog.

### Edge Cases
| Scenario | Action |
|----------|--------|
| Hard to test (UI, ngspice) | Implement, commit, flag manual testing needed in issue comment |
| Vague requirements | Make judgment call, note assumptions in commit/issue comment |
| Conflicting issues | Move to Blocked with explanation, pick next Ready item |

## Platform Notes
- **Windows**: Avoid piping `gh` output directly to `python` (fails with "pipe is being closed"). Write to a temp file first, then read it.
- **Board field updates**: `updateProjectV2Field` with `singleSelectOptions` regenerates all option IDs. Always re-query IDs after modifying field options.
