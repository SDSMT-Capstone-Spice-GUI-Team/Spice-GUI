---
name: merge-prs
description: Review and merge your open pull requests. Checks CI status, fixes failures, merges green PRs one at a time. Use at session start to clean up PRs from prior sessions, or invoke manually when needed. Usage /merge-prs
user-invocable: true
---

## Open PRs

!`gh pr list --repo SDSMT-Capstone-Spice-GUI-Team/Spice-GUI --json number,title,headRefName,mergeable,reviewDecision --jq "[.[] | {n: .number, t: .title, b: .headRefName, m: .mergeable, r: .reviewDecision}]"`

## PR CI Status

!`gh pr list --repo SDSMT-Capstone-Spice-GUI-Team/Spice-GUI --json number,statusCheckRollup --jq "[.[] | {n: .number, checks: [.statusCheckRollup[]? | {name: .name, status: .conclusion}]}]"`

## Merge Protocol

1. **One at a time** — merge one PR, wait for CI to propagate, then merge the next
2. **Check CI** for each PR: `gh pr checks <N>`
3. **If CI green** — review the diff briefly, then merge:
   ```bash
   gh pr merge <N> --squash --delete-branch
   ```
4. **If CI failing** — check the failure:
   - Formatting: `git checkout <branch> && make format && git add -A && git commit -m "fix formatting" && git push`
   - Lint: fix the issue, `make lint`, commit, push
   - Test failure: analyze — if straightforward fix it, otherwise comment on the PR
5. **If merge conflict** — checkout the branch, rebase on target, resolve conflicts:
   ```bash
   git checkout <branch>
   git fetch origin <target>
   git rebase origin/<target>
   # resolve conflicts
   make format && make test && make lint
   git push --force-with-lease
   ```
6. **After merge** — verify the target branch CI is still green before merging the next PR

## Key Rules

- NEVER merge directly to `main` — PRs target `develop` or epic branches
- `main_window.py` is the #1 merge conflict hotspot (~1700 lines)
- Only merge PRs from branches you created. Leave other agents' PRs alone.
- Use `./scripts/orchestrator/wait-for-ci.sh <N>` instead of manual `gh pr checks` polling
- If your PR touches `main_window.py`, merge promptly to reduce the conflict window
