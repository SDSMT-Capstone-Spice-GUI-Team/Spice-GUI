"""
Circuit Design GUI Prototype
Python + Qt6 + PySpice

Requirements:
pip install PyQt6 PySpice matplotlib

This prototype implements:
- Component palette with drag-and-drop
- Grid-aligned canvas with A* path finding for wires
- Save/Load (JSON with visual layout)
- SPICE netlist generation
- SPICE simulation
- Results display
"""


import sys
from PyQt6.QtWidgets import (QApplication)
from GUI.circuit_design_gui import CircuitDesignGUI


def main():
    app = QApplication(sys.argv)
    window = CircuitDesignGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
