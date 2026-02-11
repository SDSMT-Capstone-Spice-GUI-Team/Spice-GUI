"""Tests for QTimer reuse during component drag (issue #194).

_schedule_controller_update() should reuse a single QTimer instance
instead of creating a new one on every call.

Note: schedule_wire_update() was removed in #189 (duplicate rerouting fix).
"""

from unittest.mock import MagicMock, patch

from GUI.component_item import ComponentGraphicsItem


def _make_mock_comp():
    """Create a MagicMock that delegates timer methods to the real class."""
    comp = MagicMock(spec=ComponentGraphicsItem)
    comp._position_update_timer = None
    comp._pending_position = None
    comp._schedule_controller_update = lambda: ComponentGraphicsItem._schedule_controller_update(comp)
    return comp


class TestScheduleControllerUpdateTimerReuse:
    """_schedule_controller_update() should reuse the same QTimer."""

    def _make_comp_with_scene(self):
        """Create a mock component with mocked scene and controller."""
        comp = _make_mock_comp()
        mock_canvas = MagicMock()
        mock_canvas.controller = MagicMock()
        mock_scene = MagicMock()
        mock_scene.views.return_value = [mock_canvas]
        comp.scene.return_value = mock_scene
        return comp

    @patch("GUI.component_item.QTimer")
    def test_position_timer_created_on_first_call(self, MockQTimer):
        """First call should create the position update timer."""
        comp = self._make_comp_with_scene()
        mock_timer = MagicMock()
        MockQTimer.return_value = mock_timer

        comp._schedule_controller_update()

        MockQTimer.assert_called_once()
        mock_timer.setSingleShot.assert_called_once_with(True)
        mock_timer.start.assert_called_once_with(50)

    @patch("GUI.component_item.QTimer")
    def test_position_timer_reused_on_second_call(self, MockQTimer):
        """Second call should reuse the timer."""
        comp = self._make_comp_with_scene()
        mock_timer = MagicMock()
        MockQTimer.return_value = mock_timer

        comp._schedule_controller_update()
        comp._schedule_controller_update()

        MockQTimer.assert_called_once()
        assert mock_timer.start.call_count == 2

    @patch("GUI.component_item.QTimer")
    def test_position_timer_no_scene_skips(self, MockQTimer):
        """If no scene, should not create timer."""
        comp = _make_mock_comp()
        comp.scene.return_value = None

        comp._schedule_controller_update()

        MockQTimer.assert_not_called()
        assert comp._position_update_timer is None
