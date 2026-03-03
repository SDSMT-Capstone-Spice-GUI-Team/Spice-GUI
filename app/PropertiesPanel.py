from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class PropertiesPanel(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        #Title
        propertiesTitle = QLabel("Properties")
        layout.addWidget(propertiesTitle)

