"""
Unit tests for ComponentPalette.

Tests component listing, signal emission on double-click,
and drag support configuration.
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
        item_texts = [palette.item(i).text() for i in range(palette.count())]
        for comp_type in COMPONENTS:
            assert comp_type in item_texts

    def test_item_count_matches_components(self, palette):
        assert palette.count() == len(COMPONENTS)

    def test_items_have_icons(self, palette):
        for i in range(palette.count()):
            assert not palette.item(i).icon().isNull()


class TestComponentPaletteSignals:
    """Test signal emission on interaction."""

    def test_double_click_emits_component_type(self, palette, qtbot):
        first_item = palette.item(0)
        with qtbot.waitSignal(palette.componentDoubleClicked, timeout=1000) as blocker:
            palette.itemDoubleClicked.emit(first_item)
        assert blocker.args == [first_item.text()]


class TestComponentPaletteDragConfig:
    """Test drag-and-drop configuration."""

    def test_drag_enabled(self, palette):
        assert palette.dragEnabled()

    def test_default_drop_action_is_copy(self, palette):
        assert palette.defaultDropAction() == Qt.DropAction.CopyAction
