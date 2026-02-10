import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from simulation.fft_analysis import analyze_signal_spectrum

from .format_utils import format_value, parse_value
from .measurement_cursors import MeasurementCursors, format_readout_html
from .styles import SCROLL_LOAD_COUNT

matplotlib.use("QtAgg")

# Get colors from the 'Paired' colormap for color-blind friendliness
cmap = plt.get_cmap("Paired")
HIGHLIGHT_COLORS = [QColor.fromRgbF(*cmap(i)) for i in range(12)]


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class WaveformDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Transient Analysis Waveforms")
        self.setMinimumSize(1200, 700)

        # Store data
        self.full_data = data
        self.view_data = self.full_data
        self.headers = []
        self.rows_loaded = 0

        # Visibility state for columns
        self.voltage_keys = sorted([k for k in data[0].keys() if k.lower() not in ["time", "index"]])
        self.column_visibility = {key: True for key in self.voltage_keys}

        # Assign persistent colors for each plot for color stability
        self.plot_colors = {}
        color_map = plt.get_cmap("Paired")  # Good for distinct colors
        for i, key in enumerate(self.voltage_keys):
            self.plot_colors[key] = color_map(i % 12)

        # Filter ranges
        self.time_min = None
        self.time_max = None
        self.volt_min = None
        self.volt_max = None

        # Main layout
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # --- Left Panel: Plot ---
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        main_layout.addWidget(self.canvas, 2)

        # --- Right Panel: Table and Controls ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel, 1)

        # --- Toggle Overlays ---
        toggle_group = QGroupBox("Toggle Overlays")
        toggle_layout = QVBoxLayout()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for key in self.voltage_keys:
            checkbox = QCheckBox(key)
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda state, k=key: self._on_visibility_changed(k, state))
            scroll_layout.addWidget(checkbox)

        scroll_area.setWidget(scroll_content)
        toggle_layout.addWidget(scroll_area)
        toggle_group.setLayout(toggle_layout)
        right_layout.addWidget(toggle_group)

        # --- Filter Controls ---
        filter_group = QGroupBox("Filter Data")
        form_layout = QFormLayout()

        self.time_min_edit = QLineEdit()
        self.time_max_edit = QLineEdit()
        self.volt_min_edit = QLineEdit()
        self.volt_max_edit = QLineEdit()

        form_layout.addRow("Time Min:", self.time_min_edit)
        form_layout.addRow("Time Max:", self.time_max_edit)
        form_layout.addRow("Voltage Min:", self.volt_min_edit)
        form_layout.addRow("Voltage Max:", self.volt_max_edit)

        filter_buttons_layout = QHBoxLayout()
        highlight_button = QPushButton("Highlight")
        highlight_button.clicked.connect(self.apply_highlight)
        apply_button = QPushButton("Apply Filter")
        apply_button.clicked.connect(self.apply_filters)
        reset_button = QPushButton("Reset View")
        reset_button.clicked.connect(self.reset_view)
        filter_buttons_layout.addWidget(highlight_button)
        filter_buttons_layout.addWidget(apply_button)
        filter_buttons_layout.addWidget(reset_button)

        filter_layout = QVBoxLayout()
        filter_layout.addLayout(form_layout)
        filter_layout.addLayout(filter_buttons_layout)
        filter_group.setLayout(filter_layout)
        right_layout.addWidget(filter_group)

        # Export and FFT buttons
        export_button = QPushButton("Export CSV")
        export_button.clicked.connect(self._export_csv)
        right_layout.addWidget(export_button)

        fft_button = QPushButton("Analyze FFT")
        fft_button.clicked.connect(self._show_fft_analysis)
        right_layout.addWidget(fft_button)

        # --- Measurement Cursors ---
        cursor_group = QGroupBox("Measurement Cursors")
        cursor_layout = QVBoxLayout(cursor_group)
        self.cursor_checkbox = QCheckBox("Enable Cursors")
        self.cursor_checkbox.setToolTip(
            "Left-click to place Cursor A, right-click for Cursor B. "
            "Drag an existing cursor to move it."
        )
        cursor_layout.addWidget(self.cursor_checkbox)
        self.cursor_readout = QLabel("")
        self.cursor_readout.setWordWrap(True)
        cursor_layout.addWidget(self.cursor_readout)
        right_layout.addWidget(cursor_group)

        # Create cursor manager
        self._cursors = MeasurementCursors(self.canvas, self.canvas.axes)
        self._cursors.set_readout_callback(
            lambda data: self.cursor_readout.setText(
                format_readout_html(data, x_label="Time", y_label="Voltage")
            )
        )
        self.cursor_checkbox.toggled.connect(self._cursors.set_enabled)

        # Data Table
        right_layout.addWidget(QLabel("Simulation Data"))
        self.table = QTableWidget()
        self.table.verticalScrollBar().valueChanged.connect(self._on_scroll)
        right_layout.addWidget(self.table)

        # Initial population
        self.update_view()

    def _on_visibility_changed(self, key, is_checked):
        """Updates the visibility state and refreshes the view."""
        self.column_visibility[key] = is_checked
        self.update_view()

    def _on_scroll(self, value):
        """Handler for the scrollbar valueChanged signal."""
        scrollbar = self.table.verticalScrollBar()
        # Load more rows if user is near the bottom
        if value >= scrollbar.maximum() - 5:
            self._load_more_rows()

    def _load_more_rows(self):
        """Appends the next chunk of data to the table."""
        if self.rows_loaded >= len(self.view_data):
            return

        start_index = self.rows_loaded
        end_index = min(start_index + SCROLL_LOAD_COUNT, len(self.view_data))

        data_chunk = self.view_data[start_index:end_index]

        current_row_count = self.table.rowCount()
        self.table.setRowCount(current_row_count + len(data_chunk))

        for row_index_offset, row_data in enumerate(data_chunk):
            table_row_index = current_row_count + row_index_offset

            time_val = row_data.get("time", 0)
            row_in_time_range = False
            if self.time_min is not None or self.time_max is not None:
                if (self.time_min is None or time_val >= self.time_min) and (
                    self.time_max is None or time_val <= self.time_max
                ):
                    row_in_time_range = True

            for col_index, header in enumerate(self.headers):
                value = row_data[header]
                unit = "s" if header == "time" else "V"
                formatted_str = format_value(value, unit)
                item = QTableWidgetItem(formatted_str)

                should_highlight = False
                if header == "time":
                    if row_in_time_range:
                        should_highlight = True
                else:  # Voltage column
                    cell_in_volt_range = False
                    if self.volt_min is not None or self.volt_max is not None:
                        if (self.volt_min is None or value >= self.volt_min) and (
                            self.volt_max is None or value <= self.volt_max
                        ):
                            cell_in_volt_range = True

                    if row_in_time_range or cell_in_volt_range:
                        should_highlight = True

                if should_highlight:
                    color = HIGHLIGHT_COLORS[col_index % len(HIGHLIGHT_COLORS)]
                    item.setBackground(color)

                self.table.setItem(table_row_index, col_index, item)

        self.rows_loaded = end_index

    def apply_highlight(self):
        """Applies highlighting without filtering the data and scrolls to the first highlighted row."""
        try:
            self.time_min = parse_value(self.time_min_edit.text()) if self.time_min_edit.text() else None
            self.time_max = parse_value(self.time_max_edit.text()) if self.time_max_edit.text() else None
            self.volt_min = parse_value(self.volt_min_edit.text()) if self.volt_min_edit.text() else None
            self.volt_max = parse_value(self.volt_max_edit.text()) if self.volt_max_edit.text() else None
        except ValueError:
            self.reset_view()
            return

        # Always show all data when highlighting
        self.view_data = self.full_data
        self.update_view()

        # Scroll to the first relevant row
        first_highlight_row = -1
        for i, row in enumerate(self.view_data):
            time_val = row["time"]
            time_in_range = (self.time_min is None or time_val >= self.time_min) and (
                self.time_max is None or time_val <= self.time_max
            )

            if self.time_min is not None or self.time_max is not None:
                if time_in_range:
                    first_highlight_row = i
                    break

            if self.volt_min is not None or self.volt_max is not None:
                voltage_keys = [k for k in row.keys() if k.lower() not in ["time", "index"]]
                for key in voltage_keys:
                    v = row.get(key, 0)
                    if (self.volt_min is None or v >= self.volt_min) and (self.volt_max is None or v <= self.volt_max):
                        first_highlight_row = i
                        break
                if first_highlight_row != -1:
                    break

        if first_highlight_row != -1:
            self.table.scrollToItem(self.table.item(first_highlight_row, 0))

    def apply_filters(self):
        """Filters the data based on user input and updates the view."""
        try:
            self.time_min = parse_value(self.time_min_edit.text()) if self.time_min_edit.text() else None
            self.time_max = parse_value(self.time_max_edit.text()) if self.time_max_edit.text() else None
            self.volt_min = parse_value(self.volt_min_edit.text()) if self.volt_min_edit.text() else None
            self.volt_max = parse_value(self.volt_max_edit.text()) if self.volt_max_edit.text() else None
        except ValueError:
            self.reset_view()
            return

        filtered_data = self.full_data

        if self.time_min is not None:
            filtered_data = [row for row in filtered_data if row.get("time", 0) >= self.time_min]
        if self.time_max is not None:
            filtered_data = [row for row in filtered_data if row.get("time", 0) <= self.time_max]

        if (self.volt_min is not None or self.volt_max is not None) and filtered_data:
            voltage_keys = [k for k in filtered_data[0].keys() if k.lower() not in ["time", "index"]]

            def voltage_in_range(row):
                for key in voltage_keys:
                    v = row.get(key, 0)
                    in_min = self.volt_min is None or v >= self.volt_min
                    in_max = self.volt_max is None or v <= self.volt_max
                    if in_min and in_max:
                        return True
                return False

            filtered_data = [row for row in filtered_data if voltage_in_range(row)]

        self.view_data = filtered_data
        self.update_view()

    def reset_view(self):
        """Resets all filters and highlights, showing the full dataset."""
        self.time_min_edit.clear()
        self.time_max_edit.clear()
        self.volt_min_edit.clear()
        self.volt_max_edit.clear()

        self.time_min = None
        self.time_max = None
        self.volt_min = None
        self.volt_max = None

        self.view_data = self.full_data
        self.update_view()

    def update_view(self):
        """Resets and populates the table and plot with the current view_data."""
        self.plot_data(self.view_data)
        # Restore cursor lines after axes.clear() + replot
        if hasattr(self, "_cursors"):
            self._cursors.refresh()
        self.table.clear()
        self.table.setRowCount(0)
        self.rows_loaded = 0
        self.populate_table_initial()

    def populate_table_initial(self):
        """Populates the data table with the first chunk of view_data."""
        if not self.view_data:
            self.table.setColumnCount(0)
            return

        all_headers = [h for h in self.view_data[0].keys() if h.lower() != "index"]
        # Filter headers based on visibility, always keeping 'time'
        self.headers = [h for h in all_headers if h == "time" or self.column_visibility.get(h, False)]

        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Load the first chunk of rows
        self._load_more_rows()

    def plot_data(self, data):
        """Plots the transient analysis data and highlights specific segments."""
        self.canvas.axes.clear()
        if not data:
            self.canvas.axes.text(
                0.5, 0.5, "No data to display.", horizontalalignment="center", verticalalignment="center"
            )
            self.canvas.draw()
            return

        headers = list(data[0].keys())
        time_key = "time"
        if time_key not in headers:
            self.canvas.axes.text(
                0.5, 0.5, 'No "time" column found in data.', horizontalalignment="center", verticalalignment="center"
            )
            self.canvas.draw()
            return

        time_full = [row[time_key] for row in data]

        # Use only visible keys
        visible_voltage_keys = [k for k in self.voltage_keys if self.column_visibility.get(k, False)]

        # 1. Plot base lines using persistent colors
        for key in visible_voltage_keys:
            voltage_values = [row[key] for row in data]
            if len(time_full) == len(voltage_values):
                color = self.plot_colors.get(key, "k")  # Use stored color
                self.canvas.axes.plot(time_full, voltage_values, label=f"V({key})", color=color)

        # 2. Highlighting logic: plot highlighted segments on top
        is_highlighting = (
            self.time_min is not None
            or self.time_max is not None
            or self.volt_min is not None
            or self.volt_max is not None
        )

        if is_highlighting:
            for key in visible_voltage_keys:
                current_segment_t = []
                current_segment_v = []
                color = self.plot_colors.get(key, "k")  # Get stored color

                for row in data:
                    t = row[time_key]
                    v = row[key]

                    # Determine if the point is in range
                    time_in_range = (self.time_min is None or t >= self.time_min) and (
                        self.time_max is None or t <= self.time_max
                    )
                    volt_in_range = (self.volt_min is None or v >= self.volt_min) and (
                        self.volt_max is None or v <= self.volt_max
                    )

                    point_is_in_highlight_range = False
                    if self.time_min is not None or self.time_max is not None:
                        if time_in_range:
                            point_is_in_highlight_range = True

                    if self.volt_min is not None or self.volt_max is not None:
                        if volt_in_range:
                            point_is_in_highlight_range = True

                    if point_is_in_highlight_range:
                        current_segment_t.append(t)
                        current_segment_v.append(v)
                    else:
                        if current_segment_t:
                            self.canvas.axes.plot(
                                current_segment_t,
                                current_segment_v,
                                color=color,
                                linewidth=4,
                                alpha=0.7,
                                solid_capstyle="round",
                            )
                            current_segment_t = []
                            current_segment_v = []

                if current_segment_t:
                    self.canvas.axes.plot(
                        current_segment_t,
                        current_segment_v,
                        color=color,
                        linewidth=4,
                        alpha=0.7,
                        solid_capstyle="round",
                    )

        self.canvas.axes.set_title("Transient Analysis")
        self.canvas.axes.set_xlabel("Time (s)")
        self.canvas.axes.set_ylabel("Voltage (V)")
        self.canvas.axes.legend()
        self.canvas.axes.grid(True)
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def _export_csv(self):
        """Export current view data to CSV."""
        from simulation.csv_exporter import export_transient_results, write_csv

        csv_content = export_transient_results(self.view_data)
        filename, _ = QFileDialog.getSaveFileName(self, "Export Results to CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filename:
            try:
                write_csv(csv_content, filename)
                QMessageBox.information(self, "Success", f"Exported to {filename}")
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def _show_fft_analysis(self):
        """Show FFT analysis dialog for transient results."""
        if not self.full_data or len(self.full_data) < 4:
            QMessageBox.warning(self, "Insufficient Data", "Need at least 4 data points for FFT analysis.")
            return

        # Extract time array
        time = np.array([row.get("time", 0) for row in self.full_data])

        # Get list of available signals (exclude time)
        signal_names = [k for k in self.voltage_keys if self.column_visibility.get(k, True)]

        if not signal_names:
            QMessageBox.warning(self, "No Signals", "No visible signals to analyze. Enable at least one signal.")
            return

        # Show FFT dialog with signal selection
        dialog = FFTAnalysisDialog(time, self.full_data, signal_names, self)
        dialog.exec()

    def closeEvent(self, event):
        """Clean up matplotlib figure to prevent memory leaks."""
        self._cursors.disconnect()
        plt.close(self.canvas.figure)
        super().closeEvent(event)


class FFTAnalysisDialog(QDialog):
    """Dialog for displaying FFT analysis of transient simulation signals."""

    def __init__(self, time: np.ndarray, data: list, signal_names: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFT Analysis")
        self.setMinimumSize(1000, 700)

        self.time = time
        self.data = data
        self.signal_names = signal_names

        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Controls
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Signal:"))
        self.signal_combo = QComboBox()
        self.signal_combo.addItems(signal_names)
        self.signal_combo.currentTextChanged.connect(self._update_fft)
        controls_layout.addWidget(self.signal_combo)

        controls_layout.addWidget(QLabel("Window:"))
        self.window_combo = QComboBox()
        self.window_combo.addItems(["Hanning", "Hamming", "Blackman", "None"])
        self.window_combo.currentTextChanged.connect(self._update_fft)
        controls_layout.addWidget(self.window_combo)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Info label for fundamental frequency and THD
        self.info_label = QLabel("")
        layout.addWidget(self.info_label)

        # Magnitude plot
        self.mag_canvas = MplCanvas(self, width=8, height=4, dpi=100)
        layout.addWidget(self.mag_canvas)

        # Phase plot
        self.phase_canvas = MplCanvas(self, width=8, height=3, dpi=100)
        layout.addWidget(self.phase_canvas)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        # Initial plot
        self._update_fft()

    def _update_fft(self):
        """Compute and display FFT for selected signal."""
        signal_name = self.signal_combo.currentText()
        window_type = self.window_combo.currentText().lower()

        # Extract signal data
        signal = np.array([row.get(signal_name, 0) for row in self.data])

        try:
            # Compute FFT
            fft_result = analyze_signal_spectrum(self.time, signal, signal_name, window_type)

            # Update info label
            info_text = f"<b>Signal:</b> {signal_name} | <b>Window:</b> {window_type.title()}"
            if fft_result.fundamental_freq is not None and fft_result.fundamental_freq > 0:
                info_text += f" | <b>Fundamental:</b> {fft_result.fundamental_freq:.2f} Hz"
            if fft_result.thd_percent is not None:
                info_text += f" | <b>THD:</b> {fft_result.thd_percent:.3f}%"
            self.info_label.setText(info_text)

            # Plot magnitude spectrum
            self.mag_canvas.axes.clear()
            self.mag_canvas.axes.semilogx(fft_result.frequencies, fft_result.magnitude_db, linewidth=1.5)
            self.mag_canvas.axes.set_title(f"Magnitude Spectrum - {signal_name}")
            self.mag_canvas.axes.set_xlabel("Frequency (Hz)")
            self.mag_canvas.axes.set_ylabel("Magnitude (dB)")
            self.mag_canvas.axes.grid(True, which="both", alpha=0.3)
            self.mag_canvas.figure.tight_layout()
            self.mag_canvas.draw()

            # Plot phase spectrum
            self.phase_canvas.axes.clear()
            self.phase_canvas.axes.semilogx(fft_result.frequencies, fft_result.phase, linewidth=1.5, color="orange")
            self.phase_canvas.axes.set_title("Phase Spectrum")
            self.phase_canvas.axes.set_xlabel("Frequency (Hz)")
            self.phase_canvas.axes.set_ylabel("Phase (degrees)")
            self.phase_canvas.axes.grid(True, which="both", alpha=0.3)
            self.phase_canvas.figure.tight_layout()
            self.phase_canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "FFT Error", f"Failed to compute FFT: {e}")

    def closeEvent(self, event):
        """Clean up matplotlib figures."""
        plt.close(self.mag_canvas.figure)
        plt.close(self.phase_canvas.figure)
        super().closeEvent(event)
