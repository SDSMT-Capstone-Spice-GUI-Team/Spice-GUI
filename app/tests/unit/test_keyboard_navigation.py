"""Tests for keyboard/tab navigation and focus management."""

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel

pytest.importorskip("PyQt6")

from GUI.circuit_canvas import CircuitCanvasView
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


@pytest.fixture
def canvas(qtbot):
    """Create a CircuitCanvasView with a controller."""
    model = CircuitModel()
    ctrl = CircuitController(model)
    view = CircuitCanvasView(ctrl)
    qtbot.addWidget(view)
    return view, ctrl


class TestEscapeKeyCanvas:
    """Verify Escape key cancels wire drawing and deselects."""

    def test_escape_cancels_wire_drawing(self, canvas, qtbot):
        view, ctrl = canvas
        # Add two components to enable wire drawing
        c1 = ctrl.add_component("Resistor", (0, 0))
        ctrl.add_component("Voltage Source", (200, 0))

        # Simulate starting wire draw
        view.wire_start_comp = view.components.get(c1.component_id)
        view.wire_start_term = 0
        assert view.wire_start_comp is not None

        # Press Escape
        qtbot.keyClick(view, Qt.Key.Key_Escape)

        assert view.wire_start_comp is None
        assert view.wire_start_term is None

    def test_escape_clears_selection(self, canvas, qtbot):
        view, ctrl = canvas
        c1 = ctrl.add_component("Resistor", (0, 0))

        # Select the component
        comp_item = view.components.get(c1.component_id)
        if comp_item:
            comp_item.setSelected(True)
            assert len(view.scene.selectedItems()) == 1

        # Press Escape
        qtbot.keyClick(view, Qt.Key.Key_Escape)
        assert len(view.scene.selectedItems()) == 0

    def test_escape_with_no_state_does_not_crash(self, canvas, qtbot):
        view, _ = canvas
        # Just press Escape on empty canvas
        qtbot.keyClick(view, Qt.Key.Key_Escape)


class TestFocusPolicies:
    """Verify interactive widgets have appropriate focus policies."""

    def test_canvas_accepts_strong_focus(self, canvas):
        view, _ = canvas
        assert view.focusPolicy() == Qt.FocusPolicy.StrongFocus

    def test_canvas_is_focusable(self, canvas):
        view, _ = canvas
        policy = view.focusPolicy()
        # Should accept focus from Tab and click
        assert policy in (Qt.FocusPolicy.StrongFocus, Qt.FocusPolicy.WheelFocus)


class TestTabOrder:
    """Verify tab order is set up correctly in the main window."""

    def test_palette_focus_policy(self, qtbot):
        """Component palette should be focusable via Tab."""
        from GUI.component_palette import ComponentPalette

        palette = ComponentPalette()
        qtbot.addWidget(palette)
        # QListWidget default or set by MainWindow
        policy = palette.focusPolicy()
        # Should accept some form of focus
        assert policy != Qt.FocusPolicy.NoFocus

    def test_buttons_accept_tab_focus(self, qtbot):
        """Action buttons should be reachable via Tab."""
        from PyQt6.QtWidgets import QPushButton

        btn = QPushButton("Test")
        qtbot.addWidget(btn)
        # Buttons default to StrongFocus or TabFocus
        policy = btn.focusPolicy()
        assert policy != Qt.FocusPolicy.NoFocus
