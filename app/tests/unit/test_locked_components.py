"""Tests for locked components in assignment templates (#378)."""

import json
import tempfile
from pathlib import Path

from controllers.circuit_controller import CircuitController
from controllers.template_controller import TemplateController
from models.circuit import CircuitModel
from models.template import TemplateData, TemplateMetadata
from tests.conftest import make_component, make_wire


class TestLockedComponentsModel:
    """Test locked_components field on TemplateData."""

    def test_template_data_default_no_locked(self):
        t = TemplateData()
        assert t.locked_components == []

    def test_template_data_with_locked(self):
        t = TemplateData(locked_components=["V1", "GND1"])
        assert t.locked_components == ["V1", "GND1"]

    def test_to_dict_includes_locked_when_present(self):
        t = TemplateData(
            metadata=TemplateMetadata(title="Test"),
            locked_components=["R1", "V1"],
        )
        d = t.to_dict()
        assert d["locked_components"] == ["R1", "V1"]

    def test_to_dict_omits_locked_when_empty(self):
        t = TemplateData(metadata=TemplateMetadata(title="Test"))
        d = t.to_dict()
        assert "locked_components" not in d

    def test_from_dict_reads_locked(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": "Test"},
            "instructions": "",
            "locked_components": ["V1", "R1"],
        }
        t = TemplateData.from_dict(data)
        assert t.locked_components == ["V1", "R1"]

    def test_from_dict_defaults_empty_when_missing(self):
        data = {
            "template_version": "1.0",
            "metadata": {"title": "Test"},
            "instructions": "",
        }
        t = TemplateData.from_dict(data)
        assert t.locked_components == []

    def test_roundtrip_serialization(self):
        original = TemplateData(
            metadata=TemplateMetadata(title="Lock Test"),
            locked_components=["V1", "GND1", "R1"],
        )
        d = original.to_dict()
        restored = TemplateData.from_dict(d)
        assert restored.locked_components == original.locked_components


class TestLockedComponentsController:
    """Test lock enforcement in CircuitController."""

    def _make_controller_with_components(self):
        model = CircuitModel()
        v1 = make_component("Voltage Source", "V1", "5V", (0, 0))
        r1 = make_component("Resistor", "R1", "1k", (100, 0))
        gnd = make_component("Ground", "GND1", "0V", (100, 100))
        model.add_component(v1)
        model.add_component(r1)
        model.add_component(gnd)
        model.add_wire(make_wire("V1", 0, "R1", 0))
        controller = CircuitController(model=model)
        return controller

    def test_set_and_get_locked_components(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["V1", "GND1"])
        assert ctrl.get_locked_components() == {"V1", "GND1"}

    def test_is_component_locked(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["V1"])
        assert ctrl.is_component_locked("V1") is True
        assert ctrl.is_component_locked("R1") is False

    def test_locked_component_cannot_be_removed(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["V1"])
        ctrl.remove_component("V1")
        # V1 should still exist
        assert "V1" in ctrl.model.components

    def test_unlocked_component_can_be_removed(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["V1"])
        ctrl.remove_component("R1")
        assert "R1" not in ctrl.model.components

    def test_locked_component_cannot_be_rotated(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["R1"])
        original_rotation = ctrl.model.components["R1"].rotation
        ctrl.rotate_component("R1")
        assert ctrl.model.components["R1"].rotation == original_rotation

    def test_locked_component_cannot_be_flipped(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["R1"])
        original_flip = ctrl.model.components["R1"].flip_h
        ctrl.flip_component("R1", horizontal=True)
        assert ctrl.model.components["R1"].flip_h == original_flip

    def test_locked_component_cannot_change_value(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["R1"])
        ctrl.update_component_value("R1", "2k")
        assert ctrl.model.components["R1"].value == "1k"

    def test_locked_component_cannot_be_moved(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["R1"])
        ctrl.move_component("R1", (200, 200))
        assert ctrl.model.components["R1"].position == (100, 0)

    def test_clear_locked_components(self):
        ctrl = self._make_controller_with_components()
        ctrl.set_locked_components(["V1"])
        ctrl.clear_locked_components()
        assert ctrl.is_component_locked("V1") is False
        assert ctrl.get_locked_components() == set()

    def test_locked_components_changed_event(self):
        ctrl = self._make_controller_with_components()
        events = []
        ctrl.add_observer(lambda event, data: events.append((event, data)))
        ctrl.set_locked_components(["V1"])
        assert any(e[0] == "locked_components_changed" for e in events)


class TestLockedComponentsTemplateIO:
    """Test locked_components in template save/load."""

    def test_save_and_load_template_with_locked(self):
        tc = TemplateController()
        model = CircuitModel()
        v1 = make_component("Voltage Source", "V1", "5V", (0, 0))
        model.add_component(v1)

        metadata = TemplateMetadata(title="Locked Test")

        with tempfile.NamedTemporaryFile(suffix=".spice-template", delete=False) as f:
            filepath = f.name

        tc.save_as_template(
            filepath,
            metadata=metadata,
            starter_circuit=model,
            locked_components=["V1"],
        )

        loaded = tc.load_template(filepath)
        assert loaded.locked_components == ["V1"]
        Path(filepath).unlink()

    def test_save_template_without_locked(self):
        tc = TemplateController()
        metadata = TemplateMetadata(title="No Lock Test")

        with tempfile.NamedTemporaryFile(suffix=".spice-template", delete=False) as f:
            filepath = f.name

        tc.save_as_template(filepath, metadata=metadata)
        loaded = tc.load_template(filepath)
        assert loaded.locked_components == []
        Path(filepath).unlink()
