"""
Unit tests for PropertiesPanel.

Tests no-selection state, component display, value change handling,
validation feedback, and property_changed signal emission.
"""

import pytest
from GUI.properties_panel import PropertiesPanel
from models.component import ComponentData
from PyQt6.QtCore import Qt


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


@pytest.fixture
def waveform_source():
    return ComponentData(
        component_id="VW1",
        component_type="Waveform Source",
        value="SIN(0 5 1k)",
        position=(0.0, 0.0),
    )


class TestPropertiesPanelNoSelection:
    """Test the no-selection (empty) state."""

    def test_initial_state_shows_no_selection(self, panel):
        assert panel.current_component is None
        assert panel.id_label.text() == "-"
        assert panel.type_label.text() == "-"
        assert not panel.apply_button.isEnabled()

    def test_show_no_selection_clears_fields(self, panel, resistor):
        panel.show_component(resistor)
        panel.show_no_selection()
        assert panel.current_component is None
        assert panel.id_label.text() == "-"

    def test_show_component_none_triggers_no_selection(self, panel, resistor):
        panel.show_component(resistor)
        panel.show_component(None)
        assert panel.current_component is None


class TestPropertiesPanelDisplay:
    """Test component property display."""

    def test_displays_component_id(self, panel, resistor):
        panel.show_component(resistor)
        assert panel.id_label.text() == "R1"

    def test_displays_component_type(self, panel, resistor):
        panel.show_component(resistor)
        assert panel.type_label.text() == "Resistor"

    def test_displays_component_value(self, panel, resistor):
        panel.show_component(resistor)
        assert panel.value_input.text() == "1k"

    def test_waveform_source_value_is_readonly(self, panel, waveform_source):
        panel.show_component(waveform_source)
        assert panel.value_input.isReadOnly()
        assert not panel.waveform_button.isHidden()

    def test_resistor_value_is_editable(self, panel, resistor):
        panel.show_component(resistor)
        assert not panel.value_input.isReadOnly()
        assert panel.waveform_button.isHidden()


class TestPropertiesPanelEditing:
    """Test value editing and apply behavior."""

    def test_value_change_enables_apply(self, panel, resistor):
        panel.show_component(resistor)
        assert not panel.apply_button.isEnabled()
        panel.value_input.setText("2k")
        assert panel.apply_button.isEnabled()

    def test_apply_emits_property_changed(self, panel, resistor, qtbot):
        panel.show_component(resistor)
        panel.value_input.setText("2k")
        with qtbot.waitSignal(panel.property_changed, timeout=1000) as blocker:
            panel.apply_changes()
        assert blocker.args == ["R1", "value", "2k"]

    def test_apply_with_invalid_value_shows_error(self, panel, resistor):
        panel.show_component(resistor)
        panel.value_input.setText("abc_invalid")
        panel.apply_changes()
        assert not panel.error_label.isHidden()

    def test_apply_disables_button_on_success(self, panel, resistor):
        panel.show_component(resistor)
        panel.value_input.setText("2k")
        panel.apply_changes()
        assert not panel.apply_button.isEnabled()

    def test_apply_with_same_value_does_not_emit(self, panel, resistor, qtbot):
        panel.show_component(resistor)
        # Value unchanged — type the same value
        panel.value_input.setText("1k")
        signals = []
        panel.property_changed.connect(lambda *a: signals.append(a))
        panel.apply_changes()
        assert len(signals) == 0
