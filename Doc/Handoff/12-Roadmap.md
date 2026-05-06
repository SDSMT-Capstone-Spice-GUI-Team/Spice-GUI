# Prioritized Roadmap

This is the outgoing capstone team's opinion on what to tackle next, in priority order, with rationale. Treat it as a starting point, not a contract — `wiki/Roadmap.md` and the GitHub Issues backlog are the authoritative wishlist; this file is "if we had one more semester, here's how we'd spend it."

Priorities are ranked by **value × tractability** for an incoming team that's still ramping up. Cheap wins come first.

---

## Tier 1 — Do These In Your First Month

These are small enough to ship while onboarding and they pay back immediately.

### 1.1  Prune stale branches and untrack the autosave artifact

`git branch -a` shows a graveyard of `epic/*` branches (adaptive-gui, ui-customization, stability, simulation, instructor, export, scripting), plus `dev-main-epic-front`, `dev-main-epic-front-merge-devlop`, `merge-epic-front-into-develop`, and a few personal branches (`Micah`, `Jon`, `CDR_Prototypr`, `PDR_prototype`, `MVC-migration`). Most are merged or superseded. Verify, then delete.

Add `app/.autosave_recovery.json` (and any other autosave artifacts that show up untracked) to `.gitignore` so contributors stop seeing it.

**Effort:** half a day. **Why first:** removes noise that confuses every newcomer.

### 1.2  Write the "Known Issues" list as you discover them

[10-Known-State.md](10-Known-State.md) seeds this with a handful of paper cuts. Every time you trip on something undocumented, append it there with reproduction steps. The list is most valuable in week 1; it gets harder to remember the surprises after that.

**Effort:** ongoing, ~5 min per discovery. **Why first:** the next handoff after yours depends on this.

### 1.3  Class-by-class documentation pages

The outgoing team flagged this as the highest-value gap — one page per class listing each variable and method with a one-line purpose. Start with the heaviest hitters (`CircuitModel`, `CircuitController`, `SimulationController`, `MainWindow` and its mixins, `CircuitCanvasView`, `ComponentGraphicsItem`, `WireItem`, `ThemeManager`, `NetlistGenerator`, `ResultParser`). Generate from docstrings where possible, hand-edit where not.

**Effort:** 1–2 weeks of focused work, can be split across the team. **Why first:** future onboarding (and AI-assisted contribution) gets dramatically faster once this exists.

---

## Tier 2 — High-Value Next Steps (1–2 Months In)

### 2.1  macOS and Linux installers

Only Windows is packaged today. The PyInstaller spec (`SpiceGUI.spec`) is Windows-tuned, and the CI workflow (`release-installer.yml`) only runs on `windows-latest`. To unblock the other platforms:

- macOS: add a `macos-latest` job that runs PyInstaller and packages the result as a `.dmg` (use `create-dmg` or `dmgbuild`); code-signing is a separate decision (Apple developer account required).
- Linux: an `AppImage` or `.deb` is the lowest-friction path; PyInstaller's onedir output works as a starting point, then wrap it.

The `ngspice_config.py` runtime resolution already supports a bundled-ngspice layout, so the simulator detection won't need to change.

**Effort:** 2–3 weeks per platform, mostly CI plumbing and signing decisions. **Why important:** SDSMT students aren't all on Windows; this is the single biggest accessibility gap for the project's core audience.

### 2.2  Decompose `main_window_file_ops.py` and `main_window_simulation.py`

Both mixins are approaching 800–900 lines, which is past the threshold the project uses ("split when you add a new top-level menu category"). Candidate splits:

- `main_window_file_ops.py` → `..._file_ops.py` (open/save/recent) + `..._import_export.py` (LTSpice/CircuitikZ/CSV/Excel/Markdown/ZIP/BOM)
- `main_window_simulation.py` → `..._simulation.py` (run/stop/configure) + `..._results.py` (results tab management, export from results)

**Effort:** ~1 week. **Why important:** these are the two files the next team will touch most often, and they're already painful to navigate.

### 2.3  Grading UX maturation

The auto-grading engine works; the rubric editor and feedback formatting are rough. Specific known gaps:

