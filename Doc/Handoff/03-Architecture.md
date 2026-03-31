# Architecture

## MVC Overview

The codebase follows a strict **Model-View-Controller** pattern with a hard rule: **no Qt in models or controllers**.

```
┌─────────────────────────────────────────────────────┐
│                    GUI Layer (PyQt6)                 │
│  MainWindow, Canvas, Dialogs, Palette, Panels       │
│  ─ renders model state                              │
│  ─ sends user actions to controllers                │
└──────────────────────┬──────────────────────────────┘
                       │ observes / calls
┌──────────────────────▼──────────────────────────────┐
│               Controllers (pure Python)             │
│  CircuitController, SimulationController,           │
│  FileController, UndoManager                        │
│  ─ modifies models                                  │
│  ─ broadcasts events to observers                   │
└──────────────────────┬──────────────────────────────┘
                       │ reads / writes
┌──────────────────────▼──────────────────────────────┐
│                 Models (pure Python)                 │
│  CircuitModel, ComponentData, WireData, NodeData    │
│  ─ single source of truth                           │
│  ─ no behavior, just data                           │
└─────────────────────────────────────────────────────┘
```

## Observer Pattern

Controllers use a simple callback-based observer system — no Qt signals in the business logic.

```
User clicks → View captures event
  → Controller.method() called
    → Controller modifies Model
      → Controller._notify("event_name", data)
        → All registered observers receive the update
          → Views re-render
```

## Design Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| **MVC** | `models/`, `controllers/`, `GUI/` | Separation of concerns |
| **Observer** | `CircuitController._notify()` | Decoupled view updates |
| **Command** | `commands.py`, `undo_manager.py` | Undo/redo support |
| **Strategy** | `path_finding.py` | Multiple pathfinding algorithms (IDA*, A*) |
| **Singleton** | `theme_manager.py` | Global theme access |
| **Protocol** | `protocols/` | Type-safe interfaces without inheritance |
| **Mixin** | `main_window_*.py` | MainWindow is composed of 8 focused mixins |

## Protocols (Type Contracts)

Located in `app/protocols/`, these define interfaces that decouple layers:

- `ApplicationShellProtocol` — main window interface
- `CanvasProtocol` — canvas for observers
- `DialogsProtocol` — unified dialog provider
- `PaletteProtocol`, `PropertiesProtocol`, `ResultsProtocol`

## MainWindow Composition

`MainWindow` is split across 8 mixin files to keep it manageable:

```
MainWindow (main_window.py — 554 lines)
 ├── MenuBarMixin         (main_window_menus.py)
 ├── FileOperationsMixin  (main_window_file_ops.py)
 ├── SimulationMixin      (main_window_simulation.py)
 ├── AnalysisSettingsMixin(main_window_analysis.py)
 ├── ViewOperationsMixin  (main_window_view.py)
 ├── PrintExportMixin     (main_window_print.py)
 ├── HelpMixin            (main_window_help.py)
 └── SettingsMixin        (main_window_settings.py)
```