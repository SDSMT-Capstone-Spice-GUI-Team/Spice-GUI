"""
Unit tests for ComponentPalette.

Tests component listing, signal emission on double-click,
drag support configuration, search filtering, collapsible categories,
recommended components, and used-in-file auto-detection.
"""

import pytest
from controllers.settings_service import settings as app_settings
from GUI.component_palette import _RECOMMENDED_CATEGORY, _USED_IN_FILE_CATEGORY, ComponentPalette
from GUI.styles import COMPONENTS
from models.component import COMPONENT_CATEGORIES
from PyQt6.QtCore import Qt


@pytest.fixture(autouse=True)
def _clear_palette_settings():
    """Clear palette settings before each test to avoid cross-test contamination."""
    for category_name in COMPONENT_CATEGORIES:
        app_settings.set(f"palette/expanded/{category_name}", None)
    yield
    # Cleanup after test too
    for category_name in COMPONENT_CATEGORIES:
        app_settings.set(f"palette/expanded/{category_name}", None)


@pytest.fixture
def palette(qtbot):
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
        for category_item in palette._category_items.values():
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
        app_settings.set("palette/expanded/Passive", False)
        app_settings.set("palette/expanded/Sources", True)
        # Create new palette instance
        p2 = ComponentPalette()
        qtbot.addWidget(p2)
        assert not p2._category_items["Passive"].isExpanded()
        assert p2._category_items["Sources"].isExpanded()


class TestRecommendedComponents:
    """Test file-level recommended components section."""

    def test_set_recommended_creates_section(self, palette):
        palette.set_recommended_components(["Resistor", "Capacitor"])
        assert palette.has_recommendations()
        assert palette._recommended_item is not None
        assert palette._recommended_item.text(0) == _RECOMMENDED_CATEGORY

    def test_set_recommended_children(self, palette):
        palette.set_recommended_components(["Resistor", "Capacitor"])
        child_names = [
            palette._recommended_item.child(i).text(0) for i in range(palette._recommended_item.childCount())
        ]
        assert "Resistor" in child_names
        assert "Capacitor" in child_names

    def test_set_empty_removes_section(self, palette):
        palette.set_recommended_components(["Resistor"])
        assert palette.has_recommendations()
        palette.set_recommended_components([])
        assert not palette.has_recommendations()
        assert palette._recommended_item is None

    def test_get_recommended_returns_copy(self, palette):
        palette.set_recommended_components(["Resistor"])
        result = palette.get_recommended_components()
        assert result == ["Resistor"]
        result.append("Capacitor")
        assert palette.get_recommended_components() == ["Resistor"]

    def test_invalid_names_filtered_out(self, palette):
        palette.set_recommended_components(["Resistor", "NotAComponent"])
        assert palette.get_recommended_components() == ["Resistor"]

    def test_recommended_auto_collapses_categories(self, palette):
        for cat in palette._category_items.values():
            assert cat.isExpanded()
        palette.set_recommended_components(["Resistor"])
        for cat in palette._category_items.values():
            assert not cat.isExpanded()

    def test_recommended_is_expanded(self, palette):
        palette.set_recommended_components(["Resistor"])
        assert palette._recommended_item.isExpanded()

    def test_recommended_at_tree_top(self, palette):
        palette.set_recommended_components(["Resistor"])
        first = palette.tree_widget.topLevelItem(0)
        assert first.text(0) == _RECOMMENDED_CATEGORY


