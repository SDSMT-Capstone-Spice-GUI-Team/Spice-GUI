"""Verify that ComponentGraphicsItem and WireGraphicsItem treat model as read-only.

These tests enforce the MVC boundary: graphics items expose data properties
as read-only and never bypass the controller to mutate the model directly.
See issue #579.
"""

import pytest

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


def _make_wire_item(canvas=None, waypoints=None):
    """Construct a WireGraphicsItem with mocked components, skipping if Qt unavailable."""
    try:
        from unittest.mock import MagicMock

        from GUI.wire_item import WireGraphicsItem
        from models.wire import WireData
        from PyQt6.QtCore import QPointF
    except (ImportError, RuntimeError):
        pytest.skip("PyQt6 not available in this environment")

    model = WireData(
        start_component_id="R1",
        start_terminal=0,
        end_component_id="R2",
        end_terminal=1,
        waypoints=waypoints or [],
    )

    start_comp = MagicMock()
    start_comp.component_id = "R1"
    start_comp.get_terminal_pos.return_value = QPointF(0, 0)

    end_comp = MagicMock()
    end_comp.component_id = "R2"
    end_comp.get_terminal_pos.return_value = QPointF(100, 50)

    wire = WireGraphicsItem(
        start_comp=start_comp,
        start_term=0,
        end_comp=end_comp,
        end_term=1,
        canvas=canvas,
        model=model,
    )
    return wire, model


class TestWireGraphicsItemNoFallback:
    """Ensure WireGraphicsItem delegates routing persistence to canvas only."""

    def test_persist_routing_result_delegates_to_canvas(self):
        """_persist_routing_result should call canvas.on_wire_routing_complete, not mutate model."""
        from unittest.mock import MagicMock

        canvas = MagicMock()
        canvas.on_wire_routing_complete = MagicMock()

        wire, model = _make_wire_item(canvas=canvas)
        initial_waypoints = list(model.waypoints)

        canvas.on_wire_routing_complete.reset_mock()
        wire._persist_routing_result([(10, 20), (30, 40)], runtime=0.5, iterations=3)

        # Canvas method must have been called — routing goes through controller
        canvas.on_wire_routing_complete.assert_called_once()
        # Model waypoints must not have been mutated directly by the graphics item
        assert model.waypoints == initial_waypoints

    def test_persist_routing_result_noop_without_canvas(self):
        """_persist_routing_result is a no-op when canvas is None."""
        wire, model = _make_wire_item(canvas=None)
        initial_waypoints = list(model.waypoints)

        # Must not raise and must not mutate the model
        wire._persist_routing_result([(10, 20), (30, 40)])
        assert model.waypoints == initial_waypoints

    def test_finish_waypoint_drag_delegates_to_canvas(self):
        """_finish_waypoint_drag should call canvas.on_waypoint_drag_finished, not mutate model."""
        from unittest.mock import MagicMock

        from PyQt6.QtCore import QPointF

        canvas = MagicMock()
        canvas.on_waypoint_drag_finished = MagicMock()

        wire, model = _make_wire_item(canvas=canvas, waypoints=[(0, 0), (50, 0), (100, 50)])
        # Simulate in-memory waypoints list that the graphics item maintains
        wire.waypoints = [QPointF(0, 0), QPointF(50, 0), QPointF(100, 50)]

        initial_model_waypoints = list(model.waypoints)
        initial_model_locked = model.locked

        wire._finish_waypoint_drag()

        # Canvas method must have been called — persistence goes through controller
        canvas.on_waypoint_drag_finished.assert_called_once()
        # Model waypoints and locked flag must not have been mutated directly
        assert model.waypoints == initial_model_waypoints
        assert model.locked == initial_model_locked

    def test_finish_waypoint_drag_noop_without_canvas(self):
        """_finish_waypoint_drag is a no-op when canvas is None."""
        from PyQt6.QtCore import QPointF

        wire, model = _make_wire_item(canvas=None, waypoints=[(0, 0), (50, 0), (100, 50)])
        wire.waypoints = [QPointF(0, 0), QPointF(50, 0), QPointF(100, 50)]

        initial_model_waypoints = list(model.waypoints)
        initial_model_locked = model.locked

        # Must not raise and must not mutate the model
        wire._finish_waypoint_drag()
        assert model.waypoints == initial_model_waypoints
        assert model.locked == initial_model_locked
