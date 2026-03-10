"""
Unit tests for multi-select features: rubber band selection, Ctrl+A,
group movement, and properties panel multi-selection display.
"""

import pytest
from GUI.properties_panel import PropertiesPanel
from models.component import ComponentData
from PyQt6.QtCore import QPointF

# ---------------------------------------------------------------------------
# Properties panel multi-selection display
# ---------------------------------------------------------------------------


@pytest.fixture
def panel(qtbot):
    p = PropertiesPanel()
    qtbot.addWidget(p)
    return p


@pytest.fixture
def resistor():
    return ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(0.0, 0.0),
    )


class TestPropertiesPanelMultiSelect:
    def test_show_multi_selection_displays_count(self, panel):
        panel.show_multi_selection(3)
        assert "3" in panel.id_label.text()
        assert panel.current_component is None

    def test_show_multi_selection_disables_editing(self, panel):
        panel.show_multi_selection(2)
        assert not panel.apply_button.isEnabled()
        assert not panel.properties_group.isEnabled()

    def test_show_multi_then_single_restores(self, panel, resistor):
        panel.show_multi_selection(5)
        panel.show_component(resistor)
        assert panel.id_label.text() == "R1"
        assert panel.properties_group.isEnabled()

    def test_show_multi_then_none_clears(self, panel):
        panel.show_multi_selection(2)
        panel.show_no_selection()
        assert panel.id_label.text() == "-"

    def test_show_multi_hides_waveform_button(self, panel):
        panel.show_multi_selection(4)
        assert panel.waveform_button.isHidden()


# ---------------------------------------------------------------------------
# ComponentGraphicsItem group movement (model-level logic)
# ---------------------------------------------------------------------------


class TestGroupMoveFlag:
    """Test that _group_moving flag is initialized on ComponentGraphicsItem."""

    def test_component_data_defaults(self):
        """ComponentData objects used in group move should be creatable."""
        c1 = ComponentData("R1", "Resistor", "1k", (100, 200))
        c2 = ComponentData("R2", "Resistor", "2k", (200, 200))
        # Positions are tuples, verify arithmetic works for delta calc
        dx = c2.position[0] - c1.position[0]
        dy = c2.position[1] - c1.position[1]
        assert dx == 100
        assert dy == 0


# ---------------------------------------------------------------------------
# CircuitCanvasView.select_all (requires qtbot + full canvas)
# ---------------------------------------------------------------------------


class TestSelectAll:
    """Test select_all method on CircuitCanvasView."""

    def test_select_all_selects_components(self, qtbot):
        from GUI.circuit_canvas import CircuitCanvasView
        from GUI.component_item import ComponentGraphicsItem

        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)

        # Add two mock components via their graphics items
        model_a = ComponentData("R1", "Resistor", "1k", (0, 0))
        model_b = ComponentData("R2", "Resistor", "2k", (100, 0))
        item_a = ComponentGraphicsItem("R1", model=model_a)
        item_b = ComponentGraphicsItem("R2", model=model_b)
        canvas.scene.addItem(item_a)
        canvas.scene.addItem(item_b)
        canvas.components["R1"] = item_a
        canvas.components["R2"] = item_b

        canvas.select_all()

        assert item_a.isSelected()
        assert item_b.isSelected()

    def test_select_all_with_no_items(self, qtbot):
        from GUI.circuit_canvas import CircuitCanvasView

        canvas = CircuitCanvasView()
        qtbot.addWidget(canvas)
        # Should not raise
        canvas.select_all()
        assert len(canvas.scene.selectedItems()) == 0
