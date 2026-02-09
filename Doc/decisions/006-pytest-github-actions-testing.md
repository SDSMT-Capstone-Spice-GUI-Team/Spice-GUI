# ADR 006: pytest and GitHub Actions for Testing Strategy

**Date:** 2024-10-28 (Implemented)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** 2f26688 (CI/CD pipeline), 428dcbe (test suite)

---

## Context

As the codebase grew from a prototype to a production application, we needed a comprehensive testing strategy to:
- Catch regressions when adding features
- Validate refactoring (especially the MVC migration)
- Ensure cross-platform compatibility (Windows, macOS, Linux)
- Maintain code quality as team members rotate
- Enable confident deployment

### Requirements

**Test Framework:**
- Support for unit and integration tests
- Fixture management for test data
- PyQt6 compatibility (GUI testing)
- Good error reporting and debugging
- Python 3.11+ support

**CI/CD System:**
- Automated testing on every PR and push
- Cross-platform testing (Windows, Linux, macOS)
- Matrix testing across Python versions
- Fast feedback loop (< 5 minutes)
- Integration with GitHub workflow

**Test Types Needed:**
- Unit tests for models and controllers (no Qt)
- Integration tests for simulation pipeline
- GUI tests for critical user workflows
- Import/load tests to catch missing dependencies

---

## Decision

**We will use pytest as our testing framework and GitHub Actions for CI/CD automation.**

### Test Framework: pytest

**Primary test runner:** pytest
**Test organization:** `app/tests/unit/` and `app/tests/integration/`
**Fixtures:** pytest fixtures for component/circuit setup
**Assertions:** Standard `assert` statements (pytest introspection)

### CI/CD: GitHub Actions

**Platform:** GitHub Actions (native GitHub integration)
**Test matrix:**
- OS: Ubuntu, Windows (macOS optional)
- Python: 3.11, 3.12, 3.13
**Headless GUI:** xvfb-run on Linux for PyQt6 tests
**Workflow file:** `.github/workflows/ci.yml`

### Additional Tooling

**Linting:** Ruff (separate ADR 007)
**Coverage:** Future consideration (not blocking)
**Test isolation:** Each test can run independently

---

## Consequences

### Positive

✅ **pytest Benefits:**
- Simple, Pythonic test syntax (`assert` vs `self.assertEqual`)
- Excellent fixture system for test data
- Detailed failure output with introspection
- Large plugin ecosystem (pytest-qt for GUI testing)
- Fast test discovery and execution
- Parameterized tests for testing multiple inputs
- Industry standard (most popular Python test framework)

✅ **GitHub Actions Benefits:**
- Free for open-source projects
- Native GitHub integration (PRs show test status)
- YAML-based configuration (easy to version control)
- Matrix builds (test multiple OS/Python combinations in parallel)
- Fast feedback (results in 2-5 minutes)
- No external service signup required

✅ **Cross-Platform Validation:**
- Catch platform-specific bugs early
- Validate PyQt6 works on all platforms
- Test file path handling (Windows vs Unix)
- Verify dependencies install correctly

✅ **Confidence in Refactoring:**
- 108+ unit tests enabled MVC refactoring
- Regression detection prevented bugs
- Documentation via test examples

### Negative

❌ **pytest Downsides:**
- Different from stdlib `unittest` (learning curve for some)
- Implicit test discovery can be "magical"
- Some teams prefer xUnit-style frameworks

❌ **GitHub Actions Limitations:**
- Requires internet connection to run
- Can't test locally without act or similar tool
- Limited to 2000 minutes/month on free tier (non-issue for us)
- macOS runners are slower (expensive CI minutes)

❌ **GUI Testing Challenges:**
- PyQt6 requires display server (xvfb on Linux CI)
- Headless testing doesn't catch visual bugs
- Some UI interactions hard to test programmatically

### Mitigation Strategies

**pytest Learning Curve:**
- Document common patterns in test files
- Use consistent fixture naming
- Add comments explaining complex fixtures

**GitHub Actions Local Testing:**
- Developers can run `pytest` locally before pushing
- Pre-commit hook option to run tests (optional)

