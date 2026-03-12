"""Qt implementations of DialogProvider and ProgressHandle protocols."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog


class QtProgressHandle(QObject):
    """Adapter wrapping QProgressDialog to satisfy the ProgressHandle protocol."""

    def __init__(self, dialog: QProgressDialog) -> None:
        super().__init__()
        self._dialog = dialog
        self._dialog.show()

    def update(self, value: int, message: str = "") -> bool:
        """Advance the progress bar.  Returns False if the user cancelled."""
        if message:
            self._dialog.setLabelText(message)
        self._dialog.setValue(value)
        # Process events so the dialog paints and cancel button responds.
        from PyQt6.QtWidgets import QApplication

        # AUDIT(quality): processEvents() can cause re-entrancy; consider ExcludeUserInputEvents flag or a safer approach
        QApplication.processEvents()
        return not self._dialog.wasCanceled()

    def close(self) -> None:
        """Close the progress dialog."""
        self._dialog.close()


class QtDialogProvider(QObject):
    """Qt implementation of DialogProvider using standard Qt dialog classes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._parent = parent

    # --- File dialogs ---

    def ask_save_file(self, title: str, filters: str, default_name: str = "") -> Optional[Path]:
        """Show a save-file dialog.  Returns chosen path or None."""
        filename, _ = QFileDialog.getSaveFileName(self._parent, title, default_name, filters)
        return Path(filename) if filename else None

    def ask_open_file(self, title: str, filters: str) -> Optional[Path]:
        """Show an open-file dialog.  Returns chosen path or None."""
        filename, _ = QFileDialog.getOpenFileName(self._parent, title, "", filters)
        return Path(filename) if filename else None

    # --- Confirmation / message dialogs ---

    def confirm(self, title: str, message: str) -> bool:
        """Show a yes/no confirmation.  Returns True for Yes."""
        reply = QMessageBox.question(
            self._parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def show_error(self, title: str, message: str) -> None:
        """Show an error message dialog."""
        QMessageBox.critical(self._parent, title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Show a warning message dialog."""
        QMessageBox.warning(self._parent, title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show an informational message dialog."""
        QMessageBox.information(self._parent, title, message)

    # --- Analysis configuration ---

    def ask_analysis_params(self, analysis_type: str, current_params: dict) -> Optional[dict]:
        """Show the analysis-parameter dialog.  Returns params dict or None."""
        from .analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog(analysis_type=analysis_type, parent=self._parent)
        if dialog.exec() == AnalysisDialog.DialogCode.Accepted:
            return dialog.get_parameters()
        return None

    def ask_parameter_sweep_config(self, components: dict[str, Any]) -> Optional[dict]:
        """Show the parameter-sweep configuration dialog.  Returns config or None."""
        from .parameter_sweep_dialog import ParameterSweepDialog

        dialog = ParameterSweepDialog(components=components, parent=self._parent)
        if dialog.exec() == ParameterSweepDialog.DialogCode.Accepted:
            return dialog.get_parameters()
        return None

    def ask_monte_carlo_config(self, components: dict[str, Any]) -> Optional[dict]:
        """Show the Monte Carlo configuration dialog.  Returns config or None."""
        from .monte_carlo_dialog import MonteCarloDialog

        dialog = MonteCarloDialog(components=components, parent=self._parent)
        if dialog.exec() == MonteCarloDialog.DialogCode.Accepted:
            return dialog.get_parameters()
        return None

    # --- Progress ---

    def create_progress(self, title: str, message: str, maximum: int) -> QtProgressHandle:
        """Create a cancellable progress dialog.  Returns a QtProgressHandle."""
        dialog = QProgressDialog(message, "Cancel", 0, maximum, self._parent)
        dialog.setWindowTitle(title)
        dialog.setMinimumDuration(0)
        return QtProgressHandle(dialog)
