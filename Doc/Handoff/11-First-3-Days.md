# First 3 Days

A guided onboarding path for the next team. The other handoff docs are reference material; this one is a script. Follow it in order — by the end of day 3 you should be able to ship a small change confidently.

If you only have **30 minutes** today, do steps 1.1, 1.2, and 1.3 below and stop — that gets the app on your screen.

---

## Day 1 — Get It Running, See It Move

Goal: have the app open, run a simulation, and read the test suite green. No code changes yet.

### 1.1  Clone and bootstrap (~15 min)

```bash
git clone https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI.git
cd Spice-GUI
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
make install-dev
make install-hooks
```

Install ngspice on your system (`apt install ngspice`, `brew install ngspice`, or `pacman -S ngspice`). The Windows installer bundles ngspice; the from-source path does not.

### 1.2  Run the app (~5 min)

```bash
python app/main.py
```

You should see the main window with the component palette on the left, canvas in the middle, and properties/results panels on the right.

### 1.3  Drive a simulation by hand (~10 min)

1. **File → Templates → Voltage Divider** (loads a built-in circuit).
2. **Simulate → Run Analysis** → pick **DC Operating Point** → Run.
3. Confirm the results panel shows node voltages.
4. **File → Export → Markdown Report** to see the full output flow.

If anything in 1.1–1.3 fails, that's your first issue to file. The bug-report path is `Doc/how-to-file-a-bug.md`.

### 1.4  Run the tests (~10 min)

```bash
make test
```

Expect ~189 test files (~186 unit + 3 integration) to pass. If the integration tests are skipped, ngspice isn't on your `PATH` — fix that before continuing.

```bash
make check         # lint + tests, the gate before pushing
make preflight     # sanity-check your dev env
```

`make preflight` is opinionated: it wants you on an `issue-NNN-*` branch with a clean tree, venv at `.venv/`, and pre-commit hooks installed. Read the Makefile if it complains.

### 1.5  Read the high-level docs in this order (~45 min)

1. [01-Project-Overview.md](01-Project-Overview.md) — what this thing is and who it's for
2. [03-Architecture.md](03-Architecture.md) — MVC and the no-Qt-in-business-logic rule
3. [06-Simulation-Pipeline.md](06-Simulation-Pipeline.md) — the most important data flow in the app
4. [10-Known-State.md](10-Known-State.md) — what's working, what's rough, where you are right now
5. [Doc/adr/001-mvc-testability.md](../adr/001-mvc-testability.md) and [Doc/adr/002-tiered-testing.md](../adr/002-tiered-testing.md) — the two ADRs that shaped the architecture

**End of Day 1 deliverable:** the app runs, tests pass, and you can describe MVC in one sentence to a teammate.

---

## Day 2 — Trace One Feature End-to-End

Goal: understand how a user click becomes a circuit change, a simulation, and a rendered result.

### 2.1  Read the structural docs (~30 min)

- [04-Directory-Map.md](04-Directory-Map.md) — folder-by-folder breakdown
- [05-Key-Modules.md](05-Key-Modules.md) — the classes that matter most
- [Doc/architecture/canvas-architecture.md](../architecture/canvas-architecture.md)
- [Doc/architecture/gui-protocol-guide.md](../architecture/gui-protocol-guide.md) — explains why controllers don't import Qt

### 2.2  Trace "drop a resistor on the canvas" (~45 min)

Open these files side by side and follow the chain:

1. **`app/GUI/component_palette.py`** — drag start (Qt mime data is set here)
2. **`app/GUI/circuit_canvas.py`** — `dropEvent()` — translates the drop position to grid coordinates
3. **`app/controllers/circuit_controller.py`** — `add_component()` — mutates the model and notifies observers
4. **`app/models/circuit.py`** — `CircuitModel` — the actual data lives here
5. **`app/GUI/component_item.py`** — `ComponentGraphicsItem` paints the result on the canvas

Note how the controller and model never import Qt. That's the invariant. If you're tempted to break it, read ADR-001 first.

### 2.3  Trace "run a DC operating point simulation" (~45 min)

