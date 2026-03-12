"""Tests for lazy singleton initialization (#776).

Verifies that module-level singletons:
- Do not perform I/O or heavy work at import time
- Provide reset() / override mechanisms for test isolation
- Produce correct behavior after reset
"""

from __future__ import annotations


class TestSettingsLazyProxy:
    def test_settings_proxy_is_lazy(self):
        """The module-level ``settings`` object should not be a SettingsService at import."""
        from controllers.settings_service import SettingsService, settings

        assert not isinstance(settings, SettingsService)

    def test_settings_proxy_delegates_get(self, tmp_path):
        """Attribute access is forwarded to the underlying SettingsService."""
        from controllers.settings_service import SettingsService, settings

        real = SettingsService(path=tmp_path / "s.json")
        real.set("k", "v")
        settings.reset()
        import controllers.settings_service as _mod

        _mod.settings._instance = real
        assert settings.get("k") == "v"
        settings.reset()

    def test_settings_proxy_reset_discards_instance(self, tmp_path):
        """reset() causes the next access to create a fresh instance."""
        from controllers.settings_service import SettingsService, settings

        settings.reset()
        # Trigger creation
        _ = settings.get("anything", None)
        first = object.__getattribute__(settings, "_instance")
        assert isinstance(first, SettingsService)

        settings.reset()
        assert object.__getattribute__(settings, "_instance") is None

        # Trigger creation again
        _ = settings.get("anything", None)
        second = object.__getattribute__(settings, "_instance")
        assert isinstance(second, SettingsService)
        assert first is not second


class TestNodeLazyGenerator:
    def test_generator_not_created_at_import(self):
        """_default_generator starts as None and is created on first use."""
        import models.node as node_mod

        # Reset to None to simulate fresh import state
        node_mod._default_generator = None
        assert node_mod._default_generator is None

        # First access creates it
        gen = node_mod._get_default_generator()
        assert gen is not None
        assert node_mod._default_generator is gen

    def test_reset_node_counter_works_after_lazy_init(self):
        """reset_node_counter() resets without errors after lazy init."""
        from models.node import NodeData, reset_node_counter

        reset_node_counter()
        n1 = NodeData()
        reset_node_counter()
        n2 = NodeData()
        # Both should get the first label since we reset between them
        assert n1.auto_label == n2.auto_label

    def test_generator_reused_across_calls(self):
        """_get_default_generator() always returns the same instance."""
        import models.node as node_mod

        g1 = node_mod._get_default_generator()
        g2 = node_mod._get_default_generator()
        assert g1 is g2


class TestComponentRegistryReset:
    def test_reset_removes_registered_subcircuits(self):
        """reset_component_registry() restores COMPONENT_TYPES to built-in state."""
        from models.component import COMPONENT_TYPES, reset_component_registry
        from models.subcircuit_library import SubcircuitDefinition, register_subcircuit_component

        defn = SubcircuitDefinition(
            name="TEST_RESET_SC",
            terminals=["A", "B"],
            spice_definition=".subckt TEST_RESET_SC A B\n.ends",
        )
        register_subcircuit_component(defn)
        assert "TEST_RESET_SC" in COMPONENT_TYPES

        reset_component_registry()
        assert "TEST_RESET_SC" not in COMPONENT_TYPES

    def test_reset_cleans_spice_symbols(self):
        """reset_component_registry() removes subcircuit SPICE symbols."""
        from models.component import SPICE_SYMBOLS, reset_component_registry
        from models.subcircuit_library import SubcircuitDefinition, register_subcircuit_component

        defn = SubcircuitDefinition(
            name="TEST_SYM_SC",
            terminals=["A"],
            spice_definition=".subckt TEST_SYM_SC A\n.ends",
        )
        register_subcircuit_component(defn)
        assert "TEST_SYM_SC" in SPICE_SYMBOLS

        reset_component_registry()
        assert "TEST_SYM_SC" not in SPICE_SYMBOLS

    def test_reset_preserves_builtin_components(self):
        """reset_component_registry() keeps built-in components intact."""
        from models.component import COMPONENT_TYPES, SPICE_SYMBOLS, reset_component_registry
        from models.subcircuit_library import SubcircuitDefinition, register_subcircuit_component

        register_subcircuit_component(
            SubcircuitDefinition(
                name="TEMP_SC",
                terminals=["X"],
                spice_definition=".subckt TEMP_SC X\n.ends",
            )
        )
        reset_component_registry()
        assert "Resistor" in COMPONENT_TYPES
        assert "Resistor" in SPICE_SYMBOLS
        assert SPICE_SYMBOLS["Resistor"] == "R"


class TestSubcircuitLibraryLazyDir:
    def test_library_accepts_explicit_dir(self, tmp_path):
        """SubcircuitLibrary respects an explicitly provided directory."""
        from models.subcircuit_library import SubcircuitLibrary

        lib = SubcircuitLibrary(library_dir=tmp_path)
        assert lib._library_dir == tmp_path

    def test_default_dir_not_computed_at_import(self):
        """_DEFAULT_LIBRARY_DIR constant no longer exists at module level."""
        import models.subcircuit_library as mod

        assert not hasattr(
            mod, "_DEFAULT_LIBRARY_DIR"
        ), "_DEFAULT_LIBRARY_DIR should be replaced by _default_library_dir() function"

    def test_default_dir_function_returns_path(self):
        """_default_library_dir() returns a Path under home directory."""
        from pathlib import Path

        from models.subcircuit_library import _default_library_dir

        result = _default_library_dir()
        assert isinstance(result, Path)
        assert ".spice-gui" in str(result)
