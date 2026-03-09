"""Tests for models.subcircuit_library — additional coverage.

Covers _generate_terminal_geometry, register_subcircuit_component,
SubcircuitLibrary persistence/import paths, and edge cases.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from models.subcircuit_library import (
    SubcircuitDefinition,
    SubcircuitLibrary,
    _generate_terminal_geometry,
    _register_graphics,
    _register_subcircuit_renderer,
    parse_subckt,
    register_subcircuit_component,
)

# ---- _generate_terminal_geometry ----


class TestGenerateTerminalGeometry:
    def test_one_terminal(self):
        w, h, terminals = _generate_terminal_geometry(1)
        assert w == 15
        assert h == 15
        assert terminals == [(-30, 0)]

    def test_two_terminals(self):
        w, h, terminals = _generate_terminal_geometry(2)
        assert w == 15
        assert h == 15
        assert terminals is None  # standard horizontal layout

    def test_three_terminals(self):
        w, h, terminals = _generate_terminal_geometry(3)
        assert w == 20
        assert h == 10
        assert len(terminals) == 3
        # Same as Op-Amp layout
        assert terminals[0] == (-30, -10)
        assert terminals[1] == (-30, 10)
        assert terminals[2] == (30, 0)

    def test_four_terminals(self):
        w, h, terminals = _generate_terminal_geometry(4)
        # 4 terminals: 2 left, 2 right
        assert len(terminals) == 4
        left = [t for t in terminals if t[0] < 0]
        right = [t for t in terminals if t[0] > 0]
        assert len(left) == 2
        assert len(right) == 2

    def test_five_terminals(self):
        w, h, terminals = _generate_terminal_geometry(5)
        # 5 terminals: 3 left, 2 right
        assert len(terminals) == 5
        left = [t for t in terminals if t[0] < 0]
        right = [t for t in terminals if t[0] > 0]
        assert len(left) == 3
        assert len(right) == 2

    def test_six_terminals(self):
        w, h, terminals = _generate_terminal_geometry(6)
        assert len(terminals) == 6
        left = [t for t in terminals if t[0] < 0]
        right = [t for t in terminals if t[0] > 0]
        assert len(left) == 3
        assert len(right) == 3


# ---- register_subcircuit_component ----


class TestRegisterSubcircuitComponent:
    def setup_method(self):
        # Save original state of component dicts
        from models.component import (
            COMPONENT_CATEGORIES,
            COMPONENT_COLORS,
            COMPONENT_TYPES,
            DEFAULT_VALUES,
            SPICE_SYMBOLS,
            TERMINAL_COUNTS,
            TERMINAL_GEOMETRY,
        )

        self._saved = {
            "types": list(COMPONENT_TYPES),
            "symbols": dict(SPICE_SYMBOLS),
            "counts": dict(TERMINAL_COUNTS),
            "defaults": dict(DEFAULT_VALUES),
            "colors": dict(COMPONENT_COLORS),
            "geometry": dict(TERMINAL_GEOMETRY),
            "categories": {k: list(v) for k, v in COMPONENT_CATEGORIES.items()},
        }

    def teardown_method(self):
        from models.component import (
            COMPONENT_CATEGORIES,
            COMPONENT_COLORS,
            COMPONENT_TYPES,
            DEFAULT_VALUES,
            SPICE_SYMBOLS,
            TERMINAL_COUNTS,
            TERMINAL_GEOMETRY,
        )

        COMPONENT_TYPES.clear()
        COMPONENT_TYPES.extend(self._saved["types"])
        SPICE_SYMBOLS.clear()
        SPICE_SYMBOLS.update(self._saved["symbols"])
        TERMINAL_COUNTS.clear()
        TERMINAL_COUNTS.update(self._saved["counts"])
        DEFAULT_VALUES.clear()
        DEFAULT_VALUES.update(self._saved["defaults"])
        COMPONENT_COLORS.clear()
        COMPONENT_COLORS.update(self._saved["colors"])
        TERMINAL_GEOMETRY.clear()
        TERMINAL_GEOMETRY.update(self._saved["geometry"])
        COMPONENT_CATEGORIES.clear()
        COMPONENT_CATEGORIES.update(self._saved["categories"])

    def test_register_new_subcircuit(self):
        from models.component import COMPONENT_TYPES, SPICE_SYMBOLS, TERMINAL_COUNTS

        defn = SubcircuitDefinition(
            name="TestSub", terminals=["IN", "OUT", "GND"], spice_definition=".subckt TestSub IN OUT GND\n.ends"
        )
        # Mock GUI imports to avoid Qt
        with patch("models.subcircuit_library._register_graphics"):
            register_subcircuit_component(defn)

        assert "TestSub" in COMPONENT_TYPES
        assert SPICE_SYMBOLS["TestSub"] == "X"
        assert TERMINAL_COUNTS["TestSub"] == 3

    def test_skip_if_already_registered(self):
        from models.component import SPICE_SYMBOLS

        defn = SubcircuitDefinition(
            name="TestSub2", terminals=["A", "B"], spice_definition=".subckt TestSub2 A B\n.ends"
        )
        SPICE_SYMBOLS["TestSub2"] = "X"  # pretend already registered
        with patch("models.subcircuit_library._register_graphics"):
            register_subcircuit_component(defn)
        # Should not have changed anything else (early return)

    def test_subcircuits_category_created(self):
        from models.component import COMPONENT_CATEGORIES

        defn = SubcircuitDefinition(name="NewCat", terminals=["A", "B"], spice_definition=".subckt NewCat A B\n.ends")
        with patch("models.subcircuit_library._register_graphics"):
            register_subcircuit_component(defn)
        assert "Subcircuits" in COMPONENT_CATEGORIES
        assert "NewCat" in COMPONENT_CATEGORIES["Subcircuits"]


# ---- SubcircuitLibrary persistence ----


class TestSubcircuitLibraryPersistence:
    def test_empty_library(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        # Should have builtins only
        assert isinstance(lib.definitions, dict)

    def test_add_and_get(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        defn = SubcircuitDefinition(name="MySub", terminals=["A", "B"], spice_definition=".subckt MySub A B\n.ends")
        lib.add(defn)
        assert lib.get("MySub") is defn
        assert "MySub" in lib.names()

    def test_add_persist_creates_file(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        defn = SubcircuitDefinition(name="SaveMe", terminals=["X"], spice_definition=".subckt SaveMe X\n.ends")
        lib.add(defn, persist=True)
        files = list(tmp_path.glob("*.json"))
        assert len(files) >= 1

    def test_add_no_persist(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        initial_files = set(tmp_path.glob("*.json"))
        defn = SubcircuitDefinition(name="NoPersist", terminals=["X"], spice_definition=".subckt NoPersist X\n.ends")
        lib.add(defn, persist=False)
        new_files = set(tmp_path.glob("*.json")) - initial_files
        assert len(new_files) == 0

    def test_remove_nonexistent(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        assert lib.remove("nonexistent") is False

    def test_remove_builtin_fails(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        defn = SubcircuitDefinition(
            name="BuiltinSub", terminals=["A"], spice_definition=".subckt BuiltinSub A\n.ends", builtin=True
        )
        lib.add(defn, persist=False)
        assert lib.remove("BuiltinSub") is False
        assert lib.get("BuiltinSub") is not None

    def test_remove_user_subcircuit(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        defn = SubcircuitDefinition(name="UserSub", terminals=["A", "B"], spice_definition=".subckt UserSub A B\n.ends")
        lib.add(defn)
        assert lib.remove("UserSub") is True
        assert lib.get("UserSub") is None

    def test_load_from_disk(self, tmp_path):
        # Write a JSON file that _load should pick up
        data = {
            "name": "FromDisk",
            "terminals": ["A", "B"],
            "spice_definition": ".subckt FromDisk A B\n.ends",
            "description": "loaded from disk",
        }
        (tmp_path / "FromDisk.json").write_text(json.dumps(data), encoding="utf-8")
        lib = SubcircuitLibrary(library_dir=tmp_path)
        assert lib.get("FromDisk") is not None
        assert lib.get("FromDisk").description == "loaded from disk"

    def test_load_corrupt_file_skipped(self, tmp_path):
        (tmp_path / "broken.json").write_text("not valid json", encoding="utf-8")
        SubcircuitLibrary(library_dir=tmp_path)
        # Should not raise, just skip the corrupt file

    def test_import_file(self, tmp_path):
        subckt_text = ".subckt ImportedSub IN OUT\nR1 IN OUT 1k\n.ends\n"
        subckt_file = tmp_path / "imported.subckt"
        subckt_file.write_text(subckt_text, encoding="utf-8")
        lib = SubcircuitLibrary(library_dir=tmp_path)
        result = lib.import_file(subckt_file)
        assert len(result) == 1
        assert result[0].name == "ImportedSub"
        assert lib.get("ImportedSub") is not None

    def test_import_text(self, tmp_path):
        text = ".subckt TextSub A B C\nR1 A B 1k\n.ends\n"
        lib = SubcircuitLibrary(library_dir=tmp_path)
        result = lib.import_text(text)
        assert len(result) == 1
        assert result[0].terminal_count == 3

    def test_register_all(self, tmp_path):
        lib = SubcircuitLibrary(library_dir=tmp_path)
        defn = SubcircuitDefinition(name="RegAll", terminals=["A", "B"], spice_definition=".subckt RegAll A B\n.ends")
        lib.add(defn, persist=False)
        with patch("models.subcircuit_library.register_subcircuit_component") as mock_reg:
            lib.register_all()
            # Should be called for each definition
            assert mock_reg.call_count >= 1


# ---- SubcircuitDefinition serialization ----


class TestSubcircuitDefinitionSerialization:
    def test_to_dict(self):
        defn = SubcircuitDefinition(
            name="S1", terminals=["A", "B"], spice_definition=".subckt S1 A B\n.ends", description="test"
        )
        d = defn.to_dict()
        assert d["name"] == "S1"
        assert d["terminals"] == ["A", "B"]
        assert d["builtin"] is False

    def test_from_dict(self):
        data = {
            "name": "S2",
            "terminals": ["X", "Y", "Z"],
            "spice_definition": ".subckt S2 X Y Z\n.ends",
            "description": "three pins",
            "builtin": False,
        }
        defn = SubcircuitDefinition.from_dict(data)
        assert defn.name == "S2"
        assert defn.terminal_count == 3

    def test_from_dict_ignores_unknown_keys(self):
        data = {
            "name": "S3",
            "terminals": ["A"],
            "spice_definition": ".subckt S3 A\n.ends",
            "unknown_field": "ignored",
        }
        defn = SubcircuitDefinition.from_dict(data)
        assert defn.name == "S3"


# ---- parse_subckt edge cases ----


class TestParseSubcktEdgeCases:
    def test_params_ignored(self):
        text = ".subckt MyOPA IN+ IN- OUT PARAM=value\nR1 IN+ OUT 1k\n.ends"
        defs = parse_subckt(text)
        assert defs[0].terminals == ["IN+", "IN-", "OUT"]

    def test_multiple_subcircuits(self):
        text = ".subckt A IN OUT\n.ends\n.subckt B X Y Z\n.ends\n"
        defs = parse_subckt(text)
        assert len(defs) == 2
        assert defs[0].name == "A"
        assert defs[1].name == "B"

    def test_description_from_comments(self):
        text = ".subckt D1 A B\n* First line\n* Second line\nR1 A B 1k\n.ends"
        defs = parse_subckt(text)
        assert "First line" in defs[0].description
        assert "Second line" in defs[0].description

    def test_no_subckt_raises(self):
        with pytest.raises(ValueError, match="No valid .subckt"):
            parse_subckt("just some random text")

    def test_case_insensitive(self):
        text = ".SUBCKT Upper A B\n.ENDS"
        defs = parse_subckt(text)
        assert defs[0].name == "Upper"


# ---- _load_builtins ImportError path (lines 208-209) ----


class TestLoadBuiltinsImportError:
    def test_load_builtins_import_error_silenced(self, tmp_path):
        """When models.builtin_subcircuits cannot be imported, _load_builtins silently passes."""
        with patch.dict("sys.modules", {"models.builtin_subcircuits": None}):
            lib = SubcircuitLibrary(library_dir=tmp_path)
            # Library should still be usable, just no builtins
            assert isinstance(lib.definitions, dict)


# ---- register_subcircuit_component GUI import failures (lines 307-308) ----


class TestRegisterSubcircuitComponentStylesFailure:
    def setup_method(self):
        from models.component import (
            COMPONENT_CATEGORIES,
            COMPONENT_COLORS,
            COMPONENT_TYPES,
            DEFAULT_VALUES,
            SPICE_SYMBOLS,
            TERMINAL_COUNTS,
            TERMINAL_GEOMETRY,
        )

        self._saved = {
            "types": list(COMPONENT_TYPES),
            "symbols": dict(SPICE_SYMBOLS),
            "counts": dict(TERMINAL_COUNTS),
            "defaults": dict(DEFAULT_VALUES),
            "colors": dict(COMPONENT_COLORS),
            "geometry": dict(TERMINAL_GEOMETRY),
            "categories": {k: list(v) for k, v in COMPONENT_CATEGORIES.items()},
        }

    def teardown_method(self):
        from models.component import (
            COMPONENT_CATEGORIES,
            COMPONENT_COLORS,
            COMPONENT_TYPES,
            DEFAULT_VALUES,
            SPICE_SYMBOLS,
            TERMINAL_COUNTS,
            TERMINAL_GEOMETRY,
        )

        COMPONENT_TYPES.clear()
        COMPONENT_TYPES.extend(self._saved["types"])
        SPICE_SYMBOLS.clear()
        SPICE_SYMBOLS.update(self._saved["symbols"])
        TERMINAL_COUNTS.clear()
        TERMINAL_COUNTS.update(self._saved["counts"])
        DEFAULT_VALUES.clear()
        DEFAULT_VALUES.update(self._saved["defaults"])
        COMPONENT_COLORS.clear()
        COMPONENT_COLORS.update(self._saved["colors"])
        TERMINAL_GEOMETRY.clear()
        TERMINAL_GEOMETRY.update(self._saved["geometry"])
        COMPONENT_CATEGORIES.clear()
        COMPONENT_CATEGORIES.update(self._saved["categories"])

    def test_styles_import_failure_silenced(self):
        """When GUI.styles.constants import fails, registration still completes."""
        defn = SubcircuitDefinition(
            name="StylesFail", terminals=["A", "B"], spice_definition=".subckt StylesFail A B\n.ends"
        )
        with (
            patch("models.subcircuit_library._register_graphics"),
            patch.dict("sys.modules", {"GUI.styles.constants": None}),
        ):
            register_subcircuit_component(defn)
        from models.component import SPICE_SYMBOLS

        assert SPICE_SYMBOLS["StylesFail"] == "X"


# ---- _register_graphics exception paths (lines 332-333, 339-340) ----


class TestRegisterGraphicsExceptions:
    def test_component_item_import_failure(self):
        """When GUI.component_item import fails, _register_graphics silently passes."""
        defn = SubcircuitDefinition(
            name="GfxFail1", terminals=["A", "B"], spice_definition=".subckt GfxFail1 A B\n.ends"
        )
        with patch.dict("sys.modules", {"GUI.component_item": None}):
            # Should not raise
            _register_graphics("GfxFail1", defn)

    def test_renderers_import_failure(self):
        """When GUI.renderers import fails, _register_graphics silently passes."""
        defn = SubcircuitDefinition(
            name="GfxFail2", terminals=["A", "B"], spice_definition=".subckt GfxFail2 A B\n.ends"
        )
        with patch.dict("sys.modules", {"GUI.renderers": None}):
            _register_graphics("GfxFail2", defn)


# ---- SubcircuitRenderer.draw and get_obstacle_shape (lines 355-383) ----


class TestSubcircuitRenderer:
    def _make_renderer(self, terminal_count):
        """Create a SubcircuitRenderer instance via _register_subcircuit_renderer."""
        from GUI.renderers import ComponentRenderer, _bounding_rect_obstacle

        defn = SubcircuitDefinition(
            name=f"RenderTest{terminal_count}",
            terminals=[f"t{i}" for i in range(terminal_count)],
            spice_definition=f".subckt RenderTest{terminal_count} "
            + " ".join(f"t{i}" for i in range(terminal_count))
            + "\n.ends",
        )
        captured = {}

        def fake_register(name, style, renderer):
            captured.setdefault(name, {})[style] = renderer

        _register_subcircuit_renderer(defn.name, defn, fake_register, lambda r: r)
        return captured[defn.name]["ieee"]

    def test_draw_two_terminals(self):
        """Exercise the 2-terminal draw branch."""
        renderer = self._make_renderer(2)
        painter = MagicMock()
        component = MagicMock()
        component.scene.return_value = MagicMock()  # non-None scene
        renderer.draw(painter, component)
        painter.drawRect.assert_called_once_with(-18, -15, 36, 30)
        # 2-terminal draws 2 lines
        assert painter.drawLine.call_count == 2

    def test_draw_three_terminals(self):
        """Exercise the 3-terminal draw branch."""
        renderer = self._make_renderer(3)
        painter = MagicMock()
        component = MagicMock()
        component.scene.return_value = MagicMock()
        renderer.draw(painter, component)
        painter.drawRect.assert_called_once()
        # 3-terminal draws 3 lines
        assert painter.drawLine.call_count == 3

    def test_draw_four_terminals(self):
        """Exercise the 4+ terminal draw branch (left/right leads)."""
        renderer = self._make_renderer(4)
        painter = MagicMock()
        component = MagicMock()
        component.scene.return_value = MagicMock()
        renderer.draw(painter, component)
        painter.drawRect.assert_called_once()
        # 4 terminals = 4 lead lines
        assert painter.drawLine.call_count == 4

    def test_draw_no_scene(self):
        """When component.scene() is None, terminal lines are skipped."""
        renderer = self._make_renderer(3)
        painter = MagicMock()
        component = MagicMock()
        component.scene.return_value = None
        renderer.draw(painter, component)
        painter.drawRect.assert_called_once()
        # No drawLine calls when scene is None
        painter.drawLine.assert_not_called()

    def test_get_obstacle_shape(self):
        """Exercise get_obstacle_shape method."""
        renderer = self._make_renderer(2)
        component = MagicMock()
        result = renderer.get_obstacle_shape(component)
        # Should return whatever _bounding_rect_obstacle returns
        assert result is not None


# ---- _register_subcircuit_renderer exception path (lines 389-390) ----


class TestRegisterRendererException:
    def test_register_fn_failure_silenced(self):
        """When register_fn raises, _register_subcircuit_renderer silently passes."""
        from GUI.renderers import ComponentRenderer, _bounding_rect_obstacle

        defn = SubcircuitDefinition(name="RegFail", terminals=["A", "B"], spice_definition=".subckt RegFail A B\n.ends")

        def failing_register(name, style, renderer):
            raise RuntimeError("registration failed")

        # Should not raise
        _register_subcircuit_renderer("RegFail", defn, failing_register, lambda r: r)


# ---- builtin_subcircuits.py load_builtin_subcircuits_into_library (lines 96-97) ----


class TestLoadBuiltinSubcircuitsIntoLibrary:
    def test_load_builtin_subcircuits_into_library(self, tmp_path):
        """Calling load_builtin_subcircuits_into_library adds all builtins to the library."""
        from models.builtin_subcircuits import BUILTIN_SUBCIRCUITS, load_builtin_subcircuits_into_library

        lib = SubcircuitLibrary(library_dir=tmp_path)
        load_builtin_subcircuits_into_library(lib)
        for defn in BUILTIN_SUBCIRCUITS:
            loaded = lib.get(defn.name)
            assert loaded is not None
            assert loaded.name == defn.name
