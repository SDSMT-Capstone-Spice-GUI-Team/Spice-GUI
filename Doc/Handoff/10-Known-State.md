# Known State (March 2026)

## Current Branch

**`dev-main-epic-front`** — focused on frontend/UI work. Working tree is clean.

## Recent Work

The last several commits focused on:

1. **Theming** — dark mode and light mode fully implemented with QSS stylesheets
2. **Scrollbar** — component palette scrollbar fixed and styled
3. **UI polish** — layout tweaks, margins, dark-mode-specific styling fixes
4. **Test coverage** — MVC layers brought to 99-100%
5. **Canvas features** — middle-mouse-button panning, splash screen

## What's Working

- Circuit design (drag-drop, wire routing, rotation, undo/redo)
- All 9 simulation analysis types via ngspice
- File save/load with JSON format
- Import/export (LTSpice, SPICE netlist, CSV, Excel, LaTeX)
- Dark and light themes
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