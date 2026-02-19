"""
Unit tests for ComponentPalette.

Tests component listing, signal emission on double-click,
drag support configuration, search filtering, collapsible categories, and pinned favorites.
"""

from unittest.mock import patch

import pytest
from GUI.component_palette import ITEM_ROLE, ITEM_TYPE_COMPONENT, ITEM_TYPE_FAVORITE, ITEM_TYPE_HEADER, ComponentPalette
from GUI.styles import COMPONENTS
from models.component import COMPONENT_CATEGORIES
from PyQt6.QtCore import QSettings, Qt


@pytest.fixture(autouse=True)
def _clear_palette_settings():
    """Clear palette QSettings before each test to avoid cross-test contamination."""
    settings = QSettings("SDSMT", "SDM Spice")
    for category_name in COMPONENT_CATEGORIES:
        settings.remove(f"palette/expanded/{category_name}")
    settings.remove("palette/favorites")
    yield
    # Cleanup after test too
    for category_name in COMPONENT_CATEGORIES:
        settings.remove(f"palette/expanded/{category_name}")
    settings.remove("palette/favorites")


@pytest.fixture
def palette(qtbot):
    with patch("GUI.component_palette._load_favorites", return_value=[]):
        p = ComponentPalette()
        qtbot.addWidget(p)
    return p


@pytest.fixture
def palette_with_favorites(qtbot):
    with patch(
        "GUI.component_palette._load_favorites",
        return_value=["Resistor", "Capacitor"],
    ):
        p = ComponentPalette()
        qtbot.addWidget(p)
    return p


def _visible_component_names(palette):
    """Return names of all visible (non-hidden) component items."""
    names = []
    for item in palette.get_all_component_items():
        if not item.isHidden():
            parent = item.parent()
            if parent is not None and not parent.isHidden():
                names.append(item.text(0))
    return names


def _all_visible_names(palette):
    """Return visible component names (both favorites and regular categories)."""
    names = []
    # Include favorites
    for item in palette.get_favorite_items():
        if not item.isHidden():
            parent = item.parent()
            if parent is not None and not parent.isHidden():
                names.append(item.text(0))
    # Include regular components
    names.extend(_visible_component_names(palette))
    return names


class TestComponentPaletteContents:
    """Test that palette lists all expected components."""

    def test_lists_all_component_types(self, palette):
        item_texts = [item.text(0) for item in palette.get_all_component_items()]
        for comp_type in COMPONENTS:
            assert comp_type in item_texts

    def test_item_count_matches_components(self, palette):
        assert len(palette.get_all_component_items()) == len(COMPONENTS)

    def test_items_have_icons(self, palette):
        for item in palette.get_all_component_items():
            assert not item.icon(0).isNull()

    def test_items_have_component_data_role(self, palette):
        for item in palette.get_all_component_items():
            assert item.data(0, ITEM_ROLE) == ITEM_TYPE_COMPONENT


class TestComponentPaletteSignals:
    """Test signal emission on interaction."""

    def test_double_click_emits_component_type(self, palette, qtbot):
        first_item = palette.get_all_component_items()[0]
        with qtbot.waitSignal(palette.componentDoubleClicked, timeout=1000) as blocker:
            palette.tree_widget.itemDoubleClicked.emit(first_item, 0)
        assert blocker.args == [first_item.text(0)]

    def test_double_click_on_category_does_not_emit(self, palette, qtbot):
        category_item = list(palette._category_items.values())[0]
        with qtbot.assertNotEmitted(palette.componentDoubleClicked):
            palette.tree_widget.itemDoubleClicked.emit(category_item, 0)


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
        visible = _visible_component_names(palette)
        assert "Resistor" in visible
        assert "Capacitor" not in visible

    def test_filter_is_case_insensitive(self, palette):
        palette.search_input.setText("CAPACITOR")
        visible = _visible_component_names(palette)
        assert "Capacitor" in visible

    def test_empty_filter_shows_all(self, palette):
        palette.search_input.setText("xyz")
        palette.search_input.setText("")
        visible = _visible_component_names(palette)
        assert len(visible) == len(COMPONENTS)

    def test_filter_matches_tooltip(self, palette):
        # "Resists" appears in the Resistor tooltip
        palette.search_input.setText("resists")
        visible = _visible_component_names(palette)
        assert "Resistor" in visible

    def test_filter_no_matches(self, palette):
        palette.search_input.setText("xyznonexistent")
        visible = _visible_component_names(palette)
        assert len(visible) == 0

    def test_search_input_has_placeholder(self, palette):
        assert "filter" in palette.search_input.placeholderText().lower()


