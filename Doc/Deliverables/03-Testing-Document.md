# Testing Document — SDM Spice

**Last Updated:** 2026-05-06
**Audience:** Developers, QA testers

---

## 1. Testing Philosophy

SDM Spice follows a **tiered testing** model ([ADR 002](../adr/002-tiered-testing.md)) that separates fast automated checks from human judgment calls.

| Tier | What | Tool | Gate |
|------|------|------|------|
| 1 | Unit tests (model + controller logic) | pytest | CI — must pass |
| 2 | Netlist snapshot tests (SPICE output correctness) | pytest | CI — must pass |
| 3 | Widget tests (individual dialogs) | pytest-qt / qtbot | CI — must pass |
| 4 | Structural assertions (terminal positions, bounding boxes) | pytest | CI — must pass |
| 5 | Human testing (visual, drag feel, print output) | Human testers | Release gate — human sign-off |

The no-Qt-in-controllers rule (ADR 001) is what makes tiers 1–4 fast and headless. The entire business logic layer can be exercised without a running display server.

---

## 2. Test Suite Structure

```
app/tests/
├── conftest.py              ← Shared pytest fixtures
├── unit/                    ← 186 test files
│   ├── test_circuit_model.py
│   ├── test_circuit_controller.py
│   ├── test_component_*.py
│   ├── test_wire_*.py
│   ├── test_*_dialog.py
│   ├── test_*_exporter.py
│   ├── test_grading_*.py
│   └── controllers/         ← Controller-specific coverage tests
└── integration/             ← 3 integration test files
    ├── test_ngspice_smoke.py          ← Is ngspice installed and responsive?
    ├── test_ngspice_workflows.py      ← Full simulation flows
    └── test_phase4_mvc_integration.py ← MVC integration scenarios
```

---

## 3. Running Tests

```bash
# Full suite (from repo root)
make test

# Or directly
cd app && pytest tests/ -v

# Single file
cd app && pytest tests/unit/test_circuit_model.py -v

# Integration only (requires ngspice on PATH)
cd app && pytest tests/integration/ -v

# With coverage report
cd app && pytest tests/ --cov=. --cov-report=term-missing

# Lint + tests together (the gate before pushing)
make check
```

---

## 4. Coverage

| Layer | Coverage |
|-------|---------|
| Models | ~100% |
| Controllers | 99%+ |
| Simulation pipeline | High |
| Grading | High |
| GUI / Dialogs | Partial (isolated dialog tests; MainWindow is not tested with qtbot) |

`make check` runs ruff + bandit (security) + pytest. All three must pass before a PR can be merged.

---

## 5. Fixtures (`conftest.py`)

Key shared fixtures include:

- **Mock controllers** — pre-wired `CircuitController` instances with an empty model
- **Sample circuit models** — pre-populated `CircuitModel` objects for common topologies (voltage divider, RC circuit)
- **Test component factories** — helpers that return `ComponentData` without needing canvas coordinates
- **Temp directory fixtures** — for testing file I/O without polluting the filesystem

All fixtures work without a running display server — no `DISPLAY` or `QApplication` required for unit tests.

---

## 6. Writing New Tests

### Unit Test Pattern

```python
# tests/unit/test_circuit_controller.py
def test_add_component_notifies_observers(circuit_controller):
    events = []
    circuit_controller.add_observer(lambda name, data: events.append(name))

    circuit_controller.add_component("Resistor", position=(100, 100))

    assert "component_added" in events
    assert len(circuit_controller.model.components) == 1
```

### Netlist Snapshot Pattern

```python
def test_voltage_divider_netlist(sample_divider_model):
    netlist = NetlistGenerator(sample_divider_model).generate()
    assert "R1" in netlist
    assert ".op" in netlist
```

### Widget Test Pattern (pytest-qt)

```python
def test_preferences_dialog_opens(qtbot):
    dialog = PreferencesDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.isVisible()
    qtbot.mouseClick(dialog.cancel_button, Qt.MouseButton.LeftButton)
    assert not dialog.isVisible()
```

