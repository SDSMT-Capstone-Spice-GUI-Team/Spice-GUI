"""
Unit tests for ComponentPalette.

Tests component listing, categories, pinned favorites, signal emission
on double-click, drag support configuration, search filtering, and
collapse persistence.
"""

import pytest
from GUI.component_palette import COMPONENT_CATEGORIES, ComponentPalette
from GUI.styles import COMPONENTS
from PyQt6.QtCore import QSettings, Qt


@pytest.fixture
def palette(qtbot):
    # Clean up any leftover favorites from prior runs
    QSettings("SDSMT", "SDM Spice").remove("palette/favorites")
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
        for cat_name, cat_item in palette._category_items.items():
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
        palette._category_items["Passive"].setExpanded(False)
        palette._save_collapse_state()

        p2 = ComponentPalette()
        qtbot.addWidget(p2)
        assert not p2.is_category_expanded("Passive")

        settings = QSettings("SDSMT", "SDM Spice")
        settings.remove("palette/collapsed/Passive")

    def test_expand_persists(self, palette, qtbot):
        palette._category_items["Sources"].setExpanded(True)
        palette._save_collapse_state()

        p2 = ComponentPalette()
        qtbot.addWidget(p2)
        assert p2.is_category_expanded("Sources")


class TestComponentPaletteFavorites:
    """Test pinned favorites functionality."""

    def test_no_favorites_by_default(self, palette):
        assert palette.get_favorites() == []

    def test_favorites_section_hidden_when_empty(self, palette):
        assert palette._favorites_item.isHidden()

    def test_favorites_not_in_category_names_when_empty(self, palette):
        assert "Favorites" not in palette.get_category_names()

    def test_pin_favorite(self, palette):
        palette._pin_favorite("Resistor")
        assert "Resistor" in palette.get_favorites()
        assert not palette._favorites_item.isHidden()

        # Clean up
        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_unpin_favorite(self, palette):
        palette._pin_favorite("Resistor")
        palette._unpin_favorite("Resistor")
        assert "Resistor" not in palette.get_favorites()
        assert palette._favorites_item.isHidden()

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_favorites_appear_in_category_names(self, palette):
        palette._pin_favorite("Capacitor")
        assert "Favorites" in palette.get_category_names()

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_favorite_has_icon(self, palette):
        palette._pin_favorite("Resistor")
        fav_child = palette._favorites_item.child(0)
        assert not fav_child.icon(0).isNull()

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_favorite_has_tooltip(self, palette):
        palette._pin_favorite("Resistor")
        fav_child = palette._favorites_item.child(0)
        assert "Resists" in fav_child.toolTip(0)

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_favorites_persist_across_instances(self, palette, qtbot):
        palette._pin_favorite("Inductor")

        p2 = ComponentPalette()
        qtbot.addWidget(p2)
        assert "Inductor" in p2.get_favorites()
        assert not p2._favorites_item.isHidden()

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_duplicate_pin_ignored(self, palette):
        palette._pin_favorite("Resistor")
        palette._pin_favorite("Resistor")
        assert palette.get_favorites().count("Resistor") == 1

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_favorites_section_is_expanded(self, palette):
        palette._pin_favorite("Resistor")
        assert palette.is_category_expanded("Favorites")

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_component_still_in_original_category(self, palette):
        palette._pin_favorite("Resistor")
        # Resistor should still be in Passive
        cat = palette._category_items["Passive"]
        children = [cat.child(i).text(0) for i in range(cat.childCount())]
        assert "Resistor" in children

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_double_click_on_favorite_emits_signal(self, palette, qtbot):
        palette._pin_favorite("Capacitor")
        fav_child = palette._favorites_item.child(0)
        with qtbot.waitSignal(palette.componentDoubleClicked, timeout=1000) as blocker:
            palette.tree_widget.itemDoubleClicked.emit(fav_child, 0)
        assert blocker.args == ["Capacitor"]

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")

    def test_favorite_items_are_draggable(self, palette):
        palette._pin_favorite("Resistor")
        fav_child = palette._favorites_item.child(0)
        assert fav_child.flags() & Qt.ItemFlag.ItemIsDragEnabled

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")


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
        palette._category_items["Passive"].setExpanded(False)
        palette.search_input.setText("resistor")
        assert palette.is_category_expanded("Passive")

    def test_filter_hides_empty_categories(self, palette):
        palette.search_input.setText("resistor")
        assert palette._category_items["Semiconductors"].isHidden()
        assert not palette._category_items["Passive"].isHidden()

    def test_search_includes_favorites(self, palette):
        palette._pin_favorite("Resistor")
        palette.search_input.setText("resistor")
        # Favorites section should be visible with matching favorite
        assert not palette._favorites_item.isHidden()
        fav_child = palette._favorites_item.child(0)
        assert not fav_child.isHidden()

        QSettings("SDSMT", "SDM Spice").remove("palette/favorites")