- Rubric editor (`rubric_editor_dialog.py`) is functional but unintuitive — workflows for "edit one criterion across all rubrics" don't exist.
- Feedback export: the per-student feedback document is plain text; a templated Markdown/PDF format would land much better with instructors.
- Batch grading progress UI is minimal — no per-student status, no resumable runs.

**Effort:** 3–4 weeks. **Why important:** grading is half the value proposition for instructors; current state is "works in a demo, painful in a real class."

### 2.4  GUI dialog test coverage

ADR-002 explicitly chose tiered testing — that's still the right call, but the dialog layer has grown enough that the gap is real. Goal: at least smoke-level `pytest-qt` coverage for every dialog under `app/GUI/*_dialog.py` (constructor, default state, OK/Cancel paths). Don't aim for 100% line coverage — aim for "every dialog can open and close without crashing."

**Effort:** 2 weeks. **Why important:** dialogs are where the most user-visible regressions land.

---

## Tier 3 — Larger Investments (Pick One Per Semester)

### 3.1  Performance on larger circuits

The IDA\* router (`app/algorithms/path_finding.py`, ~850 lines) is the most algorithmically interesting piece of the codebase. Anecdotally it slows on 50+ component circuits. Concrete asks:

- Profile with a large circuit (a few hundred components) and identify hotspots.
- Consider hierarchical pathfinding or caching repeated subproblems.
- Add a benchmark test so regressions are visible.

**Effort:** 4–6 weeks for someone interested in algorithms. **Why valuable:** opens the door to using the tool for non-trivial circuits in upper-division coursework.

### 3.2  Subcircuit polish

Subcircuits load and simulate, but the editing UX (`subcircuit_dialog.py`, `subcircuit_gui_registration.py`) is awkward — creating a new subcircuit definition is a multi-step ritual that students won't discover on their own. A "select these components → make subcircuit" right-click flow would be transformative.

**Effort:** 3–4 weeks. **Why valuable:** subcircuits are the gateway to scaling circuits past hand-soldering complexity.

### 3.3  Web / Jupyter front-end

The headless scripting API (`app/scripting/`) and Jupyter integration already exist. A natural next step is a browser-based viewer (using PyScript, or rendering the canvas to SVG and shipping a static viewer) so instructors can share live circuits in a learning-management system without the install hurdle.

**Effort:** unscoped, probably a full semester project. **Why valuable:** removes the install barrier entirely for the read-only / demo case.

### 3.4  Cloud sync / classroom mode

The `requests` dependency is already in `requirements.txt` "for future cloud features." If you want to take that swing: a hosted endpoint where instructors push a circuit and students pull it (or push their submissions back). Authentication, hosting, and FERPA all become real concerns — **don't pick this without faculty / IT / legal buy-in first.**

**Effort:** semester+. **Why risky:** anything touching student data needs institutional sign-off.

---

## Don't-Do List

These look attractive but burn time without paying back. The previous team learned the hard way:

- **Don't reintroduce `ruff format` / `ruff-format`.** It conflicted with `black` and caused infinite reformat loops in CI. The `ci.yml` comment documents this. Stay with `ruff check` + `isort` + `black`.
- **Don't move models or controllers into a Qt-aware module.** ADR-001 and the entire test infrastructure depend on this. If you find yourself "needing" Qt in a controller, you're missing a protocol abstraction.
- **Don't expand `inspect.getsource()`-based tests.** The team already replaced them with behavioral tests (#773) — they were fragile and tested the wrong thing.
- **Don't hardcode colors anywhere.** Theme migrations (#491, #492, #516) routed every color through the theme system; adding a hardcoded color reverses that work.
- **Don't merge `epic/*` branches without verifying the work is already on `develop`.** Most of them are stale and merging them produces conflicts and resurrects deleted code.

---

## Process Notes

- The release pipeline triggers on `v*` tag push. Your first release of the next academic year is a good forcing function for testing the runbook end-to-end.
- The wiki under `wiki/` mirrors the GitHub Wiki — when you change one, sync the other, or pick one to be canonical.
- `make preflight` enforces the `issue-NNN-*` branch convention. If you change the branch model, update the Makefile rule too — silent drift between docs and tooling is how the previous "branching strategy" doc went stale.