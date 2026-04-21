# Known State (April 2026)

## Current Branch

**`dev-main-epic-front`** — focused on frontend/UI work. Working tree is clean.

## Recent Work

The last several commits focused on:

1. **Palette profiles** — `app/services/palette_profiles.py` adds class-based filtering of the component palette (built-in `circuits_1` / `circuits_2` profiles plus user-defined profiles from disk)
2. **IEEE/IEC symbol toggle** — component palette regenerates icons when the user switches between American (IEEE) and European (IEC) schematic symbols
3. **Font rendering** — `GUI/styles/font_loader.py` plus bundled OpenDyslexic / JetBrains Mono fonts; `ThemeManager` exposes `font()` / `font_family` for runtime switching (likely still has rough edges per commit message)
4. **Theming** — dark mode and light mode fully implemented with QSS stylesheets
5. **Scrollbar** — component palette scrollbar fixed and styled
6. **UI polish** — layout tweaks, margins, dark-mode-specific styling fixes
7. **Test coverage** — MVC layers brought to 99-100% (148 unit test files)
8. **Canvas features** — middle-mouse-button panning, splash screen

## What's Working

- Circuit design (drag-drop, wire routing, rotation, undo/redo)
- All 9 simulation analysis types via ngspice
- File save/load with JSON format
- Import/export (LTSpice, SPICE netlist, CSV, Excel, LaTeX)
- Dark and light themes
- IEEE/IEC symbol style switching with live palette icon refresh
- Palette profiles for instructor-restricted component sets
- Bundled accessibility fonts via `font_loader.py`
- Component palette, properties panel, results panel
- Grading system (rubrics, auto-grading, batch grading)
- Keyboard shortcuts (configurable)
- Templates (7 built-in circuits)
- Print/PDF export

## Existing Documentation

The project has documentation in several places:

| Location | Content |
|----------|---------|
| `docs/adr/` | Architecture Decision Records (MVC, testing, branching) |
| `docs/` | Canvas rebuild guide, human testing guide, bug filing |
| `wiki/` | 16 user-facing guides (install, quick start, shortcuts, etc.) |
| `Doc/` | Legacy docs, discovery phase materials, this handoff |
| `README.md` | Project overview |

## Where to Start

1. Read this handoff documentation
2. Run `python app/main.py` to see the app
3. Open a template circuit (File → Templates) and run a simulation
4. Read `docs/adr/` for architectural decisions
5. Browse `wiki/` for user-facing documentation
6. Run `make test` to verify everything passes