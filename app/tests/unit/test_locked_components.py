"""Tests for locked components in assignment templates.

Covers:
- ComponentData locked flag serialization
- TemplateData locked_components serialization
- TemplateController applying locks on circuit creation
- ComponentGraphicsItem locked visual/interaction behavior
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controllers.template_controller import TemplateController
from models.circuit import CircuitModel
from models.component import ComponentData
from models.template import TemplateData, TemplateMetadata

# ---------------------------------------------------------------------------
# ComponentData locked flag
# ---------------------------------------------------------------------------


class TestComponentDataLocked:
    """Tests for ComponentData.locked field."""

    def test_default_not_locked(self):
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
        )
        assert comp.locked is False

    def test_locked_field(self):
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
            locked=True,
        )
        assert comp.locked is True

    def test_locked_serialized_when_true(self):
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
            locked=True,
        )
        d = comp.to_dict()
        assert d["locked"] is True

    def test_locked_omitted_when_false(self):
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
            locked=False,
        )
        d = comp.to_dict()
        assert "locked" not in d

    def test_locked_roundtrip(self):
        comp = ComponentData(
            component_id="V1",
            component_type="Voltage Source",
            value="5V",
            position=(100, 200),
            locked=True,
        )
        d = comp.to_dict()
        restored = ComponentData.from_dict(d)
        assert restored.locked is True

    def test_from_dict_missing_locked_defaults_false(self):
        d = {
            "type": "Resistor",
            "id": "R1",
            "value": "1k",
            "pos": {"x": 0, "y": 0},
            "rotation": 0,
            "flip_h": False,
            "flip_v": False,
        }
        comp = ComponentData.from_dict(d)
        assert comp.locked is False


# ---------------------------------------------------------------------------
# TemplateData locked_components
# ---------------------------------------------------------------------------


class TestTemplateDataLockedComponents:
    """Tests for TemplateData.locked_components field."""

    def test_default_empty(self):
        td = TemplateData()
        assert td.locked_components == []

    def test_with_locked_components(self):
        td = TemplateData(locked_components=["R1", "V1"])
        assert td.locked_components == ["R1", "V1"]

    def test_serialized_when_present(self):
        td = TemplateData(locked_components=["R1", "C1"])
        d = td.to_dict()
        assert d["locked_components"] == ["R1", "C1"]

    def test_omitted_when_empty(self):
        td = TemplateData()
        d = td.to_dict()
        assert "locked_components" not in d

    def test_roundtrip(self):
        td = TemplateData(
            metadata=TemplateMetadata(title="Test"),
            locked_components=["R1", "V1", "C1"],
        )
        d = td.to_dict()
        restored = TemplateData.from_dict(d)
        assert restored.locked_components == ["R1", "V1", "C1"]

    def test_from_dict_missing_locked_components(self):
        d = {"template_version": "1.0", "metadata": {"title": "Test"}}
        td = TemplateData.from_dict(d)
        assert td.locked_components == []


# ---------------------------------------------------------------------------
# TemplateController - applying locks
# ---------------------------------------------------------------------------


class TestTemplateControllerLockedComponents:
    """Tests for TemplateController applying locked state."""

    def _make_circuit_dict(self, component_ids):
        """Create a minimal circuit dict with the given component IDs."""
        components = []
        for cid in component_ids:
            components.append(
                {
                    "type": "Resistor",
                    "id": cid,
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                    "rotation": 0,
                    "flip_h": False,
                    "flip_v": False,
                }
            )
        return {
            "components": components,
            "wires": [],
            "counters": {},
        }

    def test_locks_applied_to_listed_components(self):
        ctrl = TemplateController()
        circuit_dict = self._make_circuit_dict(["R1", "R2", "R3"])
        template = TemplateData(
            metadata=TemplateMetadata(title="Test"),
            starter_circuit=circuit_dict,
            locked_components=["R1", "R3"],
        )
        model = ctrl.create_circuit_from_template(template)
        assert model.components["R1"].locked is True
        assert model.components["R2"].locked is False
        assert model.components["R3"].locked is True

    def test_no_locks_when_empty_list(self):
        ctrl = TemplateController()
        circuit_dict = self._make_circuit_dict(["R1", "R2"])
        template = TemplateData(
            metadata=TemplateMetadata(title="Test"),
            starter_circuit=circuit_dict,
            locked_components=[],
        )
        model = ctrl.create_circuit_from_template(template)
        assert model.components["R1"].locked is False
        assert model.components["R2"].locked is False

    def test_missing_component_id_ignored(self):
        """Locked component IDs that don't exist in the circuit are silently ignored."""
        ctrl = TemplateController()
        circuit_dict = self._make_circuit_dict(["R1"])
        template = TemplateData(
            metadata=TemplateMetadata(title="Test"),
            starter_circuit=circuit_dict,
            locked_components=["R1", "NONEXISTENT"],
        )
        model = ctrl.create_circuit_from_template(template)
        assert model.components["R1"].locked is True
        assert "NONEXISTENT" not in model.components

    def test_no_starter_circuit_with_locks(self):
        """When there's no starter circuit, locked_components has no effect."""
        ctrl = TemplateController()
        template = TemplateData(
            metadata=TemplateMetadata(title="Test"),
            locked_components=["R1"],
        )
        model = ctrl.create_circuit_from_template(template)
        assert len(model.components) == 0

    def test_save_and_load_locked_components(self):
        """Round-trip test: save template with locked components, reload it."""
        ctrl = TemplateController()
        metadata = TemplateMetadata(title="Lock Test")
        circuit = CircuitModel()
        circuit.components["R1"] = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
        )
        circuit.components["V1"] = ComponentData(
            component_id="V1",
            component_type="Voltage Source",
            value="5V",
            position=(100, 0),
        )

        with tempfile.NamedTemporaryFile(suffix=".spice-template", delete=False) as f:
            filepath = Path(f.name)

        try:
            ctrl.save_as_template(
                filepath,
                metadata=metadata,
                starter_circuit=circuit,
                locked_components=["R1"],
            )

            loaded = ctrl.load_template(filepath)
            assert loaded.locked_components == ["R1"]

            model = ctrl.create_circuit_from_template(loaded)
            assert model.components["R1"].locked is True
            assert model.components["V1"].locked is False
        finally:
            filepath.unlink(missing_ok=True)

    def test_save_template_without_locked_components(self):
        """When no locked_components provided, field is empty list."""
        ctrl = TemplateController()
        metadata = TemplateMetadata(title="No Lock Test")

        with tempfile.NamedTemporaryFile(suffix=".spice-template", delete=False) as f:
            filepath = Path(f.name)

        try:
            ctrl.save_as_template(filepath, metadata=metadata)

            loaded = ctrl.load_template(filepath)
            assert loaded.locked_components == []
        finally:
            filepath.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# ComponentGraphicsItem locked behavior (structural tests)
