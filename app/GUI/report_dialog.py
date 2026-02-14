"""Dialog for configuring circuit report generation."""

from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QVBoxLayout)


class ReportDialog(QDialog):
    """Dialog for selecting which sections to include in a circuit report.

    Presents checkboxes for each report section and text fields for
    student name and circuit name.
    """

    def __init__(self, parent=None, circuit_name: str = "", has_results: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Generate Circuit Report")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Circuit info section
        info_group = QGroupBox("Report Info")
        info_layout = QVBoxLayout(info_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Circuit Name:"))
        self._circuit_name = QLineEdit(circuit_name)
        self._circuit_name.setPlaceholderText("My Circuit")
        name_row.addWidget(self._circuit_name)
        info_layout.addLayout(name_row)

        student_row = QHBoxLayout()
        student_row.addWidget(QLabel("Student Name:"))
        self._student_name = QLineEdit()
        self._student_name.setPlaceholderText("(optional)")
        student_row.addWidget(self._student_name)
        info_layout.addLayout(student_row)

        layout.addWidget(info_group)

        # Sections checkboxes
        sections_group = QGroupBox("Report Sections")
        sections_layout = QVBoxLayout(sections_group)

        self._cb_title = QCheckBox("Title Page")
        self._cb_title.setChecked(True)
        sections_layout.addWidget(self._cb_title)

        self._cb_schematic = QCheckBox("Schematic Diagram")
        self._cb_schematic.setChecked(True)
        sections_layout.addWidget(self._cb_schematic)

        self._cb_netlist = QCheckBox("SPICE Netlist")
        self._cb_netlist.setChecked(True)
        sections_layout.addWidget(self._cb_netlist)

        self._cb_analysis = QCheckBox("Analysis Configuration")
        self._cb_analysis.setChecked(True)
        sections_layout.addWidget(self._cb_analysis)

        self._cb_results = QCheckBox("Simulation Results")
        self._cb_results.setChecked(has_results)
        if not has_results:
            self._cb_results.setEnabled(False)
            self._cb_results.setToolTip("No simulation results available")
        sections_layout.addWidget(self._cb_results)

        layout.addWidget(sections_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self):
        """Return a ReportConfig from the dialog selections.

        Returns:
            ReportConfig with the user's selections.
        """
        from GUI.report_generator import ReportConfig

        return ReportConfig(
            include_title=self._cb_title.isChecked(),
            include_schematic=self._cb_schematic.isChecked(),
            include_netlist=self._cb_netlist.isChecked(),
            include_analysis=self._cb_analysis.isChecked(),
            include_results=self._cb_results.isChecked(),
            student_name=self._student_name.text().strip(),
            circuit_name=self._circuit_name.text().strip(),
        )
