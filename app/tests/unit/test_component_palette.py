"""
Unit tests for ComponentPalette.

Tests component listing, signal emission on double-click,
drag support configuration, search filtering, and pinned favorites.
"""

from unittest.mock import patch

import pytest
from GUI.component_palette import ITEM_ROLE, ITEM_TYPE_COMPONENT, ITEM_TYPE_FAVORITE, ITEM_TYPE_HEADER, ComponentPalette
from GUI.styles import COMPONENTS
from PyQt6.QtCore import Qt


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


def _component_items(palette):
    """Return list widget items that are regular components (not headers/favorites)."""
    lw = palette.list_widget
    return [lw.item(i) for i in range(lw.count()) if lw.item(i).data(ITEM_ROLE) == ITEM_TYPE_COMPONENT]


def _all_visible_component_names(palette):
    """Return visible component names (both favorites and regular)."""
    lw = palette.list_widget
    names = []
    for i in range(lw.count()):
        item = lw.item(i)
        if item.data(ITEM_ROLE) == ITEM_TYPE_HEADER:
            continue
        if not item.isHidden():
            names.append(item.text())
    return names


class TestComponentPaletteContents:
    """Test that palette lists all expected components."""

    def test_lists_all_component_types(self, palette):
        items = _component_items(palette)
        item_texts = [item.text() for item in items]
        for comp_type in COMPONENTS:
            assert comp_type in item_texts

    def test_item_count_matches_components(self, palette):
        items = _component_items(palette)
        assert len(items) == len(COMPONENTS)

    def test_items_have_icons(self, palette):
        items = _component_items(palette)
        for item in items:
            assert not item.icon().isNull()

    def test_items_have_component_data_role(self, palette):
        items = _component_items(palette)
        for item in items:
            assert item.data(ITEM_ROLE) == ITEM_TYPE_COMPONENT


class TestComponentPaletteSignals:
    """Test signal emission on interaction."""

    def test_double_click_emits_component_type(self, palette, qtbot):
        lw = palette.list_widget
        first_component = _component_items(palette)[0]
        with qtbot.waitSignal(palette.componentDoubleClicked, timeout=1000) as blocker:
            lw.itemDoubleClicked.emit(first_component)
        assert blocker.args == [first_component.text()]


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
        visible = _all_visible_component_names(palette)
        assert "Resistor" in visible
        assert "Capacitor" not in visible

    def test_filter_is_case_insensitive(self, palette):
        palette.search_input.setText("CAPACITOR")
        visible = _all_visible_component_names(palette)
        assert "Capacitor" in visible

    def test_empty_filter_shows_all(self, palette):
        palette.search_input.setText("xyz")
        palette.search_input.setText("")
        visible = _all_visible_component_names(palette)
        assert len(visible) == len(COMPONENTS)

    def test_filter_matches_tooltip(self, palette):
        # "Resists" appears in the Resistor tooltip
        palette.search_input.setText("resists")
        visible = _all_visible_component_names(palette)
        assert "Resistor" in visible

    def test_filter_no_matches(self, palette):
        palette.search_input.setText("xyznonexistent")
        visible = _all_visible_component_names(palette)
        assert len(visible) == 0

    def test_search_input_has_placeholder(self, palette):
        assert "filter" in palette.search_input.placeholderText().lower()


