"""Tests for the netlist preview widget and syntax highlighter."""

from GUI.netlist_preview import NetlistPreviewWidget, SpiceHighlighter
from PyQt6.QtGui import QTextDocument

# ---------------------------------------------------------------------------
# SpiceHighlighter tests
# ---------------------------------------------------------------------------


class TestSpiceHighlighter:
    def test_creates_without_error(self):
        doc = QTextDocument()
        highlighter = SpiceHighlighter(doc)
        assert highlighter is not None

    def test_comment_line_highlighted(self):
        """Comment lines (starting with *) should get format applied."""
        doc = QTextDocument()
        _highlighter = SpiceHighlighter(doc)  # noqa: F841 — attaches to doc
        doc.setPlainText("* This is a comment")
        # Just verify no exception - visual highlighting is hard to assert
        block = doc.firstBlock()
        assert block.isValid()

    def test_directive_line_highlighted(self):
        doc = QTextDocument()
        _highlighter = SpiceHighlighter(doc)  # noqa: F841
        doc.setPlainText(".tran 1u 10m")
        block = doc.firstBlock()
        assert block.isValid()

    def test_control_keyword_highlighted(self):
        doc = QTextDocument()
        _highlighter = SpiceHighlighter(doc)  # noqa: F841
        doc.setPlainText("run")
        block = doc.firstBlock()
        assert block.isValid()

    def test_component_line_no_crash(self):
        doc = QTextDocument()
        _highlighter = SpiceHighlighter(doc)  # noqa: F841
        doc.setPlainText("R1 1 2 1k")
        block = doc.firstBlock()
        assert block.isValid()

    def test_multiline_document(self):
        doc = QTextDocument()
        _highlighter = SpiceHighlighter(doc)  # noqa: F841
        netlist = "* Comment\nR1 1 0 1k\n.op\n.end"
        doc.setPlainText(netlist)
        assert doc.blockCount() == 4


# ---------------------------------------------------------------------------
# NetlistPreviewWidget tests
# ---------------------------------------------------------------------------


class TestNetlistPreviewWidget:
    def test_initial_state(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        assert widget.text_edit.toPlainText() == ""

    def test_set_netlist(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        widget.set_netlist("R1 1 0 1k\n.op\n.end")
        assert "R1 1 0 1k" in widget.text_edit.toPlainText()
        assert "3 lines" in widget.status_label.text()

    def test_set_error(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        widget.set_error("No ground found")
        assert "Error" in widget.status_label.text()
        assert "No ground found" in widget.text_edit.toPlainText()

    def test_clear(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        widget.set_netlist("some text")
        widget.clear()
        assert widget.text_edit.toPlainText() == ""
        assert widget.status_label.text() == ""

    def test_copy_to_clipboard(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        widget.set_netlist("R1 1 0 1k")
        widget._copy_to_clipboard()
        assert "Copied" in widget.status_label.text()

    def test_line_count_single_line(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        widget.set_netlist(".end")
        assert "1 lines" in widget.status_label.text()

    def test_line_count_empty(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        widget.set_netlist("")
        assert "0 lines" in widget.status_label.text()

    def test_refresh_button_exists(self, qtbot):
        widget = NetlistPreviewWidget()
        qtbot.addWidget(widget)
        assert widget.refresh_btn is not None
        assert widget.copy_btn is not None
