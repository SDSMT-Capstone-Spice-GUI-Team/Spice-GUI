# Future Roadmap — SDM Spice

**Last Updated:** 2026-05-06
**Audience:** Incoming development teams, project sponsors, stakeholders

> This document consolidates the **prioritized next-step guidance** from the outgoing capstone team with the **feature phase status** from the project roadmap. The GitHub Issues backlog and `wiki/Roadmap.md` are the authoritative tracking locations; this document is the strategic layer — the *why* and *in what order*.

---

## What Has Been Built

As of May 2026, the following phases are complete:

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Student MVP (circuit design + simulation) | ✅ Complete |
| 2 | Enhanced Export (reports, images, SVG shareable, CLI) | 🔄 Partial — export done; LMS integration not built |
| 3 | Instructor Tools (templates, grading, rubrics) | ✅ Complete |
| 4 | Advanced Instructor Features (analytics, batch grading) | ✅ Complete |
| 5 | TA Role Support | 📋 Not started |
| 6 | Researcher Features (scripting API, Jupyter, Monte Carlo) | ✅ Complete |
| 7 | Advanced Features and Polish | 📋 Not started |

**All core simulation, grading, and scripting features are working.** What remains is primarily installer parity (macOS/Linux), UX polish, and institutional integration (LMS).

---

## Tier 1 — Do These in Your First Month

These are small enough to ship while onboarding and they pay back immediately.

### 1.1  Prune Stale Branches and Fix the `.gitignore`

`git branch -a` shows a graveyard of `epic/*` branches (adaptive-gui, ui-customization, stability, simulation, instructor, export, scripting) plus several personal branches. Most are merged or superseded. Verify and delete them.

Add `app/.autosave_recovery.json` to `.gitignore` so contributors stop seeing it as an untracked file.

**Effort:** half a day. **Why first:** removes noise that confuses every newcomer.

### 1.2  Maintain the Known Issues List

`Doc/Handoff/10-Known-State.md` seeds this. Every time you trip on something undocumented, append it with reproduction steps. The list is most valuable in week 1 — it gets harder to remember surprises after that.

**Effort:** ongoing, ~5 min per discovery. **Why first:** the next handoff after yours depends on this.

### 1.3  Class-by-Class Documentation Pages

The highest-value documentation gap: one page per class, listing each attribute and method with a one-line purpose. Start with the heaviest hitters:

- `CircuitModel`, `CircuitController`, `SimulationController`
- `MainWindow` and its 8 mixins
- `CircuitCanvasView`, `ComponentGraphicsItem`, `WireItem`
- `ThemeManager`, `NetlistGenerator`, `ResultParser`

Generate from docstrings where possible; hand-edit where not.

**Effort:** 1–2 weeks for the team. **Why first:** future onboarding (and AI-assisted contribution) gets dramatically faster.

---

## Tier 2 — High-Value Next Steps (1–2 Months In)

### 2.1  macOS and Linux Installers

Only Windows is packaged today. The PyInstaller spec (`SpiceGUI.spec`) is Windows-tuned; the CI workflow (`release-installer.yml`) only runs on `windows-latest`.

**macOS path:**
- Add a `macos-latest` CI job running PyInstaller + `create-dmg` or `dmgbuild`
- Code-signing requires an Apple developer account (separate decision)
- `ngspice_config.py` already supports bundled-ngspice layout

**Linux path:**
- AppImage or `.deb` from PyInstaller's onedir output

**Effort:** 2–3 weeks per platform, mostly CI plumbing and signing decisions.
**Why important:** Not all SDSMT students are on Windows — this is the single biggest accessibility gap.

### 2.2  Decompose Oversized Mixin Files

Two mixins are approaching 800–900 lines, past the project's split threshold:

- `main_window_file_ops.py` → split into `..._file_ops.py` (open/save/recent) + `..._import_export.py` (all format conversions)
- `main_window_simulation.py` → split into `..._simulation.py` (run/stop/configure) + `..._results.py` (results tab management, export from results)

**Effort:** ~1 week. **Why important:** these are the two files the next team touches most, and they're already painful to navigate.

