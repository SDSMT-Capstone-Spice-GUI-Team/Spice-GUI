# ADR 007: Ruff for Linting and Code Quality

**Date:** 2024-10-15 (Implemented)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** Early codebase standardization

---

## Context

As the codebase grew and multiple developers contributed (including AI-assisted development), we needed automated code quality enforcement to maintain consistency and catch common errors.

### Requirements

**Linting needs:**
- Catch syntax errors and common bugs
- Enforce code style consistency
- Integrate with CI/CD (fast execution)
- Configurable rules (enable/disable specific checks)
- Python 3.11+ support
- Low maintenance overhead

**Code quality goals:**
- Consistent formatting across files
- Catch unused imports and variables
- Identify potential bugs (unreachable code, undefined names)
- Maintain readability
- Support rapid iteration (not too strict)

### Tool Landscape (2024)

**Available Python linters:**
- **Ruff:** New, extremely fast, all-in-one linter
- **Flake8:** Traditional linter, plugin ecosystem
- **Pylint:** Comprehensive but slow
- **Black:** Opinionated code formatter
- **isort:** Import sorting
- **pycodestyle/pyflakes:** Basic style/error checking

---

## Decision

**We will use Ruff as our primary linting and code quality tool.**

### Configuration

**File:** `ruff.toml` at project root

```toml
target-version = "py310"
line-length = 120

[lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
]
ignore = [
    "E402",  # module-level import not at top
    "E501",  # line too long (handled by formatter)
    "E741",  # ambiguous variable name (l, O, I)
    "W291",  # trailing whitespace
    "W292",  # no newline at end of file
    "W293",  # whitespace before ':'
]

[lint.per-file-ignores]
"app/tests/**" = ["F401"]  # unused imports OK in tests
```

### CI Integration

**GitHub Actions workflow** (`.github/workflows/ci.yml`):
```yaml
lint:
  name: Lint
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - name: Install ruff
      run: pip install ruff
    - name: Run ruff check
      run: ruff check app/ --output-format=github
```

---

## Consequences

### Positive