**GUI Testing Limitations:**
- Focus unit tests on models/controllers (no Qt dependencies)
- Integration tests for critical user flows only
- Manual testing for visual/UX validation

**CI Minutes Budget:**
- Skip macOS in matrix (Windows + Linux sufficient)
- Can add macOS testing if needed later
- Optimize test suite to run faster

---

## Implementation Details

### Test Structure

```
app/
├── tests/
│   ├── unit/                    # Fast, isolated tests
│   │   ├── test_circuit_model.py
│   │   ├── test_circuit_controller.py
│   │   ├── test_file_controller.py
│   │   ├── test_simulation_controller.py
│   │   ├── test_netlist_generator.py
│   │   └── test_result_parser.py
│   └── integration/             # Multi-component tests
│       ├── test_simulation_pipeline.py
│       └── test_save_load.py
```

### pytest Configuration

**No pytest.ini needed** - Using defaults with command-line flags:
```bash
pytest tests/ -v --tb=short
```

**Flags:**
- `-v` - Verbose output (show each test)
- `--tb=short` - Shorter traceback format
- Working directory: `app/` (so imports work correctly)

### Example Test (pytest style)

```python
# tests/unit/test_circuit_model.py
import pytest
from models.circuit import CircuitModel
from models.component import Component

@pytest.fixture
def empty_circuit():
    """Fixture providing a fresh CircuitModel."""
    return CircuitModel()

@pytest.fixture
def resistor():
    """Fixture providing a test resistor component."""
    return Component(
        id='R1',
        comp_type='resistor',
        value='1k',
        pos={'x': 100, 'y': 200},
        rotation=0
    )

def test_add_component(empty_circuit, resistor):
    """Test adding a component to the circuit."""
    empty_circuit.add_component(resistor)

    assert len(empty_circuit.components) == 1
    assert empty_circuit.components[0].id == 'R1'
    assert empty_circuit.components[0].value == '1k'

def test_remove_component(empty_circuit, resistor):
    """Test removing a component from the circuit."""
    empty_circuit.add_component(resistor)
    empty_circuit.remove_component('R1')

    assert len(empty_circuit.components) == 0
```

### GitHub Actions Workflow