class TestComponentPaletteCategories:
    """Test collapsible category group functionality."""

    def test_all_categories_present(self, palette):
        for category_name in COMPONENT_CATEGORIES:
            assert category_name in palette._category_items

    def test_category_count(self, palette):
        assert len(palette._category_items) == len(COMPONENT_CATEGORIES)

    def test_categories_default_expanded(self, palette):
        for name, category_item in palette._category_items.items():
            assert category_item.isExpanded()

    def test_category_collapse_and_expand(self, palette):
        cat_item = list(palette._category_items.values())[0]
        cat_item.setExpanded(False)
        assert not cat_item.isExpanded()
        cat_item.setExpanded(True)
        assert cat_item.isExpanded()

    def test_category_items_are_not_draggable(self, palette):
        for category_item in palette._category_items.values():
            flags = category_item.flags()
            assert not (flags & Qt.ItemFlag.ItemIsDragEnabled)

    def test_component_items_are_draggable(self, palette):
        for item in palette.get_all_component_items():
            flags = item.flags()
            assert flags & Qt.ItemFlag.ItemIsDragEnabled

    def test_search_auto_expands_matching_categories(self, palette):
        # Collapse all categories first
        for cat_item in palette._category_items.values():
            cat_item.setExpanded(False)
        # Search for a passive component
        palette.search_input.setText("resistor")
        assert palette._category_items["Passive"].isExpanded()

    def test_search_hides_non_matching_categories(self, palette):
        palette.search_input.setText("resistor")
        # Semiconductors category should be hidden (no match)
        assert palette._category_items["Semiconductors"].isHidden()
        # Passive category should be visible
        assert not palette._category_items["Passive"].isHidden()

    def test_clear_search_restores_collapsed_state(self, palette):
        # Collapse one category
        palette._category_items["Passive"].setExpanded(False)
        palette._save_expanded_state()
        # Search expands it
        palette.search_input.setText("resistor")
        assert palette._category_items["Passive"].isExpanded()
        # Clear search restores collapsed state
        palette.search_input.setText("")
        assert not palette._category_items["Passive"].isExpanded()

    def test_components_grouped_correctly(self, palette):
        for category_name, expected_components in COMPONENT_CATEGORIES.items():
            category_item = palette._category_items[category_name]
            actual_names = [category_item.child(i).text(0) for i in range(category_item.childCount())]
            for comp_name in expected_components:
                if comp_name in COMPONENTS:
                    assert comp_name in actual_names


class TestComponentPaletteSettingsPersistence:
    """Test QSettings persistence of expanded/collapsed state."""

    def test_save_and_load_expanded_state(self, palette):
        # Collapse a category
        palette._category_items["Passive"].setExpanded(False)
        palette._save_expanded_state()
        # Verify saved state
        state = palette._load_expanded_state()
        assert state["Passive"] is False
        # Verify others remain expanded
        assert state["Sources"] is True

    def test_new_palette_loads_saved_state(self, qtbot):
        # Save collapsed state
        settings = QSettings("SDSMT", "SDM Spice")
        settings.setValue("palette/expanded/Passive", False)
        settings.setValue("palette/expanded/Sources", True)
        # Create new palette instance
        with patch("GUI.component_palette._load_favorites", return_value=[]):
            p2 = ComponentPalette()
            qtbot.addWidget(p2)
        assert not p2._category_items["Passive"].isExpanded()
        assert p2._category_items["Sources"].isExpanded()


