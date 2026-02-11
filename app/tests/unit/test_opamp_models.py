"""Tests for real op-amp model support (#234).

Verifies that the op-amp component supports model selection
(Ideal, LM741, TL081, LM358) and that each model produces the
correct SPICE subcircuit in the generated netlist.
"""

import inspect

import pytest
from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from models.component import DEFAULT_VALUES, OPAMP_MODELS, OPAMP_SUBCIRCUITS


class TestOpampModelConstants:
    """Test op-amp model definitions."""

    def test_opamp_models_list_exists(self):
        """OPAMP_MODELS should be defined."""
        assert isinstance(OPAMP_MODELS, list)

    def test_opamp_models_contains_ideal(self):
        """Ideal should be an available model."""
        assert "Ideal" in OPAMP_MODELS

    def test_opamp_models_contains_lm741(self):
        """LM741 should be an available model."""
        assert "LM741" in OPAMP_MODELS

    def test_opamp_models_contains_tl081(self):
        """TL081 should be an available model."""
        assert "TL081" in OPAMP_MODELS

    def test_opamp_models_contains_lm358(self):
        """LM358 should be an available model."""
        assert "LM358" in OPAMP_MODELS

    def test_opamp_subcircuits_match_models(self):
        """Every model in OPAMP_MODELS should have a subcircuit definition."""
        for model in OPAMP_MODELS:
            assert model in OPAMP_SUBCIRCUITS, f"Missing subcircuit for {model}"

    def test_opamp_default_value_is_ideal(self):
        """Default op-amp value should be 'Ideal'."""
        assert DEFAULT_VALUES["Op-Amp"] == "Ideal"


class TestOpampSubcircuitDefinitions:
    """Test subcircuit content for each model."""

    def test_ideal_subcircuit_has_high_gain(self):
        """Ideal model should have very high gain (1e6)."""
        subckt = OPAMP_SUBCIRCUITS["Ideal"]
        assert "1e6" in subckt
        assert ".subckt OPAMP_IDEAL" in subckt
        assert ".ends" in subckt

    def test_lm741_subcircuit_is_valid(self):
        """LM741 subcircuit should have input resistance and bandwidth limiting."""
        subckt = OPAMP_SUBCIRCUITS["LM741"]
        assert ".subckt LM741" in subckt
        assert "Rin" in subckt
        assert ".ends" in subckt

    def test_tl081_subcircuit_has_high_input_impedance(self):
        """TL081 is JFET-input; should have very high input resistance."""
        subckt = OPAMP_SUBCIRCUITS["TL081"]
        assert ".subckt TL081" in subckt
        assert "1e12" in subckt  # JFET input ~1 TOhm
        assert ".ends" in subckt

    def test_lm358_subcircuit_is_valid(self):
        """LM358 subcircuit should be a valid SPICE definition."""
        subckt = OPAMP_SUBCIRCUITS["LM358"]
        assert ".subckt LM358" in subckt
        assert ".ends" in subckt

    def test_all_subcircuits_have_three_ports(self):
        """All subcircuits should define inp, inn, out ports."""
        for model, subckt in OPAMP_SUBCIRCUITS.items():
            first_line = subckt.split("\n")[0]
            assert "inp" in first_line, f"{model} missing inp port"
            assert "inn" in first_line, f"{model} missing inn port"
            assert "out" in first_line, f"{model} missing out port"


