"""Tests that component boundingRect() includes text label extents.

Issue #866: boundingRect() returned a fixed rect but paint() drew variable-width
text labels that extended beyond it. With MinimalViewportUpdate, old text pixels
were never invalidated during drag, leaving rendering artifacts.

Fix: boundingRect() now unions _symbol_rect() with QFontMetrics-measured text.
"""

import pytest


class TestBoundingRectIncludesText:
    """Behavioral tests verifying boundingRect() accounts for text labels."""

    def test_base_bounding_rect_contains_symbol_rect(self):
        """boundingRect() must contain the entire _symbol_rect() area."""
        from GUI.component_item import Resistor

        comp = Resistor("R1")
        symbol = comp._symbol_rect()
        bounding = comp.boundingRect()

        assert bounding.left() <= symbol.left(), "boundingRect left must be <= symbol rect left"
        assert bounding.top() <= symbol.top(), "boundingRect top must be <= symbol rect top"
        assert bounding.right() >= symbol.right(), "boundingRect right must be >= symbol rect right"
        assert bounding.bottom() >= symbol.bottom(), "boundingRect bottom must be >= symbol rect bottom"

    def test_base_bounding_rect_larger_than_symbol_rect_when_labels_shown(self):
        """boundingRect() must be larger than _symbol_rect() when labels are visible."""
        from GUI.component_item import Resistor

        comp = Resistor("R1")
        symbol = comp._symbol_rect()
        bounding = comp.boundingRect()

        # With labels shown (the default when canvas is None), text is included
        symbol_area = symbol.width() * symbol.height()
        bounding_area = bounding.width() * bounding.height()
        assert (
            bounding_area > symbol_area
        ), "boundingRect() area must exceed _symbol_rect() area when text labels are included"

    def test_base_bounding_rect_equals_symbol_rect_when_labels_hidden(self):
        """boundingRect() must equal _symbol_rect() when both label and value are hidden."""
        from unittest.mock import MagicMock

        from GUI.component_item import Resistor

        comp = Resistor("R1")
        # Attach a mock canvas that hides both label and value
        canvas = MagicMock()
        canvas.show_component_labels = False
        canvas.show_component_values = False
        comp.canvas = canvas

        symbol = comp._symbol_rect()
        bounding = comp.boundingRect()

        assert bounding.contains(symbol), "boundingRect() must contain _symbol_rect() when no text is shown"

    def test_label_text_helper_exists(self):
        """_label_text() helper must exist for boundingRect() to measure."""
        from GUI.component_item import ComponentGraphicsItem

        assert hasattr(ComponentGraphicsItem, "_label_text")
        assert callable(ComponentGraphicsItem._label_text)

    def test_subclasses_override_symbol_rect_not_bounding_rect(self):
        """Subclasses with custom geometry must override _symbol_rect(), not boundingRect()."""
        from GUI.component_item import (
            BJTNPN,
            BJTPNP,
            CCCS,
            CCVS,
            VCCS,
            VCVS,
            ComponentGraphicsItem,
            OpAmp,
            Transformer,
            VCSwitch,
        )

        subclasses_with_custom_rect = [
            OpAmp,
            VCVS,
            CCVS,
            VCCS,
            CCCS,
            BJTNPN,
            BJTPNP,
            VCSwitch,
            Transformer,
        ]
        for cls in subclasses_with_custom_rect:
            # _symbol_rect must be overridden
            assert (
                cls._symbol_rect is not ComponentGraphicsItem._symbol_rect
            ), f"{cls.__name__} must override _symbol_rect()"
            # boundingRect must NOT be overridden (inherits text-aware version)
            assert (
                cls.boundingRect is ComponentGraphicsItem.boundingRect
            ), f"{cls.__name__} must not override boundingRect() — override _symbol_rect() instead"

    def test_obstacle_shape_matches_symbol_rect_not_bounding_rect(self):
        """_bounding_rect_obstacle must produce a polygon matching _symbol_rect(), not boundingRect()."""
        from GUI.component_item import Resistor
        from GUI.renderers import _bounding_rect_obstacle

        comp = Resistor("R1")
        symbol = comp._symbol_rect()
        bounding = comp.boundingRect()

        obstacle = _bounding_rect_obstacle(comp)

        # The obstacle polygon corners must match the symbol rect corners exactly
        expected = [
            (symbol.left(), symbol.top()),
            (symbol.right(), symbol.top()),
            (symbol.right(), symbol.bottom()),
            (symbol.left(), symbol.bottom()),
        ]
        assert obstacle == expected, "Obstacle shape must be derived from _symbol_rect()"

        # Verify the obstacle does NOT match the (larger) bounding rect corners
        bounding_corners = [
            (bounding.left(), bounding.top()),
            (bounding.right(), bounding.top()),
            (bounding.right(), bounding.bottom()),
            (bounding.left(), bounding.bottom()),
        ]
        assert (
            obstacle != bounding_corners
        ), "Obstacle shape must not be derived from boundingRect() — it would include text area"