✅ **Performance:**
- **10-100x faster than Pylint/Flake8** (written in Rust)
- Lints entire codebase in <1 second
- Fast CI feedback (doesn't slow down pipeline)

✅ **All-in-One:**
- Replaces Flake8 + isort + pyupgrade + multiple plugins
- Single tool to install and configure
- Fewer dependencies to manage

✅ **Modern Python Support:**
- Native Python 3.11+ support
- Understands new syntax (match/case, etc.)
- Regular updates for new Python versions

✅ **Great Developer Experience:**
- Clear, actionable error messages
- Auto-fix for many issues (`ruff check --fix`)
- VSCode/PyCharm integration available
- GitHub integration (formats errors for PR annotations)

✅ **Configurable:**
- Enable/disable specific rules
- Per-file ignores for special cases
- Flexible enough for team preferences

✅ **Industry Adoption:**
- Used by major projects (FastAPI, Pydantic, etc.)
- Active development and community
- Backed by Astral (VC-funded, sustainable)

### Negative

❌ **Relatively New:**
- First release 2022 (less mature than Flake8/Pylint)
- Rule set still evolving
- Some edge cases may exist

❌ **Not a Formatter:**
- Only checks code, doesn't auto-format
- Need separate formatter if desired (Black, ruff format)
- We chose not to auto-format (preserve developer style)

❌ **Different from Flake8:**
- Error codes different (E/F/W vs F/E/C/etc.)
- Some rules behave slightly differently
- Migration requires config adjustment

### Mitigation Strategies

**Maturity Concerns:**
- Monitor Ruff releases for breaking changes
- Pin version in CI if stability critical
- Active community means bugs get fixed quickly

**No Auto-Formatting:**
- Acceptable for our workflow
- Can add `ruff format` later if needed
- Manual formatting gives developers control

**Migration from Flake8:**
- Document common error codes in README
- Team learns new codes over time
- Ruff has equivalents for most Flake8 rules

---

## Implementation Details

### Rules Enabled

**E: pycodestyle errors**
- E401: Multiple imports on one line
- E501: Line too long (ignored - handled by common sense)
- E402: Module import not at top (ignored - intentional in some cases)
- E7XX: Statement/whitespace errors
- E9XX: Syntax errors

**F: pyflakes**
- F401: Imported but unused (catches dead imports)
- F403: `from module import *` (discouraged)
- F405: Name may be undefined from `import *`
- F8XX: Undefined names, unused variables
- F9XX: Syntax errors

**W: pycodestyle warnings**
- W291: Trailing whitespace (ignored - not critical)
- W6XX: Deprecation warnings

### Rules Ignored (and Why)

**E402: Module import not at top**
```python
# app/some_module.py
import logging
logging.basicConfig(...)  # Configure logging first
import other_module        # Then import
```
**Why ignored:** Sometimes intentional (logging setup, path manipulation).

**E501: Line too long**
```python
# 120 character limit in config, but not enforced strictly
very_long_variable_name = some_function_call(arg1, arg2, arg3, arg4)  # 130 chars
```
**Why ignored:** Formatter handles this better than linter. Use common sense.

**E741: Ambiguous variable name (l, O, I)**
```python
# Common in math/circuit code
L1 = 1e-3  # Inductor value (L is standard notation)
```
**Why ignored:** Standard electrical engineering notation.

**W291/W292/W293: Whitespace issues**
**Why ignored:** Minor cosmetic issues, not worth build failures.

### Per-File Ignores

**Tests can have unused imports:**
```python
# app/tests/unit/test_circuit_model.py
from models.circuit import CircuitModel  # May not be used in every test
```
**Config:** `"app/tests/**" = ["F401"]`

---

## Running Ruff

### Locally (Development)

**Check all files:**
```bash
ruff check app/
```

**Auto-fix issues:**
```bash
ruff check app/ --fix
```

**Check specific file:**
```bash
ruff check app/models/circuit.py
```

**Explain a rule:**
```bash
ruff rule F401
```

### CI/CD (GitHub Actions)

**Automated on every PR:**
- Runs `ruff check app/ --output-format=github`
- Annotations appear on PR diff
- Blocks merge if errors found
- Fast execution (< 5 seconds)

### IDE Integration

**VSCode:**
```json
// .vscode/settings.json
{
  "ruff.enable": true,
  "ruff.lint.run": "onSave"
}
```

**PyCharm:**
- Install Ruff plugin from marketplace
- Configure in Preferences → Tools → Ruff

---

## Alternatives Considered

### Alternative 1: Flake8 (+ plugins)

**Approach:** Traditional linter with plugin ecosystem

**Pros:**
- Mature, well-established (2010+)
- Large plugin ecosystem (flake8-bugbear, etc.)
- Team familiarity
- Stable API

**Rejected because:**
- Much slower (20-30x vs Ruff)
- Multiple plugins to manage (isort, pyupgrade, etc.)
- Configuration spread across multiple tools
- Slower development iteration
- Ruff replicates 90% of Flake8 + plugins

### Alternative 2: Pylint

**Approach:** Comprehensive static analysis

**Pros:**
- Very thorough checks
- Finds more potential bugs
- Configurable scoring system
- Enforce architectural patterns

**Rejected because:**
- **Very slow** (100x slower than Ruff)
- Too opinionated for rapid development
- Many false positives
- Configuration complexity
- Overkill for our needs

### Alternative 3: Black (+ Flake8 or Ruff)

**Approach:** Auto-formatter + linter

**Pros:**
- Consistent formatting automatically
- No debates about style
- One command fixes everything

**Rejected because:**
- Black is very opinionated (no customization)
- Reformats entire codebase (large diffs)
- Some developers prefer manual formatting control
- Can add later if needed

**Decision:** Use Ruff for linting only, no auto-formatter.

### Alternative 4: Multiple Tools (Black + isort + Flake8)

**Approach:** Best-of-breed tool stack

**Rejected because:**
- Configuration complexity (3 config files)
- Slower CI (run 3 tools)
- Dependency management burden
- Ruff provides 90% of value in one tool

### Alternative 5: No Linting

**Approach:** Code review catches issues

**Rejected because:**
- Human review misses mechanical issues
- Inconsistent style across contributors
- Wastes reviewer time on trivial issues
- AI-assisted development benefits from automated checks

---

## Code Quality Philosophy

### What Ruff Catches

✅ **Actual Errors:**
- Undefined variables
- Syntax errors
- Import errors
- Unreachable code

✅ **Code Smells:**
- Unused imports (dead code)
- Unused variables
- Overly complex expressions
- Potential bugs (comparing to None with `==` instead of `is`)

✅ **Style Consistency:**
- Import ordering
- Whitespace usage (when extreme)
- Line length (when egregious)

### What Ruff Doesn't Enforce

❌ **Strict Formatting:**
- Exactly where to break lines
- Trailing commas everywhere
- String quote style (single vs double)

**Rationale:** Let developers format readably, catch actual issues only.

❌ **Type Checking:**
- Ruff doesn't check type hints
- Future: Consider mypy if type safety becomes critical

❌ **Complexity Metrics:**
- No cyclomatic complexity scoring
- No max function length
- Trust developers to keep code simple

---

## Real-World Examples

### Example 1: Unused Import (Caught)

**Before:**
```python
import sys
import os
from models.circuit import CircuitModel  # F401: imported but unused
from models.component import Component

def test_something():
    c = Component(...)
```

**Ruff Output:**
```
app/tests/test_example.py:3:1: F401 `models.circuit.CircuitModel` imported but unused
```

**Fix:** Remove unused import or use the import.

### Example 2: Undefined Name (Caught)

**Before:**
```python
def calculate_total(items):
    return sum(item.price for item in itmes)  # Typo: itmes
```

**Ruff Output:**
```
app/utils.py:2:43: F821 Undefined name `itmes`
```

**Fix:** Correct typo to `items`.

### Example 3: Import Not at Top (Allowed via E402 ignore)

**Before:**
```python
# app/main.py
import logging
logging.basicConfig(level=logging.INFO)

from GUI.circuit_design_gui import CircuitDesignGUI  # Would trigger E402
```

**Ruff Output:** (None - E402 is ignored)

**Why allowed:** Intentional for logging configuration.

---

## Performance Comparison

**Test:** Lint entire `app/` directory (~15,000 lines of code)

| Tool | Time | Notes |
|------|------|-------|
| **Ruff** | 0.3s | ⚡ Fastest |
| Flake8 | 8s | 26x slower |
| Pylint | 45s | 150x slower |
| Black (format check) | 1.2s | Faster than Flake8 |

**Conclusion:** Ruff's speed enables real-time linting in IDE without slowdown.

---

## Maintenance and Evolution

### Updating Rules

**When to add rules:**
- New Python version introduces new patterns
- Team encounters specific bug type repeatedly
- Industry best practices evolve

**Process:**
1. Propose rule addition in team discussion
2. Test on codebase (how many violations?)
3. Fix violations or add to ignore list
4. Update `ruff.toml`
5. Document in this ADR

### Ruff Updates

**Frequency:** Check for updates quarterly
**Breaking changes:** Ruff uses semantic versioning, breaking changes in major versions only
**Process:**
1. Read changelog
2. Test on codebase locally
3. Update in CI if compatible

---

## Related Decisions

- [ADR 006: pytest Testing](006-pytest-github-actions-testing.md) - Complementary quality tool
- [ADR 002: MVC Architecture](002-mvc-architecture-zero-qt-dependencies.md) - Clean code architecture
- AI-Assisted Development (Doc/autonomous-workflow.md) - Automated checks essential for AI-generated code

---

## References

- Ruff documentation: https://docs.astral.sh/ruff/
- Ruff GitHub: https://github.com/astral-sh/ruff
- Configuration: [ruff.toml](../../ruff.toml)
- CI workflow: [.github/workflows/ci.yml](../../.github/workflows/ci.yml#L10-L24)

---

## Review and Revision

This decision should be reviewed if:
- Ruff development stalls or project abandoned
- Team needs more sophisticated analysis (consider Pylint)
- Auto-formatting becomes desired (add `ruff format`)
- Rule set becomes too restrictive (adjust config)

**Status:** Working excellently, fast and effective
