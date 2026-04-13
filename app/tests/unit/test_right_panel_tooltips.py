"""Tests for right-panel and results-panel button tooltips (#910).

Structural tests verify that setToolTip() is called on buttons that
previously lacked tooltips, by reading source files directly
(not via inspect.getsource).
"""

from pathlib import Path


def _module_source(module):
    """Return the source text of a module by reading its __file__."""
    return Path(module.__file__).read_text()


class TestRightPanelTooltipsStructural:
    """Verify setToolTip is called on right-panel action buttons in MainWindow."""

    def _get_source(self):
        from GUI import main_window

        return _module_source(main_window)

    def test_btn_save_has_tooltip(self):
        src = self._get_source()
        assert "btn_save.setToolTip" in src

    def test_btn_load_has_tooltip(self):
        src = self._get_source()
        assert "btn_load.setToolTip" in src

    def test_btn_clear_has_tooltip(self):
        src = self._get_source()
        assert "btn_clear.setToolTip" in src

    def test_btn_netlist_has_tooltip(self):
        src = self._get_source()
        assert "btn_netlist.setToolTip" in src

    def test_btn_simulate_has_tooltip(self):
        src = self._get_source()
        assert "btn_simulate.setToolTip" in src


class TestResultsPanelTooltipsStructural:
    """Verify setToolTip is called on results-panel export buttons."""

    def _get_source(self):
        from GUI import results_panel

        return _module_source(results_panel)

    def test_btn_export_csv_has_tooltip(self):
        src = self._get_source()
        assert "btn_export_csv.setToolTip" in src

    def test_btn_export_excel_has_tooltip(self):
        src = self._get_source()
        assert "btn_export_excel.setToolTip" in src

    def test_btn_copy_markdown_has_tooltip(self):
        src = self._get_source()
        assert "btn_copy_markdown.setToolTip" in src
