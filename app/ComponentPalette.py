from PyQt6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QLineEdit, QVBoxLayout
from PyQt6.QtCore import Qt

class ComponentPalette(QWidget):
    def __init__(self):
        super().__init__()

        #Setting up Palette Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        #Searchbar
        self.__searchbar = QLineEdit()
        self.__searchbar.setPlaceholderText("Search Components:")
        self.__searchbar.setClearButtonEnabled(True)
        layout.addWidget(self.__searchbar)

        #List of Components
        self.__listWidget = QTreeWidget()
        item1 = QTreeWidgetItem(self.__listWidget)
        item2 = QTreeWidgetItem(self.__listWidget)
        item1.setText(0, "Item 1")
        item2.setText(0, "Item 2")
        layout.addWidget(self.__listWidget)
