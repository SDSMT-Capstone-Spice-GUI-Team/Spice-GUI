# Onboarding Document — SDM Spice

**Last Updated:** 2026-05-06
**Audience:** New developers joining the project

---

## 1. What Is SDM Spice?

SDM Spice is an **open-source, cross-platform circuit design and simulation GUI** built at South Dakota School of Mines and Technology (SDSMT). It provides a drag-and-drop interface for designing electronic circuits and running SPICE simulations, targeted at students learning circuit analysis.

### Who Uses It

| Role | How |
|------|-----|
| **Students** | Build and simulate circuits for coursework |
| **Instructors** | Create assignment templates, auto-grade student submissions |
| **Researchers** | Script simulations via headless API or Jupyter |

### Current State (May 2026)

All major features are implemented and working:
- Circuit design with drag-and-drop placement, wire routing, undo/redo
- 9 simulation analysis types via ngspice
- Educational grading system (rubrics, batch grading, auto-grading)
- Python scripting API and Jupyter integration
- Dark/light themes, IEEE/IEC symbol styles, accessible fonts

The active branch is **`design-fair`**. CI runs on Ubuntu/Windows × Python 3.11/3.12/3.13.

---

## 2. Tech Stack

### Core

| Technology | Version | Role |
|-----------|---------|------|
| Python | 3.10+ | Primary language |
| PyQt6 | 6.9.1 | Desktop GUI framework — [ADR 008](../adr/008-pyqt6-desktop-framework.md) |
| ngspice | 36+ | SPICE simulation engine (external binary) — [ADR 007](../adr/007-ngspice-external-simulation-engine.md) |
| matplotlib | 3.10.6 | Waveform plotting |
| numpy | 2.3.3 | Numerical computing |
| openpyxl | 3.1.5 | Excel export |

### Dev Tools

| Tool | Role |
|------|------|
| ruff | Fast Python linter |
| black | Code formatter (120-char lines) |
| isort | Import sorting |
| bandit | Security linting |
| pytest | Test framework |
| pre-commit | Git hook manager |
| Makefile | Build targets |

### Key Architecture Constraint

> **Models and controllers have zero PyQt6 dependencies.**
> All business logic can be tested headlessly, without a display server. See [ADR 001](../adr/001-mvc-testability.md) and [ADR 005](../adr/005-mvc-architecture-zero-qt-dependencies.md).

---

## 3. Prerequisites

Before you start:

