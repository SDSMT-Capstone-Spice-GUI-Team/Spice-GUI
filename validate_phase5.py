#!/usr/bin/env python3
"""
Phase 5 Validation Script - Check observer pattern implementation
without requiring Qt or GUI dependencies.
"""

import sys
import os

sys.path.insert(0, 'app')

def validate_phase5():
    """Validate Phase 5 observer pattern implementation"""
    errors = []
    successes = []

    # Test 1: Check CircuitController has observer methods
    try:
        from controllers.circuit_controller import CircuitController
        ctrl = CircuitController()
        assert hasattr(ctrl, 'add_observer'), "Missing add_observer method"
        assert hasattr(ctrl, 'remove_observer'), "Missing remove_observer method"
        assert hasattr(ctrl, '_notify'), "Missing _notify method"
        successes.append("✅ CircuitController observer pattern OK")
    except Exception as e:
        errors.append(f"❌ CircuitController error: {e}")

    # Test 2: Check FileController accepts circuit_ctrl parameter
    try:
        from controllers.file_controller import FileController
        from models.circuit import CircuitModel
        model = CircuitModel()
        ctrl = CircuitController(model)
        file_ctrl = FileController(model, ctrl)
        assert file_ctrl.circuit_ctrl is ctrl, "circuit_ctrl not stored"
        successes.append("✅ FileController accepts circuit_ctrl parameter")
    except Exception as e:
        errors.append(f"❌ FileController error: {e}")

    # Test 3: Check SimulationController accepts circuit_ctrl parameter
    try:
        from controllers.simulation_controller import SimulationController
        sim_ctrl = SimulationController(model, ctrl)
        assert sim_ctrl.circuit_ctrl is ctrl, "circuit_ctrl not stored"
        successes.append("✅ SimulationController accepts circuit_ctrl parameter")
    except Exception as e:
        errors.append(f"❌ SimulationController error: {e}")

    # Test 4: Verify sync methods are gone from canvas (check source code)
    try:
        with open('app/GUI/circuit_canvas.py', 'r') as f:
            content = f.read()
            assert 'def sync_to_model(' not in content, "sync_to_model still exists"
            assert 'def sync_from_model(' not in content, "sync_from_model still exists"
        successes.append("✅ Sync methods deleted from circuit_canvas.py")
    except Exception as e:
        errors.append(f"❌ Sync methods check error: {e}")

    # Test 5: Verify no sync calls in MainWindow
    try:
        with open('app/GUI/main_window.py', 'r') as f:
            content = f.read()
            assert '.sync_to_model(' not in content, "sync_to_model calls still exist"
            assert '.sync_from_model(' not in content, "sync_from_model calls still exist"
        successes.append("✅ All sync calls removed from MainWindow")
    except Exception as e:
        errors.append(f"❌ MainWindow sync calls check error: {e}")

    # Test 6: Check Node helper methods exist
    try:
        with open('app/GUI/circuit_node.py', 'r') as f:
            content = f.read()
            assert 'def from_node_data' in content, "from_node_data method missing"
            assert 'def matches_node_data' in content, "matches_node_data method missing"
        successes.append("✅ Node helper methods exist")
    except Exception as e:
        errors.append(f"❌ Node helper methods error: {e}")

    # Test 7: Check observer events documented in CircuitController
    try:
        with open('app/controllers/circuit_controller.py', 'r') as f:
            content = f.read()
            assert 'model_loaded' in content, "model_loaded event not documented"
            assert 'model_saved' in content, "model_saved event not documented"
            assert 'simulation_started' in content, "simulation_started event not documented"
            assert 'simulation_completed' in content, "simulation_completed event not documented"
        successes.append("✅ New observer events documented")
    except Exception as e:
        errors.append(f"❌ Observer events documentation error: {e}")

    # Test 8: Check observer pattern works
    try:
        from controllers.circuit_controller import CircuitController
        from models.circuit import ComponentData

        model = CircuitModel()
        ctrl = CircuitController(model)

        events_received = []
        def observer_callback(event, data):
            events_received.append(event)

        ctrl.add_observer(observer_callback)
        ctrl.add_component('Resistor', (100, 200))

        assert 'component_added' in events_received, "Observer not notified"
        successes.append("✅ Observer pattern functional")
    except Exception as e:
        errors.append(f"❌ Observer pattern test error: {e}")

    # Print results
    print("\n" + "="*60)
    print("Phase 5 Validation Results")
    print("="*60 + "\n")

    for success in successes:
        print(success)

    if errors:
        print("\n" + "-"*60)
        for error in errors:
            print(error)
        print("-"*60)

    print(f"\n✅ {len(successes)} checks passed")
    if errors:
        print(f"❌ {len(errors)} checks failed")
        return False
    else:
        print("\n🎉 Phase 5 implementation validated successfully!")
        return True

if __name__ == "__main__":
    success = validate_phase5()
    sys.exit(0 if success else 1)
