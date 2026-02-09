"""Tests for copy/paste/cut functionality in CircuitController."""

import pytest
from controllers.circuit_controller import CircuitController
from models.clipboard import ClipboardData
from models.node import reset_node_counter


@pytest.fixture(autouse=True)
def reset_nodes():
    reset_node_counter()


@pytest.fixture
def controller():
    return CircuitController()


@pytest.fixture
def events():
    recorded = []

    def callback(event, data):
        recorded.append((event, data))

    return recorded, callback


@pytest.fixture
def two_resistor_circuit(controller):
    """Create a circuit with R1-R2 connected by a wire."""
    controller.add_component("Resistor", (0.0, 0.0))
    controller.add_component("Resistor", (100.0, 0.0))
    controller.add_wire("R1", 1, "R2", 0)
    return controller


class TestClipboardData:
    def test_empty_clipboard(self):
        cb = ClipboardData()
        assert cb.is_empty()
        assert cb.paste_count == 0

    def test_non_empty_clipboard(self):
        cb = ClipboardData(components=[{'id': 'R1'}])
        assert not cb.is_empty()


class TestCopyComponents:
    def test_copy_single_component(self, controller):
        controller.add_component("Resistor", (50.0, 50.0))
        result = controller.copy_components(["R1"])
        assert result is True
        assert controller.has_clipboard_content()

    def test_copy_empty_list_returns_false(self, controller):
        result = controller.copy_components([])
        assert result is False

    def test_copy_nonexistent_id_returns_false(self, controller):
        result = controller.copy_components(["R999"])
        assert result is False

    def test_copy_preserves_component_data(self, controller):
        controller.add_component("Resistor", (50.0, 75.0))
        controller.update_component_value("R1", "10k")
        controller.rotate_component("R1")
        controller.copy_components(["R1"])
        assert len(controller._clipboard.components) == 1
        comp = controller._clipboard.components[0]
        assert comp['value'] == '10k'
        assert comp['rotation'] == 90

    def test_copy_multiple_components(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        result = ctrl.copy_components(["R1", "R2"])
        assert result is True
        assert len(ctrl._clipboard.components) == 2

    def test_copy_includes_internal_wires(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])
        assert len(ctrl._clipboard.wires) == 1
        wire = ctrl._clipboard.wires[0]
        assert wire['start_comp'] == 'R1'
        assert wire['end_comp'] == 'R2'

    def test_copy_excludes_external_wires(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        # Only copy R1 -- the wire to R2 should NOT be included
        ctrl.copy_components(["R1"])
        assert len(ctrl._clipboard.wires) == 0

    def test_copy_resets_paste_count(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.paste_components()
        assert controller._clipboard.paste_count == 1
        # Copy again should reset
        controller.copy_components(["R1"])
        assert controller._clipboard.paste_count == 0


class TestPasteComponents:
    def test_paste_empty_clipboard(self, controller):
        new_comps, new_wires = controller.paste_components()
        assert new_comps == []
        assert new_wires == []

    def test_paste_creates_new_ids(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert len(new_comps) == 1
        assert new_comps[0].component_id == "R2"
        assert new_comps[0].component_id != "R1"

    def test_paste_offsets_position(self, controller):
        controller.add_component("Resistor", (100.0, 200.0))
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].position == (140.0, 240.0)

    def test_paste_multiple_times_increments_offset(self, controller):
        controller.add_component("Resistor", (100.0, 100.0))
        controller.copy_components(["R1"])

        comps1, _ = controller.paste_components()
        assert comps1[0].position == (140.0, 140.0)

        comps2, _ = controller.paste_components()
        assert comps2[0].position == (180.0, 180.0)
        assert comps2[0].component_id == "R3"

    def test_paste_preserves_rotation_and_value(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.update_component_value("R1", "4.7k")
        controller.rotate_component("R1")  # 90 degrees
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].value == "4.7k"
        assert new_comps[0].rotation == 90

    def test_paste_remaps_wire_ids(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])
        new_comps, new_wires = ctrl.paste_components()
        assert len(new_wires) == 1
        wire = new_wires[0]
        new_ids = {c.component_id for c in new_comps}
        assert wire.start_component_id in new_ids
        assert wire.end_component_id in new_ids
        # Old IDs should NOT appear
        assert wire.start_component_id not in {"R1", "R2"}
        assert wire.end_component_id not in {"R1", "R2"}

    def test_paste_fires_observer_events(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.add_observer(callback)
        controller.paste_components()
        comp_events = [e for e in recorded if e[0] == 'component_added']
        assert len(comp_events) == 1

    def test_paste_adds_to_model(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.paste_components()
        assert "R1" in controller.model.components
        assert "R2" in controller.model.components
        assert len(controller.model.components) == 2

    def test_paste_waveform_source(self, controller):
        controller.add_component("Waveform Source", (0.0, 0.0))
        controller.copy_components(["VW1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].component_type == "Waveform Source"
        assert new_comps[0].waveform_type is not None

    def test_paste_multiple_components_with_wire(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])
        new_comps, new_wires = ctrl.paste_components()
        assert len(new_comps) == 2
        assert len(new_wires) == 1
        # Verify model has all 4 components and 2 wires
        assert len(ctrl.model.components) == 4
        assert len(ctrl.model.wires) == 2


class TestCutComponents:
    def test_cut_copies_and_deletes(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        result = controller.cut_components(["R1"])
        assert result is True
        assert controller.has_clipboard_content()
        assert "R1" not in controller.model.components
        assert ('component_removed', 'R1') in recorded

    def test_cut_then_paste(self, controller):
        controller.add_component("Resistor", (50.0, 50.0))
        controller.cut_components(["R1"])
        assert len(controller.model.components) == 0
        new_comps, _ = controller.paste_components()
        assert len(new_comps) == 1
        assert len(controller.model.components) == 1

    def test_cut_empty_list(self, controller):
        assert controller.cut_components([]) is False

    def test_cut_removes_wires_too(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.cut_components(["R1"])
        assert "R1" not in ctrl.model.components
        assert "R2" in ctrl.model.components
        # Wire connecting R1 to R2 should be removed
        assert len(ctrl.model.wires) == 0


class TestNoQtDependencies:
    def test_clipboard_no_pyqt(self):
        import models.clipboard as mod
        source = open(mod.__file__).read()
        assert 'PyQt' not in source
        assert 'QtCore' not in source

    def test_controller_no_pyqt(self):
        import controllers.circuit_controller as mod
        source = open(mod.__file__).read()
        assert 'PyQt' not in source
        assert 'QtCore' not in source
