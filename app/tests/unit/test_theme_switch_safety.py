"""Tests for #860 — theme switching must not segfault with loaded circuits.

Structural tests verify the safe detach-rebuild pattern exists so that
``setStyleSheet()`` cannot destroy live QGraphicsItems during a repaint.
"""

import ast
import textwrap
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent.parent  # …/app


class TestApplyThemeDetachPattern:
    """apply_theme() must detach the scene before calling setStyleSheet()."""

    def _get_apply_theme_body(self):
        source = (APP_DIR / "GUI" / "main_window_view.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "apply_theme":
                return ast.dump(node), [ast.dump(stmt) for stmt in node.body if not isinstance(stmt, ast.Expr)]
        raise AssertionError("apply_theme not found")  # pragma: no cover

    def test_detach_scene_called_before_setStyleSheet(self):
        """detach_scene() must appear before setStyleSheet() in apply_theme."""
        source = (APP_DIR / "GUI" / "main_window_view.py").read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "apply_theme":
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            calls.append((child.func.attr, child.lineno))
                # Find positions
                detach_line = next((line for name, line in calls if name == "detach_scene"), None)
                set_ss_line = next((line for name, line in calls if name == "setStyleSheet"), None)
                rebuild_line = next((line for name, line in calls if name == "rebuild_scene"), None)

                assert detach_line is not None, "detach_scene() not called in apply_theme"
                assert set_ss_line is not None, "setStyleSheet() not called in apply_theme"
                assert rebuild_line is not None, "rebuild_scene() not called in apply_theme"
                assert detach_line < set_ss_line, "detach_scene() must be called before setStyleSheet()"
                assert set_ss_line < rebuild_line, "rebuild_scene() must be called after setStyleSheet()"
                return
        raise AssertionError("apply_theme not found")  # pragma: no cover


class TestCanvasHasDetachRebuildMethods:
    """CircuitCanvasView must expose detach_scene / rebuild_scene."""

    def _get_method_names(self):
        source = (APP_DIR / "GUI" / "circuit_canvas.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "CircuitCanvasView":
                return {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
        raise AssertionError("CircuitCanvasView not found")  # pragma: no cover

    def test_detach_scene_exists(self):
        assert "detach_scene" in self._get_method_names()

    def test_rebuild_scene_exists(self):
        assert "rebuild_scene" in self._get_method_names()

    def test_refresh_theme_still_exists(self):
        """refresh_theme is still used for non-QSS refreshes (e.g. wire color updates)."""
        assert "refresh_theme" in self._get_method_names()
