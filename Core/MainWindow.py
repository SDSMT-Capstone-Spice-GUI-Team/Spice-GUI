import sys
import random
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QApplication, QDockWidget, QMainWindow, QMenu,
    QMenuBar, QSizePolicy, QStatusBar, QWidget)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        #Set Window Title and start Maximized
        self.setWindowTitle("SDM-Spice")
        self.showMaximized()

        #Setup Menubar
        self.__init_menubar()

        #Set PLACEHOLDER button
        button = QtWidgets.QPushButton("Press Me!")

        self.setCentralWidget(button)

    def __init_menubar(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        new_circuit_action = QAction("&New Circuit", self)
        new_circuit_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_circuit_action)
        load_circuit_action = QAction("&Load Circuit", self)
        load_circuit_action.setShortcut("Ctrl+L")
        file_menu.addAction(load_circuit_action)
        save_circuit_action = QAction("&Save Circuit", self)
        save_circuit_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_circuit_action)
        save_circuit_as_action = QAction("&Save Circuit As", self)
        save_circuit_as_action.setShortcut("Ctrl+Shift+S")
        file_menu.addAction(save_circuit_as_action)
        export_circuit_action = QAction("&Export Circuit", self)
        file_menu.addAction(export_circuit_action)
        file_menu.addSeparator()
        quit_action = QAction("&Quit SDM-Spice", self)
        quit_action.setShortcut("Ctrl+Q")
        file_menu.addAction(quit_action)

        edit_menu = menu.addMenu("&Edit")
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        cut_action = QAction("&Cut", self)
        cut_action.setShortcut("Ctrl+X")
        edit_menu.addAction(cut_action)
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut("Ctrl+C")
        edit_menu.addAction(copy_action)
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        edit_menu.addAction(paste_action)
        delete_action = QAction("&Delete", self)
        delete_action.setShortcut("Delete")
        edit_menu.addAction(delete_action)
        edit_menu.addSeparator()
        select_all_action = QAction("&Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        edit_menu.addAction(select_all_action)

        sim_menu = menu.addMenu("&Simulation")
        run_sim_action = QAction("&Run Simulation", self)
        sim_menu.addAction(run_sim_action)
        show_previous_sim_action = QAction("&Show Previous Simulation Results", self)
        sim_menu.addAction(show_previous_sim_action)

        help_menu = menu.addMenu("&Help")
        show_documentation_action = QAction("&Show Documentation", self)
        help_menu.addAction(show_documentation_action)
        about_sdm_spice_action = QAction("&About SDM-Spice", self)
        help_menu.addAction(about_sdm_spice_action)

class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Welcome to SDM-Spice!")

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