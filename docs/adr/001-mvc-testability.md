# ADR-001: MVC Architecture for Testability

**Date**: 2026-02-11
**Status**: Accepted
**Participants**: Jeremy (Software Architect), Claude Agent (Opus 4.6)

## Decision

The project uses a Model-View-Controller (MVC) pattern that separates data (models), business logic (controllers), and UI (GUI). This separation exists specifically to enable unit testing without the Qt GUI layer.

## Context

PyQt6's `MainWindow` hangs when instantiated in offscreen/CI test mode (`QT_QPA_PLATFORM=offscreen`). This means any test that requires `MainWindow` cannot run in CI. Without MVC separation, testing would require launching the full GUI — making automated testing impractical.

The test suite has ~46 pre-existing GUI test failures in headless environments due to Qt display server limitations. These are expected and accepted.

## Architecture

```
app/
├── models/          # Data classes, no Qt dependency
│                    # CircuitModel, ComponentData, WireData, NodeData
│                    # → Testable with plain pytest
│
├── controllers/     # Business logic, minimal Qt dependency
│                    # CircuitController, SimulationController, FileController
│                    # → Testable with pytest + mock
│
├── GUI/             # PyQt6 views, depends on models + controllers
│                    # MainWindow, CircuitCanvas, dialogs, graphics items
│                    # → Testable with qtbot on individual widgets (never MainWindow)
│
├── simulation/      # ngspice pipeline, no Qt dependency
│                    # Netlist generation, runner, parser, validator
│                    # → Testable with pytest, mock ngspice for CI
│
└── tests/           # pytest suite
    ├── unit/        # Model, controller, simulation tests
    └── integration/ # Cross-layer tests (model → controller → file I/O)
```

## Test Layer Priority

When deciding how to test a behavior, prefer the highest layer that can cover it without the GUI:

1. **Model/controller test** — serialization, undo, node consistency, file operations
2. **Netlist snapshot test** — component SPICE output, analysis directives, model deduplication
3. **qtbot widget test** — dialogs, menus, panels (never MainWindow)
4. **Structural assertion** — terminal positions, bounding boxes, z-order (`zValue()`)
5. **Human testing item** — drag feel, visual aesthetics, print dialogs, cross-session UX

## Consequences

- Most new feature tests should target the model or controller layer
- GUI tests use `qtbot` on individual widgets, dialogs, or `QGraphicsScene` — never `MainWindow`
- Features that can only be verified visually get filed as human testing items on [Project #3](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)
- Test count grows primarily in `app/tests/unit/`, not GUI-dependent tests
