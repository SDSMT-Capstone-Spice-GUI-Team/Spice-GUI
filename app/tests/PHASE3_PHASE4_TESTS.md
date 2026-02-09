# Phase 3 & Phase 4 Test Suite

This document describes the comprehensive test suite for Phase 3 (Renaming) and Phase 4 (MVC Refactoring).

## Test Files

### Unit Tests

#### `test_phase3_renaming.py`
Tests backward compatibility aliases after Phase 3 renaming:
- `ComponentItem` → `ComponentGraphicsItem`
- `WireItem` → `WireGraphicsItem`
- `CircuitCanvas` → `CircuitCanvasView`

**Test Coverage:**
- Backward compatibility aliases work correctly
- Old names map to new classes
- Module exports include both old and new names
- WireData model backing integration
- Component inheritance hierarchy
- Various import patterns

**Key Tests:**
- `test_component_item_backward_compatibility()` - Verifies ComponentItem alias
- `test_wire_item_backward_compatibility()` - Verifies WireItem alias
- `test_circuit_canvas_backward_compatibility()` - Verifies CircuitCanvas alias
- `test_gui_module_exports_both_names()` - Verifies exports
- `test_wire_data_integration()` - Verifies WireData backing

#### `test_canvas_sync.py`
Tests canvas-model synchronization methods added in Phase 4:
- `sync_to_model()` - Push canvas state to model
- `sync_from_model()` - Pull model state to canvas

**Test Coverage:**
- Component synchronization
- Wire synchronization
- Node graph synchronization
- Component counter preservation
- Canvas clearing before restore
- Bidirectional consistency
- Empty circuit handling
- Property preservation
- Error handling

**Key Tests:**
- `test_sync_to_model_updates_components()` - Component data sync
- `test_sync_from_model_restores_components()` - Component restoration
- `test_sync_bidirectional_consistency()` - Roundtrip verification
- `test_sync_handles_empty_circuit()` - Edge case handling

#### `test_main_window_mvc.py`
Tests MainWindow MVC architecture and separation of concerns:
- Controller instantiation
- Business logic delegation
- View responsibilities
- Error handling

**Test Coverage:**
- MainWindow creates model and controllers
- File operations delegated to FileController
- Simulation delegated to SimulationController
- Canvas syncs before save/after load
- Analysis settings managed by controller
- UI construction stays in view
- Settings persistence in view
- View coordination in MainWindow
- Result display formatting
- Session management
- Error handling for save/load/simulation
- Dialog integration
- Proper MVC separation

**Key Tests:**
- `test_file_operations_delegated_to_file_controller()` - File delegation
- `test_simulation_operations_delegated_to_simulation_controller()` - Simulation delegation
- `test_canvas_syncs_before_save()` - Pre-save sync
- `test_canvas_syncs_after_load()` - Post-load sync
- `test_view_does_not_contain_business_logic()` - MVC separation
- `test_controllers_do_not_contain_ui_code()` - MVC separation
- `test_model_is_framework_agnostic()` - Pure Python model

### Integration Tests

#### `test_phase4_mvc_integration.py`
Tests complete MVC workflows end-to-end:
- File operations through controllers
- Simulation through controllers
- Circuit operations through controllers
- Data flow between layers

**Test Coverage:**
- Save/load roundtrip through FileController
- Session persistence
- Simulation controller integration
- Analysis type switching
- Component CRUD through CircuitController
- Model independence
- Controller model sharing
- Model serialization/deserialization
- Error propagation
- Backward compatibility with Phase 3
- Complete workflows

**Key Tests:**
- `test_save_load_roundtrip_through_controllers()` - Full save/load cycle
- `test_simulation_controller_integration()` - Simulation integration
- `test_controller_shares_model_reference()` - Shared model pattern
- `test_complete_save_simulate_load_workflow()` - Complete workflow
- `test_phase3_models_work_with_phase4_controllers()` - Backward compat

## Running the Tests

### Run All Tests
```bash
cd /home/jeremy/Documents/SDSMT/sr_design/Spice-GUI
pytest app/tests/ -v
```

### Run Unit Tests Only
```bash
pytest app/tests/unit/ -v
```

### Run Integration Tests Only
```bash
pytest app/tests/integration/ -v
```

### Run Phase 3 Tests
```bash
pytest app/tests/unit/test_phase3_renaming.py -v
```

### Run Phase 4 Tests
```bash
pytest app/tests/unit/test_canvas_sync.py -v
pytest app/tests/unit/test_main_window_mvc.py -v
pytest app/tests/integration/test_phase4_mvc_integration.py -v
```

### Run with Coverage
```bash
pytest app/tests/ --cov=app --cov-report=html
```

## Test Dependencies

The tests require:
- pytest
- pytest-cov (for coverage reports)
- unittest.mock (included in Python standard library)

Install with:
```bash
pip install pytest pytest-cov
```

## Test Fixtures

The tests use fixtures defined in `conftest.py`:
- `simple_resistor_circuit` - V1 -- R1 -- GND
- `resistor_divider_circuit` - V1+ -- R1 -- R2 -- GND

These fixtures provide:
- `components` - Dictionary of ComponentData objects
- `wires` - List of WireData objects
- `nodes` - List of NodeData objects
- `terminal_to_node` - Terminal-to-node mapping

## Coverage Goals

### Phase 3 Coverage
- ✅ Backward compatibility aliases
- ✅ Module exports
- ✅ Import patterns
- ✅ WireData integration
- ✅ Component hierarchy

### Phase 4 Coverage
- ✅ MainWindow MVC structure
- ✅ Controller delegation
- ✅ Canvas synchronization
- ✅ File operations
- ✅ Simulation operations
- ✅ Session management
- ✅ Error handling
- ✅ MVC separation of concerns
- ✅ Complete workflows

## Known Limitations

1. **Qt Dependencies**: Some tests mock Qt objects since they can't be instantiated without a QApplication. The actual Qt integration is tested manually.

2. **ngspice Execution**: Simulation tests verify controller logic but don't run actual ngspice simulations (would require ngspice installation).

3. **GUI Interaction**: User interaction tests (clicking buttons, dialogs) are not included as they require GUI testing frameworks.

## Future Test Additions

Potential areas for additional testing:
- Qt integration tests using pytest-qt
- GUI interaction tests
- Performance tests for large circuits
- Stress tests for model synchronization
- More edge cases for error handling

## Test Maintenance

When modifying code:
1. Run affected tests to ensure no regressions
2. Update tests if interfaces change
3. Add new tests for new features
4. Keep test documentation current

## Continuous Integration

These tests are suitable for CI/CD pipelines:
```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest app/tests/ -v --cov=app --cov-report=xml
```

## Test Results

All tests should pass with Phase 3 and Phase 4 complete:
- ✅ Backward compatibility maintained
- ✅ MVC architecture properly implemented
- ✅ Controllers handle business logic
- ✅ Views handle UI concerns
- ✅ Model remains framework-agnostic
- ✅ Synchronization works bidirectionally
- ✅ Error handling propagates correctly