1. **`app/GUI/main_window_simulation.py`** — toolbar/menu handler
2. **`app/controllers/simulation_controller.py`** — orchestrates validate → generate → run → parse
3. **`app/simulation/circuit_semantic_validator.py`** — pre-flight checks (ground exists, etc.)
4. **`app/simulation/netlist_generator.py`** — `CircuitModel` → SPICE text
5. **`app/simulation/ngspice_runner.py`** — subprocess invocation (binary resolved by `ngspice_config.py`)
6. **`app/simulation/result_parser.py`** — text → `SimulationResult`
7. **`app/GUI/results_panel.py`** — renders the result

### 2.4  Run a single test file with pytest verbosity (~15 min)

```bash
cd app
pytest tests/unit/test_circuit_controller.py -v
pytest tests/integration/test_ngspice_smoke.py -v
```

Open one of those test files and read it. Notice they don't need a display server — that's the payoff for the no-Qt-in-controllers rule.

### 2.5  Skim the wiki and pick a personal area (~30 min)

`wiki/` has user-facing docs. Read [Architecture-Overview.md](../../wiki/Architecture-Overview.md), [Components.md](../../wiki/Components.md), and [Roadmap.md](../../wiki/Roadmap.md). Pick one subsystem you find interesting (canvas, grading, simulation, theming, scripting) — that's where you start tomorrow.

**End of Day 2 deliverable:** you can explain what happens between a user click and a rendered simulation result without looking it up.

---

## Day 3 — Ship a Small Change

Goal: open a feature branch, fix something small, get a green PR.

### 3.1  Pick an issue (~20 min)

Open the [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) tab. Filter on labels like `good-first-issue` or look for something tagged with the subsystem you picked yesterday. Read the [12-Roadmap.md](12-Roadmap.md) priority list — the easier items there are also fine starting points.

If nothing fits, the **"What's Rough or Half-Done"** list in [10-Known-State.md](10-Known-State.md) has real paper cuts (e.g. add `app/.autosave_recovery.json` to `.gitignore` is a one-line PR you could ship today).

### 3.2  Branch, fix, test (~2 hr)

```bash
git checkout develop
git pull
git checkout -b issue-NNN-short-description
# ... make your change ...
make check
make preflight
```

`make preflight` will refuse if your branch name doesn't match `issue-NNN-*`. That's the convention CI and reviewers expect.

### 3.3  Open the PR (~15 min)

- Push the branch and open a PR against `develop` (not `main`).
- Reference the issue number in the title and body.
- Watch CI: lint + bandit + tests on Ubuntu/Windows × Python 3.11/3.12/3.13 + integration with ngspice + import-check. All green is the bar.

### 3.4  Read what you didn't yet (~rest of the day)

- [02-Tech-Stack.md](02-Tech-Stack.md), [07-Feature-List.md](07-Feature-List.md), [08-Testing.md](08-Testing.md), [09-Dev-Setup.md](09-Dev-Setup.md)
- [Doc/Handoff/design-discussions/2026-02-10-epic-workflow-and-branch-strategy.md](design-discussions/2026-02-10-epic-workflow-and-branch-strategy.md) — branching history
- [Doc/canvas-rebuild-guide.md](../canvas-rebuild-guide.md) — useful if you ever touch the canvas
- [Doc/human-testing-guide.md](../human-testing-guide.md) — what to manually verify before release

**End of Day 3 deliverable:** a PR open against `develop` with green CI.

---

## Reference Card

| Need to... | Run |
|-----------|-----|
| Run the app | `python app/main.py` |
| Run all tests | `make test` |
| Run lint + tests | `make check` |
| Auto-format | `make format` |
| Verify your dev env | `make preflight` |
| Run one test file verbosely | `cd app && pytest tests/unit/<file>.py -v` |
| Run ngspice integration tests | `cd app && pytest tests/integration/ -v` |
| Build the Windows installer locally | `python -m PyInstaller SpiceGUI.spec` then run Inno Setup on `installer/spicegui.iss` |
| Cut a release | Push a `v*` tag — CI builds the installer and attaches it to the GitHub Release |

## When You Get Stuck

1. Check `Doc/Handoff/` and `Doc/adr/` — most architectural questions have a written answer.
2. `git log -- <file>` and `git blame <file>` — most non-obvious code has context in a commit message or PR.
3. Search closed PRs on GitHub — issue-NNN branch naming makes this fast.
4. Ask the previous team. Capstone advisor / sponsor contacts should be in the project charter under `Doc/project-charter/`.