class TestPinnedFavorites:
    """Test pinned favorites functionality."""

    def test_no_favorites_section_when_empty(self, palette):
        """Favorites header should not appear when no favorites are pinned."""
        lw = palette.list_widget
        for i in range(lw.count()):
            assert lw.item(i).data(ITEM_ROLE) != ITEM_TYPE_HEADER
            assert lw.item(i).data(ITEM_ROLE) != ITEM_TYPE_FAVORITE

    def test_favorites_section_appears_when_pinned(self, palette_with_favorites):
        """Favorites header and items should appear when favorites exist."""
        lw = palette_with_favorites.list_widget
        first_item = lw.item(0)
        assert first_item.data(ITEM_ROLE) == ITEM_TYPE_HEADER
        assert lw.item(1).data(ITEM_ROLE) == ITEM_TYPE_FAVORITE
        assert lw.item(1).text() == "Resistor"
        assert lw.item(2).data(ITEM_ROLE) == ITEM_TYPE_FAVORITE
        assert lw.item(2).text() == "Capacitor"

    def test_favorites_still_appear_in_main_list(self, palette_with_favorites):
        """Pinned components should still appear in their regular position."""
        items = _component_items(palette_with_favorites)
        item_texts = [item.text() for item in items]
        assert "Resistor" in item_texts
        assert "Capacitor" in item_texts

    def test_pin_favorite(self, palette):
        """Pinning a favorite should add it to the favorites section."""
        with patch("GUI.component_palette._save_favorites"):
            palette._pin_favorite("Inductor")
        assert "Inductor" in palette.get_favorites()
        # Check it appears in the list
        lw = palette.list_widget
        assert lw.item(0).data(ITEM_ROLE) == ITEM_TYPE_HEADER
        assert lw.item(1).data(ITEM_ROLE) == ITEM_TYPE_FAVORITE
        assert lw.item(1).text() == "Inductor"

    def test_unpin_favorite(self, palette_with_favorites):
        """Unpinning removes a component from favorites."""
        with patch("GUI.component_palette._save_favorites"):
            palette_with_favorites._unpin_favorite("Resistor")
        assert "Resistor" not in palette_with_favorites.get_favorites()
        assert "Capacitor" in palette_with_favorites.get_favorites()

    def test_unpin_all_removes_favorites_section(self, palette_with_favorites):
        """Removing all favorites should hide the entire favorites section."""
        with patch("GUI.component_palette._save_favorites"):
            palette_with_favorites._unpin_favorite("Resistor")
            palette_with_favorites._unpin_favorite("Capacitor")
        lw = palette_with_favorites.list_widget
        for i in range(lw.count()):
            assert lw.item(i).data(ITEM_ROLE) != ITEM_TYPE_HEADER
            assert lw.item(i).data(ITEM_ROLE) != ITEM_TYPE_FAVORITE

    def test_pin_duplicate_is_noop(self, palette_with_favorites):
        """Pinning an already-pinned component should not duplicate it."""
        with patch("GUI.component_palette._save_favorites"):
            palette_with_favorites._pin_favorite("Resistor")
        assert palette_with_favorites.get_favorites().count("Resistor") == 1

    def test_search_includes_favorites(self, palette_with_favorites):
        """Search filter should show matching favorites."""
        palette_with_favorites.search_input.setText("resistor")
        lw = palette_with_favorites.list_widget
        # Check that a favorite Resistor item is visible
        found_visible_favorite = False
        for i in range(lw.count()):
            item = lw.item(i)
            if item.data(ITEM_ROLE) == ITEM_TYPE_FAVORITE and item.text() == "Resistor" and not item.isHidden():
                found_visible_favorite = True
                break
        assert found_visible_favorite

    def test_search_hides_favorites_header_when_no_match(self, palette_with_favorites):
        """Favorites header should be hidden when no favorites match search."""
        palette_with_favorites.search_input.setText("xyznonexistent")
        lw = palette_with_favorites.list_widget
        header = lw.item(0)
        assert header.data(ITEM_ROLE) == ITEM_TYPE_HEADER
        assert header.isHidden()

    def test_search_shows_favorites_header_when_match(self, palette_with_favorites):
        """Favorites header should be visible when a favorite matches search."""
        palette_with_favorites.search_input.setText("resistor")
        lw = palette_with_favorites.list_widget
        header = lw.item(0)
        assert header.data(ITEM_ROLE) == ITEM_TYPE_HEADER
        assert not header.isHidden()

    def test_double_click_header_does_not_emit(self, palette_with_favorites, qtbot):
        """Double-clicking the header should not emit componentDoubleClicked."""
        lw = palette_with_favorites.list_widget
        header = lw.item(0)
        assert header.data(ITEM_ROLE) == ITEM_TYPE_HEADER
        # Should not emit signal — no timeout needed, just verify no error
        emitted = []
        palette_with_favorites.componentDoubleClicked.connect(lambda x: emitted.append(x))
        palette_with_favorites._on_item_double_clicked(header)
        assert len(emitted) == 0

    def test_double_click_favorite_emits_signal(self, palette_with_favorites, qtbot):
        """Double-clicking a favorite item should emit componentDoubleClicked."""
        lw = palette_with_favorites.list_widget
        fav_item = lw.item(1)  # First favorite (Resistor)
        assert fav_item.data(ITEM_ROLE) == ITEM_TYPE_FAVORITE
        with qtbot.waitSignal(palette_with_favorites.componentDoubleClicked, timeout=1000) as blocker:
            lw.itemDoubleClicked.emit(fav_item)
        assert blocker.args == ["Resistor"]

    def test_get_favorites_returns_copy(self, palette_with_favorites):
        """get_favorites should return a copy, not a reference."""
        favs = palette_with_favorites.get_favorites()
        favs.append("Ground")
        assert "Ground" not in palette_with_favorites.get_favorites()


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