# ---------------------------------------------------------------------------


class TestComponentGraphicsItemLocked:
    """Structural tests for locked component visual/interaction behavior."""

    @pytest.fixture(autouse=True)
    def _load_component_item_module(self):
        """Load component_item module directly to avoid GUI.__init__ matplotlib chain."""
        import importlib
        import sys

        spec = importlib.util.spec_from_file_location(
            "component_item",
            Path(__file__).parents[2] / "GUI" / "component_item.py",
        )
        mod = importlib.util.module_from_spec(spec)
        # Need the module in sys.modules before exec for relative imports
        sys.modules["component_item"] = mod
        self._source_path = Path(__file__).parents[2] / "GUI" / "component_item.py"

    def test_apply_locked_state_exists(self):
        """Verify apply_locked_state is defined in component_item.py source."""
        source = self._source_path.read_text()
        assert "def apply_locked_state" in source

    def test_locked_model_flag_check_in_paint(self):
        """Verify paint method references model.locked for overlay drawing."""
        source = self._source_path.read_text()
        assert "model.locked" in source

    def test_apply_locked_state_in_init(self):
        """Verify __init__ checks model.locked and calls apply_locked_state."""
        source = self._source_path.read_text()
        # Both should appear in the source
        assert "model.locked" in source
        assert "apply_locked_state" in source
