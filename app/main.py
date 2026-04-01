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


def main():
    # Handle --selftest before importing Qt to allow headless execution.
    if "--selftest" in sys.argv:
        from simulation.selftest import print_selftest, run_selftest

        result = run_selftest()
        print_selftest(result)
        sys.exit(0 if result.passed else 1)

    from GUI.main_window import MainWindow
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
