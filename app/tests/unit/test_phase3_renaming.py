"""
Unit tests for Phase 3: Backward Compatibility Aliases

Tests that the renamed classes (ComponentItem → ComponentGraphicsItem,
WireItem → WireGraphicsItem, CircuitCanvas → CircuitCanvasView) maintain
backward compatibility through aliases.
"""
import pytest


def test_component_item_backward_compatibility():
    """Test that ComponentItem is an alias for ComponentGraphicsItem"""
    from GUI.component_item import ComponentGraphicsItem, ComponentItem

    # ComponentItem should be the same class as ComponentGraphicsItem
    assert ComponentItem is ComponentGraphicsItem
    assert ComponentItem.__name__ == 'ComponentGraphicsItem'


def test_wire_item_backward_compatibility():
    """Test that WireItem is an alias for WireGraphicsItem"""
    from GUI.wire_item import WireGraphicsItem, WireItem

    # WireItem should be the same class as WireGraphicsItem
    assert WireItem is WireGraphicsItem
    assert WireItem.__name__ == 'WireGraphicsItem'


def test_circuit_canvas_backward_compatibility():
    """Test that CircuitCanvas is an alias for CircuitCanvasView"""
    from GUI.circuit_canvas import CircuitCanvasView, CircuitCanvas

    # CircuitCanvas should be the same class as CircuitCanvasView
    assert CircuitCanvas is CircuitCanvasView
    assert CircuitCanvas.__name__ == 'CircuitCanvasView'


def test_gui_module_exports_both_names():
    """Test that GUI.__init__ exports both old and new names"""
    from GUI import (
        ComponentGraphicsItem,
        WireGraphicsItem,
        CircuitCanvasView,
        CircuitCanvas,
        WireItem
    )

    # New names should work
    assert ComponentGraphicsItem is not None
    assert WireGraphicsItem is not None
    assert CircuitCanvasView is not None

    # Old names should still work (backward compatibility)
    assert CircuitCanvas is not None
    assert WireItem is not None

    # Old names should be aliases to new names
    assert CircuitCanvas is CircuitCanvasView
    assert WireItem is WireGraphicsItem


def test_app_module_exports():
    """Test that top-level app module exports the new names"""
    import app

    # Should export MainWindow (new in Phase 4)
    assert hasattr(app, 'MainWindow')
    assert app.MainWindow is not None

    # Should export view classes
    assert hasattr(app, 'ComponentGraphicsItem')
    assert hasattr(app, 'WireGraphicsItem')
    assert hasattr(app, 'CircuitCanvasView')

    # Backward compatibility exports
    assert hasattr(app, 'CircuitCanvas')
    assert hasattr(app, 'WireItem')


def test_wire_data_integration():
    """Test that WireGraphicsItem has WireData model backing"""
    from models.wire import WireData
    from GUI.wire_item import WireGraphicsItem

    # Create a WireData model
    wire_data = WireData(
        start_component_id='R1',
        start_terminal=0,
        end_component_id='R2',
        end_terminal=0,
        algorithm='astar'
    )

    # Verify it has the expected attributes
    assert wire_data.start_component_id == 'R1'
    assert wire_data.start_terminal == 0
    assert wire_data.end_component_id == 'R2'
    assert wire_data.end_terminal == 0
    assert wire_data.algorithm == 'astar'

    # WireGraphicsItem should accept a model parameter
    # (Can't instantiate without Qt, but we can check the signature)
    import inspect
    sig = inspect.signature(WireGraphicsItem.__init__)
    assert 'model' in sig.parameters


def test_component_graphics_item_inheritance():
    """Test that component subclasses work with new name"""
    from GUI.component_item import (
        ComponentGraphicsItem,
        Resistor,
        Capacitor,
        VoltageSource,
        Ground
    )

    # All component types should be subclasses of ComponentGraphicsItem
    assert issubclass(Resistor, ComponentGraphicsItem)
    assert issubclass(Capacitor, ComponentGraphicsItem)
    assert issubclass(VoltageSource, ComponentGraphicsItem)
    assert issubclass(Ground, ComponentGraphicsItem)


def test_import_patterns():
    """Test various import patterns to ensure backward compatibility"""
    # Old-style import should work
    from GUI.wire_item import WireItem as OldWire

    # New-style import should work
    from GUI.wire_item import WireGraphicsItem as NewWire

    # They should be the same class
    assert OldWire is NewWire

    # Same for canvas
    from GUI.circuit_canvas import CircuitCanvas as OldCanvas
    from GUI.circuit_canvas import CircuitCanvasView as NewCanvas
    assert OldCanvas is NewCanvas


def test_phase3_no_functionality_regression():
    """Verify that renaming didn't break basic model operations"""
    from models.component import ComponentData
    from models.wire import WireData
    from models.node import NodeData

    # Create basic model objects
    comp = ComponentData(
        component_id='R1',
        component_type='Resistor',
        value='1k',
        position=(0, 0)
    )

    wire = WireData(
        start_component_id='R1',
        start_terminal=0,
        end_component_id='R2',
        end_terminal=0
    )

    node = NodeData(
        terminals={('R1', 0), ('R2', 0)},
        wire_indices={0}
    )

    # Basic operations should work
    assert comp.component_id == 'R1'
    assert comp.to_dict()['id'] == 'R1'

    assert wire.start_component_id == 'R1'
    assert wire.to_dict()['start_comp'] == 'R1'

    assert len(node.terminals) == 2
    assert ('R1', 0) in node.terminals
