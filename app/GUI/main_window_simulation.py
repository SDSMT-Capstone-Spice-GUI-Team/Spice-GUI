"""Simulation execution, result display, plot management, and CSV export for MainWindow."""

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog

from .monte_carlo_results_dialog import MonteCarloResultsDialog
from .parameter_sweep_plot_dialog import ParameterSweepPlotDialog
from .results_plot_dialog import ACSweepPlotDialog, DCSweepPlotDialog
from .waveform_dialog import WaveformDialog

logger = logging.getLogger(__name__)


class SimulationMixin:
    """Mixin providing simulation execution, result display, and CSV export."""

    def generate_netlist(self):
        """Generate SPICE netlist"""
        try:
            # Phase 5: No sync needed - model always up to date
            netlist = self.simulation_ctrl.generate_netlist()
            self.results_text.setPlainText("SPICE Netlist:\n\n" + netlist)
        except (ValueError, KeyError, TypeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to generate netlist: {e}")

    def run_simulation(self):
        """Run SPICE simulation"""
        try:
            if self.model.analysis_type == "Parameter Sweep":
                result = self._run_parameter_sweep()
            elif self.model.analysis_type == "Monte Carlo":
                result = self._run_monte_carlo()
            else:
                # Phase 5: No sync needed - model always up to date
                result = self.simulation_ctrl.run_simulation()

            # Display results (view responsibility)
            self._display_simulation_results(result)

        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as e:
            logger.error("Simulation failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "Error", f"Simulation failed: {e}")

    def _run_parameter_sweep(self):
        """Run parameter sweep with a progress dialog."""
        sweep_config = self.model.analysis_params
        num_steps = sweep_config.get("num_steps", 10)
        component_id = sweep_config.get("component_id", "?")

        progress = QProgressDialog(
            f"Running parameter sweep on {component_id}...",
            "Cancel",
            0,
            num_steps,
            self,
        )
        progress.setWindowTitle("Parameter Sweep")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        def on_progress(step, total):
            progress.setValue(step)
            progress.setLabelText(f"Running step {step + 1} of {total}...")
            QApplication.processEvents()
            return not progress.wasCanceled()

        result = self.simulation_ctrl.run_parameter_sweep(
            sweep_config,
            progress_callback=on_progress,
        )
        progress.setValue(num_steps)
        progress.close()

        # Add sweep_labels to the data for the plot dialog
        if result.data:
            from .format_utils import format_value

            result.data["sweep_labels"] = [format_value(v).strip() for v in result.data.get("sweep_values", [])]

        return result

    def _run_monte_carlo(self):
        """Run Monte Carlo analysis with a progress dialog."""
        mc_config = self.model.analysis_params
        num_runs = mc_config.get("num_runs", 20)

        progress = QProgressDialog(
            "Running Monte Carlo analysis...",
            "Cancel",
            0,
            num_runs,
            self,
        )
        progress.setWindowTitle("Monte Carlo")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        def on_progress(step, total):
            progress.setValue(step)
            progress.setLabelText(f"Running simulation {step + 1} of {total}...")
            QApplication.processEvents()
            return not progress.wasCanceled()

        result = self.simulation_ctrl.run_monte_carlo(
            mc_config,
            progress_callback=on_progress,
        )
        progress.setValue(num_runs)
        progress.close()
        return result

    def _display_simulation_results(self, result):
        """Display simulation results based on analysis type."""
        self._last_results = None
        self._last_results_type = self.model.analysis_type
        self.btn_export_csv.setEnabled(False)

        self.results_text.setPlainText("\n" + "=" * 70)
        self.results_text.append(f"SIMULATION COMPLETE - {self.model.analysis_type}")
        self.results_text.append("=" * 70)

        if not result.success:
            self._display_simulation_errors(result)
            return

        handlers = {
            "DC Operating Point": self._display_op_results,
            "DC Sweep": self._display_dc_sweep_results,
            "AC Sweep": self._display_ac_sweep_results,
            "Transient": self._display_transient_results,
            "Temperature Sweep": self._display_temp_sweep_results,
            "Parameter Sweep": self._display_param_sweep_results,
            "Monte Carlo": self._display_monte_carlo_results,
        }
        handler = handlers.get(self.model.analysis_type)
        if handler:
            handler(result)

        self.results_text.append("=" * 70)

        if self._last_results is not None:
            self.btn_export_csv.setEnabled(True)

    def _display_simulation_errors(self, result):
        """Display validation/simulation errors in the results panel."""
        self.results_text.append("\nSIMULATION COULD NOT RUN")
        self.results_text.append("=" * 40)
        if result.errors:
            self.results_text.append("\nPlease fix the following issues:\n")
            for error in result.errors:
                self.results_text.append(f"  - {error}")
        if result.warnings:
            self.results_text.append("\nAdditional notes:\n")
            for warning in result.warnings:
                self.results_text.append(f"  - {warning}")
        if result.error and not result.errors:
            self.results_text.append(f"\n{result.error}")

        # Also show a popup so the user notices immediately
        popup_lines = list(result.errors or [])
        if result.warnings:
            popup_lines.append("")
            popup_lines.extend(result.warnings)
        if not popup_lines and result.error:
            popup_lines.append(result.error)
        QMessageBox.warning(
            self,
            "Circuit Validation",
            "\n\n".join(popup_lines),
        )

    def _display_op_results(self, result):
        """Display DC Operating Point results."""
        op_data = result.data if result.data else {}
        # Handle new dict format with node_voltages/branch_currents
        if isinstance(op_data, dict) and "node_voltages" in op_data:
            node_voltages = op_data["node_voltages"]
            branch_currents = op_data.get("branch_currents", {})
        else:
            # Backward compat: plain dict of voltages
            node_voltages = op_data
            branch_currents = {}

        if node_voltages:
            self._last_results = node_voltages
            self.results_text.append("\nNODE VOLTAGES:")
            self.results_text.append("-" * 40)
            for node, voltage in sorted(node_voltages.items()):
                self.results_text.append(f"  {node:15s} : {voltage:12.6f} V")
            self.results_text.append("-" * 40)
            if branch_currents:
                self.results_text.append("\nBRANCH CURRENTS:")
                self.results_text.append("-" * 40)
                for device, current in sorted(branch_currents.items()):
                    self.results_text.append(f"  {device:15s} : {current:12.6e} A")
                self.results_text.append("-" * 40)
            self.canvas.set_op_results(node_voltages, branch_currents)

            # Calculate and display power dissipation
            self._calculate_power(node_voltages)
        else:
            self.results_text.append("\nNo node voltages found in output.")
            self.canvas.clear_op_results()
            self.properties_panel.clear_simulation_results()

    def _display_dc_sweep_results(self, result):
        """Display DC Sweep results."""
        sweep_data = result.data if result.data else None
        if sweep_data:
            self._last_results = sweep_data
            self.results_text.append("\nDC SWEEP RESULTS:")
            self.results_text.append("-" * 40)
            headers = sweep_data.get("headers", [])
            rows = sweep_data.get("data", [])
            if headers and rows:
                self.results_text.append("  ".join(f"{h:>12}" for h in headers))
                for row in rows[:20]:
                    self.results_text.append("  ".join(f"{v:12.6g}" for v in row))
                if len(rows) > 20:
                    self.results_text.append(f"  ... ({len(rows)} total rows)")
            self.results_text.append("\nPlot opened in a new window.")
            self._show_or_overlay_plot("DC Sweep", sweep_data, DCSweepPlotDialog)
        else:
            self.results_text.append("\nDC Sweep data - see raw output below")
        self.canvas.clear_op_results()
        self.properties_panel.clear_simulation_results()

    def _display_ac_sweep_results(self, result):
        """Display AC Sweep results."""
        ac_data = result.data if result.data else None
        if ac_data:
            self._last_results = ac_data
            self.results_text.append("\nAC SWEEP RESULTS:")
            self.results_text.append("-" * 40)
            freqs = ac_data.get("frequencies", [])
            mag = ac_data.get("magnitude", {})
            self.results_text.append(f"  Frequency points: {len(freqs)}")
            self.results_text.append(f"  Signals: {', '.join(sorted(mag.keys()))}")
            if freqs:
                self.results_text.append(f"  Range: {freqs[0]:.4g} Hz — {freqs[-1]:.4g} Hz")
            self.results_text.append("\nBode plot opened in a new window.")
            self._show_or_overlay_plot("AC Sweep", ac_data, ACSweepPlotDialog)
        else:
            self.results_text.append("\nAC Sweep data - see raw output below")
        self.canvas.clear_op_results()
        self.properties_panel.clear_simulation_results()

    def _display_transient_results(self, result):
        """Display Transient analysis results."""
        tran_data = result.data if result.data else None

        if tran_data:
            self._last_results = tran_data
            self.results_text.append("\nTRANSIENT ANALYSIS RESULTS:")

            from simulation import ResultParser

            table_string = ResultParser.format_results_as_table(tran_data)
            self.results_text.append(table_string)

            self.results_text.append("\n" + "-" * 40)
            self.results_text.append("Waveform plot has also been generated in a new window.")

            # Check for overlay on existing waveform dialog
            if self._waveform_dialog is not None and self._waveform_dialog.isVisible():
                reply = QMessageBox.question(
                    self,
                    "Overlay Results",
                    "A waveform window is already open.\n\n"
                    "Yes = Overlay new results on existing plot\n"
                    "No = Replace with new results only",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._waveform_dialog.add_dataset(tran_data)
                    self._waveform_dialog.raise_()
                    self._waveform_dialog.activateWindow()
                else:
                    self._waveform_dialog.close()
                    self._waveform_dialog.deleteLater()
                    self._waveform_dialog = WaveformDialog(tran_data, self)
                    self._waveform_dialog.show()
            else:
                # Clean up previous waveform dialog
                if self._waveform_dialog is not None:
                    self._waveform_dialog.close()
                    self._waveform_dialog.deleteLater()
                self._waveform_dialog = WaveformDialog(tran_data, self)
                self._waveform_dialog.show()
        else:
            self.results_text.append("\nNo transient data found in output.")
        self.canvas.clear_op_results()
        self.properties_panel.clear_simulation_results()

    def _display_temp_sweep_results(self, result):
        """Display Temperature Sweep results."""
        temp_data = result.data if result.data else {}
        if isinstance(temp_data, dict) and "node_voltages" in temp_data:
            node_voltages = temp_data["node_voltages"]
        else:
            node_voltages = temp_data
        if node_voltages:
            self._last_results = node_voltages
            self.results_text.append("\nTEMPERATURE SWEEP RESULTS:")
            self.results_text.append("-" * 40)
            params = self.model.analysis_params
            self.results_text.append(
                f"Temperature range: {params.get('tempStart', '?')}\u00b0C "
                f"to {params.get('tempStop', '?')}\u00b0C "
                f"(step {params.get('tempStep', '?')}\u00b0C)"
            )
            self.results_text.append("")
            for node, voltage in sorted(node_voltages.items()):
                self.results_text.append(f"  {node:15s} : {voltage:12.6f} V")
            self.results_text.append("-" * 40)
            self.results_text.append("Note: values shown are from the final temperature step.")
        else:
            self.results_text.append("\nNo results found. Check raw output below.")
        self.canvas.clear_op_results()
        self.properties_panel.clear_simulation_results()

    def _display_param_sweep_results(self, result):
        """Display Parameter Sweep results."""
        sweep_data = result.data if result.data else None
        if sweep_data:
            self._last_results = sweep_data
            comp_id = sweep_data.get("component_id", "?")
            base_type = sweep_data.get("base_analysis_type", "?")
            labels = sweep_data.get("sweep_labels", [])
            step_results = sweep_data.get("results", [])
            ok_count = sum(1 for r in step_results if r.success)

            self.results_text.append("\nPARAMETER SWEEP RESULTS:")
            self.results_text.append("-" * 40)
            self.results_text.append(f"  Component:      {comp_id}")
            self.results_text.append(f"  Base analysis:  {base_type}")
            self.results_text.append(f"  Steps:          {ok_count}/{len(step_results)} succeeded")
            if labels:
                self.results_text.append(f"  Range:          {labels[0]} to {labels[-1]}")
            if sweep_data.get("cancelled"):
                self.results_text.append("  (sweep was cancelled)")
            self.results_text.append("-" * 40)

            if result.errors:
                self.results_text.append("\nStep errors:")
                for err in result.errors[:10]:
                    self.results_text.append(f"  - {err}")

            if ok_count > 0:
                self.results_text.append("\nPlot opened in a new window.")
                self._show_plot_dialog(ParameterSweepPlotDialog(sweep_data, self))
        else:
            self.results_text.append("\nNo parameter sweep data.")
        self.canvas.clear_op_results()
        self.properties_panel.clear_simulation_results()

    def _display_monte_carlo_results(self, result):
        """Display Monte Carlo results."""
        mc_data = result.data if result.data else None
        if mc_data:
            self._last_results = mc_data
            base_type = mc_data.get("base_analysis_type", "?")
            step_results = mc_data.get("results", [])
            ok_count = sum(1 for r in step_results if r.success)

            self.results_text.append("\nMONTE CARLO RESULTS:")
            self.results_text.append("-" * 40)
            self.results_text.append(f"  Base analysis:  {base_type}")
            self.results_text.append(f"  Runs:           {ok_count}/{len(step_results)} succeeded")
            tolerances = mc_data.get("tolerances", {})
            for cid, tol in sorted(tolerances.items()):
                self.results_text.append(
                    f"  {cid}: \u00b1{tol['tolerance_pct']}% ({tol.get('distribution', 'gaussian')})"
                )
            if mc_data.get("cancelled"):
                self.results_text.append("  (analysis was cancelled)")
            self.results_text.append("-" * 40)

            if result.errors:
                self.results_text.append("\nRun errors:")
                for err in result.errors[:10]:
                    self.results_text.append(f"  - {err}")

            if ok_count > 0:
                self.results_text.append("\nResults opened in a new window.")
                self._show_plot_dialog(MonteCarloResultsDialog(mc_data, self))
        else:
            self.results_text.append("\nNo Monte Carlo data.")
        self.canvas.clear_op_results()

    def _calculate_power(self, node_voltages):
        """Calculate and display power dissipation for all components."""
        from simulation.power_calculator import calculate_power, total_power

        components = self.circuit_ctrl.model.components
        nodes = self.circuit_ctrl.model.nodes
        power_data = calculate_power(components, nodes, node_voltages)

        if power_data:
            # Build voltage-across data for properties panel
            voltage_data = {}
            # Build terminal-to-node lookup
            term_to_label = {}
            for node in nodes:
                label = node.get_label()
                for comp_id, term_idx in node.terminals:
                    term_to_label[(comp_id, term_idx)] = label

            for comp in components:
                cid = comp.component_id
                l0 = term_to_label.get((cid, 0))
                l1 = term_to_label.get((cid, 1))
                if l0 and l1 and l0 in node_voltages and l1 in node_voltages:
                    voltage_data[cid] = node_voltages[l0] - node_voltages[l1]

            tp = total_power(power_data)
            self.properties_panel.set_simulation_results(power_data, voltage_data, tp)

            # Show summary in results text
            from GUI.format_utils import format_value

            self.results_text.append("\nPOWER DISSIPATION:")
            self.results_text.append("-" * 40)
            for cid, p in sorted(power_data.items()):
                sign = "dissipating" if p >= 0 else "supplying"
                self.results_text.append(f"  {cid:15s} : {format_value(abs(p), 'W'):>12s} ({sign})")
            self.results_text.append("-" * 40)
            self.results_text.append(f"  {'Total':15s} : {format_value(abs(tp), 'W'):>12s}")
        else:
            self.properties_panel.clear_simulation_results()

    def _show_plot_dialog(self, dialog):
        """Show a plot dialog, closing any previous one."""
        if self._plot_dialog is not None:
            self._plot_dialog.close()
            self._plot_dialog.deleteLater()
        self._plot_dialog = dialog
        self._plot_dialog.show()

    def _show_or_overlay_plot(self, analysis_type, data, dialog_class):
        """Show a new plot or overlay data on an existing compatible dialog.

        If a plot dialog of the same analysis type is already open, the user
        is asked whether to overlay the new results or replace the old plot.
        """
        if (
            self._plot_dialog is not None
            and self._plot_dialog.isVisible()
            and getattr(self._plot_dialog, "analysis_type", None) == analysis_type
        ):
            reply = QMessageBox.question(
                self,
                "Overlay Results",
                "A plot window is already open.\n\n"
                "Yes = Overlay new results on existing plot\n"
                "No = Replace with new results only",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._plot_dialog.add_dataset(data)
                self._plot_dialog.raise_()
                self._plot_dialog.activateWindow()
                return

        self._show_plot_dialog(dialog_class(data, self))

    def export_results_csv(self):
        """Export the last simulation results to a CSV file"""
        if self._last_results is None:
            return

        from simulation.csv_exporter import (
            export_ac_results,
            export_dc_sweep_results,
            export_op_results,
            export_transient_results,
            write_csv,
        )

        circuit_name = os.path.basename(str(self.file_ctrl.current_file)) if self.file_ctrl.current_file else ""

        if self._last_results_type == "DC Operating Point":
            csv_content = export_op_results(self._last_results, circuit_name)
        elif self._last_results_type == "DC Sweep":
            csv_content = export_dc_sweep_results(self._last_results, circuit_name)
        elif self._last_results_type == "AC Sweep":
            csv_content = export_ac_results(self._last_results, circuit_name)
        elif self._last_results_type == "Transient":
            csv_content = export_transient_results(self._last_results, circuit_name)
        else:
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export Results to CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filename:
            try:
                write_csv(csv_content, filename)
                statusBar = self.statusBar()
                if statusBar:
                    statusBar.showMessage(f"Results exported to {filename}", 3000)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")
