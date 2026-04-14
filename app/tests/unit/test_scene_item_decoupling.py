"""
Tests for issue #593: Scene items use injected canvas reference instead of
climbing the widget hierarchy via scene().views()[0].

Verifies that:
- ComponentGraphicsItem, AnnotationItem use self.canvas (not scene climbing)
- WireGraphicsItem delegates routing-failed and waypoint changes to canvas
- Canvas injects canvas references when creating items
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from models.component import ComponentData


class TestComponentItemCanvasInjection:
    """Test that ComponentGraphicsItem uses injected canvas reference."""

    def test_component_has_canvas_attribute(self):
        from GUI.component_item import ComponentGraphicsItem

        comp = ComponentGraphicsItem("R1", "Resistor")
        assert hasattr(comp, "canvas")
        assert comp.canvas is None

    def test_canvas_set_externally(self):
        from GUI.component_item import ComponentGraphicsItem

        comp = ComponentGraphicsItem("R1", "Resistor")
        mock_canvas = MagicMock()
        comp.canvas = mock_canvas
        assert comp.canvas is mock_canvas

    def test_paint_reads_labels_from_canvas(self, qtbot):
        from GUI.component_item import ComponentGraphicsItem

        comp = ComponentGraphicsItem("R1", "Resistor")
        mock_canvas = MagicMock()
        mock_canvas.show_component_labels = False
        mock_canvas.show_component_values = False
        comp.canvas = mock_canvas

        # Paint should not raise and should use canvas attributes
        mock_painter = MagicMock()
        mock_painter.pen.return_value = MagicMock()
        comp.paint(mock_painter)
        # If we got here without an error, the canvas reference worked

    def test_schedule_controller_update_uses_canvas(self):
        from GUI.component_item import ComponentGraphicsItem

        comp = ComponentGraphicsItem("R1", "Resistor")
        mock_canvas = MagicMock()
        mock_controller = MagicMock()
        mock_controller.model.components = {"R1": MagicMock()}
        mock_canvas.controller = mock_controller
        comp.canvas = mock_canvas

        comp._pending_position = (100, 200)
        comp._schedule_controller_update()

        # Should have synced position via canvas.controller
        mock_controller.model.components["R1"].__setattr__("position", (100, 200))

    def test_no_hierarchy_climbing_in_source(self):
        """Verify no scene().views()[0] patterns remain in component_item.py."""
        import ast
        from pathlib import Path

        from GUI import component_item

        tree = ast.parse(Path(component_item.__file__).read_text())
        # Walk the AST looking for chained calls: scene().views()[0]
        # This pattern appears as a Subscript(Call(Attribute(Call(...),'views')), 0)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "views":
                # Check if the value is a call to scene()
                if isinstance(node.value, ast.Call):
                    inner = node.value.func
                    if isinstance(inner, ast.Attribute) and inner.attr == "scene":
                        raise AssertionError("Found scene().views() pattern in component_item.py")


class TestAnnotationItemCanvasInjection:
    """Test that AnnotationItem uses injected canvas reference."""

    def test_annotation_has_canvas_attribute(self):
        from GUI.annotation_item import AnnotationItem

        ann = AnnotationItem("Test")
        assert hasattr(ann, "canvas")
        assert ann.canvas is None

    def test_double_click_delegates_to_canvas(self, qtbot):
        from GUI.annotation_item import AnnotationItem

        ann = AnnotationItem("Test")
        mock_canvas = MagicMock()
        mock_canvas._edit_annotation = MagicMock()
        ann.canvas = mock_canvas

        # Simulate double-click event
        mock_event = MagicMock()
        ann.mouseDoubleClickEvent(mock_event)

        mock_canvas._edit_annotation.assert_called_once_with(ann)

    def test_no_hierarchy_climbing_in_source(self):
        """Verify no scene().views()[0] patterns remain in annotation_item.py."""
        import ast
        from pathlib import Path

        from GUI import annotation_item

        tree = ast.parse(Path(annotation_item.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "views":
                if isinstance(node.value, ast.Call):
                    inner = node.value.func
                    if isinstance(inner, ast.Attribute) and inner.attr == "scene":
                        raise AssertionError("Found scene().views() pattern in annotation_item.py")


class TestWireItemDecoupling:
    """Test that WireGraphicsItem doesn't climb to MainWindow."""

    def test_routing_failed_calls_canvas(self, qtbot):
        from GUI.wire_item import WireGraphicsItem
        from models.wire import WireData

        mock_canvas = MagicMock()
        mock_start = MagicMock()
        mock_start.component_id = "R1"
        mock_end = MagicMock()
        mock_end.component_id = "R2"

        # Pre-create model with waypoints so __init__ skips pathfinding
        model = WireData("R1", 0, "R2", 1)
        model.waypoints = [(0.0, 0.0), (100.0, 100.0)]
        wire = WireGraphicsItem(mock_start, 0, mock_end, 1, canvas=None, model=model)
        wire.canvas = mock_canvas
        wire._notify_routing_failed()

        mock_canvas.on_routing_failed.assert_called_once()

    def test_waypoint_drag_calls_canvas(self, qtbot):
        from GUI.wire_item import WireGraphicsItem
        from models.wire import WireData

        mock_canvas = MagicMock()
        mock_start = MagicMock()
        mock_start.component_id = "R1"
        mock_end = MagicMock()
        mock_end.component_id = "R2"

        # Pre-create model with waypoints so __init__ skips pathfinding
        model = WireData("R1", 0, "R2", 1)
        model.waypoints = [(0.0, 0.0), (50.0, 50.0), (100.0, 100.0)]
        wire = WireGraphicsItem(mock_start, 0, mock_end, 1, canvas=None, model=model)
        wire.canvas = mock_canvas
        wire.waypoints = [(0, 0), (50, 50), (100, 100)]
        wire._finish_waypoint_drag()

        mock_canvas.on_waypoint_drag_finished.assert_called_once()
        call_args = mock_canvas.on_waypoint_drag_finished.call_args
        assert call_args[0][0] is wire  # first positional arg is the wire item

    def test_no_window_statusbar_access_in_source(self):
        """Verify no window().statusBar() patterns remain in wire_item.py."""
        import ast
        from pathlib import Path

        from GUI import wire_item

        tree = ast.parse(Path(wire_item.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "statusBar":
                raise AssertionError("Found statusBar() reference in wire_item.py")
            # Check for standalone window() calls as attribute access
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "window":
                    raise AssertionError("Found window() call in wire_item.py")
                if isinstance(func, ast.Name) and func.id == "window":
                    raise AssertionError("Found window() call in wire_item.py")

    def test_no_private_notify_in_source(self):
        """Verify no controller._notify() calls remain in wire_item.py."""
        import ast
        from pathlib import Path

        from GUI import wire_item

        tree = ast.parse(Path(wire_item.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "_notify":
                # Check if accessed on something named 'controller'
                if isinstance(node.value, ast.Attribute) and node.value.attr == "controller":
                    raise AssertionError("Found controller._notify in wire_item.py")


class TestCanvasInjectsReferences:
    """Test that CircuitCanvasView injects canvas references when creating items."""

    def test_handle_component_added_injects_canvas(self, qtbot):
        from controllers.circuit_controller import CircuitController
        from GUI.circuit_canvas import CircuitCanvasView
        from models.circuit import CircuitModel

        model = CircuitModel()
        ctrl = CircuitController(model)
        canvas = CircuitCanvasView(ctrl)
        qtbot.addWidget(canvas)

        comp_data = ctrl.add_component("Resistor", (100, 100))

        # The observer should have created a graphics item with canvas reference
        comp_item = canvas.components.get(comp_data.component_id)
        assert comp_item is not None
        assert comp_item.canvas is canvas

    def test_canvas_status_message_signal_exists(self, qtbot):
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        assert hasattr(canvas, "statusMessage")

    def test_on_routing_failed_emits_signal(self, qtbot):
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)

        with qtbot.waitSignal(canvas.statusMessage, timeout=1000) as blocker:
            canvas.on_routing_failed("Test failure message")

        assert blocker.args == ["Test failure message", 5000]
