"""
Unit tests for ComponentPalette.

Tests component listing, signal emission on double-click,
drag support configuration, and search filtering.
"""

import pytest
from GUI.component_palette import ComponentPalette
from GUI.styles import COMPONENTS
from PyQt6.QtCore import Qt


@pytest.fixture
def palette(qtbot):
    p = ComponentPalette()
    qtbot.addWidget(p)
    return p


class TestComponentPaletteContents:
    """Test that palette lists all expected components."""

    def test_lists_all_component_types(self, palette):
        lw = palette.list_widget
        item_texts = [lw.item(i).text() for i in range(lw.count())]
        for comp_type in COMPONENTS:
            assert comp_type in item_texts

    def test_item_count_matches_components(self, palette):
        assert palette.list_widget.count() == len(COMPONENTS)

    def test_items_have_icons(self, palette):
        lw = palette.list_widget
        for i in range(lw.count()):
            assert not lw.item(i).icon().isNull()


class TestComponentPaletteSignals:
    """Test signal emission on interaction."""

    def test_double_click_emits_component_type(self, palette, qtbot):
        lw = palette.list_widget
        first_item = lw.item(0)
        with qtbot.waitSignal(palette.componentDoubleClicked, timeout=1000) as blocker:
            lw.itemDoubleClicked.emit(first_item)
        assert blocker.args == [first_item.text()]


class TestComponentPaletteDragConfig:
    """Test drag-and-drop configuration."""

    def test_drag_enabled(self, palette):
        assert palette.list_widget.dragEnabled()

    def test_default_drop_action_is_copy(self, palette):
        assert palette.list_widget.defaultDropAction() == Qt.DropAction.CopyAction


class TestComponentPaletteSearch:
    """Test search/filter functionality."""

    def test_filter_hides_non_matching(self, palette):
        palette.search_input.setText("resistor")
        lw = palette.list_widget
        visible = [
            lw.item(i).text() for i in range(lw.count()) if not lw.item(i).isHidden()
        ]
        assert "Resistor" in visible
        assert "Capacitor" not in visible

    def test_filter_is_case_insensitive(self, palette):
        palette.search_input.setText("CAPACITOR")
        lw = palette.list_widget
        visible = [
            lw.item(i).text() for i in range(lw.count()) if not lw.item(i).isHidden()
        ]
        assert "Capacitor" in visible

    def test_empty_filter_shows_all(self, palette):
        palette.search_input.setText("xyz")
        palette.search_input.setText("")
        lw = palette.list_widget
        visible_count = sum(1 for i in range(lw.count()) if not lw.item(i).isHidden())
        assert visible_count == len(COMPONENTS)

    def test_filter_matches_tooltip(self, palette):
        # "Resists" appears in the Resistor tooltip
        palette.search_input.setText("resists")
        lw = palette.list_widget
        visible = [
            lw.item(i).text() for i in range(lw.count()) if not lw.item(i).isHidden()
        ]
        assert "Resistor" in visible

    def test_filter_no_matches(self, palette):
        palette.search_input.setText("xyznonexistent")
        lw = palette.list_widget
        visible_count = sum(1 for i in range(lw.count()) if not lw.item(i).isHidden())
        assert visible_count == 0

    def test_search_input_has_placeholder(self, palette):
        assert "filter" in palette.search_input.placeholderText().lower()
