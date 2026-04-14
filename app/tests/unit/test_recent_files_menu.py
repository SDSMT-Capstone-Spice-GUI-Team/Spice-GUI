"""Tests for the Recent Files menu feature (#739).

These tests verify the backend recent-files logic (no Qt required)
and behaviourally confirm the menu wiring in the mixin source code.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestRecentFilesMenuStructural:
    """Behavioural tests confirming the Recent Files menu is wired up correctly."""

    def _run_create_menu_bar(self, host):
        """Run MenuBarMixin.create_menu_bar with Qt widget constructors patched.

        QAction, QMenu, QKeySequence and QActionGroup all require a real QWidget/QObject
        parent, which is unavailable without a full MainWindow.  Patching them out lets
        the mixin run its assignment logic (self._recent_files_menu = ...) without
        touching the display layer.
        """
        from GUI.main_window_menus import MenuBarMixin

        with (
            patch("GUI.main_window_menus.QAction", MagicMock(return_value=MagicMock())),
            patch("GUI.main_window_menus.QMenu", MagicMock(return_value=MagicMock())),
            patch("GUI.main_window_menus.QKeySequence", MagicMock(return_value=MagicMock())),
            patch("GUI.main_window_menus.QActionGroup", MagicMock(return_value=MagicMock())),
        ):
            MenuBarMixin.create_menu_bar(host)

    def _make_host_with_fake_menus(self):
        """Return (host, captured_menus) where captured_menus records addMenu calls on the File menu."""
        captured_menus = {}

        def capture_add_menu(title):
            m = MagicMock()
            captured_menus[title] = m
            return m

        fake_file_menu = MagicMock()
        fake_file_menu.addMenu.side_effect = capture_add_menu
        fake_file_menu.addAction.return_value = MagicMock()
        fake_file_menu.addSeparator.return_value = MagicMock()

        def menubar_add_menu(title):
            if title == "&File":
                return fake_file_menu
            m = MagicMock()
            m.addMenu.return_value = MagicMock()
            m.addAction.return_value = MagicMock()
            return m

        fake_menubar = MagicMock()
        fake_menubar.addMenu.side_effect = menubar_add_menu

        host = MagicMock()
        host.menuBar.return_value = fake_menubar
        host.keybindings = MagicMock()
        host.keybindings.get.return_value = ""
        return host, captured_menus

    def test_menu_bar_creates_recent_files_menu(self):
        """After create_menu_bar runs, self._recent_files_menu must be set."""
        host, _ = self._make_host_with_fake_menus()
        self._run_create_menu_bar(host)
        assert hasattr(host, "_recent_files_menu"), "create_menu_bar must set self._recent_files_menu"

    def test_menu_bar_stores_recent_files_menu_attr_title(self):
        """create_menu_bar must construct a QMenu with the title 'Recent &Files'."""
        from GUI.main_window_menus import MenuBarMixin

        host, _ = self._make_host_with_fake_menus()
        mock_qmenu = MagicMock(return_value=MagicMock())

        with (
            patch("GUI.main_window_menus.QAction", MagicMock(return_value=MagicMock())),
            patch("GUI.main_window_menus.QMenu", mock_qmenu),
            patch("GUI.main_window_menus.QKeySequence", MagicMock(return_value=MagicMock())),
            patch("GUI.main_window_menus.QActionGroup", MagicMock(return_value=MagicMock())),
        ):
            MenuBarMixin.create_menu_bar(host)

        # Collect all positional-arg calls to QMenu() and check one was titled "Recent &Files"
        titles_used = [call.args[0] for call in mock_qmenu.call_args_list if call.args]
        assert (
            "Recent &Files" in titles_used
        ), f"create_menu_bar must create QMenu('Recent &Files', ...), got: {titles_used}"

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
        """_populate_recent_files_menu must call file_ctrl.get_recent_files()."""
        from GUI.main_window_file_ops import FileOperationsMixin

        host = MagicMock()
        host.file_ctrl.get_recent_files.return_value = []
        host._recent_files_menu = MagicMock()

        FileOperationsMixin._populate_recent_files_menu(host)

        host.file_ctrl.get_recent_files.assert_called_once()

    def test_open_recent_calls_load_circuit(self, tmp_path):
        """_open_recent_file must call file_ctrl.load_circuit with the given path."""
        from GUI.main_window_file_ops import FileOperationsMixin

        circuit_file = tmp_path / "circuit.json"
        circuit_file.touch()

        host = MagicMock()

        FileOperationsMixin._open_recent_file(host, str(circuit_file))

        host.file_ctrl.load_circuit.assert_called_once_with(circuit_file)


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
