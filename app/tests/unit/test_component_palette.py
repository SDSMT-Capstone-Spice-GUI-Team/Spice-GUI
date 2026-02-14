"""
Unit tests for ComponentPalette.

Tests component listing, categories, signal emission on double-click,
drag support configuration, search filtering, and collapse persistence.
"""

import pytest
from GUI.component_palette import COMPONENT_CATEGORIES, ComponentPalette
from GUI.styles import COMPONENTS
from PyQt6.QtCore import QSettings, Qt


@pytest.fixture
def palette(qtbot):
    p = ComponentPalette()
    qtbot.addWidget(p)
    return p


class TestComponentPaletteContents:
    """Test that palette lists all expected components."""

    def test_lists_all_component_types(self, palette):
        names = palette.get_component_names()
        for comp_type in COMPONENTS:
            assert comp_type in names

    def test_component_count_matches(self, palette):
        assert len(palette.get_component_names()) == len(COMPONENTS)

    def test_items_have_icons(self, palette):
        for cat_item in palette._category_items.values():
            for i in range(cat_item.childCount()):
                assert not cat_item.child(i).icon(0).isNull()


class TestComponentPaletteCategories:
    """Test collapsible category groups."""

    def test_has_expected_categories(self, palette):
        assert palette.get_category_names() == list(COMPONENT_CATEGORIES.keys())

    def test_all_categories_expanded_by_default(self, palette):
        for category_name in COMPONENT_CATEGORIES:
            assert palette.is_category_expanded(category_name)

    def test_passive_category_contains_expected(self, palette):
        cat = palette._category_items["Passive"]
        children = [cat.child(i).text(0) for i in range(cat.childCount())]
        assert children == ["Resistor", "Capacitor", "Inductor"]

    def test_sources_category_contains_expected(self, palette):
        cat = palette._category_items["Sources"]
        children = [cat.child(i).text(0) for i in range(cat.childCount())]
        assert children == ["Voltage Source", "Current Source", "Waveform Source"]

    def test_semiconductors_category_contains_expected(self, palette):
        cat = palette._category_items["Semiconductors"]
        children = [cat.child(i).text(0) for i in range(cat.childCount())]
        assert "Diode" in children
        assert "BJT NPN" in children
        assert "MOSFET NMOS" in children

    def test_category_headers_are_bold(self, palette):
        for cat_item in palette._category_items.values():
            assert cat_item.font(0).bold()

    def test_category_items_not_selectable(self, palette):
        for cat_item in palette._category_items.values():
            assert not (cat_item.flags() & Qt.ItemFlag.ItemIsSelectable)

    def test_component_items_are_selectable(self, palette):
        cat = palette._category_items["Passive"]
        child = cat.child(0)
        assert child.flags() & Qt.ItemFlag.ItemIsSelectable

    def test_component_items_are_draggable(self, palette):
        cat = palette._category_items["Passive"]
        child = cat.child(0)
        assert child.flags() & Qt.ItemFlag.ItemIsDragEnabled


class TestComponentPaletteCollapseState:
    """Test that collapse state persists via QSettings."""

    def test_collapse_persists(self, palette, qtbot):
        # Collapse the Passive category
        palette._category_items["Passive"].setExpanded(False)
        palette._save_collapse_state()

        # Create a new palette - should restore collapsed state
        p2 = ComponentPalette()
        qtbot.addWidget(p2)
        assert not p2.is_category_expanded("Passive")

        # Clean up: restore default
        settings = QSettings("SDSMT", "SDM Spice")
        settings.remove("palette/collapsed/Passive")

    def test_expand_persists(self, palette, qtbot):
        # Ensure expanded state round-trips
        palette._category_items["Sources"].setExpanded(True)
        palette._save_collapse_state()

        p2 = ComponentPalette()
        qtbot.addWidget(p2)
        assert p2.is_category_expanded("Sources")


class TestComponentPaletteSignals:
    """Test signal emission on interaction."""

    def test_double_click_emits_component_type(self, palette, qtbot):
        cat = palette._category_items["Passive"]
        first_child = cat.child(0)
        with qtbot.waitSignal(palette.componentDoubleClicked, timeout=1000) as blocker:
            palette.tree_widget.itemDoubleClicked.emit(first_child, 0)
        assert blocker.args == [first_child.text(0)]

    def test_double_click_on_category_does_not_emit(self, palette, qtbot):
        cat = palette._category_items["Passive"]
        with qtbot.assertNotEmitted(palette.componentDoubleClicked):
            palette.tree_widget.itemDoubleClicked.emit(cat, 0)


class TestComponentPaletteDragConfig:
    """Test drag-and-drop configuration."""

    def test_drag_enabled(self, palette):
        assert palette.tree_widget.dragEnabled()

    def test_default_drop_action_is_copy(self, palette):
        assert palette.tree_widget.defaultDropAction() == Qt.DropAction.CopyAction


class TestComponentPaletteSearch:
    """Test search/filter functionality."""

    def test_filter_hides_non_matching(self, palette):
        palette.search_input.setText("resistor")
        visible = palette.get_visible_component_names()
        assert "Resistor" in visible
        assert "Capacitor" not in visible

    def test_filter_is_case_insensitive(self, palette):
        palette.search_input.setText("CAPACITOR")
        visible = palette.get_visible_component_names()
        assert "Capacitor" in visible

    def test_empty_filter_shows_all(self, palette):
        palette.search_input.setText("xyz")
        palette.search_input.setText("")
        visible = palette.get_visible_component_names()
        assert len(visible) == len(COMPONENTS)

    def test_filter_matches_tooltip(self, palette):
        # "Resists" appears in the Resistor tooltip
        palette.search_input.setText("resists")
        visible = palette.get_visible_component_names()
        assert "Resistor" in visible

    def test_filter_no_matches(self, palette):
        palette.search_input.setText("xyznonexistent")
        visible = palette.get_visible_component_names()
        assert len(visible) == 0

    def test_search_input_has_placeholder(self, palette):
        assert "filter" in palette.search_input.placeholderText().lower()

    def test_filter_auto_expands_matching_category(self, palette):
        # Collapse Passive, then search for "resistor" - should auto-expand
        palette._category_items["Passive"].setExpanded(False)
        palette.search_input.setText("resistor")
        assert palette.is_category_expanded("Passive")

    def test_filter_hides_empty_categories(self, palette):
        palette.search_input.setText("resistor")
        # Semiconductors should be hidden (no matches)
        assert palette._category_items["Semiconductors"].isHidden()
        # Passive should be visible
        assert not palette._category_items["Passive"].isHidden()
