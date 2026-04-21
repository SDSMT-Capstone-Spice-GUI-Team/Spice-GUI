# Testing

## Test Organization

```
app/tests/
├── conftest.py              ← Shared pytest fixtures
├── unit/                    ← 148 test files
│   ├── test_circuit_model.py
│   ├── test_circuit_controller.py
│   ├── test_component_*.py
│   ├── test_wire_*.py
│   ├── test_*_dialog.py
│   ├── test_*_exporter.py
│   ├── test_grading_*.py
│   └── controllers/        ← Controller-specific coverage tests
└── integration/             ← 4 integration test files
    ├── test_ngspice_smoke.py         ← Is ngspice installed?
    ├── test_ngspice_workflows.py     ← Full simulation flows
    ├── test_save_load.py             ← File I/O round-trips
    └── test_phase4_mvc_integration.py
```

## Testing Strategy (ADR-002)

The project follows a **tiered testing** approach:

1. **Unit tests** — Model and controller logic, no Qt required. Fast and comprehensive.
2. **Netlist snapshot tests** — Verify generated SPICE output matches expected strings.
3. **Widget tests** — Individual dialogs tested with `pytest-qt` (`qtbot`). MainWindow is NOT tested this way.
4. **Structural assertions** — Terminal positions, bounding boxes, z-order.
5. **Human testing** — Visual aesthetics, drag feel, print output. See `docs/human-testing-guide.md`.

## Running Tests

```bash
# Full suite
make test

# Or directly
cd app && pytest tests/ -v

# Specific file
cd app && pytest tests/unit/test_circuit_model.py -v

# Integration only (requires ngspice installed)
cd app && pytest tests/integration/ -v

# With coverage
cd app && pytest tests/ --cov=. --cov-report=term-missing
```

## Current Coverage

| Layer | Coverage |
|-------|---------|
| Models | ~100% |
| Controllers | 99%+ |
| Simulation | High |
| Grading | High |
| GUI/Dialogs | Partial (isolated dialog tests) |

## Fixtures (`conftest.py`)

Key fixtures include mock controllers, sample circuit models, and test component factories — all designed to work without a running display server.

## CI

GitHub Actions runs the test suite on push. See `.github/` for workflow definitions.