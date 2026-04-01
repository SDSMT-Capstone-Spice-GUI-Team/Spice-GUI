"""Tests that component boundingRect() includes text label extents.

Issue #866: boundingRect() returned a fixed rect but paint() drew variable-width
text labels that extended beyond it. With MinimalViewportUpdate, old text pixels
were never invalidated during drag, leaving rendering artifacts.

Fix: boundingRect() now unions _symbol_rect() with QFontMetrics-measured text.
"""

import inspect
import textwrap

import pytest


class TestBoundingRectIncludesText:
    """Structural tests verifying boundingRect() accounts for text labels."""

    def test_base_bounding_rect_calls_symbol_rect(self):
        """boundingRect() must delegate to _symbol_rect() for the symbol portion."""
        from GUI.component_item import ComponentGraphicsItem

        src = textwrap.dedent(inspect.getsource(ComponentGraphicsItem.boundingRect))
        assert "_symbol_rect()" in src

    def test_base_bounding_rect_uses_font_metrics(self):
        """boundingRect() must measure text with QFontMetricsF."""
        from GUI.component_item import ComponentGraphicsItem

        src = textwrap.dedent(inspect.getsource(ComponentGraphicsItem.boundingRect))
        assert "QFontMetricsF" in src

    def test_base_bounding_rect_unions_text_rect(self):
        """boundingRect() must union the symbol rect with the text rect."""
        from GUI.component_item import ComponentGraphicsItem

        src = textwrap.dedent(inspect.getsource(ComponentGraphicsItem.boundingRect))
        assert ".united(" in src

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

    def test_obstacle_shape_uses_symbol_rect(self):
        """_bounding_rect_obstacle must use _symbol_rect, not boundingRect."""
        from GUI.renderers import _bounding_rect_obstacle

        src = textwrap.dedent(inspect.getsource(_bounding_rect_obstacle))
        assert "_symbol_rect()" in src
        assert "boundingRect" not in src
