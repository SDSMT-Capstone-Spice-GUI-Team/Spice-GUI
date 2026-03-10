# Proposed CLAUDE.md Changes for Epic Workflow

**Status**: Draft — requires team review before applying.

These are the specific sections of CLAUDE.md that would change. Unchanged sections are omitted.

---

## Section: Git Conventions (Replace Existing)

```markdown
## Git Conventions

### Branch Structure

```
main                              <- always demo-ready, tagged for releases
├── develop                       <- integration branch, CI must pass
│   ├── epic/<name>               <- grouped multi-issue feature work
│   │   └── issue-<N>-<description>
│   └── issue-<N>-<description>   <- standalone fixes/features
└── release/vX.Y                  <- cut from develop for release stabilization
    └── hotfix/vX.Y.Z             <- critical fixes on released versions
```

### Branch Rules

| Branch | Base | PR Target | Who Merges | Protection |
|--------|------|-----------|------------|------------|
| `main` | — | — | Jeremy | Require PR, no direct push |
| `develop` | `main` | `main` (via release) | PR mgmt agents + Jeremy | Require CI pass |
| `epic/<name>` | `develop` | `develop` | Jeremy reviews | Require CI pass |
| `issue-<N>-*` | epic or develop | epic or develop | Coding agents create PR | — |
| `release/vX.Y` | `develop` | `main` | Jeremy | — |
| `hotfix/vX.Y.Z` | `release/vX.Y` | `main` + `develop` | Jeremy | — |

### Branch Naming
- Epic branches: `epic/<name>` (e.g., `epic/monte-carlo`, `epic/ui-overhaul`)
- Issue branches: `issue-<N>-short-description` (e.g., `issue-75-csv-export`)
- Release branches: `release/v<major>.<minor>` (e.g., `release/v1.3`)
- Hotfix branches: `hotfix/v<major>.<minor>.<patch>` (e.g., `hotfix/v1.3.1`)

### Commit Messages
- Lowercase imperative (e.g. "add CSV export", "fix wire rendering")
- Co-author tag on all agent commits:
  ```
  Co-Authored-By: Claude <model> <noreply@anthropic.com>
  ```
```

---

## Section: Autonomous Workflow — Pre-flight Checklist (Modify Step 1)

Replace:
```markdown
1. **Start from Fresh Main**
   ```bash
   git checkout main && git pull origin main
   ```
```

With:
```markdown
1. **Start from Fresh Develop**
   ```bash
   git checkout develop && git pull origin develop
   ```
   - Feature branches are based on `develop`, not `main`
   - Run this at session start and before creating each new feature branch
```

---

## Section: Autonomous Workflow — Work Loop (Replace Steps 2-5, 10, 13)

Replace step 2:
```markdown
2. Query board for next **Ready** item (prefer higher priority, lower issue number)
```

With:
```markdown
2. Query board for next **Ready** item (prefer higher priority, lower issue number)
```
*(No change to step 2 itself)*

Replace steps 4-5:
```markdown
4. Move issue to **In Progress**
5. **Resolve base branch** using the Branch Resolution Algorithm:
   a. Read issue labels: `gh issue view <N> --json labels --jq '.labels[].name'`
   b. Check for `epic:<name>` label
   c. If epic label found:
      - BASE = `epic/<name>`
      - If branch doesn't exist on remote, create it from `develop`:
        ```bash
        git checkout develop && git pull origin develop
        git checkout -b epic/<name> && git push -u origin epic/<name>
        ```
   d. If no epic label: BASE = `develop`
   e. Check issue body for `Base-Branch:` override (takes precedence)
   f. Create issue branch from BASE:
      ```bash
      git checkout <BASE> && git pull origin <BASE>
      git checkout -b issue-<N>-short-description
      ```
```

Replace step 10:
```markdown
10. Fetch and rebase on latest base branch (epic or develop):
    ```bash
    git fetch origin
    git rebase origin/<BASE>
    ```
```

Replace step 13:
```markdown
13. Create PR targeting the **base branch** (epic or develop). NEVER target `main` directly.
    ```bash
    gh pr create --base <BASE> --title "..." --body "..."
    ```
```

---

## New Section: Agent Roles (Add After Autonomous Workflow)

```markdown
## Agent Roles

Multiple Claude agents may operate concurrently. Each role has specific responsibilities:

### Coding Agents (2-5 concurrent)
- Pick Ready items from the board
- Follow the Work Loop (above)
- One issue per agent, no file overlap within an epic
- PR to epic branch (if labeled) or `develop` (standalone)
- NEVER PR to `main`

### PR Management Agents (1-2)
- Monitor open PRs for CI status
- Merge `issue -> epic` when CI passes + agent feedback posted
- Flag `epic -> develop` merges for Jeremy's review
- Auto-merge standalone `issue -> develop` if CI passes and test count increases

### Backlog Grooming Agents (1-2)
- Assign `epic:<name>` labels to issues
- Break large issues into sub-tasks with clear acceptance criteria
- Flag issues needing domain expert input (Marc/Micah) with `needs:ee-review` label
- Ensure all Ready items have an epic label or are explicitly standalone

### Wiki/Docs Agents (0-1)
- Update wiki pages when features ship
- Keep architecture documentation current
- Do NOT modify CLAUDE.md without Jeremy's approval

### DevOps Agents (1-2)
- Implement CI/CD changes, branch protection rules
- Update Makefile, scripts, pre-commit config
- All changes PR to `develop` with `devops` label
```

---

## New Section: Epic Management (Add After Agent Roles)

```markdown
## Epic Management

### Creating Epics
1. Create a GitHub Milestone for the epic (provides progress tracking)
2. Add `epic:<name>` label to the repo
3. Label all related issues with `epic:<name>`
4. Epic branch is created automatically by the first coding agent that picks up a labeled issue

### Epic Lifecycle
- **Max lifetime**: 2 weeks. If an epic runs longer, close it and create a follow-up.
- **Staleness**: PR management agents rebase epic branches on `develop` weekly.
- **Completion**: When all issues in an epic are done:
  1. PR management agent creates `epic/<name> -> develop` PR
  2. Jeremy reviews and merges
  3. Delete the epic branch

### Reserved Epic Namespaces
- `epic/ui-*` — Reserved for Jon (UI/UX work). Agents only touch if issue is explicitly labeled.
- All other epic names are available for agent use.
```

---

## Notes

These changes are **additive** — most existing CLAUDE.md content stays the same. The key changes are:

1. `develop` replaces `main` as the base branch for all feature work
2. Branch resolution algorithm added (label-based epic detection)
3. Agent role definitions added
4. Epic lifecycle management added
5. PR targets change from `main` to epic/develop

The existing sections for Setup, Testing, Project Structure, Board Commands, Environment Setup, Session Management, and Platform Notes remain unchanged.