class TestUsedInFile:
    """Test 'Used in File' auto-detection section."""

    def test_update_creates_section(self, palette):
        palette.update_used_in_file(["Resistor", "Capacitor"])
        assert palette._used_in_file_item is not None
        assert palette._used_in_file_item.text(0) == _USED_IN_FILE_CATEGORY

    def test_update_deduplicates(self, palette):
        palette.update_used_in_file(["Resistor", "Resistor", "Capacitor"])
        count = palette._used_in_file_item.childCount()
        assert count == 2

    def test_update_sorts_types(self, palette):
        palette.update_used_in_file(["Resistor", "Capacitor"])
        names = [palette._used_in_file_item.child(i).text(0) for i in range(palette._used_in_file_item.childCount())]
        assert names == sorted(names)

    def test_update_empty_removes_section(self, palette):
        palette.update_used_in_file(["Resistor"])
        assert palette._used_in_file_item is not None
        palette.update_used_in_file([])
        assert palette._used_in_file_item is None

    def test_update_filters_invalid_types(self, palette):
        palette.update_used_in_file(["Resistor", "BogusComponent"])
        count = palette._used_in_file_item.childCount()
        assert count == 1

    def test_used_in_file_children_are_draggable(self, palette):
        palette.update_used_in_file(["Resistor"])
        child = palette._used_in_file_item.child(0)
        assert child.flags() & Qt.ItemFlag.ItemIsDragEnabled

    def test_used_in_file_after_recommended(self, palette):
        palette.set_recommended_components(["Capacitor"])
        palette.update_used_in_file(["Resistor"])
        first = palette.tree_widget.topLevelItem(0)
        second = palette.tree_widget.topLevelItem(1)
        assert first.text(0) == _RECOMMENDED_CATEGORY
        assert second.text(0) == _USED_IN_FILE_CATEGORY

    def test_used_in_file_at_top_when_no_recommended(self, palette):
        palette.update_used_in_file(["Resistor"])
        first = palette.tree_widget.topLevelItem(0)
        assert first.text(0) == _USED_IN_FILE_CATEGORY

    def test_used_in_file_is_expanded(self, palette):
        palette.update_used_in_file(["Resistor"])
        assert palette._used_in_file_item.isExpanded()

    def test_search_filters_used_in_file(self, palette):
        palette.update_used_in_file(["Resistor", "Capacitor"])
        palette.search_input.setText("resistor")
        for i in range(palette._used_in_file_item.childCount()):
            child = palette._used_in_file_item.child(i)
            if child.text(0) == "Resistor":
                assert not child.isHidden()
            elif child.text(0) == "Capacitor":
                assert child.isHidden()


class TestRecommendedComponentsDialog:
    """Test the RecommendedComponentsDialog."""

    def test_dialog_creates(self, qtbot):
        from GUI.recommended_components_dialog import RecommendedComponentsDialog

        dialog = RecommendedComponentsDialog(["Resistor"], None)
        qtbot.addWidget(dialog)
        result = dialog.get_recommended()
        assert "Resistor" in result

    def test_dialog_empty_recommendations(self, qtbot):
        from GUI.recommended_components_dialog import RecommendedComponentsDialog

        dialog = RecommendedComponentsDialog([], None)
        qtbot.addWidget(dialog)
        assert dialog.get_recommended() == []

    def test_dialog_preserves_recommendations(self, qtbot):
        from GUI.recommended_components_dialog import RecommendedComponentsDialog

        recs = ["Resistor", "Capacitor"]
        dialog = RecommendedComponentsDialog(recs, None)
        qtbot.addWidget(dialog)
        result = dialog.get_recommended()
        assert set(result) == set(recs)


class TestCircuitModelRecommendedPersistence:
    """Test that recommended_components persists in CircuitModel serialization."""

    def test_to_dict_includes_recommended(self):
        from models.circuit import CircuitModel

        model = CircuitModel()
        model.recommended_components = ["Resistor", "Capacitor"]
        data = model.to_dict()
        assert data["recommended_components"] == ["Resistor", "Capacitor"]

    def test_to_dict_omits_empty_recommended(self):
        from models.circuit import CircuitModel

        model = CircuitModel()
        data = model.to_dict()
        assert "recommended_components" not in data

    def test_from_dict_restores_recommended(self):
        from models.circuit import CircuitModel

        data = {"recommended_components": ["Resistor", "Inductor"]}
        model = CircuitModel.from_dict(data)
        assert model.recommended_components == ["Resistor", "Inductor"]

    def test_from_dict_defaults_to_empty(self):
        from models.circuit import CircuitModel

        model = CircuitModel.from_dict({})
        assert model.recommended_components == []

    def test_clear_resets_recommended(self):
        from models.circuit import CircuitModel

        model = CircuitModel()
        model.recommended_components = ["Resistor"]
        model.clear()
        assert model.recommended_components == []
