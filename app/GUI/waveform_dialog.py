import matplotlib
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QWidget, QHeaderView, QLabel,
                             QPushButton, QGroupBox, QFormLayout, QLineEdit, QCheckBox, QScrollArea)
import matplotlib.pyplot as plt
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .format_utils import parse_value, format_value

matplotlib.use('QtAgg')

# Constants for infinite scroll
INITIAL_LOAD_COUNT = 50
SCROLL_LOAD_COUNT = 25

# Get colors from the 'Paired' colormap for color-blind friendliness
cmap = plt.get_cmap('Paired')
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
        self.voltage_keys = sorted([k for k in data[0].keys() if k.lower() not in ['time', 'index']])
        self.column_visibility = {key: True for key in self.voltage_keys}

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

            time_val = row_data.get('time', 0)
            row_in_time_range = False
            if self.time_min is not None or self.time_max is not None:
                if (self.time_min is None or time_val >= self.time_min) and \
                   (self.time_max is None or time_val <= self.time_max):
                    row_in_time_range = True

            for col_index, header in enumerate(self.headers):
                value = row_data[header]
                unit = "s" if header == "time" else "V"
                formatted_str = format_value(value, unit)
                item = QTableWidgetItem(formatted_str)

                should_highlight = False
                if header == 'time':
                    if row_in_time_range:
                        should_highlight = True
                else:  # Voltage column
                    cell_in_volt_range = False
                    if self.volt_min is not None or self.volt_max is not None:
                        if (self.volt_min is None or value >= self.volt_min) and \
                           (self.volt_max is None or value <= self.volt_max):
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
            time_val = row['time']
            time_in_range = (self.time_min is None or time_val >= self.time_min) and \
                            (self.time_max is None or time_val <= self.time_max)
            
            if self.time_min is not None or self.time_max is not None:
                if time_in_range:
                    first_highlight_row = i
                    break
            
            if self.volt_min is not None or self.volt_max is not None:
                voltage_keys = [k for k in row.keys() if k.lower() not in ['time', 'index']]
                for key in voltage_keys:
                    v = row.get(key, 0)
                    if (self.volt_min is None or v >= self.volt_min) and \
                       (self.volt_max is None or v <= self.volt_max):
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
            filtered_data = [row for row in filtered_data if row.get('time', 0) >= self.time_min]
        if self.time_max is not None:
            filtered_data = [row for row in filtered_data if row.get('time', 0) <= self.time_max]

        if (self.volt_min is not None or self.volt_max is not None) and filtered_data:
            voltage_keys = [k for k in filtered_data[0].keys() if k.lower() not in ['time', 'index']]
            
            def voltage_in_range(row):
                for key in voltage_keys:
                    v = row.get(key, 0)
                    in_min = (self.volt_min is None or v >= self.volt_min)
                    in_max = (self.volt_max is None or v <= self.volt_max)
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
        self.table.clear()
        self.table.setRowCount(0)
        self.rows_loaded = 0
        self.populate_table_initial()

    def populate_table_initial(self):
        """Populates the data table with the first chunk of view_data."""
        if not self.view_data:
            self.table.setColumnCount(0)
            return
        
        all_headers = [h for h in self.view_data[0].keys() if h.lower() != 'index']
        # Filter headers based on visibility, always keeping 'time'
        self.headers = [h for h in all_headers if h == 'time' or self.column_visibility.get(h, False)]

        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Load the first chunk of rows
        self._load_more_rows()

    def plot_data(self, data):
        """Plots the transient analysis data and highlights specific segments."""
        self.canvas.axes.clear()
        if not data:
            self.canvas.axes.text(0.5, 0.5, 'No data to display.',
                                  horizontalalignment='center', verticalalignment='center')
            self.canvas.draw()
            return

        headers = list(data[0].keys())
        time_key = 'time'
        if time_key not in headers:
            self.canvas.axes.text(0.5, 0.5, 'No "time" column found in data.',
                                  horizontalalignment='center', verticalalignment='center')
            self.canvas.draw()
            return

        time_full = [row[time_key] for row in data]
        
        # Use only visible keys
        visible_voltage_keys = [k for k in self.voltage_keys if self.column_visibility.get(k, False)]

        # 1. Plot base lines and store colors
        line_colors = {}
        for key in visible_voltage_keys:
            voltage_values = [row[key] for row in data]
            if len(time_full) == len(voltage_values):
                line, = self.canvas.axes.plot(time_full, voltage_values, label=f'V({key})')
                line_colors[key] = line.get_color()

        # 2. Highlighting logic: plot highlighted segments on top
        is_highlighting = self.time_min is not None or self.time_max is not None or \
                          self.volt_min is not None or self.volt_max is not None

        if is_highlighting:
            for key in visible_voltage_keys:
                current_segment_t = []
                current_segment_v = []

                for row in data:
                    t = row[time_key]
                    v = row[key]

                    # Determine if the point is in range
                    time_in_range = (self.time_min is None or t >= self.time_min) and \
                                    (self.time_max is None or t <= self.time_max)
                    volt_in_range = (self.volt_min is None or v >= self.volt_min) and \
                                    (self.volt_max is None or v <= self.volt_max)

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
                            self.canvas.axes.plot(current_segment_t, current_segment_v,
                                                  color=line_colors[key],
                                                  linewidth=4,
                                                  alpha=0.7,
                                                  solid_capstyle='round')
                            current_segment_t = []
                            current_segment_v = []
                
                if current_segment_t:
                    self.canvas.axes.plot(current_segment_t, current_segment_v,
                                          color=line_colors[key],
                                          linewidth=4,
                                          alpha=0.7,
                                          solid_capstyle='round')

        self.canvas.axes.set_title('Transient Analysis')
        self.canvas.axes.set_xlabel('Time (s)')
        self.canvas.axes.set_ylabel('Voltage (V)')
        self.canvas.axes.legend()
        self.canvas.axes.grid(True)
        self.canvas.figure.tight_layout()
        self.canvas.draw()