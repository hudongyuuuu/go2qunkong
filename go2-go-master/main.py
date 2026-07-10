#!/usr/bin/env python3
# main.py
"""
Unitree GO2AIR Robot Control - Main Entry Point
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow


def setup_high_dpi():
    """Setup high DPI scaling - MUST be called before creating QApplication"""
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def main():
    """Main entry point"""
    # Setup high DPI BEFORE creating QApplication
    setup_high_dpi()

    # Create application
    app = QApplication(sys.argv)

    # Set application info
    app.setApplicationName("Unitree GO2AIR Robot Control")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Unitree")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create and show main window
    try:
        window = MainWindow()
        window.show()
    except Exception as e:
        print(f"Error creating window: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Run event loop
    return app.exec_()


if __name__ == "__main__":
    main()
