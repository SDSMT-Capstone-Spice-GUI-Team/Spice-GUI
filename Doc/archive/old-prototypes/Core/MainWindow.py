import sys
import random
from PySide6 import QtCore, QtWidgets, QtGui

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDM-Spice")
        self.setWindowState(QtCore.Qt.WindowMaximized)

class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.newCircuitButton = QtWidgets.QPushButton("New Circuit")
        self.loadCircuitButton = QtWidgets.QPushButton("Load Circuit")
        self.preferencesButton = QtWidgets.QPushButton("Preferences")
        self.aboutButton = QtWidgets.QPushButton("About SDM-Spice")
        self.text = QtWidgets.QLabel("Welcome to SDM-Spice", alignment=QtCore.Qt.AlignCenter)
        self.image = QtWidgets.QLabel("I'm a picture, shhhhhh")

        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setVerticalSpacing(15)
        self.layout.addWidget(self.text, 0, 1)
        self.layout.addWidget(self.newCircuitButton, 1, 0)
        self.layout.addWidget(self.loadCircuitButton, 2, 0)
        self.layout.addWidget(self.preferencesButton, 3, 0)
        self.layout.addWidget(self.aboutButton, 4, 0)
        self.layout.addWidget(self.image, 2, 2)

        self.resize(800, 600)

        desktopScreen = self.frameGeometry()
        centerPoint = QtWidgets.QApplication.primaryScreen().geometry().center()
        desktopScreen.moveCenter(centerPoint)
        self.move(desktopScreen.topLeft())

    #@QtCore.Slot()
    #def magic(self):
        #self.text.setText(random.choice(self.hello))


def main():
    app = QtWidgets.QApplication([])

    window = MainWindow()
    window.show()

    widget = MyWidget()
    widget.show()

    with open("darkMode.qss", "r") as file:
        _style = file.read()
        app.setStyleSheet(_style)

    sys.exit(app.exec())

main()