# Claude Code Autonomous Permissions Guide

This document explains the recommended permissions for autonomous operation, with safety scores and justifications.

## Safety Score Legend
- **🟢 Safe (5/5)**: Read-only, no side effects, completely reversible
- **🟡 Low Risk (4/5)**: Local changes only, easily reversible
- **🟠 Moderate Risk (3/5)**: Local changes with some effort to reverse
- **🔴 High Risk (1-2/5)**: Affects remote state or hard to reverse (EXCLUDED from this list)

---

## Git Commands

### Read-Only Operations 🟢 Safe (5/5)
- `git status` - View working tree status
- `git log` - View commit history
- `git diff` - View changes between commits/files
- `git show` - Display commit details
- `git branch` - List branches (read-only without flags)

**Justification**: Essential for understanding repository state. No side effects.

### Local Staging & Commits 🟡 Low Risk (4/5)
- `git add` - Stage files for commit
- `git commit` - Create local commits
- `git stash` - Temporarily save uncommitted changes

**Justification**: Needed for creating commits. All operations are local and reversible (commits can be reset, stashes can be popped/dropped).

### Branch Operations 🟡 Low Risk (4/5)
- `git checkout` - Switch branches or restore files
- `git restore` - Restore working tree files

**Justification**: Required for branch switching and file restoration. Changes to uncommitted work can be recovered via stash.

