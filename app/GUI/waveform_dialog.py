import matplotlib
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QWidget, QHeaderView, QLabel,
                             QPushButton, QGroupBox, QFormLayout, QLineEdit)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

matplotlib.use('QtAgg')

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
        self.current_page = 0
        self.page_size = 10
        self.view_data = self.full_data

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
        right_layout.addWidget(self.table)
        
        # Pagination Controls
        pagination_layout = QHBoxLayout()
        self.prev_button = QPushButton("<< Previous")
        self.prev_button.clicked.connect(self.show_previous_page)
        self.page_label = QLabel()
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self.show_next_page)
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.next_button)
        right_layout.addLayout(pagination_layout)
        
        # Initial population
        self.update_view()

    def apply_filters(self):
        """Filters the data based on user input and updates the view."""
        filtered_data = self.full_data
        
        # Parse filter values safely
        try:
            time_min = float(self.time_min_edit.text()) if self.time_min_edit.text() else None
            time_max = float(self.time_max_edit.text()) if self.time_max_edit.text() else None
            volt_min = float(self.volt_min_edit.text()) if self.volt_min_edit.text() else None
            volt_max = float(self.volt_max_edit.text()) if self.volt_max_edit.text() else None
        except ValueError:
            # Handle case where user enters non-numeric text
            # For simplicity, we just won't filter in this case.
            # A real app would show an error message.
            self.reset_filters() 
            return

        # Apply time filter
        if time_min is not None:
            filtered_data = [row for row in filtered_data if row.get('time', 0) >= time_min]
        if time_max is not None:
            filtered_data = [row for row in filtered_data if row.get('time', 0) <= time_max]

        # Apply voltage filter
        if volt_min is not None or volt_max is not None:
            voltage_keys = [k for k in self.full_data[0].keys() if k not in ['time', 'index']]
            
            def voltage_in_range(row):
                for key in voltage_keys:
                    v = row.get(key, 0)
                    in_min = (volt_min is None or v >= volt_min)
                    in_max = (volt_max is None or v <= volt_max)
                    if in_min and in_max:
                        return True # Match if any voltage in the row is within range
                return False

            filtered_data = [row for row in filtered_data if voltage_in_range(row)]

        self.view_data = filtered_data
        self.current_page = 0
        self.update_view()

    def reset_filters(self):
        """Resets all filters and shows the full dataset."""
        self.time_min_edit.clear()
        self.time_max_edit.clear()
        self.volt_min_edit.clear()
        self.volt_max_edit.clear()
        
        self.view_data = self.full_data
        self.current_page = 0
        self.update_view()

    def update_view(self):
        """Populates the table and plot with the current view_data"""
        self.plot_data(self.view_data)
        self.populate_table()

    def populate_table(self):
        """Populates the data table with the current page of view_data"""
        if not self.view_data:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self._update_pagination_controls()
            return

        headers = list(self.view_data[0].keys())
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Calculate data slice for the current page
        start_index = self.current_page * self.page_size
        end_index = start_index + self.page_size
        data_slice = self.view_data[start_index:end_index]
        
        self.table.setRowCount(len(data_slice))

        for row_index, row_data in enumerate(data_slice):
            for col_index, header in enumerate(headers):
                item = QTableWidgetItem(f"{row_data[header]:.6e}")
                self.table.setItem(row_index, col_index, item)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._update_pagination_controls()

    def _update_pagination_controls(self):
        """Updates the pagination buttons and label"""
        total_rows = len(self.view_data)
        start_index = self.current_page * self.page_size
        end_index = min(start_index + self.page_size, total_rows)

        if total_rows > 0:
            self.page_label.setText(f"Showing {start_index + 1}-{end_index} of {total_rows}")
        else:
            self.page_label.setText("Showing 0-0 of 0")

        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(end_index < total_rows)

    def show_previous_page(self):
        """Navigate to the previous page of data"""
        if self.current_page > 0:
            self.current_page -= 1
            self.populate_table()
    
    def show_next_page(self):
        """Navigate to the next page of data"""
        total_rows = len(self.view_data)
        if (self.current_page + 1) * self.page_size < total_rows:
            self.current_page += 1
            self.populate_table()

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