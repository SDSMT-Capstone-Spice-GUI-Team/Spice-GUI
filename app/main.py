"""
Circuit Design GUI Prototype
Python + Qt6 + PySpice

Requirements:
pip install PyQt6 PySpice matplotlib

This prototype implements:
- Component palette with drag-and-drop
- Grid-aligned canvas with IDA* path finding for wires
- Save/Load (JSON with visual layout)
- SPICE netlist generation
- SPICE simulation
- Results display
"""

import sys

from GUI.main_window import MainWindow
from PyQt6.QtWidgets import QApplication

from app.GUI.main_window import SplashScreen


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    widget = SplashScreen()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
