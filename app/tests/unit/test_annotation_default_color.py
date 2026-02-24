"""
Unit tests for Issue #509: Annotation default color should be visible on all themes.

The old default (#FFFFFF / white) was invisible on light backgrounds.
The new default uses theme_manager.color_hex("text_primary") which adapts
to the active theme.
"""

from unittest.mock import patch

import pytest
from models.annotation import AnnotationData


class TestAnnotationDataDefaultColor:
    """Test that AnnotationData default color is no longer hardcoded white."""

    def test_default_color_is_empty_sentinel(self):
        """Default color should be empty string (resolved at UI layer)."""
        ann = AnnotationData(text="hello")
        assert ann.color == ""

    def test_explicit_color_preserved(self):
        """An explicit color should be kept as-is."""
        ann = AnnotationData(text="hello", color="#FF0000")
        assert ann.color == "#FF0000"

    def test_from_dict_without_color_uses_sentinel(self):
        """Loading a dict with no color key should use empty sentinel."""
        ann = AnnotationData.from_dict({"text": "hi"})
        assert ann.color == ""

    def test_from_dict_with_explicit_color_preserved(self):
        """Loading a dict with an explicit color should keep it."""
        ann = AnnotationData.from_dict({"text": "hi", "color": "#00FF00"})
        assert ann.color == "#00FF00"

    def test_to_dict_round_trip(self):
        """to_dict / from_dict preserves explicit color."""
        original = AnnotationData(text="test", color="#123456")
        restored = AnnotationData.from_dict(original.to_dict())
        assert restored.color == "#123456"


class TestAnnotationItemDefaultColor:
    """Test that AnnotationItem resolves empty color to theme default."""

    def test_empty_color_resolved_to_theme(self):
        """Empty color should be resolved via theme_manager."""
        with patch("GUI.annotation_item.theme_manager") as mock_tm:
            mock_tm.color_hex.return_value = "#000000"
            from GUI.annotation_item import AnnotationItem

            ann = AnnotationItem(text="hello", color="")
            assert ann._color_hex == "#000000"
            mock_tm.color_hex.assert_called_with("text_primary")

    def test_explicit_color_not_overridden(self):
        """Explicit color should not be replaced by theme color."""
        with patch("GUI.annotation_item.theme_manager") as mock_tm:
            mock_tm.color_hex.return_value = "#000000"
            from GUI.annotation_item import AnnotationItem

            ann = AnnotationItem(text="hello", color="#FF0000")
            assert ann._color_hex == "#FF0000"
            mock_tm.color_hex.assert_not_called()

    def test_from_dict_no_color_uses_theme(self):
        """from_dict without color key should resolve to theme default."""
        with patch("GUI.annotation_item.theme_manager") as mock_tm:
            mock_tm.color_hex.return_value = "#D4D4D4"
            from GUI.annotation_item import AnnotationItem

            ann = AnnotationItem.from_dict({"text": "test"})
            assert ann._color_hex == "#D4D4D4"

    def test_from_dict_with_color_preserves_it(self):
        """from_dict with explicit color should not consult theme."""
        with patch("GUI.annotation_item.theme_manager") as mock_tm:
            mock_tm.color_hex.return_value = "#000000"
            from GUI.annotation_item import AnnotationItem

            ann = AnnotationItem.from_dict({"text": "test", "color": "#ABCDEF"})
            assert ann._color_hex == "#ABCDEF"
