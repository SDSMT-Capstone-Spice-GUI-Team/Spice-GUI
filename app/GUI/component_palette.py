from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag

# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Waveform Source': {'symbol': 'VW', 'terminals': 2, 'color': '#E91E63'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
    'Op-Amp': {'symbol': 'OA', 'terminals': 5, 'color': '#FFC107'},
}

class ComponentPalette(QListWidget):
    """Component palette with drag support"""
    
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        
        for component_name in COMPONENTS.keys():
            item = QListWidgetItem(component_name)
            self.addItem(item)
    
    def startDrag(self, supportedActions):
        """Start drag operation"""
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)
