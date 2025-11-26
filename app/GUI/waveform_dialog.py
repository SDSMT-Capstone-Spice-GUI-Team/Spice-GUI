import matplotlib
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QWidget, QHeaderView, QLabel,
                             QPushButton, QGroupBox, QFormLayout, QLineEdit)
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .format_utils import parse_value, format_value

matplotlib.use('QtAgg')

# Constants for infinite scroll
INITIAL_LOAD_COUNT = 50
SCROLL_LOAD_COUNT = 25

HIGHLIGHT_COLORS = [
    QColor(255, 230, 230),  # Light Red
    QColor(230, 255, 230),  # Light Green
    QColor(230, 230, 255),  # Light Blue
    QColor(255, 255, 230),  # Light Yellow
    QColor(255, 230, 255),  # Light Magenta
    QColor(230, 255, 255),  # Light Cyan
]

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
        apply_button = QPushButton("Apply Filter")
        apply_button.clicked.connect(self.apply_filters)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_filters)
        filter_buttons_layout.addWidget(apply_button)
        filter_buttons_layout.addWidget(reset_button)
        
        filter_layout = QVBoxLayout()
        filter_layout.addLayout(form_layout)
        filter_layout.addLayout(filter_buttons_layout)
        filter_group.setLayout(filter_layout)
        right_layout.addWidget(filter_group)

        # Data Table
        right_layout.addWidget(QLabel("Simulation Data"))
        self.table = QTableWidget()
        self.table.verticalScrollBar().valueChanged.connect(self._on_scroll)
        right_layout.addWidget(self.table)
        
        # Initial population
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
            for col_index, header in enumerate(self.headers):
                unit = "s" if header == "time" else "V"
                formatted_str = format_value(row_data[header], unit)
                item = QTableWidgetItem(formatted_str)
                self.table.setItem(table_row_index, col_index, item)
        
        self.rows_loaded = end_index

    def apply_filters(self):
        """Filters the data based on user input and updates the view."""
        filtered_data = self.full_data
        
        try:
            time_min = parse_value(self.time_min_edit.text()) if self.time_min_edit.text() else None
            time_max = parse_value(self.time_max_edit.text()) if self.time_max_edit.text() else None
            volt_min = parse_value(self.volt_min_edit.text()) if self.volt_min_edit.text() else None
            volt_max = parse_value(self.volt_max_edit.text()) if self.volt_max_edit.text() else None
        except ValueError:
            self.reset_filters() 
            return

        if time_min is not None:
            filtered_data = [row for row in filtered_data if row.get('time', 0) >= time_min]
        if time_max is not None:
            filtered_data = [row for row in filtered_data if row.get('time', 0) <= time_max]

        if (volt_min is not None or volt_max is not None) and filtered_data:
            voltage_keys = [k for k in filtered_data[0].keys() if k not in ['time', 'index']]
            
            def voltage_in_range(row):
                for key in voltage_keys:
                    v = row.get(key, 0)
                    in_min = (volt_min is None or v >= volt_min)
                    in_max = (volt_max is None or v <= volt_max)
                    if in_min and in_max:
                        return True
                return False

            filtered_data = [row for row in filtered_data if voltage_in_range(row)]

        self.view_data = filtered_data
        self.update_view()

    def reset_filters(self):
        """Resets all filters and shows the full dataset."""
        self.time_min_edit.clear()
        self.time_max_edit.clear()
        self.volt_min_edit.clear()
        self.volt_max_edit.clear()
        
        self.view_data = self.full_data
        self.update_view()

    def update_view(self):
        """Resets and populates the table and plot with the current view_data."""
        self.plot_data(self.view_data)
        self.table.clear()
        self.table.setRowCount(0)
        self.rows_loaded = 0
        self.populate_table_initial()

    def populate_table_initial(self):
        """Populates the data table with the first chunk of view_data."""
        if not self.view_data:
            self.table.setColumnCount(0)
            return
        
        # Set headers, excluding 'index'
        self.headers = [h for h in self.view_data[0].keys() if h.lower() != 'index']
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Load the first chunk of rows
        self._load_more_rows()

    def plot_data(self, data):
        """Plots the transient analysis data from a list of dictionaries."""
        self.canvas.axes.clear()
        if not data:
            self.canvas.axes.text(0.5, 0.5, 'No data to display.',
                                  horizontalalignment='center',
                                  verticalalignment='center')
            self.canvas.draw()
            return

        headers = list(data[0].keys())
        time_key = 'time' if 'time' in headers else None
        
        if not time_key or not data:
            self.canvas.axes.text(0.5, 0.5, 'No "time" column found in data.',
                                  horizontalalignment='center',
                                  verticalalignment='center')
            self.canvas.draw()
            return
            
        time = [row[time_key] for row in data]
        
        voltage_keys = [h for h in headers if h != time_key and h.lower() != 'index']
        
        for key in voltage_keys:
            voltage_values = [row[key] for row in data]
            if len(time) == len(voltage_values):
                self.canvas.axes.plot(time, voltage_values, label=f'V({key})')

        self.canvas.axes.set_title('Transient Analysis')
        self.canvas.axes.set_xlabel('Time (s)')
        self.canvas.axes.set_ylabel('Voltage (V)')
        self.canvas.axes.legend()
        self.canvas.axes.grid(True)
        self.canvas.figure.tight_layout()
        self.canvas.draw()