### Remote Read Operations 🟢 Safe (5/5)
- `git fetch` - Download objects from remote (doesn't modify working tree)

**Justification**: Updates remote-tracking branches without affecting working tree.

### Integration Operations 🟠 Moderate Risk (3/5)
- `git pull` - Fetch and merge remote changes
- `git merge` - Merge branches
- `git rebase` - Reapply commits

**Justification**: Needed for keeping branches up-to-date. Can create merge conflicts but doesn't affect remote. Changes are local and can be aborted.

**NOT INCLUDED (High Risk)**:
- ❌ `git push` - Affects remote repository (requires explicit user confirmation)
- ❌ `git reset --hard` - Destroys uncommitted work
- ❌ `git clean -f` - Deletes untracked files permanently
- ❌ `git push --force` - Can overwrite remote history

---

## GitHub CLI Commands

### Repository & PR Viewing 🟢 Safe (5/5)
- `gh repo view` - View repository details
- `gh pr view` - View pull request details
- `gh pr list` - List pull requests
- `gh pr checks` - View PR check status
- `gh pr diff` - View PR diff

**Justification**: Read-only operations for gathering PR/repository information.

### Issue Viewing 🟢 Safe (5/5)
- `gh issue view` - View issue details
- `gh issue list` - List issues

**Justification**: Read-only operations for issue tracking.

### API & Workflow Viewing 🟢 Safe (5/5)
- `gh api` - Make authenticated GitHub API requests
- `gh run view` - View workflow run details
- `gh run list` - List workflow runs

**Justification**: Enables reading GitHub data via API. Read operations only (write operations would require confirmation).

**NOT INCLUDED (High Risk)**:
- ❌ `gh pr create` - Creates public PR (requires confirmation)
- ❌ `gh pr comment` - Public comment (requires confirmation)
- ❌ `gh issue create` - Creates public issue (requires confirmation)

---

## Build & Test Commands

### Node.js/npm 🟡 Low Risk (4/5)
- `npm install`, `npm ci` - Install dependencies
- `npm run`, `npm test`, `npm run build`, `npm run dev`, `npm run start` - Run scripts

**Justification**: Essential for running tests, builds, and development servers. Local only, no remote effects. `npm ci` provides clean installs.

### Yarn 🟡 Low Risk (4/5)
- `yarn install`, `yarn test`, `yarn build`, `yarn run` - Same as npm

**Justification**: Alternative package manager, same safety profile as npm.

### pnpm 🟡 Low Risk (4/5)
- `pnpm install`, `pnpm test`, `pnpm run` - Same as npm/yarn

**Justification**: Alternative package manager, same safety profile.

### Python 🟡 Low Risk (4/5)
- `pip install` - Install Python packages
- `python -m pytest`, `python -m unittest` - Run tests
- `python setup.py`, `python -m build` - Build packages

**Justification**: Required for Python development workflows. Local operations.

### Make 🟡 Low Risk (4/5)
- `make`, `make test`, `make build`, `make clean` - Run Makefile targets

**Justification**: Standard build system. Operations defined in Makefile are project-specific.

### Other Languages 🟡 Low Risk (4/5)
- `cargo test/build/run` - Rust toolchain
- `go test/build/run` - Go toolchain
- `mvn test/build` - Maven (Java)
- `gradle test/build` - Gradle (Java)

**Justification**: Language-specific build and test commands. All local operations.

---

## Linting & Formatting

### Code Quality Tools 🟢 Safe (5/5)
- `eslint` - JavaScript linter (read-only without --fix)
- `prettier` - Code formatter
- `black`, `ruff` - Python formatters
- `flake8`, `pylint` - Python linters

**Justification**: Code quality checks. Formatters modify files but changes are visible in git diff and easily reversible.

---

## File Search & Inspection

### Search Tools 🟢 Safe (5/5)
- `grep`, `rg` (ripgrep) - Search file contents
- `find` - Search for files
- `ls`, `tree` - List directory contents

**Justification**: Read-only operations. (Note: Should prefer Grep/Glob tools when possible, but bash fallback is safe)

### File Reading 🟢 Safe (5/5)
- `cat`, `head`, `tail` - Display file contents
- `wc` - Count lines/words/characters

**Justification**: Read-only operations. (Note: Should prefer Read tool, but bash fallback is safe)

---

## File Operations

### Safe File Operations 🟡 Low Risk (4/5)
- `mkdir` - Create directories
- `cp`, `mv` - Copy/move files
- `chmod` - Change file permissions

**Justification**: Basic file operations needed for project work. All changes are tracked by git. `cp` is safer than `mv` (preserves original).

**NOT INCLUDED (High Risk)**:
- ❌ `rm -rf` - Permanent deletion (requires confirmation)
- ❌ `rm` with wildcards - Risk of accidental deletion

---

## Docker Commands

### Container Operations 🟡 Low Risk (4/5)
- `docker build` - Build images
- `docker run` - Run containers
- `docker ps` - List containers
- `docker logs` - View container logs
- `docker exec` - Execute commands in containers

**Justification**: Essential for containerized development. Operations are local and isolated.

### Docker Compose 🟡 Low Risk (4/5)
- `docker-compose up/down/build` - Manage multi-container apps

**Justification**: Required for docker-based development environments. Local operations.

---

## System Information

### Process & System Info 🟢 Safe (5/5)
- `ps`, `top`, `htop` - View running processes
- `df`, `du` - Disk usage
- `which`, `whereis` - Locate commands

**Justification**: Read-only system information gathering.

---

## Summary

**Total Permissions Recommended**: ~85 commands across 10 categories

**Safety Breakdown**:
- 🟢 Safe (5/5): ~35 commands (read-only operations)
- 🟡 Low Risk (4/5): ~45 commands (local, reversible changes)
- 🟠 Moderate Risk (3/5): ~5 commands (git merge/rebase/pull)
- 🔴 High Risk: 0 commands (excluded - require user confirmation)

**What's NOT Included (Requires Manual Approval)**:
- Remote operations: `git push`, `gh pr create`, `gh pr comment`
- Destructive operations: `git reset --hard`, `rm -rf`, `git clean -f`
- Force operations: `git push --force`, `--no-verify` flags
- Sudo/privileged operations
- Operations that send messages or affect shared state

This permission set allows autonomous work on code development, testing, and local git operations while ensuring all risky actions still require user approval.
