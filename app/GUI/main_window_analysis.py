"""Analysis type configuration dialogs and menu synchronization for MainWindow."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox

from .analysis_dialog import AnalysisDialog
from .monte_carlo_dialog import MonteCarloDialog
from .parameter_sweep_dialog import ParameterSweepDialog

# Maps analysis short codes (used in CourseProfile.allowed_analyses) to the
# full analysis-type name stored in CircuitModel.analysis_type.
_CODE_TO_ANALYSIS_TYPE: dict[str, str] = {
    "op": "DC Operating Point",
    "dc": "DC Sweep",
    "ac": "AC Sweep",
    "tran": "Transient",
    "temp": "Temperature Sweep",
    "noise": "Noise",
    "sweep": "Parameter Sweep",
    "mc": "Monte Carlo",
}


class AnalysisSettingsMixin:
    """Mixin providing analysis type configuration methods."""

    def set_analysis_op(self):
        """Set analysis type to DC Operating Point"""
        self.simulation_ctrl.set_analysis("DC Operating Point", {})
        statusbar = self.statusBar()
        if statusbar:
            statusbar.showMessage("Analysis: DC Operating Point (.op)", 3000)

    def set_analysis_dc(self):
        """Set analysis type to DC Sweep with parameters"""
        dialog = AnalysisDialog("DC Sweep", self, simulation_ctrl=self.simulation_ctrl)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("DC Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: DC Sweep (V: {params['min']}V to {params['max']}V, step {params['step']}V)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_ac(self):
        """Set analysis type to AC Sweep with parameters"""
        dialog = AnalysisDialog("AC Sweep", self, simulation_ctrl=self.simulation_ctrl)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("AC Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: AC Sweep ({params['fStart']}Hz to {params['fStop']}Hz, {params['points']} pts/decade)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_transient(self):
        """Set analysis type to Transient with parameters"""
        dialog = AnalysisDialog("Transient", self, simulation_ctrl=self.simulation_ctrl)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Transient", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Transient (duration: {params['duration']}s, step: {params['step']}s)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_temp_sweep(self):
        """Set analysis type to Temperature Sweep with parameters"""
        dialog = AnalysisDialog("Temperature Sweep", self, simulation_ctrl=self.simulation_ctrl)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Temperature Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Temperature Sweep "
                        f"({params['tempStart']}\u00b0C to "
                        f"{params['tempStop']}\u00b0C, step "
                        f"{params['tempStep']}\u00b0C)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_noise(self):
        """Set analysis type to Noise with parameters"""
        dialog = AnalysisDialog("Noise", self, simulation_ctrl=self.simulation_ctrl)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Noise", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Noise (v({params['output_node']}), {params['fStart']}Hz to {params['fStop']}Hz)",
                        3000,
                    )
            else:
                QMessageBox.warning(self, "Invalid Parameters", "Please enter valid numeric values.")
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_parameter_sweep(self):
        """Set analysis type to Parameter Sweep with configuration dialog"""
        if not self.model.components:
            QMessageBox.warning(
                self,
                "No Components",
                "Add components to the circuit before configuring a parameter sweep.",
            )
            self.op_action.setChecked(True)
            return

        dialog = ParameterSweepDialog(self.model.components, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Parameter Sweep", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Parameter Sweep on {params['component_id']} "
                        f"({params['num_steps']} steps, base: {params['base_analysis_type']})",
                        3000,
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Parameters",
                    "Please enter valid sweep parameters. Start and stop values must be different.",
                )
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def set_analysis_monte_carlo(self):
        """Set analysis type to Monte Carlo with configuration dialog."""
        if not self.model.components:
            QMessageBox.warning(
                self,
                "No Components",
                "Add components to the circuit before configuring Monte Carlo analysis.",
            )
            self.op_action.setChecked(True)
            return

        dialog = MonteCarloDialog(self.model.components, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            if params:
                self.simulation_ctrl.set_analysis("Monte Carlo", params)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(
                        f"Analysis: Monte Carlo ({params['num_runs']} runs, "
                        f"base: {params['base_analysis_type']}, "
                        f"{len(params['tolerances'])} components varied)",
                        3000,
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Parameters",
                    "Set tolerance > 0% for at least one component.",
                )
                self.op_action.setChecked(True)
        else:
            self.op_action.setChecked(True)

    def _sync_analysis_menu(self):
        """Update Analysis menu checkboxes to match model state."""
        analysis_type = self.model.analysis_type
        if analysis_type == "DC Operating Point":
            self.op_action.setChecked(True)
        elif analysis_type == "DC Sweep":
            self.dc_action.setChecked(True)
        elif analysis_type == "AC Sweep":
            self.ac_action.setChecked(True)
        elif analysis_type == "Transient":
            self.tran_action.setChecked(True)
        elif analysis_type == "Temperature Sweep":
            self.temp_action.setChecked(True)
        elif analysis_type == "Noise":
            self.noise_action.setChecked(True)
        elif analysis_type == "Parameter Sweep":
            self.sweep_action.setChecked(True)

    # ── Profile-based analysis filtering ──────────────────────────

    def _apply_analysis_profile_filter(self, profile) -> None:
        """Show/hide analysis menu actions based on the active profile.

        When the profile id is ``"full"`` every analysis is visible.
        Otherwise only analyses whose short code appears in
        ``profile.allowed_analyses`` are shown.  If the currently
        selected analysis becomes hidden, we fall back to the first
        allowed analysis type.
        """
        action_map: dict = self._analysis_action_map  # code → QAction

        if profile.id == "full":
            allowed: set[str] = set()
        else:
            allowed = set(profile.allowed_analyses)

        for code, action in action_map.items():
            hidden = bool(allowed) and code not in allowed
            action.setVisible(not hidden)

        # If the currently checked analysis is now hidden, switch to
        # the first visible analysis (prefer "op" if available).
        if allowed:
            checked = self.analysis_group.checkedAction()
            if checked is not None and not checked.isVisible():
                fallback_code = "op" if "op" in allowed else next(iter(allowed))
                fallback_action = action_map[fallback_code]
                fallback_action.setChecked(True)
                fallback_action.trigger()
