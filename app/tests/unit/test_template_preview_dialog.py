"""Tests for the template preview dialog."""

import pytest
from models.template import TemplateData, TemplateMetadata


@pytest.fixture
def sample_template():
    """Create a sample template with metadata and circuit data."""
    return TemplateData(
        metadata=TemplateMetadata(
            title="RC Low-Pass Filter",
            description="Build an RC low-pass filter circuit",
            author="Prof. Smith",
            created="2026-01-15",
            tags=["filters", "analog"],
        ),
        instructions="Connect R1 to C1 to form a voltage divider.",
        starter_circuit={
            "components": [
                {
                    "component_id": "R1",
                    "component_type": "Resistor",
                    "value": "1k",
                    "position": [0, 0],
                },
                {
                    "component_id": "C1",
                    "component_type": "Capacitor",
                    "value": "100n",
                    "position": [100, 0],
                },
            ],
            "wires": [
                {
                    "start_component_id": "R1",
                    "start_terminal": 1,
                    "end_component_id": "C1",
                    "end_terminal": 0,
                },
            ],
            "analysis_type": "AC Sweep",
        },
        reference_circuit={"components": [], "wires": []},
    )


@pytest.fixture
def empty_template():
    """Create a template with no starter circuit."""
    return TemplateData(
        metadata=TemplateMetadata(title="Empty Assignment"),
        instructions="",
        starter_circuit=None,
    )


@pytest.fixture
def dialog(qtbot, sample_template):
    """Create a TemplatePreviewDialog instance."""
    from GUI.template_preview_dialog import TemplatePreviewDialog

    dlg = TemplatePreviewDialog(sample_template)
    qtbot.addWidget(dlg)
    return dlg


class TestTemplatePreviewDialog:
    """Tests for TemplatePreviewDialog."""

    def test_title_displayed(self, dialog, sample_template):
        """Dialog displays the template title."""
        assert dialog.title_label.text() == sample_template.metadata.title

    def test_author_displayed(self, dialog):
        """Dialog displays the author."""
        assert "Prof. Smith" in dialog.author_label.text()

    def test_date_displayed(self, dialog):
        """Dialog displays the creation date."""
        assert "2026-01-15" in dialog.date_label.text()

    def test_tags_displayed(self, dialog):
        """Dialog displays the tags."""
        assert "filters" in dialog.tags_label.text()
        assert "analog" in dialog.tags_label.text()

    def test_description_displayed(self, dialog, sample_template):
        """Dialog displays the description."""
        assert dialog.description_label.text() == sample_template.metadata.description

    def test_instructions_displayed(self, dialog, sample_template):
        """Dialog displays the instructions."""
        assert dialog.instructions_text.toPlainText() == sample_template.instructions

    def test_circuit_tree_has_components(self, dialog):
        """Circuit tree shows component nodes."""
        tree = dialog.circuit_tree
        # Root items: Components, Wires, possibly Analysis Type
        assert tree.topLevelItemCount() >= 2
        comp_root = tree.topLevelItem(0)
        assert "Components" in comp_root.text(0)
        assert comp_root.childCount() == 2

    def test_circuit_tree_component_details(self, dialog):
        """Component items show ID and type/value."""
        tree = dialog.circuit_tree
        comp_root = tree.topLevelItem(0)
        first_comp = comp_root.child(0)
        assert "R1" in first_comp.text(0)
        assert "Resistor" in first_comp.text(1)

    def test_circuit_tree_has_wires(self, dialog):
        """Circuit tree shows wire nodes."""
        tree = dialog.circuit_tree
        wire_root = tree.topLevelItem(1)
        assert "Wires" in wire_root.text(0)
        assert wire_root.childCount() == 1

    def test_analysis_type_shown(self, dialog):
        """Non-default analysis type is shown in the tree."""
        tree = dialog.circuit_tree
        # Find the analysis type item
        found = False
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if "Analysis" in item.text(0):
                assert "AC Sweep" in item.text(1)
                found = True
        assert found

    def test_summary_label(self, dialog):
        """Summary shows component and wire counts."""
        assert "2 component(s)" in dialog.circuit_summary.text()
        assert "1 wire(s)" in dialog.circuit_summary.text()
        assert "reference circuit included" in dialog.circuit_summary.text()

    def test_get_template_returns_data(self, dialog, sample_template):
        """get_template returns the template data."""
        assert dialog.get_template() is sample_template


class TestTemplatePreviewEmpty:
    """Tests for preview dialog with an empty template."""

    def test_empty_circuit_message(self, qtbot, empty_template):
        """Empty starter circuit shows appropriate message."""
        from GUI.template_preview_dialog import TemplatePreviewDialog

        dlg = TemplatePreviewDialog(empty_template)
        qtbot.addWidget(dlg)
        assert "empty" in dlg.circuit_summary.text().lower() or "No" in dlg.circuit_summary.text()

    def test_no_instructions(self, qtbot, empty_template):
        """Empty instructions shows placeholder."""
        from GUI.template_preview_dialog import TemplatePreviewDialog

        dlg = TemplatePreviewDialog(empty_template)
        qtbot.addWidget(dlg)
        assert dlg.instructions_text.toPlainText() != ""

    def test_untitled_fallback(self, qtbot):
        """Template with no title shows (Untitled)."""
        from GUI.template_preview_dialog import TemplatePreviewDialog

        tmpl = TemplateData(metadata=TemplateMetadata(title=""))
        dlg = TemplatePreviewDialog(tmpl)
        qtbot.addWidget(dlg)
        assert "(Untitled)" in dlg.title_label.text()

    def test_empty_author_hidden(self, qtbot, empty_template):
        """Empty author field shows no author text."""
        from GUI.template_preview_dialog import TemplatePreviewDialog

        dlg = TemplatePreviewDialog(empty_template)
        qtbot.addWidget(dlg)
        assert dlg.author_label.text() == ""

    def test_empty_tags_hidden(self, qtbot, empty_template):
        """Empty tags field shows no tags text."""
        from GUI.template_preview_dialog import TemplatePreviewDialog

        dlg = TemplatePreviewDialog(empty_template)
        qtbot.addWidget(dlg)
        assert dlg.tags_label.text() == ""
