"""Circuit Statistics Panel - displays live circuit composition and connectivity info."""

import logging
from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFormLayout, QGroupBox, QLabel, QScrollArea,
                             QTextEdit, QVBoxLayout, QWidget)

from .styles import theme_manager

logger = logging.getLogger(__name__)


class CircuitStatisticsPanel(QWidget):
    """Panel showing live-updating circuit statistics.

    Displays component counts by type, wire/node counts, ground presence,
    floating terminal detection, and an optional netlist preview.
    """

    def __init__(self, model, circuit_ctrl, simulation_ctrl):
        super().__init__()
        self.model = model
        self.circuit_ctrl = circuit_ctrl
        self.simulation_ctrl = simulation_ctrl

        self._init_ui()

        # Register as observer for model changes
        self.circuit_ctrl.add_observer(self._on_model_changed)

        # Initial refresh
        self.refresh()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("Circuit Statistics")
        title.setFont(theme_manager.font("panel_title"))
        outer_layout.addWidget(title)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # --- Summary group ---
        self._summary_group = QGroupBox("Summary")
        self._summary_form = QFormLayout(self._summary_group)
        self._summary_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._total_components_label = QLabel("0")
        self._summary_form.addRow("Components:", self._total_components_label)

        self._wire_count_label = QLabel("0")
        self._summary_form.addRow("Wires:", self._wire_count_label)

        self._node_count_label = QLabel("0")
        self._summary_form.addRow("Nodes:", self._node_count_label)

        self._ground_label = QLabel("No")
        self._summary_form.addRow("Ground:", self._ground_label)

        self._layout.addWidget(self._summary_group)

        # --- Components by type ---
        self._components_group = QGroupBox("Components by Type")
        self._components_form = QFormLayout(self._components_group)
        self._components_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._layout.addWidget(self._components_group)

        # --- Connectivity ---
        self._connectivity_group = QGroupBox("Connectivity")
        self._connectivity_form = QFormLayout(self._connectivity_group)
        self._connectivity_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._floating_label = QLabel("None")
        self._connectivity_form.addRow("Floating:", self._floating_label)

        self._layout.addWidget(self._connectivity_group)

        # --- Netlist preview ---
        self._netlist_group = QGroupBox("Netlist Preview")
        netlist_layout = QVBoxLayout(self._netlist_group)
        self._netlist_text = QTextEdit()
        self._netlist_text.setReadOnly(True)
        self._netlist_text.setMaximumHeight(200)
        self._netlist_text.setFont(theme_manager.font("monospace"))
        netlist_layout.addWidget(self._netlist_text)
        self._layout.addWidget(self._netlist_group)

        self._layout.addStretch()
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    # --- Observer callback ---

    def _on_model_changed(self, event: str, data) -> None:
        """Handle model change events from the controller."""
        refresh_events = {
            "component_added",
            "component_removed",
            "wire_added",
            "wire_removed",
            "circuit_cleared",
            "nodes_rebuilt",
            "model_loaded",
        }
        if event in refresh_events:
            self.refresh()

    # --- Refresh ---

    def refresh(self):
        """Recalculate and display all statistics."""
        self._update_summary()
        self._update_component_breakdown()
        self._update_connectivity()
        self._update_netlist_preview()

    def _update_summary(self):
        num_components = len(self.model.components)
        num_wires = len(self.model.wires)
        num_nodes = len(self.model.nodes)
        has_ground = any(n.is_ground for n in self.model.nodes)

        self._total_components_label.setText(str(num_components))
        self._wire_count_label.setText(str(num_wires))
        self._node_count_label.setText(str(num_nodes))

        if num_components == 0:
            self._ground_label.setText("-")
            self._ground_label.setStyleSheet("")
        elif has_ground:
            self._ground_label.setText("Yes")
            self._ground_label.setStyleSheet("QLabel { color: green; }")
        else:
            self._ground_label.setText("No (required for simulation)")
            self._ground_label.setStyleSheet("QLabel { color: red; }")

    def _update_component_breakdown(self):
        # Clear old rows
        while self._components_form.rowCount() > 0:
            self._components_form.removeRow(0)

        if not self.model.components:
            self._components_form.addRow("", QLabel("(empty circuit)"))
            return

        type_counts = Counter(c.component_type for c in self.model.components.values())
        for comp_type, count in sorted(
            type_counts.items(), key=lambda x: (-x[1], x[0])
        ):
            label = QLabel(str(count))
            self._components_form.addRow(f"{comp_type}:", label)

    def _update_connectivity(self):
        floating = self._find_floating_terminals()
        if not self.model.components:
            self._floating_label.setText("-")
            self._floating_label.setStyleSheet("")
            self._floating_label.setToolTip("")
        elif floating:
            names = ", ".join(f"{cid}[{tidx}]" for cid, tidx in sorted(floating))
            self._floating_label.setText(f"{len(floating)} terminal(s)")
            self._floating_label.setStyleSheet("QLabel { color: orange; }")
            self._floating_label.setToolTip(names)
        else:
            self._floating_label.setText("All connected")
            self._floating_label.setStyleSheet("QLabel { color: green; }")
            self._floating_label.setToolTip("")

    def _find_floating_terminals(self):
        """Return set of (component_id, terminal_index) that are not in any node."""
        floating = set()
        for comp in self.model.components.values():
            if comp.component_type == "Ground":
                continue
            for tidx in range(comp.get_terminal_count()):
                key = (comp.component_id, tidx)
                if key not in self.model.terminal_to_node:
                    floating.add(key)
        return floating

    def _update_netlist_preview(self):
        if not self.model.components:
            self._netlist_text.setPlainText("(add components to see netlist)")
            return
        try:
            netlist = self.simulation_ctrl.generate_netlist()
            self._netlist_text.setPlainText(netlist)
        except Exception:
            self._netlist_text.setPlainText(
                "(netlist generation requires valid circuit)"
            )
