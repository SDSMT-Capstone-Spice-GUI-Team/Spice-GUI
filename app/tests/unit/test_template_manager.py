"""Tests for TemplateManager - template save/load/discovery."""

import json

import pytest
from controllers.template_manager import TemplateManager
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData


def _build_test_circuit():
    """Build a simple V1-R1-R2-GND circuit for testing."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5V",
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="1k",
        position=(100.0, 0.0),
    )
    model.components["R2"] = ComponentData(
        component_id="R2",
        component_type="Resistor",
        value="2k",
        position=(200.0, 0.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(300.0, 0.0),
    )
    model.wires = [
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="R1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="R2",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R2",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
    ]
    model.component_counter = {"V": 1, "R": 2, "GND": 1}
    model.rebuild_nodes()
    return model


def _write_template(directory, filename, name, category="Test", description=""):
    """Helper to write a template JSON file."""
    data = {
        "name": name,
        "description": description,
        "category": category,
        "components": [
            {
                "id": "R1",
                "type": "Resistor",
                "value": "1k",
                "pos": {"x": 0, "y": 0},
            }
        ],
        "wires": [],
        "counters": {"R": 1},
    }
    filepath = directory / filename
    filepath.write_text(json.dumps(data))
    return filepath


class TestListTemplates:
    def test_empty_directories(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        builtin.mkdir()
        user.mkdir()
        mgr = TemplateManager(builtin_dir=builtin, user_dir=user)
        assert mgr.list_templates() == []

    def test_nonexistent_directories(self, tmp_path):
        mgr = TemplateManager(
            builtin_dir=tmp_path / "no_such_builtin",
            user_dir=tmp_path / "no_such_user",
        )
        assert mgr.list_templates() == []

    def test_discovers_builtin_templates(self, tmp_path):
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        _write_template(builtin, "divider.json", "Voltage Divider", "Passives")

        mgr = TemplateManager(builtin_dir=builtin, user_dir=tmp_path / "user")
        templates = mgr.list_templates()
        assert len(templates) == 1
        assert templates[0].name == "Voltage Divider"
        assert templates[0].is_builtin is True

    def test_discovers_user_templates(self, tmp_path):
        user = tmp_path / "user"
        user.mkdir()
        _write_template(user, "my_filter.json", "My Filter", "User")

        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)
        templates = mgr.list_templates()
        assert len(templates) == 1
        assert templates[0].name == "My Filter"
        assert templates[0].is_builtin is False

    def test_combines_builtin_and_user(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        builtin.mkdir()
        user.mkdir()
        _write_template(builtin, "a.json", "Built-in A", "Passives")
        _write_template(user, "b.json", "User B", "User")

        mgr = TemplateManager(builtin_dir=builtin, user_dir=user)
        templates = mgr.list_templates()
        assert len(templates) == 2

    def test_sorted_by_category_then_name(self, tmp_path):
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        _write_template(builtin, "z.json", "Zeta", "Zzz")
        _write_template(builtin, "a.json", "Alpha", "Aaa")
        _write_template(builtin, "b.json", "Beta", "Aaa")

        mgr = TemplateManager(builtin_dir=builtin, user_dir=tmp_path / "user")
        templates = mgr.list_templates()
        assert [t.name for t in templates] == ["Alpha", "Beta", "Zeta"]

    def test_skips_invalid_json(self, tmp_path):
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        (builtin / "bad.json").write_text("not json")
        _write_template(builtin, "good.json", "Good One")

        mgr = TemplateManager(builtin_dir=builtin, user_dir=tmp_path / "user")
        templates = mgr.list_templates()
        assert len(templates) == 1
        assert templates[0].name == "Good One"


class TestLoadTemplate:
    def test_loads_components(self, tmp_path):
        builtin = tmp_path / "builtin"
        builtin.mkdir()

        # Write a circuit with two resistors
        data = {
            "name": "Test",
            "category": "Test",
            "components": [
                {
                    "id": "R1",
                    "type": "Resistor",
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                },
                {
                    "id": "R2",
                    "type": "Resistor",
                    "value": "2k",
                    "pos": {"x": 100, "y": 0},
                },
            ],
            "wires": [],
            "counters": {"R": 2},
        }
        filepath = builtin / "test.json"
        filepath.write_text(json.dumps(data))

        mgr = TemplateManager(builtin_dir=builtin, user_dir=tmp_path / "user")
        model = mgr.load_template(filepath)
        assert "R1" in model.components
        assert "R2" in model.components

    def test_recalculates_counters(self, tmp_path):
        builtin = tmp_path / "builtin"
        builtin.mkdir()

        # Write template with counters that don't match component IDs
        data = {
            "name": "Test",
            "category": "Test",
            "components": [
                {
                    "id": "R1",
                    "type": "Resistor",
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                },
                {
                    "id": "R3",
                    "type": "Resistor",
                    "value": "2k",
                    "pos": {"x": 100, "y": 0},
                },
                {
                    "id": "V1",
                    "type": "VoltageSource",
                    "value": "5V",
                    "pos": {"x": 200, "y": 0},
                },
            ],
            "wires": [],
            "counters": {"R": 999, "V": 999},
        }
        filepath = builtin / "test.json"
        filepath.write_text(json.dumps(data))

        mgr = TemplateManager(builtin_dir=builtin, user_dir=tmp_path / "user")
        model = mgr.load_template(filepath)

        # Counter should reflect actual highest ID, not the stored value
        assert model.component_counter["R"] == 3
        assert model.component_counter["V"] == 1

    def test_invalid_json_raises(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text("not json")

        mgr = TemplateManager(builtin_dir=tmp_path, user_dir=tmp_path / "user")
        with pytest.raises(json.JSONDecodeError):
            mgr.load_template(filepath)

    def test_invalid_structure_raises(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text(json.dumps({"no_components": True}))

        mgr = TemplateManager(builtin_dir=tmp_path, user_dir=tmp_path / "user")
        with pytest.raises(ValueError):
            mgr.load_template(filepath)


class TestSaveTemplate:
    def test_saves_to_user_directory(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        model = _build_test_circuit()
        filepath = mgr.save_template(model, "My Circuit", "A test circuit", "Passives")

        assert filepath.exists()
        assert filepath.parent == user

    def test_creates_user_directory(self, tmp_path):
        user = tmp_path / "user" / "templates"
        assert not user.exists()

        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)
        mgr.save_template(_build_test_circuit(), "Test")

        assert user.exists()

    def test_saves_metadata(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        filepath = mgr.save_template(
            _build_test_circuit(), "My Filter", "An RC filter", "Filters"
        )

        data = json.loads(filepath.read_text())
        assert data["name"] == "My Filter"
        assert data["description"] == "An RC filter"
        assert data["category"] == "Filters"

    def test_saves_circuit_data(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        model = _build_test_circuit()
        filepath = mgr.save_template(model, "Test")

        data = json.loads(filepath.read_text())
        assert "components" in data
        assert "wires" in data
        assert len(data["components"]) == 4
        assert len(data["wires"]) == 3

    def test_avoids_overwriting(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        model = _build_test_circuit()
        path1 = mgr.save_template(model, "Same Name")
        path2 = mgr.save_template(model, "Same Name")

        assert path1 != path2
        assert path1.exists()
        assert path2.exists()

    def test_default_category_is_user(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        filepath = mgr.save_template(_build_test_circuit(), "No Category")

        data = json.loads(filepath.read_text())
        assert data["category"] == "User"


class TestSaveLoadRoundTrip:
    def test_round_trip_preserves_components(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        original = _build_test_circuit()
        filepath = mgr.save_template(original, "Round Trip Test")
        loaded = mgr.load_template(filepath)

        assert set(loaded.components.keys()) == set(original.components.keys())

    def test_round_trip_preserves_wires(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        original = _build_test_circuit()
        filepath = mgr.save_template(original, "Round Trip Test")
        loaded = mgr.load_template(filepath)

        assert len(loaded.wires) == len(original.wires)

    def test_round_trip_recalculates_counters(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        original = _build_test_circuit()
        filepath = mgr.save_template(original, "Round Trip Test")
        loaded = mgr.load_template(filepath)

        # Counters should reflect actual component IDs
        assert loaded.component_counter["R"] == 2
        assert loaded.component_counter["V"] == 1
        assert loaded.component_counter["GND"] == 1


class TestDeleteTemplate:
    def test_delete_user_template(self, tmp_path):
        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=tmp_path / "builtin", user_dir=user)

        filepath = mgr.save_template(_build_test_circuit(), "To Delete")
        assert filepath.exists()

        result = mgr.delete_template(filepath)
        assert result is True
        assert not filepath.exists()

    def test_cannot_delete_builtin(self, tmp_path):
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        filepath = _write_template(builtin, "builtin.json", "Built-in")

        user = tmp_path / "user"
        mgr = TemplateManager(builtin_dir=builtin, user_dir=user)

        result = mgr.delete_template(filepath)
        assert result is False
        assert filepath.exists()

    def test_delete_nonexistent_returns_false(self, tmp_path):
        mgr = TemplateManager(
            builtin_dir=tmp_path / "builtin", user_dir=tmp_path / "user"
        )
        result = mgr.delete_template(tmp_path / "nonexistent.json")
        assert result is False


class TestCalculateCounters:
    def test_simple_ids(self):
        model = CircuitModel()
        model.components["R1"] = ComponentData("R1", "Resistor", "1k", (0, 0))
        model.components["R2"] = ComponentData("R2", "Resistor", "2k", (100, 0))
        model.components["C1"] = ComponentData("C1", "Capacitor", "1u", (200, 0))

        counters = TemplateManager._calculate_counters(model)
        assert counters == {"R": 2, "C": 1}

    def test_multi_char_prefix(self):
        model = CircuitModel()
        model.components["OA1"] = ComponentData("OA1", "Op-Amp", "Ideal", (0, 0))
        model.components["GND1"] = ComponentData("GND1", "Ground", "0V", (100, 0))
        model.components["VW1"] = ComponentData(
            "VW1", "Waveform Source", "SIN(0 5 1k)", (200, 0)
        )

        counters = TemplateManager._calculate_counters(model)
        assert counters == {"OA": 1, "GND": 1, "VW": 1}

    def test_gaps_in_numbering(self):
        model = CircuitModel()
        model.components["R1"] = ComponentData("R1", "Resistor", "1k", (0, 0))
        model.components["R5"] = ComponentData("R5", "Resistor", "5k", (100, 0))

        counters = TemplateManager._calculate_counters(model)
        assert counters["R"] == 5  # Highest number, not count

    def test_empty_model(self):
        model = CircuitModel()
        counters = TemplateManager._calculate_counters(model)
        assert counters == {}


class TestNameToFilename:
    def test_simple_name(self):
        assert TemplateManager._name_to_filename("My Circuit") == "my_circuit.json"

    def test_special_characters(self):
        result = TemplateManager._name_to_filename("RC Filter (1st Order)")
        assert result == "rc_filter_1st_order.json"

    def test_empty_name(self):
        assert TemplateManager._name_to_filename("") == "template.json"

    def test_whitespace_only(self):
        assert TemplateManager._name_to_filename("   ") == "template.json"


class TestBuiltinTemplatesValid:
    """Validate that all shipped built-in templates are well-formed."""

    def test_all_builtin_templates_load(self):
        """Every JSON file in app/templates/ should load without error."""
        mgr = TemplateManager()  # Uses default BUILTIN_TEMPLATES_DIR
        if not mgr.builtin_dir.exists():
            pytest.skip("Built-in templates directory not found")

        templates = mgr._scan_directory(mgr.builtin_dir, is_builtin=True)
        assert (
            len(templates) >= 5
        ), f"Expected at least 5 built-in templates, found {len(templates)}"

        for template_info in templates:
            model = mgr.load_template(template_info.filepath)
            assert (
                len(model.components) > 0
            ), f"Template {template_info.name} has no components"
            assert (
                template_info.name
            ), f"Template at {template_info.filepath} has no name"
            assert (
                template_info.category
            ), f"Template {template_info.name} has no category"

    def test_builtin_templates_have_descriptions(self):
        """All built-in templates should have descriptions."""
        mgr = TemplateManager()
        if not mgr.builtin_dir.exists():
            pytest.skip("Built-in templates directory not found")

        templates = mgr._scan_directory(mgr.builtin_dir, is_builtin=True)
        for t in templates:
            assert t.description, f"Template {t.name} has no description"
