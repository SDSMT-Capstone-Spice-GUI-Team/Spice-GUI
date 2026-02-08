# ADR 002: MVC Architecture with Zero PyQt6 Dependencies in Core Logic

**Date:** 2024-11-11 (Implemented)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** 00670ea, 4d03f20, ef2d7b5, fe7273d

---

## Context

The initial prototype was implemented as a monolithic PyQt6 application where `CircuitCanvas` (the view) contained all application logic:
- Circuit state (components, wires, nodes)
- Business logic (node graph operations, validation)
- File I/O operations
- Simulation pipeline execution

This design created several problems:
- **Difficult to test:** PyQt6 dependencies required display server, made unit testing slow
- **Tight coupling:** Business logic couldn't be reused outside the GUI
- **Poor separation:** Hard to understand what was view code vs domain logic
- **Limited reusability:** Core logic locked into Qt application context

As the application grew in complexity (adding simulations, file management, validation), the need for better architecture became critical.

---

## Decision

**We will refactor the application into a Model-View-Controller (MVC) architecture with a strict zero-PyQt6 dependency rule for models and controllers.**

### Architecture Components

**Model Layer** (Zero Qt dependencies):
- `CircuitModel` - Circuit state (components, wires, nodes, graph operations)
- Dataclasses for domain objects (Component, Wire, SimulationResult)

**Controller Layer** (Zero Qt dependencies):
- `CircuitController` - Component/wire CRUD operations with observer pattern
- `SimulationController` - Simulation pipeline (validation → netlist → execution → parsing)
- `FileController` - Save/load with JSON serialization and validation

**View Layer** (PyQt6):
- `CircuitCanvas` - Visual rendering and user interaction
- `CircuitDesignGUI` - Main window and UI orchestration
- Component/Wire graphics items

### Key Principles

1. **No PyQt6 imports in models/controllers** - Enforced by unit tests
2. **Observer pattern** - Controllers notify views of model changes
3. **Pure Python core** - Business logic usable in scripts, tests, CLI
4. **View as thin layer** - Only handles rendering and user input

---

## Consequences

### Positive

✅ **Testability**: 108 unit tests for core logic without Qt overhead
✅ **Fast tests**: Model/controller tests run in milliseconds
✅ **Reusability**: Core logic can be used in scripts, batch processing, future CLI
✅ **Clarity**: Clear boundaries between concerns
✅ **Maintainability**: Changes to business logic don't affect UI code
✅ **Parallelism**: Multiple developers can work on view vs logic independently

### Negative

❌ **More files**: ~3x more modules than monolithic design
❌ **Indirection**: View → Controller → Model adds layers
❌ **Learning curve**: New contributors must understand MVC pattern
❌ **Boilerplate**: Observer pattern requires event plumbing

### Mitigation Strategies

**Documentation:**
- Code comments explain MVC boundaries
- Tests demonstrate proper usage patterns

**Conventions:**
- Clear directory structure: `models/`, `controllers/`, `GUI/`
- Naming: `*Controller`, `*Model`, `*Item` suffixes indicate layer

**Tooling:**
- Unit tests verify zero Qt dependencies (`'PyQt6' not in sys.modules`)
- Linters can flag Qt imports in wrong layers

---

## Implementation Details

### Phase 1: Extract Model (Commit 00670ea)
```python
# Before: Everything in CircuitCanvas
class CircuitCanvas(QGraphicsView):
    def __init__(self):
        self.components = []
        self.wires = []
        self.nodes = {}
        # + 500 lines of mixed logic

# After: Separate data model
@dataclass
class CircuitModel:
    components: List[Component]
    wires: List[Wire]
    nodes: Dict[int, Set[Terminal]]
    # Pure Python, no Qt
```

### Phase 2: Extract Controllers (Commits 4d03f20, ef2d7b5, fe7273d)
```python
# Controller handles operations, notifies observers
class CircuitController:
    def __init__(self, model: CircuitModel):
        self.model = model
        self.observers = []

    def add_component(self, comp: Component):
        self.model.components.append(comp)
        self._notify_observers('component_added', comp)
```

### Observer Pattern
```python
# View registers as observer
controller.add_observer(self.on_circuit_changed)

# Controller notifies on changes
def _notify_observers(self, event: str, data):
    for observer in self.observers:
        observer(event, data)
```

---

## Alternatives Considered

### Alternative 1: Keep Monolithic Design
**Approach:** Leave all logic in `CircuitCanvas`

**Rejected because:**
- Testing requires full Qt initialization and display server
- Can't reuse logic outside GUI context
- Single file grew to 800+ lines
- Violates Single Responsibility Principle

### Alternative 2: Allow Qt in Models/Controllers
**Approach:** Use Qt signals/slots for observers, Qt data structures

**Rejected because:**
- Defeats testability benefits (still need Qt runtime)
- Creates unnecessary dependency on GUI framework
- Limits future flexibility (what if we want web UI?)
- Python built-ins (callbacks, dataclasses) are sufficient

### Alternative 3: Domain-Driven Design (DDD)
**Approach:** Full DDD with entities, aggregates, repositories, services

**Deferred because:**
- Overkill for current complexity
- Team more familiar with MVC pattern
- Can evolve to DDD later if needed
- MVC provides 80% of benefits with 20% of complexity

### Alternative 4: MVP (Model-View-Presenter) Pattern
**Approach:** Presenter mediates between passive view and model

**Not chosen because:**
- MVC more common in Python GUI applications
- Controller pattern fits PyQt's signals/slots well
- Team already familiar with MVC from web development

---

## Validation

### Test Coverage
- `test_circuit_model.py`: 253 tests for CircuitModel
- `test_circuit_controller.py`: 20 tests for observer pattern + operations
- `test_simulation_controller.py`: Tests for full simulation pipeline
- `test_file_controller.py`: Tests for save/load/validation

### Zero-Dependency Verification
```python
def test_no_pyqt6_dependency():
    """Verify CircuitModel has no PyQt6 imports"""
    import sys
    import models.circuit
    assert 'PyQt6' not in sys.modules
```

### Performance
- Model/controller tests: <1s total
- Full test suite (with Qt): ~8s
- Before MVC: All tests required Qt, took ~15s

---

## Migration Path

For new features:
1. **Add to model** - Data structures and core logic
2. **Add to controller** - Operations and notifications
3. **Update view** - Rendering and event handling

For existing code:
- Gradually extract logic from views into controllers
- Add tests as logic is extracted
- Keep view code focused on Qt-specific concerns only

---

## Related Decisions

- [ADR 001](001-local-first-no-user-accounts.md) - Local-first architecture (no backend controllers needed)
- [ADR 005](005-pyqt6-desktop-framework.md) - PyQt6 as view layer technology

---

## References

- Initial prototype: Single-file monolithic design
- MVC refactor PR: Issues #60, #61, #62, #63
- Observer pattern: [CircuitController](../../app/controllers/circuit_controller.py)
- Zero-Qt tests: [test_circuit_model.py](../../app/tests/unit/test_circuit_model.py)

---

## Review and Revision

This decision should be reviewed if:
- Adding web interface (may need different view layer)
- Moving to client-server architecture (may need API layer)
- Performance issues with observer pattern overhead

**Status:** Working well, no plans to change