**File:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }}, ${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install system dependencies (Ubuntu)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y libegl1 xvfb

      - name: Install dependencies
        run: pip install -r app/requirements.txt pytest

      - name: Run tests (Linux)
        if: runner.os == 'Linux'
        working-directory: app
        run: xvfb-run python -m pytest tests/ -v --tb=short

      - name: Run tests (Windows)
        if: runner.os == 'Windows'
        working-directory: app
        run: python -m pytest tests/ -v --tb=short
```

**Key Features:**
- **Matrix strategy:** Tests 6 combinations (2 OS × 3 Python versions)
- **fail-fast: false:** All combinations run even if one fails
- **xvfb-run:** Provides virtual display for PyQt6 on Linux
- **Platform conditionals:** Different commands for Linux vs Windows

### Running Tests Locally

**All tests:**
```bash
cd app
python -m pytest tests/ -v
```

**Specific test file:**
```bash
python -m pytest tests/unit/test_circuit_model.py -v
```

**Specific test:**
```bash
python -m pytest tests/unit/test_circuit_model.py::test_add_component -v
```

**With coverage (optional):**
```bash
pip install pytest-cov
python -m pytest tests/ --cov=models --cov=controllers
```

---

## Alternatives Considered

### Alternative 1: unittest (Python Standard Library)

**Approach:** Use built-in `unittest` framework

**Pros:**
- No external dependency
- Part of Python standard library
- Familiar xUnit-style pattern
- Good IDE integration

**Rejected because:**
- More verbose (`self.assertEqual(a, b)` vs `assert a == b`)
- Fixture setup more complex (`setUp`/`tearDown` methods)
- Less readable test code
- pytest is now de facto standard for Python projects
- pytest can run unittest tests (easy migration path)

### Alternative 2: nose2

**Approach:** Use nose2 test framework

**Rejected because:**
- Less actively maintained than pytest
- Smaller community and plugin ecosystem
- No significant advantages over pytest
- pytest more popular in 2024+

### Alternative 3: Travis CI / CircleCI

**Approach:** Use external CI/CD service

**Rejected because:**
- Requires external account signup
- GitHub Actions already integrated
- Free tier sufficient for our needs
- One less service to manage
- GitHub Actions YAML similar to others (not locked in)

### Alternative 4: GitLab CI

**Approach:** Move repository to GitLab, use GitLab CI

**Rejected because:**
- Repository already on GitHub
- GitHub Actions works well
- Team familiar with GitHub
- Migration overhead not worth it

### Alternative 5: Manual Testing Only

**Approach:** No automated tests, manual QA before releases

**Rejected because:**
- Too slow for iterative development
- Human error likely with repetitive tests
- Regression bugs would slip through
- Refactoring becomes risky without test safety net
- Can't validate cross-platform without testing on each OS

---

## Test Coverage Strategy

### What We Test Thoroughly

**Unit Tests (Fast, Isolated):**
- ✅ CircuitModel operations (CRUD, node graph)
- ✅ Controllers (CircuitController, FileController, SimulationController)
- ✅ Netlist generation (all component types)
- ✅ Result parsing (all analysis types)
- ✅ File validation (JSON schema)
- ✅ Format utilities (SI unit parsing)

**Integration Tests (Multi-Component):**
- ✅ Full simulation pipeline (model → netlist → ngspice → results)
- ✅ Save/load round-trip
- ✅ Circuit serialization

### What We Don't Fully Test (Manual/Future)

**GUI Tests (Manual):**
- ❌ Visual appearance and layout
- ❌ Drag-and-drop interactions
- ❌ Waveform plot rendering
- ⚠️ Basic import tests only (can we load GUI modules?)

**Rationale:** GUI tests are slow, brittle, and hard to maintain. Focus on testable core logic (MVC architecture enables this).

**Future Consideration:** pytest-qt for critical GUI workflows if needed.

---

## Performance Metrics

### Test Execution Time (Current)

**Local (developer machine):**
- Unit tests only: ~1 second
- All tests: ~3 seconds (including integration tests calling ngspice)

**CI (GitHub Actions):**
- Full workflow (install deps + run tests): ~2-3 minutes
- Matrix testing (6 combinations): ~15 minutes total (parallel)

**Target:** Keep full test suite under 5 seconds locally, 5 minutes in CI.

---

## Maintenance

### Adding New Tests

**When to write tests:**
- ✅ All new features should have unit tests
- ✅ Bug fixes should have regression tests
- ✅ Refactoring should be validated by existing tests

**Test naming convention:**
```python
def test_<what_is_being_tested>_<scenario>_<expected_result>():
    # Example: test_add_component_duplicate_id_raises_error()
    pass
```

### Updating CI Workflow

**When to modify `.github/workflows/ci.yml`:**
- Adding new Python version support
- Changing OS matrix
- Adding new CI jobs (linting, coverage, etc.)
- Performance optimizations

**Review:** Check CI config during Python version updates annually.

---

## Related Decisions

- [ADR 002: MVC Architecture](002-mvc-architecture-zero-qt-dependencies.md) - Enables testability by isolating core logic
- [ADR 007: Ruff for Linting](007-ruff-linting-code-quality.md) - Complementary code quality tool
- [ADR 005: PyQt6 Framework](005-pyqt6-desktop-framework.md) - GUI testing challenges with PyQt6

---

## References

- pytest documentation: https://docs.pytest.org/
- GitHub Actions: https://docs.github.com/en/actions
- CI workflow: [.github/workflows/ci.yml](../../.github/workflows/ci.yml)
- Test suite: [app/tests/](../../app/tests/)
- Test count: 108+ unit tests as of implementation

---

## Review and Revision

This decision should be reviewed if:
- pytest becomes unmaintained (unlikely)
- GitHub Actions pricing changes unfavorably
- Team needs more sophisticated test reporting
- Coverage requirements become mandatory

**Status:** Working well, 108+ tests passing on all platforms