class TestPinnedFavorites:
    """Test pinned favorites functionality."""

    def test_no_favorites_section_when_empty(self, palette):
        """Favorites header should not appear when no favorites are pinned."""
        from GUI.component_palette import FAVORITES_HEADER_TEXT

        assert FAVORITES_HEADER_TEXT not in palette._category_items

    def test_favorites_section_appears_when_pinned(self, palette_with_favorites):
        """Favorites header and items should appear when favorites exist."""
        from GUI.component_palette import FAVORITES_HEADER_TEXT

        assert FAVORITES_HEADER_TEXT in palette_with_favorites._category_items
        fav_items = palette_with_favorites.get_favorite_items()
        assert len(fav_items) == 2
        assert fav_items[0].text(0) == "Resistor"
        assert fav_items[0].data(0, ITEM_ROLE) == ITEM_TYPE_FAVORITE
        assert fav_items[1].text(0) == "Capacitor"
        assert fav_items[1].data(0, ITEM_ROLE) == ITEM_TYPE_FAVORITE

    def test_favorites_still_appear_in_main_list(self, palette_with_favorites):
        """Pinned components should still appear in their regular category position."""
        item_texts = [item.text(0) for item in palette_with_favorites.get_all_component_items()]
        assert "Resistor" in item_texts
        assert "Capacitor" in item_texts

    def test_pin_favorite(self, palette):
        """Pinning a favorite should add it to the favorites section."""
        with patch("GUI.component_palette._save_favorites"):
            palette._pin_favorite("Inductor")
        assert "Inductor" in palette.get_favorites()
        # Check it appears in the favorites section
        fav_items = palette.get_favorite_items()
        assert len(fav_items) == 1
        assert fav_items[0].text(0) == "Inductor"
        assert fav_items[0].data(0, ITEM_ROLE) == ITEM_TYPE_FAVORITE

    def test_unpin_favorite(self, palette_with_favorites):
        """Unpinning removes a component from favorites."""
        with patch("GUI.component_palette._save_favorites"):
            palette_with_favorites._unpin_favorite("Resistor")
        assert "Resistor" not in palette_with_favorites.get_favorites()
        assert "Capacitor" in palette_with_favorites.get_favorites()

    def test_unpin_all_removes_favorites_section(self, palette_with_favorites):
        """Removing all favorites should hide the entire favorites section."""
        from GUI.component_palette import FAVORITES_HEADER_TEXT

        with patch("GUI.component_palette._save_favorites"):
            palette_with_favorites._unpin_favorite("Resistor")
            palette_with_favorites._unpin_favorite("Capacitor")
        assert FAVORITES_HEADER_TEXT not in palette_with_favorites._category_items

    def test_pin_duplicate_is_noop(self, palette_with_favorites):
        """Pinning an already-pinned component should not duplicate it."""
        with patch("GUI.component_palette._save_favorites"):
            palette_with_favorites._pin_favorite("Resistor")
        assert palette_with_favorites.get_favorites().count("Resistor") == 1

    def test_search_includes_favorites(self, palette_with_favorites):
        """Search filter should show matching favorites."""
        palette_with_favorites.search_input.setText("resistor")
        fav_items = palette_with_favorites.get_favorite_items()
        found_visible_favorite = False
        for item in fav_items:
            if item.text(0) == "Resistor" and not item.isHidden():
                found_visible_favorite = True
                break
        assert found_visible_favorite

    def test_search_hides_favorites_header_when_no_match(self, palette_with_favorites):
        """Favorites category should be hidden when no favorites match search."""
        from GUI.component_palette import FAVORITES_HEADER_TEXT

        palette_with_favorites.search_input.setText("xyznonexistent")
        fav_category = palette_with_favorites._category_items[FAVORITES_HEADER_TEXT]
        assert fav_category.isHidden()

    def test_search_shows_favorites_header_when_match(self, palette_with_favorites):
        """Favorites category should be visible when a favorite matches search."""
        from GUI.component_palette import FAVORITES_HEADER_TEXT

        palette_with_favorites.search_input.setText("resistor")
        fav_category = palette_with_favorites._category_items[FAVORITES_HEADER_TEXT]
        assert not fav_category.isHidden()

    def test_double_click_favorites_header_does_not_emit(self, palette_with_favorites, qtbot):
        """Double-clicking the favorites category header should not emit componentDoubleClicked."""
        from GUI.component_palette import FAVORITES_HEADER_TEXT

        fav_category = palette_with_favorites._category_items[FAVORITES_HEADER_TEXT]
        emitted = []
        palette_with_favorites.componentDoubleClicked.connect(lambda x: emitted.append(x))
        palette_with_favorites._on_item_double_clicked(fav_category, 0)
        assert len(emitted) == 0

    def test_double_click_favorite_emits_signal(self, palette_with_favorites, qtbot):
        """Double-clicking a favorite item should emit componentDoubleClicked."""
        fav_items = palette_with_favorites.get_favorite_items()
        first_fav = fav_items[0]  # Resistor
        with qtbot.waitSignal(palette_with_favorites.componentDoubleClicked, timeout=1000) as blocker:
            palette_with_favorites.tree_widget.itemDoubleClicked.emit(first_fav, 0)
        assert blocker.args == ["Resistor"]

    def test_get_favorites_returns_copy(self, palette_with_favorites):
        """get_favorites should return a copy, not a reference."""
        favs = palette_with_favorites.get_favorites()
        favs.append("Ground")
        assert "Ground" not in palette_with_favorites.get_favorites()

    def test_favorite_items_are_draggable(self, palette_with_favorites):
        """Favorite items should be draggable."""
        for item in palette_with_favorites.get_favorite_items():
            flags = item.flags()
            assert flags & Qt.ItemFlag.ItemIsDragEnabled


class TestFavoritesPersistence:
    """Test that favorites persist via QSettings."""

    def test_save_favorites_called_on_pin(self, palette):
        """Pinning should save to QSettings."""
        with patch("GUI.component_palette._save_favorites") as mock_save:
            palette._pin_favorite("Inductor")
            mock_save.assert_called_once_with(["Inductor"])

    def test_save_favorites_called_on_unpin(self, palette_with_favorites):
        """Unpinning should save to QSettings."""
        with patch("GUI.component_palette._save_favorites") as mock_save:
            palette_with_favorites._unpin_favorite("Resistor")
            mock_save.assert_called_once_with(["Capacitor"])
