"""Tests for the Recent Files menu feature (#739).

These tests verify the backend recent-files logic (no Qt required)
and structurally confirm the menu wiring in the mixin source code.
"""

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestRecentFilesMenuStructural:
    """Structural tests confirming the Recent Files menu exists in the mixin code."""

    def test_menu_bar_creates_recent_files_menu(self):
        """MenuBarMixin.create_menu_bar must reference 'Recent &Files'."""
        from GUI.main_window_menus import MenuBarMixin

        source = inspect.getsource(MenuBarMixin.create_menu_bar)
        assert "Recent &Files" in source, "create_menu_bar must create a 'Recent &Files' QMenu"

    def test_menu_bar_stores_recent_files_menu_attr(self):
        """MenuBarMixin.create_menu_bar must assign self._recent_files_menu."""
        from GUI.main_window_menus import MenuBarMixin

        source = inspect.getsource(MenuBarMixin.create_menu_bar)
        assert "_recent_files_menu" in source

    def test_file_ops_has_populate_method(self):
        """FileOperationsMixin must define _populate_recent_files_menu."""
        from GUI.main_window_file_ops import FileOperationsMixin

        assert hasattr(FileOperationsMixin, "_populate_recent_files_menu")

    def test_file_ops_has_open_recent_file_method(self):
        """FileOperationsMixin must define _open_recent_file."""
        from GUI.main_window_file_ops import FileOperationsMixin

        assert hasattr(FileOperationsMixin, "_open_recent_file")

    def test_file_ops_has_clear_recent_files_method(self):
        """FileOperationsMixin must define _clear_recent_files."""
        from GUI.main_window_file_ops import FileOperationsMixin

        assert hasattr(FileOperationsMixin, "_clear_recent_files")

    def test_populate_calls_file_ctrl(self):
        """_populate_recent_files_menu must call file_ctrl.get_recent_files."""
        from GUI.main_window_file_ops import FileOperationsMixin

        source = inspect.getsource(FileOperationsMixin._populate_recent_files_menu)
        assert "get_recent_files" in source

    def test_open_recent_calls_load_circuit(self):
        """_open_recent_file must call file_ctrl.load_circuit."""
        from GUI.main_window_file_ops import FileOperationsMixin

        source = inspect.getsource(FileOperationsMixin._open_recent_file)
        assert "load_circuit" in source


class TestRecentFilesBackend:
    """Tests for the FileController recent files API used by the menu."""

    def test_get_recent_files_empty_initially(self):
        """A fresh FileController should return no recent files."""
        from controllers.file_controller import FileController

        with patch("controllers.file_controller.settings") as mock_settings:
            mock_settings.get_list.return_value = []
            ctrl = FileController()
            assert ctrl.get_recent_files() == []

    def test_add_and_get_recent_file(self, tmp_path):
        """add_recent_file should make the file appear in get_recent_files."""
        from controllers.file_controller import FileController

        stored = []

        def fake_get_list(key):
            return list(stored)

        def fake_set(key, val):
            stored.clear()
            stored.extend(val)

        with patch("controllers.file_controller.settings") as mock_settings:
            mock_settings.get_list.side_effect = fake_get_list
            mock_settings.set.side_effect = fake_set

            ctrl = FileController()
            test_file = tmp_path / "circuit.json"
            test_file.touch()

            ctrl.add_recent_file(test_file)
            recent = ctrl.get_recent_files()
            assert len(recent) == 1
            assert str(test_file.absolute()) in recent[0]

    def test_clear_recent_files(self):
        """clear_recent_files should result in an empty list."""
        from controllers.file_controller import FileController

        with patch("controllers.file_controller.settings") as mock_settings:
            ctrl = FileController()
            ctrl.clear_recent_files()
            mock_settings.set.assert_called_with("file/recent_files", [])