- **Python 3.10 or higher** — `python --version`
- **ngspice 36+** — must be installed and on your `PATH`
  - Ubuntu/Debian: `sudo apt install ngspice`
  - macOS: `brew install ngspice`
  - Arch: `sudo pacman -S ngspice`
  - Windows: download from [ngspice.sourceforge.io](http://ngspice.sourceforge.io/download.html) (the Windows installer bundles ngspice automatically)
- **Git**

---

## 4. Get It Running (30 min)

```bash
git clone https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI.git
cd Spice-GUI

python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

make install-dev              # installs runtime + dev dependencies
make install-hooks            # installs pre-commit hooks

python app/main.py            # launch the app
```

You should see the main window: component palette on the left, circuit canvas in the center, properties/results panels on the right.

### Verify the Test Suite

```bash
make test
```

Expect ~186 unit test files + 3 integration test files to pass. If integration tests are skipped, ngspice isn't on your `PATH`.

```bash
make check      # lint + tests (the gate before pushing)
make preflight  # sanity-check your dev env (branch naming, venv, hooks)
```

---

## 5. Drive a Simulation (10 min)

1. **File → Templates → Voltage Divider** — loads a built-in circuit.
2. **Analysis → DC Operating Point (.op)** — selects the analysis type.
3. **F5** (or **Simulation → Run Simulation**) — runs it.
4. Confirm node voltages appear on the canvas and in the results panel.
5. **File → Export → Markdown Report** — exercises the full output flow.

If anything fails, file a bug at `Doc/how-to-file-a-bug.md`.

---

## 6. Makefile Reference

| Target | What It Does |
|--------|-------------|
| `make test` | Full test suite |
| `make lint` | Ruff + bandit |
| `make format` | black + isort |
| `make check` | lint + test combined |
| `make install-dev` | Install dev dependencies |
| `make install-hooks` | Install pre-commit hooks |
| `make preflight` | Validate dev environment |

---

## 7. IDE Setup

The repo ships configs for both **PyCharm** (`.idea/`) and **VS Code** (`.vscode/`). Point either at the `.venv` virtual environment and they work out of the box.

**VS Code:** Press **F5** and select **"Run Spice-GUI"** to launch with the debugger attached.

---

## 8. Codebase Orientation (1–2 hr read)

Read these in order — each is short and focused:

1. [03-Architecture.md](../Handoff/03-Architecture.md) — MVC and the no-Qt-in-business-logic rule
2. [04-Directory-Map.md](../Handoff/04-Directory-Map.md) — folder-by-folder breakdown
3. [05-Key-Modules.md](../Handoff/05-Key-Modules.md) — the classes that matter most
4. [06-Simulation-Pipeline.md](../Handoff/06-Simulation-Pipeline.md) — the most important data flow
5. [ADR 001](../adr/001-mvc-testability.md) and [ADR 002](../adr/002-tiered-testing.md) — the two decisions that shaped everything

Then skim the wiki for user-facing context: [Architecture-Overview.md](../../wiki/Architecture-Overview.md) and [Components.md](../../wiki/Components.md).

---

## 9. Trace a Feature End-to-End (45 min)

### "Drop a resistor on the canvas"

Open these files side by side and follow the call chain:

1. `app/GUI/component_palette.py` — drag start (Qt mime data is set here)
2. `app/GUI/circuit_canvas.py` — `dropEvent()` — translates drop position to grid coordinates
3. `app/controllers/circuit_controller.py` — `add_component()` — mutates the model and notifies observers
4. `app/models/circuit.py` — `CircuitModel` — the actual data lives here
5. `app/GUI/component_item.py` — `ComponentGraphicsItem` paints the result on canvas

Notice that the controller and model never import Qt. That's the invariant — if you're tempted to break it, read ADR-001 first.

### "Run a DC operating point simulation"

1. `app/GUI/main_window_simulation.py` — toolbar/menu handler
2. `app/controllers/simulation_controller.py` — validate → generate → run → parse
3. `app/simulation/circuit_semantic_validator.py` — pre-flight checks
4. `app/simulation/netlist_generator.py` — `CircuitModel` → SPICE text
5. `app/simulation/ngspice_runner.py` — subprocess invocation
6. `app/simulation/result_parser.py` — text → `SimulationResult`
7. `app/GUI/results_panel.py` — renders the result

---

## 10. Branching and Contributing

- **`main`** — stable, releasable. Never commit directly.
- **`develop`** — integration branch. PRs target this.
- **Feature branches** — named `issue-NNN-short-description`. `make preflight` enforces this.

```bash
git checkout develop
git pull
git checkout -b issue-NNN-short-description
# ... make your change ...
make check
make preflight
# open PR against develop
```

CI gate: ruff + bandit + pytest on Ubuntu/Windows × Python 3.11/3.12/3.13 + ngspice integration + import check. All green is the bar.

See [ADR 003](../adr/003-branching-strategy.md) for the full branching strategy.

---

## 11. When You Get Stuck

1. **`Doc/Handoff/`** and **`Doc/adr/`** — most architectural questions have a written answer.
2. **`git log -- <file>`** and **`git blame <file>`** — most non-obvious code has context in a commit message.
3. **Closed PRs on GitHub** — `issue-NNN` branch naming makes searching fast.
4. **Previous team contacts** — see `Doc/project-charter/` for capstone advisor and sponsor contacts.

---

## 12. Quick Reference Card

| Task | Command |
|------|---------|
| Run the app | `python app/main.py` |
| Run all tests | `make test` |
| Lint + test | `make check` |
| Auto-format | `make format` |
| Verify dev env | `make preflight` |
| Run one test file | `cd app && pytest tests/unit/<file>.py -v` |
| Run integration tests | `cd app && pytest tests/integration/ -v` |
| Build Windows installer | `python -m PyInstaller SpiceGUI.spec` then Inno Setup on `installer/spicegui.iss` |
| Cut a release | Push a `v*` tag — CI builds the installer and attaches it to GitHub Release |