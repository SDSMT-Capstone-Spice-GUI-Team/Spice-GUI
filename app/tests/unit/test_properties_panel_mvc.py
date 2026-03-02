"""
Tests for issue #601: PropertiesPanel routes property changes through controller.

Verifies that:
- PropertiesPanel.configure_waveform() does not directly mutate ComponentData
- CircuitController.update_component_waveform() updates model and notifies
- CircuitController.update_component_initial_condition() updates model and notifies
- MainWindow.on_property_changed() delegates to controller for all property types
"""

import pytest
from controllers.circuit_controller import CircuitController
from models.circuit import CircuitModel
from models.component import ComponentData


class TestControllerWaveformUpdate:
    """Test CircuitController.update_component_waveform()."""

    @pytest.fixture
    def controller_with_waveform(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Waveform Source", (100.0, 100.0))
        return ctrl, comp

    def test_update_waveform_changes_model(self, controller_with_waveform):
        ctrl, comp = controller_with_waveform
        new_params = {
            "v1": "0",
            "v2": "3.3",
            "td": "0",
            "tr": "1n",
            "tf": "1n",
            "pw": "250u",
            "per": "500u",
        }
        ctrl.update_component_waveform(comp.component_id, "PULSE", new_params)

        updated = ctrl.model.components[comp.component_id]
        assert updated.waveform_type == "PULSE"
        assert updated.waveform_params["PULSE"] == new_params
        assert "PULSE" in updated.value

    def test_update_waveform_notifies_observers(self, controller_with_waveform):
        ctrl, comp = controller_with_waveform
        events = []
        ctrl.add_observer(lambda event, data: events.append((event, data)))

        ctrl.update_component_waveform(comp.component_id, "PULSE", {"v1": "0", "v2": "5"})

        value_events = [e for e in events if e[0] == "component_value_changed"]
        assert len(value_events) == 1
        assert value_events[0][1].component_id == comp.component_id

    def test_update_waveform_locked_component_rejected(self, controller_with_waveform):
        ctrl, comp = controller_with_waveform
        ctrl.set_locked_components([comp.component_id])
        original_type = comp.waveform_type

        ctrl.update_component_waveform(comp.component_id, "PULSE", {"v1": "0"})

        assert ctrl.model.components[comp.component_id].waveform_type == original_type

    def test_update_waveform_nonexistent_component(self, controller_with_waveform):
        ctrl, _ = controller_with_waveform
        # Should not raise
        ctrl.update_component_waveform("NONEXISTENT", "PULSE", {})

    def test_update_waveform_updates_spice_value(self, controller_with_waveform):
        ctrl, comp = controller_with_waveform
        sin_params = {
            "offset": "0",
            "amplitude": "10",
            "frequency": "2k",
            "delay": "0",
            "theta": "0",
            "phase": "0",
        }
        ctrl.update_component_waveform(comp.component_id, "SIN", sin_params)

        updated = ctrl.model.components[comp.component_id]
        assert updated.value == updated.get_spice_value()
        assert "10" in updated.value
        assert "2k" in updated.value


class TestControllerInitialConditionUpdate:
    """Test CircuitController.update_component_initial_condition()."""

    @pytest.fixture
    def controller_with_capacitor(self):
        model = CircuitModel()
        ctrl = CircuitController(model)
        comp = ctrl.add_component("Capacitor", (50.0, 50.0))
        return ctrl, comp

    def test_update_initial_condition_changes_model(self, controller_with_capacitor):
        ctrl, comp = controller_with_capacitor
        ctrl.update_component_initial_condition(comp.component_id, "5V")

        updated = ctrl.model.components[comp.component_id]
        assert updated.initial_condition == "5V"

    def test_update_initial_condition_clears_when_none(self, controller_with_capacitor):
        ctrl, comp = controller_with_capacitor
        ctrl.update_component_initial_condition(comp.component_id, "5V")
        ctrl.update_component_initial_condition(comp.component_id, None)

        updated = ctrl.model.components[comp.component_id]
        assert updated.initial_condition is None

    def test_update_initial_condition_notifies_observers(self, controller_with_capacitor):
        ctrl, comp = controller_with_capacitor
        events = []
        ctrl.add_observer(lambda event, data: events.append((event, data)))

        ctrl.update_component_initial_condition(comp.component_id, "3.3")

        value_events = [e for e in events if e[0] == "component_value_changed"]
        assert len(value_events) == 1

    def test_update_initial_condition_locked_component_rejected(self, controller_with_capacitor):
        ctrl, comp = controller_with_capacitor
        ctrl.set_locked_components([comp.component_id])

        ctrl.update_component_initial_condition(comp.component_id, "5V")

        assert ctrl.model.components[comp.component_id].initial_condition is None

    def test_update_initial_condition_nonexistent_component(self, controller_with_capacitor):
        ctrl, _ = controller_with_capacitor
        # Should not raise
        ctrl.update_component_initial_condition("NONEXISTENT", "5V")


class TestPropertiesPanelNoDirectMutation:
    """Verify PropertiesPanel.configure_waveform() does not mutate the model."""

    @pytest.fixture
    def panel(self, qtbot):
        from GUI.properties_panel import PropertiesPanel

        p = PropertiesPanel()
        qtbot.addWidget(p)
        return p

    def test_configure_waveform_emits_signal_only(self, panel, qtbot, monkeypatch):
        """configure_waveform should emit property_changed without mutating current_component."""
        comp = ComponentData(
            component_id="VW1",
            component_type="Waveform Source",
            value="SIN(0 5 1k)",
            position=(0.0, 0.0),
        )
        panel.show_component(comp)

        original_waveform_type = comp.waveform_type
        original_value = comp.value

        # Mock the dialog to return a new waveform config
        mock_dialog_cls = type(
            "MockDialog",
            (),
            {
                "__init__": lambda self, *a, **kw: None,
                "exec": lambda self: True,
                "get_parameters": lambda self: ("PULSE", {"v1": "0", "v2": "3.3"}),
            },
        )
        monkeypatch.setattr("GUI.properties_panel.WaveformConfigDialog", mock_dialog_cls, raising=False)
        # Force the lazy import path to use our mock
        import sys

        import GUI.properties_panel as pp_mod

        # Patch the import inside configure_waveform
        monkeypatch.setitem(sys.modules, "GUI.waveform_config_dialog", type(sys)("mock_mod"))
        sys.modules["GUI.waveform_config_dialog"].WaveformConfigDialog = mock_dialog_cls

        signals = []
        panel.property_changed.connect(lambda *a: signals.append(a))

        panel.configure_waveform()

        # Signal should have been emitted
        assert len(signals) == 1
        assert signals[0] == ("VW1", "waveform", ("PULSE", {"v1": "0", "v2": "3.3"}))

        # Model should NOT have been mutated by the panel
        assert comp.waveform_type == original_waveform_type
        assert comp.value == original_value

    def test_apply_changes_does_not_mutate_value(self, panel):
        """apply_changes should emit signal, not directly set component.value."""
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0.0, 0.0),
        )
        panel.show_component(comp)
        panel.value_input.setText("2k")

        signals = []
        panel.property_changed.connect(lambda *a: signals.append(a))
        panel.apply_changes()

        # Signal should be emitted for controller to handle
        assert len(signals) == 1
        assert signals[0] == ("R1", "value", "2k")

        # The panel should NOT have directly mutated the model
        # (The model still has the old value — controller will update it)
        assert comp.value == "1k"
