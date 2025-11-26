import matplotlib
from PyQt6.QtWidgets import QDialog, QVBoxLayout
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
        self.setMinimumSize(800, 600)

        # Create the matplotlib canvas
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)

        # Plot the data
        self.plot_data(data)

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_data(self, data):
        """Plots the transient analysis data from a list of dictionaries."""
        if not data:
            self.canvas.axes.text(0.5, 0.5, 'No transient data to display.',
                                  horizontalalignment='center',
                                  verticalalignment='center')
            return

        headers = list(data[0].keys())
        time_key = None
        if 'time' in headers:
            time_key = 'time'
        
        if not time_key:
            self.canvas.axes.text(0.5, 0.5, 'No "time" column found in data.',
                                  horizontalalignment='center',
                                  verticalalignment='center')
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