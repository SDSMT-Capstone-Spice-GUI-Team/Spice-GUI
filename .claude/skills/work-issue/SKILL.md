---
name: work-issue
description: Implement a GitHub issue end-to-end. Takes an issue number, reads the issue, creates a branch, implements, tests, and creates a PR. Usage /work-issue <number>
user-invocable: true
---

## Issue Details

!`gh issue view $ARGUMENTS --repo SDSMT-Capstone-Spice-GUI-Team/Spice-GUI --json title,body,labels,state,comments`

## Implementation Checklist

Follow these steps in order:

1. **Verify issue is open and Ready** — if closed or already In Progress, stop and report
2. **Move to In Progress** on the board (use `/board-state` for item ID if needed)
3. **Resolve base branch**:
   - Check labels for `epic:<name>` — if found, base = `epic/<name>` (create from `develop` if it doesn't exist)
   - If no epic label, base = `develop`
4. **Create branch**: `git checkout <BASE> && git pull origin <BASE> && git checkout -b issue-$ARGUMENTS-<short-description>`
5. **Read epic context** if applicable: `gh issue view <epic-number> --json body`
6. **Plan** — assess complexity, identify files to change
7. **Implement** the change
8. **Write tests** — follow Test Layer Priority (model > netlist > qtbot > structural > human testing item)
9. **Format, test, lint**:
   ```bash
   make format && make test && make lint
   ```
10. **File human testing items** if UI-visible behavior not covered by automated tests — add checkbox to appropriate issue (#269-#279)
11. **Commit** with co-author tag:
    ```
    Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
    ```
12. **Rebase** on latest base branch: `git fetch origin <BASE> && git rebase origin/<BASE>`
13. **Re-test** after rebase: `make test && make lint`
14. **Push**: `git push -u origin issue-$ARGUMENTS-<description>`
15. **Create PR** targeting the base branch (epic or `develop`, NEVER `main`)
16. **Wait for CI**: `./scripts/orchestrator/wait-for-ci.sh <PR-number> 600`
17. **Fix CI failures** if any:
    - Formatting: `make format`, commit "fix formatting", push
    - Lint: fix issue, `make lint`, commit, push
    - Test failure: analyze — fix if straightforward, otherwise move issue to Blocked
    - Re-wait for CI after fix push
18. **Resolve merge conflicts** if any: `git fetch origin <BASE> && git rebase origin/<BASE>`, resolve, `make format && make test && make lint`, `git push --force-with-lease`
19. **Merge PR**: `gh pr merge <PR-number> --squash --delete-branch`
20. **Verify target branch CI** is still green after merge
21. **Close issue**: `gh issue close $ARGUMENTS`
22. **Move to Done** on the board
23. **Log hours**: comment `⏱️ Xh - description` on the issue
24. **Post feedback** on the issue: clarity (X/5), confidence, assumptions, review focus areas
