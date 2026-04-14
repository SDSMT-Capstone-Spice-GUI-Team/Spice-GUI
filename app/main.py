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

    from GUI.main_window import MainWindow  # , SplashScreen
    from GUI.styles.font_loader import DEFAULT_FONT_FAMILY, load_bundled_fonts
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    load_bundled_fonts()

    # Set default font if user has no saved preference
    from controllers.settings_service import settings
    from services.theme_manager import ThemeManager

    if not settings.get_str("view/font_family", ""):
        ThemeManager().set_font_family(DEFAULT_FONT_FAMILY)

    window = MainWindow()
    window.show()
    # widget = SplashScreen(main_window=window)
    # window.splash_screen = widget
    # widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
