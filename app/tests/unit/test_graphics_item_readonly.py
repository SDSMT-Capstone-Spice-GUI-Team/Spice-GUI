"""Verify that ComponentGraphicsItem and WireGraphicsItem treat model as read-only.

These tests enforce the MVC boundary: graphics items expose data properties
as read-only and never bypass the controller to mutate the model directly.
See issue #579.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------------------
# ComponentGraphicsItem property-setter removal
# ---------------------------------------------------------------------------

# We cannot instantiate the full Qt graphics items in headless mode, so we
# verify the *class descriptors* directly — if a property has no setter the
# assignment will raise AttributeError at the language level.


def _make_component_item_class():
    """Import ComponentGraphicsItem, skipping if Qt unavailable."""
    try:
        from GUI.component_item import ComponentGraphicsItem

        return ComponentGraphicsItem
    except (ImportError, RuntimeError):
        pytest.skip("PyQt6 not available in this environment")


def _make_waveform_source_class():
    """Import WaveformVoltageSource, skipping if Qt unavailable."""
    try:
        from GUI.component_item import WaveformVoltageSource

        return WaveformVoltageSource
    except (ImportError, RuntimeError):
        pytest.skip("PyQt6 not available in this environment")


class TestComponentGraphicsItemReadOnly:
    """Ensure data-delegation properties on ComponentGraphicsItem have no setters."""

    def test_value_is_readonly(self):
        cls = _make_component_item_class()
        prop = getattr(cls, "value", None)
        assert isinstance(prop, property), "value should be a property"
        assert prop.fset is None, "value property must not have a setter"

    def test_rotation_angle_is_readonly(self):
        cls = _make_component_item_class()
        prop = getattr(cls, "rotation_angle", None)
        assert isinstance(prop, property), "rotation_angle should be a property"
        assert prop.fset is None, "rotation_angle property must not have a setter"

    def test_initial_condition_is_readonly(self):
        cls = _make_component_item_class()
        prop = getattr(cls, "initial_condition", None)
        assert isinstance(prop, property), "initial_condition should be a property"
        assert prop.fset is None, "initial_condition property must not have a setter"

    def test_component_id_is_readonly(self):
        cls = _make_component_item_class()
        prop = getattr(cls, "component_id", None)
        assert isinstance(prop, property), "component_id should be a property"
        assert prop.fset is None, "component_id property must not have a setter"


class TestWaveformSourceReadOnly:
    """Ensure waveform properties on WaveformVoltageSource have no setters."""

    def test_waveform_type_is_readonly(self):
        cls = _make_waveform_source_class()
        prop = getattr(cls, "waveform_type", None)
        assert isinstance(prop, property), "waveform_type should be a property"
        assert prop.fset is None, "waveform_type property must not have a setter"

    def test_waveform_params_is_readonly(self):
        cls = _make_waveform_source_class()
        prop = getattr(cls, "waveform_params", None)
        assert isinstance(prop, property), "waveform_params should be a property"
        assert prop.fset is None, "waveform_params property must not have a setter"


class TestWireGraphicsItemNoFallback:
    """Ensure WireGraphicsItem delegates routing persistence to canvas only."""

    def test_persist_routing_result_no_fallback(self):
        """_persist_routing_result should be a no-op when canvas is unavailable."""
        try:
            from GUI.wire_item import WireGraphicsItem
        except (ImportError, RuntimeError):
            pytest.skip("PyQt6 not available in this environment")

        import ast
        import inspect
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(WireGraphicsItem._persist_routing_result)))
        # The method should NOT contain direct model mutations like self.model.waypoints
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "waypoints":
                if isinstance(node.value, ast.Attribute) and node.value.attr == "model":
                    raise AssertionError("Found self.model.waypoints in _persist_routing_result")

    def test_finish_waypoint_drag_no_fallback(self):
        """_finish_waypoint_drag should not contain direct model mutation fallback."""
        try:
            from GUI.wire_item import WireGraphicsItem
        except (ImportError, RuntimeError):
            pytest.skip("PyQt6 not available in this environment")

        import ast
        import inspect
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(WireGraphicsItem._finish_waypoint_drag)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("waypoints", "locked"):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "model":
                    raise AssertionError(f"Found self.model.{node.attr} in _finish_waypoint_drag")
