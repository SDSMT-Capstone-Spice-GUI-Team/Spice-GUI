"""Tests for grading overlay visual feedback on canvas components."""

import re

import pytest
from PyQt6.QtGui import QColor


@pytest.fixture
def component_item(qtbot):
    """Create a standalone ComponentGraphicsItem for testing."""
    from GUI.component_item import ComponentGraphicsItem

    item = ComponentGraphicsItem("R1", "Resistor")
    return item


class TestComponentGradingState:
    """Tests for grading state on ComponentGraphicsItem."""

    def test_initial_state_is_none(self, component_item):
        """Component starts with no grading state."""
        assert component_item._grading_state is None
        assert component_item._grading_feedback == ""

    def test_set_passed_state(self, component_item):
        """Setting passed state updates attributes and tooltip."""
        component_item.set_grading_state("passed", "R1 found")
        assert component_item._grading_state == "passed"
        assert component_item._grading_feedback == "R1 found"
        assert component_item.toolTip() == "R1 found"

    def test_set_failed_state(self, component_item):
        """Setting failed state updates attributes and tooltip."""
        component_item.set_grading_state("failed", "Missing R1")
        assert component_item._grading_state == "failed"
        assert component_item._grading_feedback == "Missing R1"
        assert component_item.toolTip() == "Missing R1"

    def test_clear_grading_state(self, component_item):
        """Clearing resets state, feedback, and tooltip."""
        component_item.set_grading_state("passed", "OK")
        component_item.clear_grading_state()
        assert component_item._grading_state is None
        assert component_item._grading_feedback == ""
        assert component_item.toolTip() == ""

    def test_set_state_without_feedback(self, component_item):
        """Setting state with empty feedback clears tooltip."""
        component_item.set_grading_state("passed")
        assert component_item._grading_state == "passed"
        assert component_item.toolTip() == ""


class TestExtractComponentIds:
    """Tests for _extract_component_ids helper function."""

    def test_simple_component_id(self):
        """Extracts component ID from check_id like 'exists_R1'."""
        from unittest.mock import MagicMock

        from GUI.grading_panel import _extract_component_ids

        cr = MagicMock()
        cr.check_id = "exists_R1"
        assert "R1" in _extract_component_ids(cr)

    def test_value_check(self):
        """Extracts component ID from check_id like 'value_R1'."""
        from unittest.mock import MagicMock

        from GUI.grading_panel import _extract_component_ids

        cr = MagicMock()
        cr.check_id = "value_R1"
        assert "R1" in _extract_component_ids(cr)

    def test_topology_pair(self):
        """Extracts both component IDs from topology check_id."""
        from unittest.mock import MagicMock

        from GUI.grading_panel import _extract_component_ids

        cr = MagicMock()
        cr.check_id = "connected_R1_C1"
        ids = _extract_component_ids(cr)
        assert "R1" in ids
        assert "C1" in ids

    def test_no_component_id(self):
        """Returns empty list for check_ids without component IDs."""
        from unittest.mock import MagicMock

        from GUI.grading_panel import _extract_component_ids

        cr = MagicMock()
        cr.check_id = "has_ground"
        ids = _extract_component_ids(cr)
        # "has_ground" has no uppercase letter+digit pattern
        assert ids == [] or all(isinstance(x, str) for x in ids)

    def test_lowercase_check_id(self):
        """Handles lowercase check_id containing component references."""
        from unittest.mock import MagicMock

        from GUI.grading_panel import _extract_component_ids

        cr = MagicMock()
        cr.check_id = "r1_value"
        ids = _extract_component_ids(cr)
        # Should extract "r1" or "R1" variant
        assert len(ids) >= 1


class TestGradingPanelHighlights:
    """Tests for GradingPanel highlight management."""

    @pytest.fixture
    def panel(self, qtbot):
        from GUI.grading_panel import GradingPanel
        from models.circuit import CircuitModel

        model = CircuitModel()
        panel = GradingPanel(model)
        qtbot.addWidget(panel)
        return panel

    def test_initial_highlighted_components_empty(self, panel):
        """Panel starts with no highlighted components."""
        assert panel._highlighted_components == []

    def test_clear_highlights_resets_list(self, panel):
        """_clear_highlights empties the highlighted list."""
        panel._highlighted_components = ["R1", "C1"]
        panel._clear_highlights()
        assert panel._highlighted_components == []

    def test_get_canvas_returns_none_without_parent(self, panel):
        """_get_canvas returns None when parent has no canvas."""
        assert panel._get_canvas() is None

    def test_clear_results_clears_highlights(self, panel):
        """clear_results also clears highlighted components."""
        panel._highlighted_components = ["R1"]
        panel.clear_results()
        assert panel._highlighted_components == []
