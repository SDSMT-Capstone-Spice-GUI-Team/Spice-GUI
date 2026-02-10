# Command Reference - Automated Workflow Session 2026-02-09

## Table of Contents
1. [GitHub Projects API](#github-projects-api)
2. [Git Workflow](#git-workflow)
3. [Testing](#testing)
4. [Linting & Formatting](#linting--formatting)
5. [File Operations](#file-operations)
6. [Common Patterns](#common-patterns)

---

## GitHub Projects API

### Query Projects
```bash
# List all projects for an organization
gh project list --owner SDSMT-Capstone-Spice-GUI-Team

# List projects with specific fields
gh project list --owner SDSMT-Capstone-Spice-GUI-Team --format json
```

### List Project Items
```bash
# List all items in a project (with limit)
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 100

# Filter items by status using jq
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 100 | \
  jq -r '.items[] | select(.status == "Ready") | "\(.content.number)\t\(.content.title)"'

# Get specific item ID by issue number
gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 100 | \
  jq -r '.items[] | select(.content.number == 104) | .id'
```

### Query Field Information
```bash
# List all fields in a project
gh project field-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json

# Get specific field ID by name
gh project field-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json | \
  jq -r '.fields[] | select(.name == "Status") | .id'

# List all options for a select field
gh project field-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json | \
  jq -r '.fields[] | select(.name == "Status") | .options[] | .name'

# Get specific option ID
gh project field-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json | \
  jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "In progress") | .id'
```

### Update Project Items
```bash
# Update status field (single-select)
gh project item-edit \
  --project-id PVT_kwDODeVytM4BDeCn \
  --id PVTI_lADODeVytM4BDeCnzglIKBA \
  --field-id PVTSSF_lADODeVytM4BDeCnzg1YR9g \
  --single-select-option-id 5a223f5b

# Update number field (Hours)
gh project item-edit \
  --project-id PVT_kwDODeVytM4BDeCn \
  --id PVTI_lADODeVytM4BDeCnzglIKBA \
  --field-id PVTF_lADODeVytM4BDeCnzg9ICv8 \
  --number 3.0
```

### Project-Specific IDs (Spice-GUI)
```bash
# These IDs are specific to the Spice-GUI project and can be reused
PROJECT_ID="PVT_kwDODeVytM4BDeCn"
STATUS_FIELD_ID="PVTSSF_lADODeVytM4BDeCnzg1YR9g"
HOURS_FIELD_ID="PVTF_lADODeVytM4BDeCnzg9ICv8"
IN_PROGRESS_OPTION="5a223f5b"
IN_REVIEW_OPTION="68747673"

# Item IDs are unique per issue and must be queried each time
```

---

## Git Workflow

### Branch Management
```bash
# Check current branch
git branch

# List all branches (including remote)
git branch -a

# Create new feature branch
git checkout -b issue-99-undo-redo

# Switch to existing branch
git checkout main

# Create branch from specific commit/branch
git checkout -b issue-104-fft-analysis main
```

### Stashing
```bash
# Stash uncommitted changes
git stash

# Stash with message
git stash save "Work in progress on FFT"

# List stashes
git stash list

# Apply most recent stash
git stash pop

# Apply specific stash
git stash apply stash@{0}

# Show stash contents
git stash show -p
```

### Status and Inspection
```bash
# Check status
git status

# Short status
git status --short

# View changes summary
git diff --stat

# View specific file diff
git diff GUI/main_window.py

# View staged changes
git diff --cached

# View recent commits
git log --oneline -5

# View commit with changes
git show b515372
```

### Committing
```bash
# Stage specific files
git add controllers/commands.py controllers/undo_manager.py

# Stage all modified files
git add -u

# Stage all files (including new)
git add .

# Commit with message
git commit -m "Implement undo/redo system"

# Commit with multiline message using heredoc
git commit -m "$(cat <<'EOF'
Implement undo/redo system with command pattern

Implements comprehensive undo/redo functionality:
- Create Command base class
- Implement 10 concrete commands
- Add keyboard shortcuts

Closes #99

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"

# Bypass pre-commit hooks (for legacy branches)
PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "message"
```

### Pushing
```bash
# Push and set upstream
git push -u origin issue-99-undo-redo

# Force push (use with caution!)
git push --force origin issue-99-undo-redo

# Push all branches
git push --all
```

### File Operations
```bash
# Copy file from another branch
git show main:app/simulation/fft_analysis.py > simulation/fft_analysis.py

# Restore file from staging
git restore --staged ../CLAUDE.md

# Restore file from HEAD
git restore GUI/main_window.py

# Resolve merge conflict (choose theirs)
git checkout --theirs GUI/waveform_dialog.py
```

---

## Testing

### Running Tests
```bash
# Activate virtual environment (from project root)
source .venv/bin/activate

# Activate from app/ directory
source ../.venv/bin/activate

# Run specific test file
cd app && python -m pytest tests/unit/test_undo_redo.py -v

# Run specific test class
python -m pytest tests/unit/test_undo_redo.py::TestUndoManager -v

# Run specific test method
python -m pytest tests/unit/test_undo_redo.py::TestUndoManager::test_initial_state -v

# Run all tests
python -m pytest tests/ -v

# Run with short traceback
python -m pytest tests/ -v --tb=short

# Run with line-only traceback
python -m pytest tests/ -v --tb=line

# Show last N lines of output
python -m pytest tests/ -v 2>&1 | tail -50

# Run tests matching pattern
python -m pytest tests/ -v -k "undo"

# Run tests and show coverage
python -m pytest tests/ -v --cov=controllers --cov-report=term-missing
```

### Using Makefile
```bash
# Run all tests (from project root)
make test

# Run linting checks
make lint

# Auto-format code
make format

# Run all checks (lint + test)
make check

# Show help
make help
```

---

## Linting & Formatting

### Ruff (Linter)
```bash
# Check all files in current directory
ruff check .

# Check specific file
ruff check controllers/commands.py

# Auto-fix issues
ruff check --fix .

# Show fixes without applying
ruff check --diff .

# Check with specific rules
ruff check --select E,F,W .
```

### Black (Formatter)
```bash
# Check formatting
black --check --line-length=120 app/

# Format files
black --line-length=120 app/

# Show diff without modifying
black --diff --line-length=120 app/

# Format specific file
black --line-length=120 controllers/commands.py
```

### isort (Import Sorting)
```bash
# Check import sorting
isort --check-only --profile=black --line-length=120 app/

# Sort imports
isort --profile=black --line-length=120 app/

# Show diff without modifying
isort --diff --profile=black --line-length=120 app/

# Sort specific file
isort --profile=black controllers/commands.py
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Skip hooks for one commit
git commit --no-verify -m "message"

# Or use environment variable
PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "message"
```

---

## GitHub CLI (gh)

### Issues
```bash
# View issue
gh issue view 99

# View with specific fields
gh issue view 99 --json title,body,labels

# Create issue
gh issue create --title "Title" --body "Description"

# Close issue
gh issue close 99

# Close with comment
gh issue close 99 --comment "Resolved in PR #133"

# Comment on issue
gh issue comment 99 --body "⏱️ 3h - Implemented undo/redo system"

# List issues
gh issue list

# List with filters
gh issue list --state open --label bug

# Search issues
gh issue list --search "undo in:title"
```

### Pull Requests
```bash
# Create PR
gh pr create --title "Title" --body "Description"

# Create with heredoc for multiline body
gh pr create --title "Add undo/redo" --body "$(cat <<'EOF'
## Summary
- Implemented command pattern
- Added keyboard shortcuts

Closes #99
EOF
)"

# View PR
gh pr view 133

# List PRs
gh pr list

# Merge PR
gh pr merge 133

# Merge with options
gh pr merge 133 --squash --delete-branch

# Check PR status
gh pr status

# View PR diff
gh pr diff 133
```

### Repository
```bash
# Clone repository
gh repo clone SDSMT-Capstone-Spice-GUI-Team/Spice-GUI

# View repository
gh repo view

# Open repository in browser
gh repo view --web

# Fork repository
gh repo fork
```

---

## File Operations (Claude Tools)

### Reading Files
```bash
# Read entire file
Read: file_path="/path/to/file.py"

# Read with offset and limit
Read: file_path="/path/to/file.py", offset=100, limit=50

# Read PDF pages
Read: file_path="/path/to/doc.pdf", pages="1-5"
```

### Writing Files
```bash
# Create new file
Write: file_path="/path/to/new_file.py", content="..."

# Note: Write requires Read first for existing files
```

### Editing Files
```bash
# Edit existing file
Edit: file_path="/path/to/file.py",
      old_string="original text",
      new_string="new text"

# Replace all occurrences
Edit: file_path="/path/to/file.py",
      old_string="old",
      new_string="new",
      replace_all=true
```

### Searching
```bash
# Search for files
Glob: pattern="**/*.py"
Glob: pattern="tests/unit/test_*.py"

# Search file contents
Grep: pattern="def undo", path="controllers/"
Grep: pattern="class.*Command", output_mode="content", -n=true
Grep: pattern="import.*pytest", output_mode="files_with_matches"

# With context
Grep: pattern="execute", -B=2, -A=2, output_mode="content"
```

---

## Common Patterns

### Complete Issue Workflow
```bash
# 1. Move to In Progress
ITEM_ID=$(gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team \
  --format json --limit 100 | \
  jq -r '.items[] | select(.content.number == 99) | .id')

gh project item-edit \
  --project-id PVT_kwDODeVytM4BDeCn \
  --id $ITEM_ID \
  --field-id PVTSSF_lADODeVytM4BDeCnzg1YR9g \
  --single-select-option-id 5a223f5b

# 2. Create feature branch
git checkout main
git pull origin main
git checkout -b issue-99-undo-redo

# 3. Implement solution
# (create files, write code, write tests)

# 4. Run tests
source ../.venv/bin/activate
cd app && python -m pytest tests/unit/test_undo_redo.py -v

# 5. Run linting
ruff check .

# 6. Commit
git add controllers/commands.py controllers/undo_manager.py \
        controllers/circuit_controller.py GUI/main_window.py \
        tests/unit/test_undo_redo.py
git commit -m "$(cat <<'EOF'
Implement undo/redo system

Closes #99

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"

# 7. Push
git push -u origin issue-99-undo-redo

# 8. Create PR
gh pr create --title "Implement undo/redo system" --body "$(cat <<'EOF'
## Summary
...
EOF
)"

# 9. Close issue
gh issue close 99 --comment "Resolved in PR #133"

# 10. Move to In Review
gh project item-edit \
  --project-id PVT_kwDODeVytM4BDeCn \
  --id $ITEM_ID \
  --field-id PVTSSF_lADODeVytM4BDeCnzg1YR9g \
  --single-select-option-id 68747673

# 11. Log hours
gh issue comment 99 --body "⏱️ 3h - Implemented undo/redo system..."

gh project item-edit \
  --project-id PVT_kwDODeVytM4BDeCn \
  --id $ITEM_ID \
  --field-id PVTF_lADODeVytM4BDeCnzg9ICv8 \
  --number 3.0
```

### Testing Workflow
```bash
# Full test cycle
source ../.venv/bin/activate
cd app

# Run specific tests during development
python -m pytest tests/unit/test_undo_redo.py -v

# Run all tests before commit
python -m pytest tests/ -v --tb=short

# Check coverage
python -m pytest tests/unit/test_undo_redo.py --cov=controllers --cov-report=term-missing

# Lint code
ruff check .
black --check --line-length=120 .
isort --check-only --profile=black .

# Or use Makefile from project root
cd ..
make test
make lint
```

### Branch Management Pattern
```bash
# Always verify branch before creating files
git branch  # Should show feature branch with *

# If on wrong branch, stash and switch
git stash
git checkout issue-99-undo-redo
git stash pop

# Or copy files from another branch
git show main:app/simulation/fft_analysis.py > simulation/fft_analysis.py
```

### Handling Merge Conflicts
```bash
# When stash pop causes conflict
git status  # See conflicting files

# Option 1: Take theirs (stashed version)
git checkout --theirs GUI/waveform_dialog.py
git add GUI/waveform_dialog.py

# Option 2: Take ours (current version)
git checkout --ours GUI/waveform_dialog.py
git add GUI/waveform_dialog.py

# Option 3: Manually resolve
# Edit file, remove conflict markers
git add GUI/waveform_dialog.py
```

### Pre-commit Hook Workflow
```bash
# First commit attempt (hooks may fail and auto-fix)
git commit -m "message"

# If hooks auto-fix files, stage and re-commit
git add -u
git commit -m "message"

# For legacy branches without .pre-commit-config.yaml
PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "message"
```

---

## Environment Setup

### Virtual Environment
```bash
# Create venv
python3 -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Deactivate
deactivate

# Install dependencies
pip install -r app/requirements.txt
pip install -r app/requirements-dev.txt

# Or use Makefile
make install-dev
```

### Pre-commit Setup
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Or use Makefile
make install-hooks

# Test hooks
pre-commit run --all-files
```

### GitHub CLI Setup
```bash
# Login
gh auth login

# Check authentication
gh auth status

# Set default repository
gh repo set-default SDSMT-Capstone-Spice-GUI-Team/Spice-GUI
```

---

## Debugging Commands

### Find Why Tests Fail
```bash
# Run with verbose output
python -m pytest tests/unit/test_undo_redo.py -v -s

# Run with full traceback
python -m pytest tests/unit/test_undo_redo.py -v --tb=long

# Run single failing test
python -m pytest tests/unit/test_undo_redo.py::TestUndoManager::test_clear -v

# Drop into debugger on failure
python -m pytest tests/unit/test_undo_redo.py --pdb
```

### Find Files
```bash
# Find by name
find . -name "test_undo_*.py"

# Find recently modified
find app/ -name "*.py" -mtime -1

# Or use Glob tool (Claude)
Glob: pattern="**/test_undo*.py"
```

### Search Code
```bash
# Search with context
grep -r "class Command" app/ -A 5 -B 2

# Or use Grep tool (Claude)
Grep: pattern="class Command", output_mode="content", -A=5, -B=2
```

---

## Quick Reference Card

### Most Used Commands
```bash
# Git
git status
git checkout -b issue-X-description
git add file1 file2
git commit -m "message"
git push -u origin branch-name

# Testing
source ../.venv/bin/activate
cd app && python -m pytest tests/unit/test_file.py -v

# Linting
ruff check .

# GitHub
gh issue close 99 --comment "Resolved in PR #133"
gh pr create --title "Title" --body "Description"

# Projects
gh project item-edit --project-id PVT_kwDODeVytM4BDeCn \
  --id ITEM_ID --field-id FIELD_ID --single-select-option-id OPTION_ID
```

### JQ Patterns for Project API
```bash
# Get item ID
jq -r '.items[] | select(.content.number == 99) | .id'

# Get field ID
jq -r '.fields[] | select(.name == "Status") | .id'

# Get option ID
jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "In progress") | .id'

# Filter by status
jq -r '.items[] | select(.status == "Ready") | "\(.content.number)\t\(.content.title)"'
```

---

**Generated**: 2026-02-09
**Session**: Automated workflow with Issues #104 and #99
**Claude Model**: claude-sonnet-4-5-20250929