class TestOpampNetlistGeneration:
    """Test netlist generation with different op-amp models."""

    def _make_circuit(self, opamp_value="Ideal"):
        """Build a simple inverting amplifier circuit."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        oa = ctrl.add_component("Op-Amp", (200, 0))
        gnd = ctrl.add_component("Ground", (0, 100))
        # Set op-amp model
        oa.value = opamp_value
        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, oa.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(oa.component_id, 2, gnd.component_id, 0)
        return model, ctrl

    def test_ideal_opamp_generates_opamp_ideal(self):
        """Ideal model should reference OPAMP_IDEAL subcircuit."""
        model, ctrl = self._make_circuit("Ideal")
        sim = SimulationController(model, circuit_ctrl=ctrl)
        netlist = sim.generate_netlist()
        assert "OPAMP_IDEAL" in netlist
        assert ".subckt OPAMP_IDEAL" in netlist

    def test_lm741_generates_lm741_subcircuit(self):
        """LM741 model should include LM741 subcircuit definition."""
        model, ctrl = self._make_circuit("LM741")
        sim = SimulationController(model, circuit_ctrl=ctrl)
        netlist = sim.generate_netlist()
        assert ".subckt LM741" in netlist
        assert "LM741" in netlist
        # Should NOT include OPAMP_IDEAL
        assert "OPAMP_IDEAL" not in netlist

    def test_tl081_generates_tl081_subcircuit(self):
        """TL081 model should include TL081 subcircuit definition."""
        model, ctrl = self._make_circuit("TL081")
        sim = SimulationController(model, circuit_ctrl=ctrl)
        netlist = sim.generate_netlist()
        assert ".subckt TL081" in netlist

    def test_lm358_generates_lm358_subcircuit(self):
        """LM358 model should include LM358 subcircuit definition."""
        model, ctrl = self._make_circuit("LM358")
        sim = SimulationController(model, circuit_ctrl=ctrl)
        netlist = sim.generate_netlist()
        assert ".subckt LM358" in netlist

    def test_unknown_model_falls_back_to_ideal(self):
        """Unknown model values should fall back to Ideal."""
        model, ctrl = self._make_circuit("UnknownModel")
        sim = SimulationController(model, circuit_ctrl=ctrl)
        netlist = sim.generate_netlist()
        assert "OPAMP_IDEAL" in netlist

    def test_instance_line_uses_correct_model(self):
        """The X instance line should reference the selected model."""
        model, ctrl = self._make_circuit("LM741")
        sim = SimulationController(model, circuit_ctrl=ctrl)
        netlist = sim.generate_netlist()
        # Find the XOA line
        for line in netlist.split("\n"):
            if line.startswith("XOA"):
                assert line.endswith("LM741"), f"Expected LM741, got: {line}"
                break
        else:
            pytest.fail("No XOA instance line found in netlist")


class TestOpampModelSerialization:
    """Test that op-amp model selection persists through save/load."""

    def test_model_roundtrip(self):
        """Op-amp with LM741 should survive serialize/deserialize."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        oa = ctrl.add_component("Op-Amp", (0, 0))
        oa.value = "LM741"
        data = model.to_dict()
        restored = CircuitModel.from_dict(data)
        oa_restored = restored.components[oa.component_id]
        assert oa_restored.value == "LM741"

    def test_all_models_roundtrip(self):
        """All op-amp models should survive serialization."""
        for model_name in OPAMP_MODELS:
            model = CircuitModel()
            ctrl = CircuitController(model)
            oa = ctrl.add_component("Op-Amp", (0, 0))
            oa.value = model_name
            data = model.to_dict()
            restored = CircuitModel.from_dict(data)
            assert restored.components[oa.component_id].value == model_name


class TestOpampPropertiesPanel:
    """Test properties panel UI for op-amp model selection."""

    def test_properties_panel_has_opamp_combo(self, qtbot):
        """PropertiesPanel should have an opamp_model_combo widget."""
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert hasattr(panel, "opamp_model_combo")

    def test_opamp_combo_has_all_models(self, qtbot):
        """The combo box should contain all OPAMP_MODELS."""
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        items = [panel.opamp_model_combo.itemText(i) for i in range(panel.opamp_model_combo.count())]
        for model in OPAMP_MODELS:
            assert model in items

    def test_opamp_combo_hidden_by_default(self, qtbot):
        """Combo should be hidden when no component is selected."""
        from GUI.properties_panel import PropertiesPanel

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert panel.opamp_model_combo.isHidden()

    def test_opamp_combo_shown_for_opamp(self, qtbot):
        """Combo should be visible when an op-amp is selected."""
        from GUI.properties_panel import PropertiesPanel
        from models.component import ComponentData

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("OA1", "Op-Amp", "Ideal", (0, 0))
        panel.show_component(comp)
        assert not panel.opamp_model_combo.isHidden()

    def test_opamp_combo_hidden_for_resistor(self, qtbot):
        """Combo should be hidden when a non-op-amp is selected."""
        from GUI.properties_panel import PropertiesPanel
        from models.component import ComponentData

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("R1", "Resistor", "1k", (0, 0))
        panel.show_component(comp)
        assert panel.opamp_model_combo.isHidden()

    def test_opamp_combo_reflects_component_value(self, qtbot):
        """Combo should show the component's current model."""
        from GUI.properties_panel import PropertiesPanel
        from models.component import ComponentData

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("OA1", "Op-Amp", "TL081", (0, 0))
        panel.show_component(comp)
        assert panel.opamp_model_combo.currentText() == "TL081"

    def test_opamp_combo_change_emits_signal(self, qtbot):
        """Changing the combo should emit property_changed signal."""
        from GUI.properties_panel import PropertiesPanel
        from models.component import ComponentData

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("OA1", "Op-Amp", "Ideal", (0, 0))
        panel.show_component(comp)

        with qtbot.waitSignal(panel.property_changed, timeout=1000) as blocker:
            panel.opamp_model_combo.setCurrentText("LM741")

        assert blocker.args == ["OA1", "value", "LM741"]

    def test_value_input_hidden_for_opamp(self, qtbot):
        """Value text input should be hidden when op-amp is selected."""
        from GUI.properties_panel import PropertiesPanel
        from models.component import ComponentData

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        comp = ComponentData("OA1", "Op-Amp", "Ideal", (0, 0))
        panel.show_component(comp)
        assert panel.value_input.isHidden()

    def test_value_input_restored_after_opamp(self, qtbot):
        """Value text input should reappear when switching from op-amp to resistor."""
        from GUI.properties_panel import PropertiesPanel
        from models.component import ComponentData

        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        # Show op-amp (hides value_input)
        oa = ComponentData("OA1", "Op-Amp", "Ideal", (0, 0))
        panel.show_component(oa)
        assert panel.value_input.isHidden()
        # Switch to resistor (should restore value_input)
        r = ComponentData("R1", "Resistor", "1k", (0, 0))
        panel.show_component(r)
        assert not panel.value_input.isHidden()
