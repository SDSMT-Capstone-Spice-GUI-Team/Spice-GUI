"""
Netlist Preview Widget — read-only panel showing the generated SPICE netlist
with basic syntax highlighting.
"""

import re

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class SpiceHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for SPICE netlist text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        # Comments: lines starting with * (green)
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#4CAF50"))
        self._rules.append((re.compile(r"^\*.*$"), comment_fmt))

        # Directives: lines starting with . (blue)
        directive_fmt = QTextCharFormat()
        directive_fmt.setForeground(QColor("#2196F3"))
        directive_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"^\..*$"), directive_fmt))

        # Control block keywords (purple)
        control_fmt = QTextCharFormat()
        control_fmt.setForeground(QColor("#9C27B0"))
        control_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"^(run|quit|print|set|let|wrdata|setplot)\b.*$", re.IGNORECASE), control_fmt))

    def highlightBlock(self, text):
        """Apply syntax highlighting rules to a single line of text."""
        for pattern, fmt in self._rules:
            match = pattern.match(text)
            if match:
                self.setFormat(0, len(text), fmt)
                return


class NetlistPreviewWidget(QWidget):
    """Widget for displaying a read-only SPICE netlist with syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with buttons
        header = QHBoxLayout()
        header.addWidget(QLabel("Generated SPICE Netlist"))

        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setToolTip("Copy the netlist text to the system clipboard")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        header.addWidget(self.copy_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Regenerate the netlist from the current circuit")
        header.addWidget(self.refresh_btn)

        header.addStretch()
        layout.addLayout(header)

        # Text display
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Monospace", 9))
        self.text_edit.setPlaceholderText("No netlist generated yet. Add components and click Refresh.")
        layout.addWidget(self.text_edit)

        # Attach syntax highlighter
        self._highlighter = SpiceHighlighter(self.text_edit.document())

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.status_label)

    def set_netlist(self, netlist_text):
        """Set the netlist text to display.

        Args:
            netlist_text: the full SPICE netlist string
        """
        self.text_edit.setPlainText(netlist_text)
        line_count = netlist_text.count("\n") + 1 if netlist_text else 0
        self.status_label.setText(f"{line_count} lines")

    def set_error(self, message):
        """Display an error message instead of a netlist."""
        self.text_edit.setPlainText(f"Error generating netlist:\n\n{message}")
        self.status_label.setText("Error")

    def clear(self):
        """Clear the netlist display."""
        self.text_edit.clear()
        self.status_label.setText("")

    def _copy_to_clipboard(self):
        """Copy the netlist text to the system clipboard."""
        from PyQt6.QtWidgets import QApplication

        text = self.text_edit.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
                self.status_label.setText("Copied to clipboard")