### 2.3  Grading UX Maturation

The auto-grading engine works; the UX is rough. Known gaps:

- **Rubric editor** (`rubric_editor_dialog.py`) — no "edit one criterion across all rubrics" flow
- **Feedback export** — plain text; a templated Markdown/PDF format would land better with instructors
- **Batch grading progress UI** — minimal; no per-student status, no resumable runs

**Effort:** 3–4 weeks.
**Why important:** grading is half the value proposition for instructors; current state is "works in a demo, painful in a real class."

### 2.4  Dialog Test Coverage

Every dialog under `app/GUI/*_dialog.py` should have at least smoke-level `pytest-qt` coverage (constructor, default state, OK/Cancel paths). Goal is "every dialog can open and close without crashing" — not 100% line coverage.

**Effort:** 2 weeks.
**Why important:** dialogs are where the most user-visible regressions appear.

---

## Tier 3 — Larger Investments (Pick One Per Semester)

### 3.1  Performance on Larger Circuits

The IDA\* router (`app/algorithms/path_finding.py`, ~850 lines) slows noticeably on 50+ component circuits.

- Profile with a large circuit (hundreds of components) and identify hotspots
- Consider hierarchical pathfinding or subproblem caching
- Add a benchmark test so regressions are visible

**Effort:** 4–6 weeks for someone interested in algorithms.
**Why valuable:** opens the door to non-trivial circuits in upper-division coursework.

### 3.2  Subcircuit Editing UX

Subcircuits load and simulate, but creating a new subcircuit definition is a multi-step ritual students won't discover on their own. A "select these components → right-click → Make Subcircuit" flow would be transformative.

**Effort:** 3–4 weeks.
**Why valuable:** subcircuits are the gateway to scaling circuits beyond introductory labs.

### 3.3  Web / Jupyter Front-End

The headless scripting API and Jupyter integration already exist. A logical next step is a browser-based viewer (using PyScript, or rendering the canvas to SVG and shipping a static viewer) so instructors can share live circuits in an LMS without requiring an install.

**Effort:** unscoped, probably a full semester.
**Why valuable:** removes the install barrier for read-only / demo use cases.

### 3.4  LMS Integration

The `requests` dependency is in `requirements.txt` "for future cloud features." If you take this on: a hosted endpoint where instructors push a circuit and students pull it (or submit back). Authentication, hosting, and FERPA all become real concerns.

**Effort:** semester+.
**Warning:** anything touching student data needs institutional sign-off from IT, legal, and the sponsor before starting.

---

## Process Notes for the Incoming Team

- **Release pipeline** triggers on `v*` tag push. Your first release is a good forcing function for testing the runbook end-to-end.
- **`make preflight`** enforces the `issue-NNN-*` branch naming convention. If you change the branch model, update the Makefile rule too.
- **The wiki** under `wiki/` mirrors the GitHub Wiki. When you change one, sync the other, or pick one to be canonical and redirect the other.
- **ADR process:** when you make a significant architectural decision, write an ADR. The next ADR number is 012. Template is in `Doc/adr/README.md`.

---

## Don't-Do List

These look attractive but waste time. The previous team learned the hard way:

| What | Why Not |
|------|---------|
| Use `ruff format` / `ruff-format` | Conflicts with `black`; caused infinite CI reformat loops. Use `ruff check` + `black` only. |
| Import Qt into models or controllers | ADR-001 and the entire test suite depend on this boundary. If you think you need it, you're missing a Protocol abstraction. |
| Expand `inspect.getsource()` tests | Already replaced (#773) — they tested implementation details and were fragile. Write behavioral tests instead. |
| Hardcode colors | Migrations #491, #492, #516 routed every color through ThemeManager. Adding a hardcoded color reverses this. |
| Merge `epic/*` branches without verifying | Most are stale; merging them produces conflicts and resurrects deleted code. |

---

## Appendix: GitHub Resources

- **Issues / backlog:** https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues
- **Human testing board:** https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3
- **Releases:** https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/releases
- **ADRs:** `Doc/adr/` — especially ADR-001 through ADR-003 for process decisions