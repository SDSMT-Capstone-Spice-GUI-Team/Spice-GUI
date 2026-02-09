#!/usr/bin/env python3
"""
Simple test runner for Phase 3 and Phase 4 tests
Verifies basic functionality without requiring pytest installation
"""
import sys
import traceback
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

def test_phase3_backward_compatibility():
    """Test Phase 3 backward compatibility"""
    print("\n=== Testing Phase 3 Backward Compatibility ===")

    tests_passed = 0
    tests_failed = 0

    # Test 1: ComponentItem alias
    try:
        from GUI.component_item import ComponentGraphicsItem, ComponentItem
        assert ComponentItem is ComponentGraphicsItem, "ComponentItem should be alias"
        print("✓ ComponentItem backward compatibility")
        tests_passed += 1
    except Exception as e:
        print(f"✗ ComponentItem backward compatibility: {e}")
        tests_failed += 1

    # Test 2: WireItem alias
    try:
        from GUI.wire_item import WireGraphicsItem, WireItem
        assert WireItem is WireGraphicsItem, "WireItem should be alias"
        print("✓ WireItem backward compatibility")
        tests_passed += 1
    except Exception as e:
        print(f"✗ WireItem backward compatibility: {e}")
        tests_failed += 1

    # Test 3: CircuitCanvas alias
    try:
        from GUI.circuit_canvas import CircuitCanvasView, CircuitCanvas
        assert CircuitCanvas is CircuitCanvasView, "CircuitCanvas should be alias"
        print("✓ CircuitCanvas backward compatibility")
        tests_passed += 1
    except Exception as e:
        print(f"✗ CircuitCanvas backward compatibility: {e}")
        tests_failed += 1

    # Test 4: GUI module exports
    try:
        from GUI import (
            ComponentGraphicsItem,
            WireGraphicsItem,
            CircuitCanvasView,
            CircuitCanvas,
            WireItem
        )
        assert CircuitCanvas is CircuitCanvasView
        assert WireItem is WireGraphicsItem
        print("✓ GUI module exports both old and new names")
        tests_passed += 1
    except Exception as e:
        print(f"✗ GUI module exports: {e}")
        tests_failed += 1

    # Test 5: App module exports
    try:
        import app
        assert hasattr(app, 'MainWindow'), "app should export MainWindow"
        assert hasattr(app, 'ComponentGraphicsItem'), "app should export ComponentGraphicsItem"
        assert hasattr(app, 'CircuitCanvasView'), "app should export CircuitCanvasView"
        print("✓ App module exports MainWindow and view classes")
        tests_passed += 1
    except Exception as e:
        print(f"✗ App module exports: {e}")
        tests_failed += 1

    # Test 6: WireData integration
    try:
        from models.wire import WireData
        wire_data = WireData(
            start_component_id='R1',
            start_terminal=0,
            end_component_id='R2',
            end_terminal=0,
            algorithm='astar'
        )
        assert wire_data.start_component_id == 'R1'
        print("✓ WireData model backing works")
        tests_passed += 1
    except Exception as e:
        print(f"✗ WireData integration: {e}")
        tests_failed += 1

    print(f"\nPhase 3 Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_phase4_mvc_structure():
    """Test Phase 4 MVC structure"""
    print("\n=== Testing Phase 4 MVC Structure ===")

    tests_passed = 0
    tests_failed = 0

    # Test 1: MainWindow imports
    try:
        from GUI.main_window import MainWindow
        print("✓ MainWindow can be imported")
        tests_passed += 1
    except Exception as e:
        print(f"✗ MainWindow import: {e}")
        tests_failed += 1

    # Test 2: Model exists
    try:
        from models.circuit import CircuitModel
        model = CircuitModel()
        assert hasattr(model, 'components')
        assert hasattr(model, 'wires')
        print("✓ CircuitModel structure correct")
        tests_passed += 1
    except Exception as e:
        print(f"✗ CircuitModel: {e}")
        tests_failed += 1

    # Test 3: Controllers exist
    try:
        from controllers.circuit_controller import CircuitController
        from controllers.file_controller import FileController
        from controllers.simulation_controller import SimulationController
        print("✓ All controllers can be imported")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Controller imports: {e}")
        tests_failed += 1

    # Test 4: FileController functionality
    try:
        from controllers.file_controller import FileController
        from models.circuit import CircuitModel

        model = CircuitModel()
        file_ctrl = FileController(model)

        assert hasattr(file_ctrl, 'save_circuit')
        assert hasattr(file_ctrl, 'load_circuit')
        assert hasattr(file_ctrl, 'new_circuit')
        assert hasattr(file_ctrl, 'load_last_session')
        print("✓ FileController has expected methods")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FileController methods: {e}")
        tests_failed += 1

    # Test 5: SimulationController functionality
    try:
        from controllers.simulation_controller import SimulationController
        from models.circuit import CircuitModel

        model = CircuitModel()
        sim_ctrl = SimulationController(model)

        assert hasattr(sim_ctrl, 'run_simulation')
        assert hasattr(sim_ctrl, 'generate_netlist')
        assert hasattr(sim_ctrl, 'set_analysis')
        print("✓ SimulationController has expected methods")
        tests_passed += 1
    except Exception as e:
        print(f"✗ SimulationController methods: {e}")
        tests_failed += 1

    # Test 6: Model serialization
    try:
        from models.circuit import CircuitModel
        from models.component import ComponentData

        model = CircuitModel()
        model.components = {
            'R1': ComponentData('R1', 'Resistor', '1k', (0, 0))
        }

        data = model.to_dict()
        assert 'components' in data
        assert len(data['components']) == 1

        restored = CircuitModel.from_dict(data)
        assert len(restored.components) == 1
        print("✓ Model serialization roundtrip works")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Model serialization: {e}")
        tests_failed += 1

    # Test 7: Controller model sharing
    try:
        from models.circuit import CircuitModel
        from controllers.file_controller import FileController
        from controllers.simulation_controller import SimulationController

        model = CircuitModel()
        file_ctrl = FileController(model)
        sim_ctrl = SimulationController(model)

        assert file_ctrl.model is model
        assert sim_ctrl.model is model
        print("✓ Controllers share model reference")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Controller model sharing: {e}")
        tests_failed += 1

    print(f"\nPhase 4 Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def test_mvc_separation():
    """Test MVC separation of concerns"""
    print("\n=== Testing MVC Separation ===")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Controllers don't import Qt
    try:
        import controllers.file_controller as fc
        import controllers.simulation_controller as sc
        import controllers.circuit_controller as cc

        # Check that QtWidgets is not in module namespace
        assert 'QtWidgets' not in dir(fc), "FileController should not import QtWidgets"
        assert 'QtWidgets' not in dir(sc), "SimulationController should not import QtWidgets"
        assert 'QtWidgets' not in dir(cc), "CircuitController should not import QtWidgets"
        print("✓ Controllers don't import Qt")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Controller Qt separation: {e}")
        tests_failed += 1

    # Test 2: Model is framework-agnostic
    try:
        from models.circuit import CircuitModel
        from models.component import ComponentData
        from models.wire import WireData
        import inspect

        # Check that model classes don't inherit from Qt
        for cls in [CircuitModel, ComponentData, WireData]:
            bases = inspect.getmro(cls)
            base_names = [b.__name__ for b in bases]
            assert 'QObject' not in base_names, f"{cls.__name__} should not inherit from QObject"

        print("✓ Model is framework-agnostic")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Model framework agnostic: {e}")
        tests_failed += 1

    print(f"\nMVC Separation Results: {tests_passed} passed, {tests_failed} failed")
    return tests_passed, tests_failed


def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 3 & Phase 4 Test Runner")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    try:
        # Phase 3 tests
        passed, failed = test_phase3_backward_compatibility()
        total_passed += passed
        total_failed += failed

        # Phase 4 tests
        passed, failed = test_phase4_mvc_structure()
        total_passed += passed
        total_failed += failed

        # MVC separation tests
        passed, failed = test_mvc_separation()
        total_passed += passed
        total_failed += failed

    except Exception as e:
        print(f"\n✗ Test runner error: {e}")
        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 60)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if total_failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {total_failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
