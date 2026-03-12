"""Standalone simulation results display widget (ResultsDisplayProtocol)."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class ResultsPanel(QWidget):
    """Widget that owns the simulation results UI and implements ResultsDisplayProtocol.

    The panel holds the results text area and export buttons that were previously
    inlined inside MainWindow.init_ui().  MainWindow wires up the export callbacks
    and the _display_delegate so that display_simulation_result() can delegate to
    the SimulationMixin handler while still satisfying the protocol contract.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Set by MainWindow after construction to wire up the complex display handler.
        # AUDIT(architecture): mutable None-initialized delegate creates fragile dependency; require in constructor or raise explicit error when unset
        self._display_delegate = None
        # Set by MainWindow after the NetlistPreviewWidget is created.
        self._netlist_preview_widget = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header row with export buttons
        header = QHBoxLayout()
        header.addWidget(QLabel("Simulation Results"))

        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.setEnabled(False)
        header.addWidget(self.btn_export_csv)

        self.btn_export_excel = QPushButton("Export Excel")
        self.btn_export_excel.setEnabled(False)
        header.addWidget(self.btn_export_excel)

        self.btn_copy_markdown = QPushButton("Copy Markdown")
        self.btn_copy_markdown.setEnabled(False)
        header.addWidget(self.btn_copy_markdown)

        header.addStretch()
        layout.addLayout(header)

        # Read-only results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)

    # --- ResultsDisplayProtocol ---

    def display_simulation_result(self, result) -> None:
        """Display a complete simulation result (ResultsDisplayProtocol).

        Delegates to the SimulationMixin handler registered via _display_delegate
        so that all analysis-type-specific logic stays in the mixin.
        """
        if self._display_delegate is not None:
            self._display_delegate(result)

    def display_text(self, text: str) -> None:
        """Display plain text in the results area (ResultsDisplayProtocol)."""
        self.results_text.setPlainText(text)

    def set_netlist_preview(self, netlist: str) -> None:
        """Update the netlist preview tab (ResultsDisplayProtocol)."""
        if self._netlist_preview_widget is not None:
            self._netlist_preview_widget.set_netlist(netlist)

    def clear(self) -> None:
        """Clear all displayed results (ResultsDisplayProtocol)."""
        self.results_text.clear()

    def set_export_enabled(self, enabled: bool) -> None:
        """Enable or disable all export buttons (ResultsDisplayProtocol)."""
        self.btn_export_csv.setEnabled(enabled)
        self.btn_export_excel.setEnabled(enabled)
        self.btn_copy_markdown.setEnabled(enabled)
