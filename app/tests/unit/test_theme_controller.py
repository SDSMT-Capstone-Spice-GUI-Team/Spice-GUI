"""Tests for ThemeController wrapper methods and GUI mutation routing."""

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controllers.theme_controller import ThemeController, theme_ctrl


class TestThemeControllerWrappers:
    """Verify ThemeController delegates all mutations to theme_manager."""

    def setup_method(self):
        self.ctrl = ThemeController()

    @patch("controllers.theme_controller.theme_manager")
    def test_set_theme(self, mock_tm):
        theme = MagicMock()
        self.ctrl.set_theme(theme)
        mock_tm.set_theme.assert_called_once_with(theme)

    @patch("controllers.theme_controller.theme_manager")
    def test_set_theme_by_key(self, mock_tm):
        self.ctrl.set_theme_by_key("dark")
        mock_tm.set_theme_by_key.assert_called_once_with("dark")

    @patch("controllers.theme_controller.theme_manager")
    def test_set_symbol_style(self, mock_tm):
        self.ctrl.set_symbol_style("iec")
        mock_tm.set_symbol_style.assert_called_once_with("iec")

    @patch("controllers.theme_controller.theme_manager")
    def test_set_color_mode(self, mock_tm):
        self.ctrl.set_color_mode("monochrome")
        mock_tm.set_color_mode.assert_called_once_with("monochrome")

    @patch("controllers.theme_controller.theme_manager")
    def test_set_wire_thickness(self, mock_tm):
        self.ctrl.set_wire_thickness("thick")
        mock_tm.set_wire_thickness.assert_called_once_with("thick")

    @patch("controllers.theme_controller.theme_manager")
    def test_set_show_junction_dots(self, mock_tm):
        self.ctrl.set_show_junction_dots(False)
        mock_tm.set_show_junction_dots.assert_called_once_with(False)

    @patch("controllers.theme_controller.theme_manager")
    def test_set_routing_mode(self, mock_tm):
        self.ctrl.set_routing_mode("diagonal")
        mock_tm.set_routing_mode.assert_called_once_with("diagonal")

    @patch("controllers.theme_controller.theme_manager")
    def test_current_theme_property(self, mock_tm):
        mock_tm.current_theme = MagicMock()
        result = self.ctrl.current_theme
        assert result is mock_tm.current_theme


class TestModuleSingleton:
    """Verify the module-level singleton is a ThemeController."""

    def test_singleton_type(self):
        assert isinstance(theme_ctrl, ThemeController)


class TestControllerNoGuiImport:
    """Verify theme_controller.py has no runtime GUI imports."""

    def test_no_gui_runtime_import(self):
        import controllers.theme_controller as tc

        source = Path(tc.__file__).read_text()
        assert "PyQt" not in source

    def test_gui_import_only_in_type_checking(self):
        """Any GUI.styles import must be inside TYPE_CHECKING block."""
        import controllers.theme_controller as tc

        source = Path(tc.__file__).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            is_from_import = isinstance(node, ast.ImportFrom)
            if is_from_import and node.module and "GUI" in node.module:
                # Must be inside TYPE_CHECKING, not at module top level
                msg = f"GUI import '{node.module}' at line {node.lineno} is top-level"
                assert node.col_offset > 0, msg


class TestNoDirectMutationInGui:
    """Verify GUI files do not call theme_manager.set_* directly."""

    _MUTATION_METHODS = (
        "set_theme(",
        "set_theme_by_key(",
        "set_symbol_style(",
        "set_color_mode(",
        "set_wire_thickness(",
        "set_show_junction_dots(",
        "set_routing_mode(",
    )

    def _gui_python_files(self):
        gui_dir = Path(__file__).resolve().parent.parent.parent / "GUI"
        files = []
        for p in gui_dir.rglob("*.py"):
            if "__pycache__" not in str(p) and "styles" not in p.parts:
                files.append(p)
        return files

    def test_no_theme_manager_set_calls(self):
        """No GUI file outside styles/ should call theme_manager.set_*."""
        violations = []
        for path in self._gui_python_files():
            source = path.read_text()
            for line_no, line in enumerate(source.splitlines(), 1):
                # Skip comments
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for method in self._MUTATION_METHODS:
                    if f"theme_manager.{method}" in line:
                        violations.append(f"{path.name}:{line_no}: {line.strip()}")
        msg = "Use theme_ctrl, not theme_manager.set_*:\n" + "\n".join(violations)
        assert violations == [], msg