Note: `MainWindow` is **not** tested with qtbot — the integration is too complex and fragile. Instead, test its mixins through the controller APIs.

---

## 7. CI Pipeline

GitHub Actions runs the test suite on every push and pull request. See `.github/workflows/ci.yml`.

### Matrix

| OS | Python |
|----|--------|
| Ubuntu | 3.11, 3.12, 3.13 |
| Windows | 3.11, 3.12, 3.13 |

### Jobs

1. **lint** — ruff check + bandit security scan
2. **test** — pytest (unit + integration) on each matrix entry
3. **import-check** — verifies all modules import cleanly
4. **ngspice-integration** — runs integration tests against the system ngspice

All jobs must pass for a PR to be mergeable.

### Known CI Quirk

Do **not** use `ruff format` / `ruff-format` — it conflicts with `black` and caused infinite reformat loops in earlier CI configs. Use `ruff check` + `isort` + `black` only (see `ruff.toml` and `.pre-commit-config.yaml`).

---

## 8. Human Testing

Automated tests cannot verify:
- Visual aesthetics (component symbol look, wire alignment)
- Drag feel and interactive responsiveness
- Print and PDF output quality
- Installer behavior on a fresh Windows machine

These are covered by a structured **human testing process** documented in `Doc/human-testing-guide.md`.

### Human Testing Board

Testing issues are tracked at: https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3

| Issue | Section | Needs ngspice? |
|-------|---------|----------------|
| #269 | Smoke Test | 1 item |
| #270 | Components | 4 items |
| #271 | Selection & Clipboard | No |
| #272 | Wires | No |
| #273 | Undo/Redo | No |
| #279 | Annotations | No |
| #274 | File Operations | No |
| #275 | Simulation | Yes (all) |
| #276 | Plot Features | Yes (all) |
| #277 | User Interface | No |

### Features Without Testing Issues (Action Required)

The following implemented features do not yet have human testing issues. Create them before the next release:

| Feature | Action |
|---------|--------|
| Grading / Instructor tools (rubrics, batch grading) | New issue — "Grading System" |
| Parameter Sweep dialog and overlaid plot | New issue — "Parameter Sweep" |
| Monte Carlo analysis dialog and statistical output | New issue — "Monte Carlo Analysis" |
| CircuiTikZ export + import round-trip | Extend #275 or new issue |
| BOM export, ZIP bundle export | Extend #274 or new issue |
| SVG shareable (export + import circuit data) | Extend #274 or new issue |
| Subcircuit library and placement | New issue — "Subcircuits" |
| Palette profiles (instructor-restricted component sets) | New issue — "Palette Profiles" |

### Adding Test Items

When you ship a PR with UI-visible behavior, add a checkbox to the appropriate testing issue. After editing issue checklists, regenerate the pre-filled bug-report links:

```bash
python scripts/generate_bug_links.py          # dry-run preview
python scripts/generate_bug_links.py --apply   # update all issues
```

---

## 9. Pre-Commit Hooks

`make install-hooks` installs hooks that run on every `git commit`:

- **ruff** — linting (must pass)
- **black** — formatting (auto-fixes)
- **isort** — import sorting (auto-fixes)

If a hook fails, fix the issue and recommit. Never bypass with `--no-verify` unless there's a genuine emergency, and document why.

---

## 10. Test Maintenance Guidelines

- **Don't mock the database or filesystem unnecessarily.** The project learned from incidents where mocked tests passed but real behavior was broken. Use real `CircuitModel` instances; use temp directories for file I/O tests.
- **Don't use `inspect.getsource()`-based tests.** These were replaced in #773 — they were fragile and tested implementation details instead of behavior.
- **Don't expand the inspect-based test pattern.** If you find one, migrate it to a behavioral test.
- **Do add a test for every bug fix.** The test should reproduce the bug before your fix, then pass after.